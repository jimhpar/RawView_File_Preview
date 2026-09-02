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
    """Strips whitespace, underscores, and hyphens for fuzzy matching across line-wrapped labels."""
    return re.sub(r'[\s_\-]+', '', s.lower())

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

class ExplorerHoverMonitor(QObject):
    """
    Zero-lag, highly resilient file hover detector.
    Works seamlessly across Windows 11 (with XAML tabs), Windows 10,
    Explorer List/Grid/Icon views, Desktop, Network Shares (UNC), Local FTP servers, and File Dialogs.
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
        self.supported_exts = set(ext.lower() for ext in config.get("supported_formats", SUPPORTED_EXTENSIONS.keys()))
        
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
        self.supported_exts = set(ext.lower() for ext in config.get("supported_formats", SUPPORTED_EXTENSIONS.keys()))

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

        if dx > 8 or dy > 8:
            # Cursor moved significantly
            self.last_pos = cur_pos
            self.settle_start_time = now

            if self.preview_is_pinned:
                # Keep preview active when pinned
                return

            if self.is_hover_active and self.active_rect:
                left, top, right, bottom = self.active_rect
                # Allow a comfortable buffer around the hovered item
                if x < left - 30 or x > right + 30 or y < top - 30 or y > bottom + 30:
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
                if ext in self.supported_exts:
                    if self.active_file_path != file_path:
                        self.active_file_path = file_path
                        self.active_rect = bounding_rect
                        self.is_hover_active = True
                        self.file_hovered.emit(file_path, x, y)
                    return
        
        # If not hovering over a valid file and we were active
        if self.is_hover_active and not self.active_rect and not self.preview_is_pinned:
            self._clear_hover()

    def _get_candidate_folders(self) -> list:
        """Retrieves all active folder paths and FTP locations from Explorer windows and Desktop."""
        folders = list(self.desktop_paths)
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
                    if parsed:
                        if (parsed.startswith("ftp://") or parsed.startswith("ftps://") or os.path.isdir(parsed)) and parsed not in folders:
                            folders.insert(0, parsed)

                    if doc_path:
                        parsed_doc = parse_shell_url(doc_path)
                        if (parsed_doc.startswith("ftp://") or parsed_doc.startswith("ftps://") or os.path.isdir(parsed_doc)) and parsed_doc not in folders:
                            folders.insert(0, parsed_doc)
                except Exception:
                    continue
        except Exception:
            pass
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

            # Extract names from element and ancestors
            names_to_try = []
            curr = elem
            depth = 0
            while curr and depth < 6:
                name = curr.Name
                if name:
                    names_to_try.append(name)
                # Check help text / tooltip (e.g. "Type: PSD File")
                help_txt = getattr(curr, 'HelpText', '')
                if help_txt:
                    names_to_try.append(help_txt)
                if curr.ControlTypeName in ("WindowControl", "DesktopControl"):
                    break
                curr = curr.GetParentControl()
                depth += 1

            if not names_to_try:
                return None, None

            candidate_folders = self._get_candidate_folders()

            # Attempt matching each extracted name candidate
            for raw_name in names_to_try:
                # Handle line wraps and whitespace
                clean_name = " ".join(raw_name.split())
                if not clean_name:
                    continue

                # 1. Direct absolute path check
                if os.path.isabs(clean_name) and os.path.isfile(clean_name):
                    return clean_name, bounding_box

                norm_name = normalize_str(clean_name)

                # Search through candidate folders
                for folder in candidate_folders:
                    # FTP folder candidate
                    if folder.startswith("ftp://") or folder.startswith("ftps://"):
                        ext = Path(clean_name).suffix.lower()
                        if ext in self.supported_exts:
                            ftp_cand = f"{folder.rstrip('/')}/{clean_name}"
                            return ftp_cand, bounding_box
                        for e in self.supported_exts:
                            ftp_cand = f"{folder.rstrip('/')}/{clean_name}{e}"
                            return ftp_cand, bounding_box
                        continue

                    if not os.path.isdir(folder):
                        continue

                    # Direct join with extension
                    for ext in self.supported_exts:
                        cand = os.path.join(folder, f"{clean_name}{ext}")
                        if os.path.isfile(cand):
                            return cand, bounding_box

                    # Direct join
                    direct = os.path.join(folder, clean_name)
                    if os.path.isfile(direct):
                        return direct, bounding_box

                    # Fuzzy normalized match against directory files
                    try:
                        for f in os.listdir(folder):
                            base, ext = os.path.splitext(f)
                            if ext.lower() in self.supported_exts:
                                if normalize_str(base) == norm_name or normalize_str(f) == norm_name:
                                    return os.path.join(folder, f), bounding_box
                    except Exception:
                        continue

        except Exception:
            pass

        return None, None
