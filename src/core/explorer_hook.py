import os
import sys
import re
import urllib.parse
from pathlib import Path
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import pythoncom
import win32com.client
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QCursor
import uiautomation as auto
from .config import SUPPORTED_EXTENSIONS

def normalize_str(s: str) -> str:
    """Strips whitespace, underscores, hyphens, and dots for fuzzy matching across line-wrapped labels."""
    return re.sub(r'[\s_\-\.]+', '', s.lower())

def parse_shell_url(url: str) -> str:
    """Parses Explorer LocationURL into a clean local path, UNC network path, or FTP URL."""
    if not url:
        return ""
    if url.startswith("ftp://") or url.startswith("ftps://"):
        return url
    if url.startswith("file://"):
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        if parsed.netloc:
            # UNC path: file://server/share
            return f"\\\\{parsed.netloc}{path}".replace("/", "\\")
        else:
            # Local path: file:///C:/path
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]
            return path.replace("/", "\\")
    return url

def detect_extensions_from_type_text(type_text: str) -> list[str]:
    """Infers potential file extensions from Windows Explorer Type column or tooltip text."""
    if not type_text:
        return []
    t = type_text.lower()
    
    # PDF
    if "pdf" in t or "portable document" in t or "acrobat" in t:
        return [".pdf"]
    # PostScript / EPS
    if "postscript" in t or "encapsulated" in t or "eps" in t:
        return [".eps"]
    # Photoshop
    if "photoshop" in t or "psd" in t or "psb" in t:
        return [".psd", ".psb"]
    # Illustrator
    if "illustrator" in t or "ai artwork" in t:
        return [".ai", ".eps"]
    # SVG
    if "scalable vector" in t or "svg" in t:
        return [".svg", ".svgz"]
    # TIFF
    if "tiff" in t or "tif" in t:
        return [".tif", ".tiff"]
    # Camera RAW Formats
    if "digital negative" in t or "dng" in t:
        return [".dng"]
    if "canon" in t or "cr2" in t or "cr3" in t or "crw" in t:
        return [".cr2", ".cr3", ".crw"]
    if "nikon" in t or "nef" in t or "nrw" in t:
        return [".nef", ".nrw"]
    if "sony" in t or "arw" in t or "srf" in t or "sr2" in t:
        return [".arw", ".srf", ".sr2"]
    if "fujifilm" in t or "raf" in t:
        return [".raf"]
    if "olympus" in t or "orf" in t:
        return [".orf", ".ori"]
    if "lumix" in t or "panasonic" in t or "rw2" in t:
        return [".rw2"]
    if "camera raw" in t or "raw image" in t:
        return [".dng", ".raw", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"]

    # Video Formats
    if "mp4" in t or "mpeg-4" in t:
        return [".mp4", ".m4v"]
    if "mkv" in t or "matroska" in t:
        return [".mkv"]
    if "quicktime" in t or "mov" in t:
        return [".mov"]
    if "avi" in t or "audio video interleave" in t:
        return [".avi"]
    if "windows media" in t or "wmv" in t:
        return [".wmv"]
    if "webm" in t:
        return [".webm"]
    if "flash video" in t or "flv" in t:
        return [".flv"]
    if "transport stream" in t or "ts video" in t:
        return [".ts"]
    if "3gp" in t or "3gpp" in t:
        return [".3gp"]
    if "video" in t or "movie" in t or "media file" in t or "clip" in t:
        return [".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv", ".flv", ".ts", ".m4v", ".3gp"]
        
    return []

def parse_size_in_kb(size_text: str) -> float | None:
    """Parses size strings like '856 KB', '2,915 KB', '1.69 MB' into numeric KB."""
    if not size_text:
        return None
    clean = size_text.replace(",", "").strip()
    m = re.search(r"([\d\.]+)\s*(kb|mb|gb|bytes|b)?", clean, re.IGNORECASE)
    if not m:
        return None
    try:
        val = float(m.group(1))
        unit = (m.group(2) or "kb").lower()
        if unit == "kb":
            return val
        elif unit == "mb":
            return val * 1024.0
        elif unit == "gb":
            return val * 1024.0 * 1024.0
        elif unit in ("bytes", "b"):
            return val / 1024.0
        return val
    except Exception:
        return None

class ExplorerHoverMonitor(QObject):
    """
    Zero-lag, highly resilient file hover detector.
    Works seamlessly across Windows 11 (with XAML tabs), Windows 10,
    Explorer List/Grid/Icon/Details views, Desktop, Network Shares (UNC), Local FTP servers, and File Dialogs.
    """
    file_hovered = pyqtSignal(str, int, int) # (file_path, screen_x, screen_y)
    hover_cleared = pyqtSignal()
    space_pin_requested = pyqtSignal()
    escape_requested = pyqtSignal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.enabled = config.get("enabled", True)
        self.hover_delay_ms = config.get("hover_delay_ms", 120)
        self.supported_exts = [ext.lower() for ext in config.get("supported_formats", SUPPORTED_EXTENSIONS.keys())]
        self.supported_exts_set = set(self.supported_exts)
        
        self.last_pos = QPoint(-1, -1)
        self.settle_start_time = 0
        self.is_hover_active = False
        self.preview_is_visible = False
        self.preview_is_pinned = False
        self.active_file_path = ""
        self.active_rect = None
        self.space_key_down = False
        self.esc_key_down = False
        
        # Desktop candidate folders
        self.desktop_paths = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/OneDrive/Desktop"),
            "C:\\Users\\Public\\Desktop"
        ]

        # Timer ticks every 35ms for instant settle detection
        self.timer = QTimer(self)
        self.timer.setInterval(35)
        self.timer.timeout.connect(self._on_tick)

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self._clear_hover()

    def update_config(self, config: dict):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.hover_delay_ms = config.get("hover_delay_ms", 120)
        self.supported_exts = [ext.lower() for ext in config.get("supported_formats", SUPPORTED_EXTENSIONS.keys())]
        self.supported_exts_set = set(self.supported_exts)

    def set_preview_visible(self, visible: bool):
        self.preview_is_visible = visible
        if not visible:
            self.space_key_down = False
            self.esc_key_down = False

    def set_preview_pinned(self, pinned: bool):
        self.preview_is_pinned = pinned

    def _on_tick(self):
        # Global Key Interceptions when preview is active or visible or pinned
        if self.is_hover_active or self.preview_is_visible or self.preview_is_pinned:
            # Spacebar detection (0x20 = VK_SPACE)
            space_state = bool(win32api.GetAsyncKeyState(win32con.VK_SPACE) & 0x8000)
            if space_state and not self.space_key_down:
                self.space_key_down = True
                self.space_pin_requested.emit()
            elif not space_state:
                self.space_key_down = False

            # Escape detection (0x1B = VK_ESCAPE)
            esc_state = bool(win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000)
            if esc_state and not self.esc_key_down:
                self.esc_key_down = True
                self.escape_requested.emit()
                self._clear_hover()
                return
            elif not esc_state:
                self.esc_key_down = False

        if not self.enabled:
            if self.is_hover_active:
                self._clear_hover()
            return

        cur_pos = QCursor.pos()
        x, y = cur_pos.x(), cur_pos.y()
        now = ctypes.windll.kernel32.GetTickCount()

        dx = abs(x - self.last_pos.x())
        dy = abs(y - self.last_pos.y())

        if dx > 6 or dy > 6:
            # Cursor moved significantly
            self.last_pos = cur_pos
            self.settle_start_time = now

            if self.preview_is_pinned:
                # Keep preview active when pinned
                return

            if self.is_hover_active and self.active_rect:
                left, top, right, bottom = self.active_rect
                # Tight vertical buffer (4px) so moving between adjacent rows triggers instant hover switch
                if x < left - 16 or x > right + 16 or y < top - 4 or y > bottom + 4:
                    self._clear_hover()
            return

        # Cursor is settled/dwelling
        dwell_ms = now - self.settle_start_time
        if dwell_ms >= self.hover_delay_ms:
            self._resolve_and_trigger_hover(x, y)

    def _clear_hover(self):
        self.is_hover_active = False
        self.active_file_path = ""
        self.active_rect = None
        self.hover_cleared.emit()

    def _resolve_and_trigger_hover(self, x: int, y: int):
        file_path, bounding_rect = self._resolve_file_from_point(x, y)
        if file_path:
            is_valid = file_path.startswith("ftp://") or file_path.startswith("ftps://") or os.path.isfile(file_path)
            if is_valid:
                ext = Path(file_path).suffix.lower()
                if ext in self.supported_exts_set:
                    # Emit if path changed OR if bounding rect moved to a new row/item
                    rect_changed = False
                    if self.active_rect and bounding_rect:
                        # Check if row vertically changed by more than 10px
                        if abs(self.active_rect[1] - bounding_rect[1]) > 8:
                            rect_changed = True

                    if self.active_file_path != file_path or rect_changed:
                        self.active_file_path = file_path
                        self.active_rect = bounding_rect
                        self.is_hover_active = True
                        self.file_hovered.emit(file_path, x, y)
                    return
        
        # If not hovering over a valid file and we were active
        if self.is_hover_active and not self.preview_is_pinned:
            if self.active_rect:
                left, top, right, bottom = self.active_rect
                if x < left - 16 or x > right + 16 or y < top - 4 or y > bottom + 4:
                    self._clear_hover()
            else:
                self._clear_hover()

    def _get_active_explorer_context(self, x: int, y: int, expected_folder_name: str = "") -> tuple[str, str, list[str]]:
        """
        Queries the exact Shell window/tab under the mouse cursor.
        Matches the active tab by HWND and folder name for Windows 11 tabbed Explorer.
        Returns (active_folder_path, focused_item_path, selected_item_paths).
        """
        active_folder = ""
        focused_path = ""
        selected_paths = []
        try:
            hwnd = win32gui.WindowFromPoint((x, y))
            if not hwnd:
                return "", "", []
            
            root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
            
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("Shell.Application")
            
            matching_windows = []
            for w in shell.Windows():
                try:
                    w_hwnd = getattr(w, "HWND", 0)
                    if w_hwnd == root_hwnd or w_hwnd == hwnd:
                        matching_windows.append(w)
                except Exception:
                    continue

            # If multiple tabs match the same root window, find the one matching expected_folder_name
            target_w = None
            if matching_windows:
                if len(matching_windows) == 1 or not expected_folder_name:
                    target_w = matching_windows[0]
                else:
                    clean_expected = expected_folder_name.strip().lower()
                    for w in matching_windows:
                        loc_name = str(getattr(w, "LocationName", "")).strip().lower()
                        loc_url = parse_shell_url(str(getattr(w, "LocationURL", ""))).lower()
                        if loc_name == clean_expected or loc_url.endswith(clean_expected) or clean_expected in loc_url:
                            target_w = w
                            break
                    if not target_w:
                        target_w = matching_windows[0]

            if target_w:
                url = str(getattr(target_w, "LocationURL", ""))
                doc_path = ""
                if hasattr(target_w, "Document") and hasattr(target_w.Document, "Folder"):
                    doc_path = str(target_w.Document.Folder.Self.Path)
                
                active_folder = parse_shell_url(url) or parse_shell_url(doc_path)

                # Check Focused / Selected Items
                if hasattr(target_w, "Document"):
                    doc = target_w.Document
                    try:
                        focused = getattr(doc, "FocusedItem", None)
                        if focused and hasattr(focused, "Path"):
                            focused_path = str(focused.Path)
                    except Exception:
                        pass
                    
                    try:
                        sel = doc.SelectedItems()
                        if sel:
                            for i in range(min(sel.Count, 10)):
                                s_item = sel.Item(i)
                                if hasattr(s_item, "Path"):
                                    selected_paths.append(str(s_item.Path))
                    except Exception:
                        pass

        except Exception:
            pass
        return active_folder, focused_path, selected_paths

    def _get_candidate_folders(self, priority_folder: str = "") -> list:
        """Retrieves all active folder paths and FTP locations from Explorer windows and Desktop."""
        folders = []
        if priority_folder and (priority_folder.startswith("ftp://") or priority_folder.startswith("ftps://") or os.path.isdir(priority_folder)):
            folders.append(priority_folder)

        # Only expand other folders if priority_folder is not available
        if not folders:
            try:
                pythoncom.CoInitialize()
                shell = win32com.client.Dispatch("Shell.Application")
                for w in shell.Windows():
                    try:
                        url = str(getattr(w, "LocationURL", ""))
                        doc_path = ""
                        if hasattr(w, "Document") and hasattr(w.Document, "Folder"):
                            doc_path = str(w.Document.Folder.Self.Path)
                        
                        parsed = parse_shell_url(url)
                        if parsed and (parsed.startswith("ftp://") or parsed.startswith("ftps://") or os.path.isdir(parsed)) and parsed not in folders:
                            folders.append(parsed)

                        if doc_path:
                            parsed_doc = parse_shell_url(doc_path)
                            if (parsed_doc.startswith("ftp://") or parsed_doc.startswith("ftps://") or os.path.isdir(parsed_doc)) and parsed_doc not in folders:
                                folders.append(parsed_doc)
                    except Exception:
                        continue
            except Exception:
                pass

        for dp in self.desktop_paths:
            if dp not in folders and os.path.isdir(dp):
                folders.append(dp)

        return folders

    def _resolve_file_from_point(self, x: int, y: int):
        try:
            elem = auto.ControlFromPoint(x, y)
            if not elem:
                return None, None

            bounding_box = None
            try:
                r = elem.BoundingRectangle
                if r:
                    bounding_box = (r.left, r.top, r.right, r.bottom)
            except Exception:
                pass

            # Find parent list container name (e.g. "polo", "Pos_Dev", "Design", etc.)
            folder_hint = ""
            p = row_control.GetParentControl()
            p_depth = 0
            while p and p_depth < 6:
                if p.Name and p.ControlTypeName in ("ListControl", "TreeControl", "PaneControl", "WindowControl"):
                    folder_hint = p.Name
                    break
                p = p.GetParentControl()
                p_depth += 1

            # 1. Query active Explorer COM context under cursor for this specific tab
            priority_folder, focused_path, selected_paths = self._get_active_explorer_context(x, y, expected_folder_name=folder_hint)

            # Extract Name & attributes strictly from the item row and its children
            names_to_try = []
            type_hints = []
            size_hints = []

            if row_control.Name:
                names_to_try.append(row_control.Name)
            row_help = getattr(row_control, 'HelpText', '')
            if row_help:
                names_to_try.append(row_help)
                type_hints.append(row_help)
                size_hints.append(row_help)
            row_item_type = getattr(row_control, 'ItemType', '')
            if row_item_type:
                type_hints.append(row_item_type)

            # Inspect all child columns of this specific item row (Name, Type, Size)
            try:
                for child in row_control.GetChildren():
                    c_name = child.Name
                    c_auto_id = getattr(child, "AutomationId", "")
                    c_help = getattr(child, "HelpText", "")
                    c_type = getattr(child, "ItemType", "")

                    if c_name:
                        names_to_try.append(c_name)
                        # Check if column is Type
                        if any(k in c_name.lower() for k in ("document", "image", "file", "format", "postscript", "pdf", "artwork", "tiff", "raw")):
                            type_hints.append(c_name)
                        # Check if column is Size
                        if any(k in c_name.lower() for k in ("kb", "mb", "gb", "bytes", "b")) and re.search(r"\d", c_name):
                            size_hints.append(c_name)
                    
                    if c_auto_id == "System.ItemTypeText" and c_name:
                        type_hints.append(c_name)
                    elif c_auto_id == "System.Size" and c_name:
                        size_hints.append(c_name)

                    if c_help:
                        type_hints.append(c_help)
                        size_hints.append(c_help)
                    if c_type:
                        type_hints.append(c_type)
            except Exception:
                pass

            if not names_to_try:
                return None, None

            # 3. Match against COM focused/selected items ONLY if they belong to priority_folder
            all_com_cands = ([focused_path] if focused_path else []) + selected_paths
            for com_path in all_com_cands:
                if com_path and os.path.isfile(com_path):
                    if priority_folder and not os.path.dirname(com_path).lower().startswith(priority_folder.lower()):
                        continue
                    com_ext = Path(com_path).suffix.lower()
                    if com_ext in self.supported_exts_set:
                        com_stem = Path(com_path).stem.lower()
                        com_name = Path(com_path).name.lower()
                        for raw_name in names_to_try:
                            clean_n = raw_name.strip().lower()
                            if clean_n in (com_stem, com_name) or normalize_str(clean_n) in (normalize_str(com_stem), normalize_str(com_name)):
                                return com_path, bounding_box

            # 4. Resolve candidate folders
            candidate_folders = self._get_candidate_folders(priority_folder)

            # Determine target extensions from Type hints
            target_exts = []
            for th in type_hints:
                inferred = detect_extensions_from_type_text(th)
                for e in inferred:
                    if e in self.supported_exts_set and e not in target_exts:
                        target_exts.append(e)

            # Build search order: type-matched extensions FIRST, then others
            search_ext_order = target_exts + [e for e in self.supported_exts if e not in target_exts]

            # Parse size hint if available
            parsed_kb = None
            for sh in size_hints:
                val = parse_size_in_kb(sh)
                if val is not None:
                    parsed_kb = val
                    break

            # 5. Collect matching candidate files across folders
            candidates = []
            for raw_name in names_to_try:
                clean_name = " ".join(raw_name.split())
                if not clean_name:
                    continue

                # Direct absolute path check
                if os.path.isabs(clean_name) and os.path.isfile(clean_name):
                    if Path(clean_name).suffix.lower() in self.supported_exts_set:
                        return clean_name, bounding_box

                norm_name = normalize_str(clean_name)

                for folder in candidate_folders:
                    # FTP candidate check
                    if folder.startswith("ftp://") or folder.startswith("ftps://"):
                        ext = Path(clean_name).suffix.lower()
                        if ext in self.supported_exts_set:
                            return f"{folder.rstrip('/')}/{clean_name}", bounding_box
                        for e in search_ext_order:
                            return f"{folder.rstrip('/')}/{clean_name}{e}", bounding_box
                        continue

                    if not os.path.isdir(folder):
                        continue

                    # If name already has a supported extension
                    ext = Path(clean_name).suffix.lower()
                    if ext in self.supported_exts_set:
                        direct_p = os.path.join(folder, clean_name)
                        if os.path.isfile(direct_p):
                            return direct_p, bounding_box

                    # Try extensions in search_ext_order
                    for e in search_ext_order:
                        cand = os.path.join(folder, f"{clean_name}{e}")
                        if os.path.isfile(cand) and cand not in candidates:
                            candidates.append(cand)

                    # Direct join without extension (e.g. if clean_name contains extension)
                    direct = os.path.join(folder, clean_name)
                    if os.path.isfile(direct) and Path(direct).suffix.lower() in self.supported_exts_set and direct not in candidates:
                        candidates.append(direct)

                    # Normalized match against directory files
                    try:
                        for f in os.listdir(folder):
                            base, f_ext = os.path.splitext(f)
                            if f_ext.lower() in self.supported_exts_set:
                                if normalize_str(base) == norm_name or normalize_str(f) == norm_name:
                                    f_cand = os.path.join(folder, f)
                                    if f_cand not in candidates:
                                        candidates.append(f_cand)
                    except Exception:
                        continue

            if not candidates:
                return None, None

            # If only 1 candidate found, return immediately
            if len(candidates) == 1:
                return candidates[0], bounding_box

            # Disambiguation with Type hints
            if target_exts:
                for c in candidates:
                    if Path(c).suffix.lower() in target_exts:
                        if parsed_kb is not None:
                            try:
                                actual_kb = os.path.getsize(c) / 1024.0
                                if abs(actual_kb - parsed_kb) / max(parsed_kb, 1.0) < 0.25 or abs(actual_kb - parsed_kb) < 120:
                                    return c, bounding_box
                            except Exception:
                                pass
                        return c, bounding_box

            # Disambiguation with Size hint
            if parsed_kb is not None:
                best_cand = None
                best_diff = float('inf')
                for c in candidates:
                    try:
                        actual_kb = os.path.getsize(c) / 1024.0
                        diff = abs(actual_kb - parsed_kb)
                        if diff < best_diff:
                            best_diff = diff
                            best_cand = c
                    except Exception:
                        continue
                if best_cand and best_diff < max(parsed_kb * 0.35, 200):
                    return best_cand, bounding_box

            return candidates[0], bounding_box

        except Exception:
            pass

        return None, None

