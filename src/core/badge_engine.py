import os
import sys
import re
import time
from pathlib import Path
from dataclasses import dataclass
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg

@dataclass
class BadgeStyle:
    label: str
    bg_color: QColor
    text_color: QColor
    border_color: QColor

# Comprehensive format badge definitions for all RawView decoders
BADGE_CATALOG: dict[str, BadgeStyle] = {
    # Adobe Design & Motion
    ".psd":   BadgeStyle("Ps",  QColor(0, 30, 54),     QColor(49, 168, 255), QColor(49, 168, 255, 180)),
    ".psb":   BadgeStyle("Ps",  QColor(0, 30, 54),     QColor(49, 168, 255), QColor(49, 168, 255, 180)),
    ".ai":    BadgeStyle("Ai",  QColor(51, 0, 0),      QColor(255, 154, 0),  QColor(255, 154, 0, 180)),
    ".eps":   BadgeStyle("EPS", QColor(46, 8, 84),     QColor(234, 56, 255), QColor(234, 56, 255, 180)),
    ".aep":   BadgeStyle("Ae",  QColor(0, 0, 91),      QColor(153, 153, 255),QColor(153, 153, 255, 180)),
    ".aet":   BadgeStyle("Ae",  QColor(0, 0, 91),      QColor(153, 153, 255),QColor(153, 153, 255, 180)),
    ".aepx":  BadgeStyle("Ae",  QColor(0, 0, 91),      QColor(153, 153, 255),QColor(153, 153, 255, 180)),
    ".prproj":BadgeStyle("Pr",  QColor(51, 0, 51),     QColor(234, 82, 151), QColor(234, 82, 151, 180)),
    ".prset": BadgeStyle("Pr",  QColor(51, 0, 51),     QColor(234, 82, 151), QColor(234, 82, 151, 180)),

    # PDF & Documents
    ".pdf":   BadgeStyle("PDF", QColor(211, 47, 47),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".docx":  BadgeStyle("DOC", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".doc":   BadgeStyle("DOC", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".docm":  BadgeStyle("DOC", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".dotx":  BadgeStyle("DOC", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".dot":   BadgeStyle("DOC", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".rtf":   BadgeStyle("RTF", QColor(24, 90, 189),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # Spreadsheets
    ".xlsx":  BadgeStyle("XLS", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".xls":   BadgeStyle("XLS", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".xlsm":  BadgeStyle("XLS", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".xlsb":  BadgeStyle("XLS", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".xltx":  BadgeStyle("XLS", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".csv":   BadgeStyle("CSV", QColor(16, 124, 65),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # Presentations
    ".pptx":  BadgeStyle("PPT", QColor(196, 62, 28),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".ppt":   BadgeStyle("PPT", QColor(196, 62, 28),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".pptm":  BadgeStyle("PPT", QColor(196, 62, 28),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".ppsx":  BadgeStyle("PPT", QColor(196, 62, 28),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".potx":  BadgeStyle("PPT", QColor(196, 62, 28),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # Vectors
    ".svg":   BadgeStyle("SVG", QColor(255, 153, 0),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".svgz":  BadgeStyle("SVG", QColor(255, 153, 0),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # Camera RAW
    ".cr2":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".cr3":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".crw":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".nef":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".nrw":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".arw":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".srf":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".sr2":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".raf":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".orf":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".ori":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".rw2":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".pef":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".ptx":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".3fr":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".fff":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".iiq":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".raw":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".x3f":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),
    ".dng":   BadgeStyle("RAW", QColor(30, 41, 59),    QColor(245, 158, 11), QColor(245, 158, 11, 180)),

    # Archives
    ".zip":   BadgeStyle("ZIP", QColor(217, 119, 6),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".rar":   BadgeStyle("RAR", QColor(192, 38, 211),  QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".7z":    BadgeStyle("7Z",  QColor(6, 182, 212),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".tar":   BadgeStyle("TAR", QColor(71, 85, 105),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".gz":    BadgeStyle("GZ",  QColor(71, 85, 105),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".tgz":   BadgeStyle("TGZ", QColor(71, 85, 105),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".bz2":   BadgeStyle("BZ2", QColor(71, 85, 105),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # Video Formats
    ".mp4":   BadgeStyle("MP4", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".mov":   BadgeStyle("MOV", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".mkv":   BadgeStyle("MKV", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".avi":   BadgeStyle("AVI", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".wmv":   BadgeStyle("WMV", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".webm":  BadgeStyle("WEBM",QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".flv":   BadgeStyle("FLV", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".m4v":   BadgeStyle("M4V", QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".ts":    BadgeStyle("TS",  QColor(37, 99, 235),   QColor(255, 255, 255),QColor(255, 255, 255, 180)),

    # TIFF
    ".tif":   BadgeStyle("TIF", QColor(13, 148, 136),  QColor(255, 255, 255),QColor(255, 255, 255, 180)),
    ".tiff":  BadgeStyle("TIF", QColor(13, 148, 136),  QColor(255, 255, 255),QColor(255, 255, 255, 180)),
}

# In-memory fast cache for native software checks (<0.001ms)
_NATIVE_APP_CACHE: dict[str, bool] = {}
_LAST_SHOW_OVERLAY_CHECK: float = 0.0
_SHOW_OVERLAY_CACHED_VAL: bool = False

def is_show_type_overlay_enabled() -> bool:
    """Checks whether Windows Explorer ShowTypeOverlay (Display file icon on thumbnails) is active."""
    global _LAST_SHOW_OVERLAY_CHECK, _SHOW_OVERLAY_CACHED_VAL
    if not IS_WINDOWS:
        return False

    now = time.time()
    if now - _LAST_SHOW_OVERLAY_CHECK < 5.0:
        return _SHOW_OVERLAY_CACHED_VAL

    _LAST_SHOW_OVERLAY_CHECK = now
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            val, _ = winreg.QueryValueEx(k, "ShowTypeOverlay")
            _SHOW_OVERLAY_CACHED_VAL = (val == 1)
            return _SHOW_OVERLAY_CACHED_VAL
    except Exception:
        _SHOW_OVERLAY_CACHED_VAL = False
        return False

def is_native_software_installed(ext: str) -> bool:
    """
    Checks whether dedicated external software (Photoshop, Illustrator, Word, Excel, WinRAR, etc.)
    is installed and associated with this extension.
    """
    if not IS_WINDOWS:
        return False

    ext_lower = ext.lower()
    if ext_lower in _NATIVE_APP_CACHE:
        return _NATIVE_APP_CACHE[ext_lower]

    prog = None
    # 1. Check UserChoice
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\{ext_lower}\\UserChoice") as k:
            prog, _ = winreg.QueryValueEx(k, "ProgId")
    except Exception:
        pass

    # 2. Check HKCR extension default
    if not prog:
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ext_lower) as k:
                prog, _ = winreg.QueryValueEx(k, "")
        except Exception:
            pass

    if not prog or not str(prog).strip():
        _NATIVE_APP_CACHE[ext_lower] = False
        return False

    # 3. Check if ProgID points to an existing executable that is NOT RawView
    for root in [winreg.HKEY_CLASSES_ROOT, winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
        for sub in [f"{prog}\\shell\\open\\command", f"Software\\Classes\\{prog}\\shell\\open\\command"]:
            try:
                with winreg.OpenKey(root, sub) as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    m = re.search(r'"([^"]+\.exe)"', val, re.I) or re.search(r'([a-zA-Z]:\\[^\s,"]+\.exe)', val, re.I)
                    if m:
                        exe = m.group(1)
                        if os.path.isfile(exe) and "rawview" not in exe.lower():
                            _NATIVE_APP_CACHE[ext_lower] = True
                            return True
            except Exception:
                pass

    _NATIVE_APP_CACHE[ext_lower] = False
    return False

def should_stamp_badge(ext: str, mode: str = "always") -> bool:
    """
    Determines whether RawView should burn the badge directly onto the thumbnail.
    - 'always' (Default): Always burns clean high-DPI format badge directly onto the image.
                          Guarantees 100% identical and reliable appearance across all PCs.
    - 'native_only': Never burns badge into image.
    """
    ext_lower = ext.lower()
    if ext_lower not in BADGE_CATALOG:
        return False

    if mode == "native_only":
        return False

    return True

def stamp_format_badge(qimage: QImage, ext: str, mode: str = "always", target_cx: int = 0) -> QImage:
    """
    Renders an authentic, crisp, anti-aliased format badge directly into the corner of the thumbnail.
    Guarantees that files like PSD vs JPG, or AI vs PNG can be instantly distinguished at a glance!
    Calculates badge size strictly from the target thumbnail grid slot (target_cx), ensuring
    100% uniform badge dimensions across all files regardless of square, portrait, or flat landscape shapes!
    """
    ext_lower = ext.lower()
    if not should_stamp_badge(ext_lower, mode):
        return qimage

    style = BADGE_CATALOG.get(ext_lower)
    if not style:
        return qimage

    w = qimage.width()
    h = qimage.height()
    if w < 24 or h < 24:
        return qimage

    # Determine reference grid dimension (requested Explorer thumbnail grid slot)
    grid_dim = target_cx if target_cx >= 64 else max(w, h, 256)

    # Standard uniform badge height:
    # At 256 grid -> 33px
    # At 128 grid -> 22px
    # At 96 grid  -> 20px
    badge_h = max(20, min(34, int(grid_dim * 0.13)))
    aspect = 1.30 if len(style.label) >= 3 else 1.05
    badge_w = int(badge_h * aspect)
    margin = max(4, int(badge_h * 0.12))

    # Canvas Expansion for extreme aspect ratio images (e.g. flat banners, narrow ties, pant patterns)
    # If the image is too flat (h < badge_h + margin * 2) or too narrow (w < badge_w + margin * 2),
    # pad the canvas with transparent pixels (ARGB32 0x00000000) so the image is centered and the
    # badge is stamped cleanly without shrinking!
    req_w = max(w, badge_w + margin * 2 + 10)
    req_h = max(h, badge_h + margin * 2 + 10)

    if req_w > w or req_h > h:
        # Create padded transparent canvas
        canvas = QImage(req_w, req_h, QImage.Format.Format_ARGB32)
        canvas.fill(0)  # 100% Transparent ARGB32
        p_canvas = QPainter(canvas)
        # Center original artwork on transparent canvas
        offset_x = (req_w - w) // 2
        offset_y = (req_h - h) // 2
        p_canvas.drawImage(offset_x, offset_y, qimage)
        p_canvas.end()
        img = canvas
        w = req_w
        h = req_h
    else:
        if qimage.format() != QImage.Format.Format_ARGB32 and qimage.format() != QImage.Format.Format_ARGB32_Premultiplied:
            img = qimage.convertToFormat(QImage.Format.Format_ARGB32)
        else:
            img = qimage.copy()

    x = w - badge_w - margin
    y = h - badge_h - margin

    rx = max(3.0, badge_h * 0.20)
    ry = rx

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    badge_rect = QRectF(float(x), float(y), float(badge_w), float(badge_h))

    # 1. Subtle Dark Drop Shadow for legibility against white/bright backgrounds
    shadow_rect = QRectF(badge_rect.x() + 1.0, badge_rect.y() + 1.5, badge_rect.width(), badge_rect.height())
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(0, 0, 0, 110)))
    painter.drawRoundedRect(shadow_rect, rx, ry)

    # 2. Main Badge Background
    painter.setBrush(QBrush(style.bg_color))
    painter.setPen(QPen(style.border_color, 1.2))
    painter.drawRoundedRect(badge_rect, rx, ry)

    # 3. Typography
    font_size = max(8, int(badge_h * 0.52))
    font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    painter.setFont(font)
    painter.setPen(style.text_color)

    # Vertically center text with subtle baseline correction
    text_rect = QRectF(badge_rect.x(), badge_rect.y() - 0.5, badge_rect.width(), badge_rect.height())
    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, style.label)

    painter.end()
    return img

