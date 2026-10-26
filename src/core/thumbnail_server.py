import os
import sys
import struct
import threading
import time
from pathlib import Path
from PyQt6.QtGui import QImage
from PyQt6.QtCore import Qt

from src.core.config import CACHE_DIR

IS_WINDOWS = sys.platform == "win32"

RVTP_MAGIC = 0x52565450  # 'RVTP'
RVTP_STATUS_OK = 1
RVTP_STATUS_FAIL = 0
RVTP_FORMAT_BGRA32 = 1

PIPE_NAME = r"\\.\pipe\RawViewThumbnailPipe"

def fnv1a_hash_64(s: str) -> int:
    """Computes 64-bit FNV-1a hash identical to C++ implementation."""
    h = 14695981039346656037
    for ch in s:
        h ^= (ord(ch) & 0xFFFF)
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h

def get_thumb_cache_path(file_path: str, cx: int) -> Path:
    """Returns the persistent disk cache path for a file's thumbnail."""
    mtime = 0
    try:
        stat = os.stat(file_path)
        # Windows FILETIME: 100-nanosecond intervals since Jan 1, 1601
        mtime = int((stat.st_mtime * 10000000) + 116444736000000000)
    except Exception:
        pass

    h = fnv1a_hash_64(file_path)
    # Ensure this matches C++ CSIDL_LOCAL_APPDATA: %LOCALAPPDATA%\RawView\cache\thumbs
    local_app_data = os.environ.get("LOCALAPPDATA") or str(CACHE_DIR.parent)
    thumbs_dir = Path(local_app_data) / "RawView" / "cache" / "thumbs"
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    return thumbs_dir / f"thumb_{h:x}_{mtime:x}_{cx}.bmp"

def render_thumbnail(file_path: str, cx: int) -> QImage | None:
    """Decodes and scales file thumbnail to requested dimension cx."""
    if not os.path.exists(file_path):
        return None

    try:
        from src.core.decoders import DecoderManager
        res = DecoderManager.decode(file_path, max_size=max(cx, 256))
        if not res or res.qimage.isNull() or res.qimage.width() < 2:
            return None

        img = res.qimage
        # Scale smoothly while preserving aspect ratio
        thumb = img.scaled(
            cx, cx,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Convert to ARGB32 (little-endian byte order: B, G, R, A matching Windows DIB)
        argb_img = thumb.convertToFormat(QImage.Format.Format_ARGB32)
        return argb_img
    except Exception as e:
        print(f"[ThumbnailServer] Decode error for {file_path}: {e}")
        return None

def save_thumbnail_bmp(qimg: QImage, out_path: Path) -> bool:
    """Saves QImage as 32-bit ARGB BMP directly compatible with Windows LoadImageW."""
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Save as BMP
        return qimg.save(str(out_path), "BMP")
    except Exception:
        return False

def generate_headless_thumbnail(file_path: str, cx: int, out_bmp_path: str) -> bool:
    """Headless CLI worker invoked if main GUI is closed or restarting."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv[:1])

    thumb = render_thumbnail(file_path, cx)
    if thumb and not thumb.isNull():
        return save_thumbnail_bmp(thumb, Path(out_bmp_path))
    return False

class ThumbnailPipeServer:
    """High-speed Windows Named Pipe Server servicing Windows Explorer thumbnail requests."""
    def __init__(self):
        self.running = False
        self.thread = None

    def start(self):
        if not IS_WINDOWS or self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True, name="RawViewThumbnailServer")
        self.thread.start()
        print(f"[+] RawView Thumbnail Named Pipe Server listening on {PIPE_NAME}")

    def stop(self):
        if not self.running:
            return
        self.running = False
        try:
            import win32file
            h = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            win32file.CloseHandle(h)
        except Exception:
            pass

    def _get_security_attributes(self):
        """Creates a SECURITY_ATTRIBUTES descriptor granting World access and Low Mandatory Level.
        This allows medium-integrity explorer.exe and dllhost.exe to connect even if RawView was
        launched with elevated administrator privileges."""
        try:
            import win32security
            sa = win32security.SECURITY_ATTRIBUTES()
            sa.bInheritHandle = False
            # D:(A;;GA;;;WD) -> Discretionary ACL: Generic All to Everyone (WD)
            # S:(ML;;NW;;;LW) -> Mandatory Label: Low Integrity (LW), No-Write-Up (NW)
            sd = win32security.ConvertStringSecurityDescriptorToSecurityDescriptor(
                "D:(A;;GA;;;WD)S:(ML;;NW;;;LW)",
                win32security.SDDL_REVISION_1
            )
            sa.SECURITY_DESCRIPTOR = sd
            return sa
        except Exception as e:
            print(f"[!] Warning: Failed to create custom pipe security descriptor: {e}")
            return None

    def _run_server(self):
        try:
            import win32pipe
            import win32file
            import pywintypes
        except ImportError:
            print("[!] win32pipe not available. Thumbnail pipe server cannot start.")
            return

        sa = self._get_security_attributes()

        while self.running:
            try:
                # Create Named Pipe Instance
                # PIPE_ACCESS_DUPLEX = 3
                # PIPE_TYPE_MESSAGE (4) | PIPE_READMODE_MESSAGE (2) | PIPE_WAIT (0) = 6
                h_pipe = win32pipe.CreateNamedPipe(
                    PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    1024 * 1024, # 1MB Out buffer
                    64 * 1024,   # 64KB In buffer
                    1000,        # 1s default timeout
                    sa
                )

                # Wait for Explorer client connection
                try:
                    win32pipe.ConnectNamedPipe(h_pipe, None)
                except Exception as ce:
                    # 535 is ERROR_PIPE_CONNECTED: client connected between CreateNamedPipe and ConnectNamedPipe
                    winerror_code = getattr(ce, "winerror", None)
                    if winerror_code != 535:
                        try:
                            win32file.CloseHandle(h_pipe)
                        except Exception:
                            pass
                        continue

                # Handle client in a worker thread to allow concurrent requests
                t = threading.Thread(target=self._handle_client, args=(h_pipe,), daemon=True)
                t.start()

            except Exception as e:
                if self.running:
                    time.sleep(0.01)

    def _handle_client(self, h_pipe):
        try:
            import win32file

            # 1. Read Request Header: magic (4), cx (4), pathCharCount (4) = 12 bytes
            hr, data = win32file.ReadFile(h_pipe, 12)
            if hr != 0 or len(data) < 12:
                win32file.CloseHandle(h_pipe)
                return

            magic, cx, path_char_count = struct.unpack("<III", data)
            if magic != RVTP_MAGIC or path_char_count == 0 or path_char_count > 4096:
                win32file.CloseHandle(h_pipe)
                return

            # 2. Read Path Characters (wchar_t = 2 bytes per char)
            path_bytes_len = path_char_count * 2
            hr, path_bytes = win32file.ReadFile(h_pipe, path_bytes_len)
            if hr != 0 or len(path_bytes) < path_bytes_len:
                win32file.CloseHandle(h_pipe)
                return

            file_path = path_bytes.decode("utf-16-le", errors="ignore")

            # 3. Decode & Render
            thumb = render_thumbnail(file_path, cx)
            if thumb and not thumb.isNull():
                w = thumb.width()
                h = thumb.height()
                # constBits pointer to BGRA pixels
                ptr = thumb.constBits()
                ptr.setsize(thumb.sizeInBytes())
                raw_bytes = bytes(ptr)

                # Also save to disk cache asynchronously
                cache_path = get_thumb_cache_path(file_path, cx)
                save_thumbnail_bmp(thumb, cache_path)

                # 4. Write Response: magic (4), status (4), width (4), height (4), format (4), dataSize (4) = 24 bytes
                resp_header = struct.pack(
                    "<IIIIII",
                    RVTP_MAGIC,
                    RVTP_STATUS_OK,
                    w,
                    h,
                    RVTP_FORMAT_BGRA32,
                    len(raw_bytes)
                )
                win32file.WriteFile(h_pipe, resp_header)
                win32file.WriteFile(h_pipe, raw_bytes)
            else:
                # Failed response
                resp_header = struct.pack(
                    "<IIIIII",
                    RVTP_MAGIC,
                    RVTP_STATUS_FAIL,
                    0, 0, 0, 0
                )
                win32file.WriteFile(h_pipe, resp_header)

            win32file.FlushFileBuffers(h_pipe)
        except Exception:
            pass
        finally:
            try:
                import win32pipe
                win32pipe.DisconnectNamedPipe(h_pipe)
                win32file.CloseHandle(h_pipe)
            except Exception:
                pass

def invalidate_file_thumbnail_cache(file_path: str):
    """Deletes all cached BMP thumbnail resolutions for a specific file."""
    try:
        h = fnv1a_hash_64(file_path)
        local_app_data = os.environ.get("LOCALAPPDATA") or str(CACHE_DIR.parent)
        thumbs_dir = Path(local_app_data) / "RawView" / "cache" / "thumbs"
        if thumbs_dir.exists():
            prefix = f"thumb_{h:x}_"
            for f in thumbs_dir.glob(f"{prefix}*.bmp"):
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        print(f"[ThumbnailServer] Cache invalidation error for {file_path}: {e}")

def refresh_file_thumbnail(file_path: str) -> bool:
    """Refreshes and notifies Windows Shell to re-render the thumbnail for a specific file."""
    if not os.path.exists(file_path):
        return False

    # 1. Clear cached thumbnails for this file
    invalidate_file_thumbnail_cache(file_path)

    # 2. Pre-generate standard 256px thumbnail
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv[:1])

        thumb = render_thumbnail(file_path, 256)
        if thumb and not thumb.isNull():
            cache_path = get_thumb_cache_path(file_path, 256)
            save_thumbnail_bmp(thumb, cache_path)
    except Exception as e:
        print(f"[ThumbnailServer] Re-rendering error for {file_path}: {e}")

    # 3. Notify Windows Shell to update this item
    if IS_WINDOWS:
        try:
            import ctypes
            w_path = ctypes.c_wchar_p(str(Path(file_path).resolve()))
            ctypes.windll.shell32.SHChangeNotify(0x00002000, 0x0005, w_path, None) # SHCNE_UPDATEITEM
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)   # SHCNE_ASSOCCHANGED
        except Exception:
            pass

    return True

def refresh_folder_thumbnails(folder_path: str) -> int:
    """Invalidates and triggers shell refresh for all supported files in a folder."""
    if not os.path.isdir(folder_path):
        return 0

    from src.core.config import SUPPORTED_EXTENSIONS
    valid_exts = set(SUPPORTED_EXTENSIONS.keys())

    refreshed_count = 0
    try:
        for entry in os.listdir(folder_path):
            full_p = os.path.join(folder_path, entry)
            if os.path.isfile(full_p):
                ext = Path(full_p).suffix.lower()
                if ext in valid_exts:
                    invalidate_file_thumbnail_cache(full_p)
                    refreshed_count += 1
    except Exception as e:
        print(f"[ThumbnailServer] Folder refresh error for {folder_path}: {e}")

    # Notify Windows Explorer of the updated directory
    if IS_WINDOWS:
        try:
            import ctypes
            w_dir = ctypes.c_wchar_p(str(Path(folder_path).resolve()))
            ctypes.windll.shell32.SHChangeNotify(0x00001000, 0x0005, w_dir, None) # SHCNE_UPDATEDIR
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)   # SHCNE_ASSOCCHANGED
        except Exception:
            pass

    return refreshed_count
