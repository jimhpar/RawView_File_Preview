import os
import io
import struct
import gzip
import re
import base64
import shutil
import ctypes
from ctypes import wintypes, byref, c_void_p, POINTER, Structure, c_int, c_uint, c_wchar_p
from pathlib import Path
from PIL import Image, ImageOps
import pypdfium2 as pdfium
import pymupdf as fitz
import rawpy
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont, QLinearGradient, QPen
from PyQt6.QtCore import QByteArray, QSize, Qt
from PyQt6.QtSvg import QSvgRenderer
import comtypes
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

# Check if Ghostscript is available on system
GHOSTSCRIPT_AVAILABLE = bool(shutil.which("gswin64c") or shutil.which("gs") or shutil.which("gswin32c"))

# Windows Shell Thumbnail Provider Interface Definitions
class _SIZE(Structure):
    _fields_ = [('cx', c_int), ('cy', c_int)]

class _IShellItemImageFactory(IUnknown):
    _iid_ = GUID('{bcc18b79-ba16-442f-80c4-8a59c30c463b}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetImage',
                  (['in'], _SIZE, 'size'),
                  (['in'], c_uint, 'flags'),
                  (['out'], POINTER(wintypes.HBITMAP), 'phbm'))
    ]

_SHCreateItemFromParsingName = ctypes.windll.shell32.SHCreateItemFromParsingName
_SHCreateItemFromParsingName.argtypes = [c_wchar_p, c_void_p, POINTER(GUID), POINTER(c_void_p)]
_SHCreateItemFromParsingName.restype = HRESULT

_DeleteObject = ctypes.windll.gdi32.DeleteObject
_DeleteObject.argtypes = [wintypes.HGDIOBJ]
_DeleteObject.restype = wintypes.BOOL

class ShellImageFactory:
    """Hardware-accelerated Windows Shell image provider (utilizing native Adobe/system shell handlers)."""
    @staticmethod
    def get_thumbnail(file_path: str, max_size: int = 1440, thumbnail_only: bool = True) -> QImage | None:
        """
        Extracts native Windows shell thumbnail using IShellItemImageFactory.
        thumbnail_only=True (default) ensures we NEVER extract generic file icons.
        """
        try:
            if not os.path.exists(file_path):
                return None
            # Ensure COM is initialized on background worker threads
            try:
                ctypes.windll.ole32.CoInitialize(None)
            except Exception:
                pass

            iid = _IShellItemImageFactory._iid_
            p_item = c_void_p()
            hr = _SHCreateItemFromParsingName(file_path, None, byref(iid), byref(p_item))
            if hr != 0:
                return None
            factory = comtypes.cast(p_item, POINTER(_IShellItemImageFactory))
            
            # 0x00 = SIIGBF_RESIZETOFIT, 0x08 = SIIGBF_THUMBNAILONLY
            flags = 0x08 if thumbnail_only else 0x00
            hbm = factory.GetImage(_SIZE(max_size, max_size), flags)
            
            if hbm:
                qim = QImage.fromHBITMAP(int(hbm))
                try:
                    _DeleteObject(hbm)
                except Exception:
                    pass
                if not qim.isNull() and qim.width() > 10 and qim.height() > 10:
                    return qim
        except Exception:
            pass
        return None

class PreviewResult:
    """Standardized preview result holding the rendered image/video and metadata."""
    def __init__(self, qimage: QImage, width: int, height: int, mode: str, format_name: str, file_size: int, extra_info: str = "", is_video: bool = False, video_path: str = "", duration_ms: int = 0):
        self.qimage = qimage
        self.width = width
        self.height = height
        self.mode = mode
        self.format_name = format_name
        self.file_size = file_size
        self.extra_info = extra_info
        self.is_video = is_video
        self.video_path = video_path
        self.duration_ms = duration_ms

    @property
    def formatted_size(self) -> str:
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} B"
            size /= 1024.0
        return f"{size:.1f} TB"

    @property
    def dimensions_str(self) -> str:
        if self.is_video:
            if self.width > 0 and self.height > 0:
                return f"{self.width} × {self.height} px"
            return "Video"
        if self.width > 0 and self.height > 0:
            return f"{self.width} × {self.height} px"
        return "Vector"

    @property
    def duration_str(self) -> str:
        if self.duration_ms <= 0:
            return ""
        total_sec = int(self.duration_ms // 1000)
        mins = total_sec // 60
        secs = total_sec % 60
        hours = mins // 60
        mins = mins % 60
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

def extract_xmp_image(file_path: str, max_scan_bytes: int = 4 * 1024 * 1024) -> QImage | None:
    """Fast, memory-efficient scanner that extracts embedded <xmpGImg:image> JPEG thumbnail."""
    try:
        size = os.path.getsize(file_path)
        with open(file_path, "rb") as f:
            # Check header (first 4MB)
            chunk = f.read(max_scan_bytes)
            m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', chunk)
            if not m and size > max_scan_bytes:
                # Check trailer (last 4MB)
                f.seek(max(0, size - max_scan_bytes))
                chunk = f.read(max_scan_bytes)
                m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', chunk)
            if not m and size <= 32 * 1024 * 1024:
                # Full scan if under 32MB
                f.seek(0)
                full_data = f.read()
                m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', full_data)

            if m:
                b64_data = m.group(1).replace(b"&#xA;", b"").replace(b"\n", b"").replace(b"\r", b"").replace(b" ", b"").replace(b"\t", b"").strip()
                raw_bytes = base64.b64decode(b64_data)
                qim = QImage.fromData(QByteArray(raw_bytes))
                if not qim.isNull() and qim.width() > 10 and qim.height() > 10:
                    return qim
    except Exception:
        pass
    return None

def pil_to_qimage(pil_img: Image.Image) -> QImage:
    """Converts a PIL Image to a QImage directly in memory."""
    if pil_img.mode == "RGBA":
        data = pil_img.tobytes("raw", "RGBA")
        qim = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
        return qim.copy()
    elif pil_img.mode == "RGB":
        data = pil_img.tobytes("raw", "RGB")
        qim = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888)
        return qim.copy()
    elif pil_img.mode == "L":
        data = pil_img.tobytes("raw", "L")
        qim = QImage(data, pil_img.width, pil_img.height, pil_img.width, QImage.Format.Format_Grayscale8)
        return qim.copy()
    else:
        rgba = pil_img.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qim = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
        return qim.copy()

def _is_blank_image(qim: QImage, threshold: int = 248) -> bool:
    """Detects if a QImage is completely blank (all white/near-white or uniform background)
    with no visible artwork. Uses smooth area-downsampling to ensure even small vector marks
    are never missed, while reliably rejecting truly empty white pages."""
    if qim.isNull() or qim.width() < 10 or qim.height() < 10:
        return True

    # Downsample to 32x32 using SmoothTransformation (bilinear area averaging across the entire image).
    # If the image is 100% white, all 32x32 pixels will be 255.
    # If any artwork, lines, text, or logos exist anywhere on the canvas, the averaged block
    # luminance drops significantly below 248.
    try:
        thumb = qim.scaled(32, 32, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        min_val = 255
        for x in range(32):
            for y in range(32):
                c = thumb.pixelColor(x, y)
                min_val = min(min_val, c.red(), c.green(), c.blue())
                if min_val < 240:
                    return False
        return min_val >= threshold
    except Exception:
        return False


class PsdDecoder:
    """High-speed decoder for Adobe Photoshop PSD and PSB files."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        # Attempt 1: Fast composite frame via PIL
        try:
            with Image.open(file_path) as img:
                orig_w, orig_h = img.size
                mode = img.mode
                
                if mode in ("CMYK", "YCbCr", "LAB"):
                    render_img = img.convert("RGB")
                elif mode in ("RGBA", "RGB", "L"):
                    render_img = img.copy()
                else:
                    render_img = img.convert("RGBA")

                if max(orig_w, orig_h) > max_size:
                    render_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

                qim = pil_to_qimage(render_img)
                return PreviewResult(
                    qimage=qim,
                    width=orig_w,
                    height=orig_h,
                    mode=mode,
                    format_name="PSD",
                    file_size=size
                )
        except Exception:
            pass

        # Attempt 2: psd-tools composite fallback
        try:
            from psd_tools import PSDImage
            psd = PSDImage.open(file_path)
            orig_w, orig_h = psd.width, psd.height
            mode = psd.color_mode.name if hasattr(psd, "color_mode") else "RGB"
            pil_composite = psd.composite()
            if pil_composite:
                if max(orig_w, orig_h) > max_size:
                    pil_composite.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                qim = pil_to_qimage(pil_composite)
                return PreviewResult(
                    qimage=qim,
                    width=orig_w,
                    height=orig_h,
                    mode=mode,
                    format_name="PSD",
                    file_size=size
                )
        except Exception:
            pass

        # Attempt 3: Shell provider fallback
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size)
        if shell_qim:
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="RGB (Photoshop)",
                format_name="PSD",
                file_size=size
            )

        raise RuntimeError("Could not decode PSD composite frame.")

def _is_incomplete_vector_render(page, qim: QImage, xmp_qim: QImage | None) -> bool:
    """
    Detects if a PDF artboard rasterization is severely incomplete or missing artwork
    that was placed on the pasteboard/canvas or embedded in private Illustrator data.
    E.g. In Mighty Munchkin.ai, the artboard only covers 2 tiny corner boxes while
    the full graphic (child, shirt, vest) is on the pasteboard and captured in XMP.
    """
    if not xmp_qim or xmp_qim.isNull():
        return False
    # If text elements or embedded images exist in the PDF stream, it's genuine content
    if len(page.get_images()) > 0 or len(page.get_text().strip()) > 0:
        return False
    drawings = page.get_drawings()
    if len(drawings) > 8:
        return False
    rect = page.rect
    # Check if drawings extend significantly outside the artboard boundary
    has_overflow = any(
        d['rect'].x1 > rect.x1 * 1.05 or d['rect'].y1 > rect.y1 * 1.05 or
        d['rect'].x0 < -0.05 * rect.x1 or d['rect'].y0 < -0.05 * rect.y1
        for d in drawings
    )
    if not has_overflow:
        return False
    # Check non-white distribution in rendered QImage
    small = qim.scaled(120, 120)
    min_x, max_x = 120, 0
    non_white = 0
    for x in range(small.width()):
        for y in range(small.height()):
            c = small.pixelColor(x, y)
            if c.red() < 245 or c.green() < 245 or c.blue() < 245:
                non_white += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
    if non_white == 0:
        return True
    coverage_w = (max_x - min_x) / 120.0
    is_edge_squished = (min_x > 60) or (max_x < 60)
    return is_edge_squished and coverage_w < 0.45

class AiDecoder:
    """
    High-speed, high-fidelity decoder for Adobe Illustrator AI files.
    Priority:
    1. Legacy AI binary header (0xC5D0D3C6 / 0xC6D3D0C5) with embedded TIFF preview (AI v1–v8)
    2. PyMuPDF Vector Rasterizer (Full crisp 1440px / up to 300 DPI vector rendering)
    3. Fallback Vector: PDFium Rasterizer
    4. Embedded XMP Composite Thumbnail (<xmpGImg:image> - captures full canvas & pasteboard)
    5. Native Windows Shell Thumbnail (Cached thumbnail ONLY, never fallback to icon)
    6. Ghostscript PostScript rendering (if available)
    7. High-Definition Illustrator Branded Overview Card
    """
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)

        # Extract PostScript header metadata for workspace info and card fallback
        bbox_w, bbox_h = 0, 0
        creator = ""
        title = ""
        try:
            with open(file_path, "rb") as f:
                header = f.read(1024 * 512).decode("latin-1", errors="ignore")
            m = re.search(r"%%BoundingBox:\s*([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)", header)
            if m:
                x0, y0, x1, y1 = map(float, m.groups())
                bbox_w = max(int(x1) - int(x0), 0)
                bbox_h = max(int(y1) - int(y0), 0)
            m_c = re.search(r"%%Creator:\s*([^\r\n]+)", header)
            if m_c:
                creator = m_c.group(1).strip()
            m_t = re.search(r"%%Title:\s*([^\r\n]+)", header)
            if m_t:
                title = m_t.group(1).strip()
        except Exception:
            pass

        # Extract XMP embedded composite thumbnail early if present
        xmp_qim = extract_xmp_image(file_path)

        # 1. Legacy AI binary header (0xC5D0D3C6 / 0xC6D3D0C5) with embedded TIFF preview (AI v1.0–v8.0)
        try:
            with open(file_path, "rb") as f:
                header_bin = f.read(32)
                if len(header_bin) >= 30 and header_bin[:4] in (b"\xC5\xD0\xD3\xC6", b"\xC6\xD3\xD0\xC5"):
                    tiff_offset, tiff_length = struct.unpack("<II", header_bin[20:28])
                    if tiff_offset > 0 and tiff_length > 0 and (tiff_offset + tiff_length) <= size:
                        f.seek(tiff_offset)
                        tiff_bytes = f.read(tiff_length)
                        qim = QImage.fromData(QByteArray(tiff_bytes))
                        if not qim.isNull() and qim.width() > 10 and qim.height() > 10:
                            return PreviewResult(
                                qimage=qim,
                                width=qim.width(),
                                height=qim.height(),
                                mode="Legacy AI (TIFF Preview)",
                                format_name="AI",
                                file_size=size,
                                extra_info=creator if creator else "Legacy Illustrator"
                            )
        except Exception:
            pass

        # 2. Primary: PyMuPDF Vector Rasterizer (AI 9+ with PDF compatibility streams)
        # Renders crystal-clear vector artwork at high DPI (up to 1440px / 300 DPI) for crisp zoom
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                page = doc[0]
                has_content = len(page.get_drawings()) > 0 or len(page.get_text().strip()) > 0 or len(page.get_images()) > 0
                rect = page.rect
                page_w = max(int(rect.width), 10)
                page_h = max(int(rect.height), 10)

                dpi = int(min(max_size / max(page_w, page_h, 1) * 72, 300))
                dpi = max(dpi, 72)
                pix = page.get_pixmap(dpi=dpi)

                if pix.width > 0 and pix.height > 0:
                    samples = pix.samples
                    if has_content or (len(samples) > 0 and min(samples) < 248):
                        data = pix.tobytes("png")
                        qim = QImage.fromData(QByteArray(data))
                        if not qim.isNull() and not _is_blank_image(qim):
                            # Verify that vector render is complete and not an incomplete pasteboard fragment
                            if _is_incomplete_vector_render(page, qim, xmp_qim):
                                return PreviewResult(
                                    qimage=xmp_qim,
                                    width=xmp_qim.width(),
                                    height=xmp_qim.height(),
                                    mode="RGB (Full Workspace)",
                                    format_name="AI",
                                    file_size=size,
                                    extra_info="Workspace Thumbnail (Canvas Composite)"
                                )
                            artboard_info = f"Artboard 1 of {len(doc)}" if len(doc) > 1 else "Artboards: 1"
                            return PreviewResult(
                                qimage=qim,
                                width=page_w,
                                height=page_h,
                                mode="RGB (Vector Artboard)",
                                format_name="AI",
                                file_size=size,
                                extra_info=artboard_info
                            )
        except Exception:
            pass

        # 3. Fallback Vector: PDFium Rasterizer
        try:
            pdf = pdfium.PdfDocument(file_path)
            if len(pdf) > 0:
                page = pdf[0]
                page_w = int(page.get_width())
                page_h = int(page.get_height())
                scale = min(max_size / max(page_w, page_h, 1), 3.0)
                scale = max(scale, 1.0)

                pil_img = page.render(scale=scale).to_pil()
                qim = pil_to_qimage(pil_img)
                if not qim.isNull() and not _is_blank_image(qim):
                    if xmp_qim and not xmp_qim.isNull():
                        return PreviewResult(
                            qimage=xmp_qim,
                            width=xmp_qim.width(),
                            height=xmp_qim.height(),
                            mode="RGB (Full Workspace)",
                            format_name="AI",
                            file_size=size,
                            extra_info="Workspace Thumbnail"
                        )
                    artboard_info = f"Artboard 1 of {len(pdf)}" if len(pdf) > 1 else "Artboards: 1"
                    return PreviewResult(
                        qimage=qim,
                        width=page_w,
                        height=page_h,
                        mode="RGB (Vector Artboard)",
                        format_name="AI",
                        file_size=size,
                        extra_info=artboard_info
                    )
        except Exception:
            pass

        # 4. Embedded XMP Composite Thumbnail (<xmpGImg:image>)
        # Illustrator embeds the full canvas & pasteboard composite in XMP metadata.
        # This accurately renders artwork created on the pasteboard or outside artboard boundaries.
        if xmp_qim and not xmp_qim.isNull():
            return PreviewResult(
                qimage=xmp_qim,
                width=xmp_qim.width(),
                height=xmp_qim.height(),
                mode="RGB (Full Workspace)",
                format_name="AI",
                file_size=size,
                extra_info="Workspace Thumbnail"
            )

        # 5. Native Windows Shell Thumbnail (Cached thumbnail ONLY, never fallback to icon)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size, thumbnail_only=True)
        if shell_qim and not shell_qim.isNull() and not _is_blank_image(shell_qim):
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="RGB (Shell)",
                format_name="AI",
                file_size=size,
                extra_info="Native Thumbnail"
            )

        # 6. If PostScript AI and Ghostscript is installed, render via Pillow
        if GHOSTSCRIPT_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    img.load(scale=2)
                    w, h = img.size
                    qim = pil_to_qimage(img.convert("RGBA"))
                    if not qim.isNull():
                        return PreviewResult(
                            qimage=qim,
                            width=w,
                            height=h,
                            mode="PostScript Vector",
                            format_name="AI",
                            file_size=size,
                            extra_info="Legacy Illustrator (Ghostscript)"
                        )
            except Exception:
                pass

        # 6. High-Definition Adobe Illustrator Branded Overview Card
        # When an AI file was saved without PDF compatibility and without thumbnails,
        # display a clean, informative overview card instead of failing silently.
        card_w, card_h = 640, 420
        qim = QImage(card_w, card_h, QImage.Format.Format_ARGB32_Premultiplied)
        qim.fill(QColor(18, 20, 26, 255))
        painter = QPainter(qim)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer subtle amber border
        painter.setPen(QColor(230, 140, 30, 120))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(15, 15, card_w - 30, card_h - 30, 12, 12)

        # Illustrator Amber badge
        painter.setBrush(QColor(255, 154, 0, 230))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(35, 35, 95, 28, 6, 6)
        painter.setPen(QColor(26, 15, 0))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(43, 54, "AI VECTOR")

        # Document Title
        display_title = title if title else Path(file_path).name
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(35, 110, display_title)

        # Metadata Details
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor(180, 195, 215))
        painter.drawText(35, 155, "Adobe Illustrator Artwork")
        dim_str = f"{bbox_w} × {bbox_h} pt" if bbox_w > 0 and bbox_h > 0 else "Custom Canvas"
        painter.drawText(35, 190, f"Bounding Box: {dim_str}")
        if creator:
            painter.drawText(35, 225, f"Created with: {creator}")
        else:
            painter.drawText(35, 225, "Created with: Adobe Illustrator")
        painter.drawText(35, 260, f"File Size: {size / 1024.0:.1f} KB")

        # Status note
        painter.setBrush(QColor(40, 45, 60, 180))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(35, 300, 420, 34, 6, 6)
        painter.setPen(QColor(240, 170, 70))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        painter.drawText(45, 322, "ℹ Native Artwork (Saved without PDF Stream or Embedded Thumbnail)")

        painter.end()

        return PreviewResult(
            qimage=qim,
            width=bbox_w if bbox_w > 0 else card_w,
            height=bbox_h if bbox_h > 0 else card_h,
            mode="Illustrator Overview",
            format_name="AI",
            file_size=size,
            extra_info=creator if creator else "Native Artwork"
        )

class EpsDecoder:
    """High-speed decoder for Encapsulated PostScript (.eps) files."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)

        # 1. Binary EPS header (0xC5D0D3C6) with embedded TIFF preview (Sub-millisecond real artwork)
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
                if len(header) >= 30 and header[:4] in (b"\xC5\xD0\xD3\xC6", b"\xC6\xD3\xD0\xC5"):
                    tiff_offset, tiff_length = struct.unpack("<II", header[20:28])
                    if tiff_offset > 0 and tiff_length > 0 and (tiff_offset + tiff_length) <= size:
                        f.seek(tiff_offset)
                        tiff_bytes = f.read(tiff_length)
                        qim = QImage.fromData(QByteArray(tiff_bytes))
                        if not qim.isNull() and qim.width() > 10 and qim.height() > 10:
                            return PreviewResult(
                                qimage=qim,
                                width=qim.width(),
                                height=qim.height(),
                                mode="Full Artwork (TIFF)",
                                format_name="EPS",
                                file_size=size
                            )
        except Exception:
            pass

        # 2. Check for embedded XMP workspace preview in EPS (<xmpGImg:image>)
        qim = extract_xmp_image(file_path)
        if qim and not qim.isNull():
            return PreviewResult(
                qimage=qim,
                width=qim.width(),
                height=qim.height(),
                mode="Full Artwork (XMP)",
                format_name="EPS",
                file_size=size
            )

        # 3. If Ghostscript is present, render via Pillow
        if GHOSTSCRIPT_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    img.load(scale=2)
                    w, h = img.size
                    qim = pil_to_qimage(img.convert("RGBA"))
                    return PreviewResult(
                        qimage=qim,
                        width=w,
                        height=h,
                        mode="PostScript",
                        format_name="EPS",
                        file_size=size
                    )
            except Exception:
                pass

        # 4. Parse BoundingBox and Creator metadata from header lines for clean card fallback
        bbox_w, bbox_h = 600, 400
        creator = ""
        title = ""
        try:
            with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
                for _ in range(60):
                    line = f.readline()
                    if not line:
                        break
                    line_s = line.strip()
                    if line_s.startswith("%%BoundingBox:"):
                        parts = line_s.split()
                        if len(parts) >= 5:
                            try:
                                bbox_w = max(int(float(parts[3])) - int(float(parts[1])), 10)
                                bbox_h = max(int(float(parts[4])) - int(float(parts[2])), 10)
                            except Exception:
                                pass
                    elif line_s.startswith("%%Creator:"):
                        creator = line_s.replace("%%Creator:", "").strip()
                    elif line_s.startswith("%%Title:"):
                        title = line_s.replace("%%Title:", "").strip()
        except Exception:
            pass

        # Fallback clean card
        card_w, card_h = 640, 420
        qim = QImage(card_w, card_h, QImage.Format.Format_ARGB32_Premultiplied)
        qim.fill(QColor(18, 22, 34, 255))
        painter = QPainter(qim)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(60, 90, 160, 180))
        painter.drawRoundedRect(15, 15, card_w - 30, card_h - 30, 12, 12)
        painter.setBrush(QColor(38, 85, 170, 200))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(35, 35, 80, 28, 6, 6)
        painter.setPen(QColor(255, 255, 255))
        font_b = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font_b)
        painter.drawText(48, 54, "EPS")
        painter.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        display_title = title if title else Path(file_path).name
        painter.drawText(35, 110, f"{display_title}")
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor(170, 185, 215))
        painter.drawText(35, 155, f"PostScript Vector File")
        painter.drawText(35, 190, f"Bounding Box: {bbox_w} × {bbox_h} pt")
        if creator:
            painter.drawText(35, 225, f"Created with: {creator}")
        painter.drawText(35, 260, f"File Size: {size / 1024.0:.1f} KB")
        painter.end()

        return PreviewResult(
            qimage=qim,
            width=bbox_w,
            height=bbox_h,
            mode="PostScript Vector",
            format_name="EPS",
            file_size=size,
            extra_info=creator
        )

class PdfDecoder:
    """High-speed vector PDF document rasterizer."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        pdf = pdfium.PdfDocument(file_path)
        if len(pdf) == 0:
            raise RuntimeError("Empty PDF document.")

        page = pdf[0]
        page_w = int(page.get_width())
        page_h = int(page.get_height())

        scale = min(max_size / max(page_w, page_h, 1), 2.5)
        scale = max(scale, 1.0)

        pil_img = page.render(scale=scale).to_pil()
        qim = pil_to_qimage(pil_img)
        page_str = f"Page 1 of {len(pdf)}" if len(pdf) > 1 else "1 Page"

        return PreviewResult(
            qimage=qim,
            width=page_w,
            height=page_h,
            mode="RGB (PDF Document)",
            format_name="PDF",
            file_size=size,
            extra_info=page_str
        )

class TiffDecoder:
    """High-speed decoder for TIFF images (supports multi-page, 16-bit, CMYK, LAB)."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        with Image.open(file_path) as img:
            orig_w, orig_h = img.size
            mode = img.mode
            page_count = getattr(img, "n_frames", 1)

            if mode in ("CMYK", "YCbCr", "LAB"):
                render_img = img.convert("RGB")
            elif mode in ("RGBA", "RGB", "L"):
                render_img = img.copy()
            elif mode in ("I", "I;16", "I;16L", "I;16B", "F"):
                render_img = ImageOps.autocontrast(img.convert("L"))
            else:
                render_img = img.convert("RGBA")

            if max(orig_w, orig_h) > max_size:
                render_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

            qim = pil_to_qimage(render_img)
            extra = f"Pages: {page_count}" if page_count > 1 else ""
            return PreviewResult(
                qimage=qim,
                width=orig_w,
                height=orig_h,
                mode=f"{mode}",
                format_name="TIFF",
                file_size=size,
                extra_info=extra
            )

class RawCameraDecoder:
    """
    Ultra-fast decoder for all Adobe Camera RAW formats:
    DNG, CR2, CR3, CRW, NEF, NRW, ARW, SRF, SR2, RAF, ORF, ORI, RW2, PEF, PTX, 3FR, FFF, IIQ, RAW, X3F.
    """
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        ext = Path(file_path).suffix.lower()

        # Attempt 1: Instant embedded full-resolution JPEG thumbnail via LibRaw (sub-5ms!)
        try:
            with rawpy.imread(file_path) as raw:
                try:
                    thumb = raw.extract_thumb()
                    if thumb and thumb.format == rawpy.ThumbFormat.JPEG:
                        with Image.open(io.BytesIO(thumb.data)) as img:
                            w, h = img.size
                            render_img = img.convert("RGB")
                            if max(w, h) > max_size:
                                render_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                            qim = pil_to_qimage(render_img)
                            return PreviewResult(
                                qimage=qim,
                                width=w,
                                height=h,
                                mode="RAW Embedded Preview",
                                format_name=ext.replace(".", "").upper(),
                                file_size=size,
                                extra_info="Camera RAW"
                            )
                except Exception:
                    pass

                # Attempt 2: Fast half-size raw postprocess
                rgb = raw.postprocess(use_camera_wb=True, half_size=True, no_auto_bright=True)
                img = Image.fromarray(rgb)
                w, h = img.size
                if max(w, h) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                qim = pil_to_qimage(img)
                return PreviewResult(
                    qimage=qim,
                    width=raw.sizes.raw_width,
                    height=raw.sizes.raw_height,
                    mode="RAW Sensor Data",
                    format_name=ext.replace(".", "").upper(),
                    file_size=size,
                    extra_info="Camera RAW"
                )
        except Exception:
            pass

        # Attempt 3: PIL Image fallback (handles DNG, etc.)
        try:
            with Image.open(file_path) as img:
                w, h = img.size
                render_img = img.convert("RGB")
                if max(w, h) > max_size:
                    render_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
                qim = pil_to_qimage(render_img)
                return PreviewResult(
                    qimage=qim,
                    width=w,
                    height=h,
                    mode="RAW (DNG)",
                    format_name=ext.replace(".", "").upper(),
                    file_size=size
                )
        except Exception as e:
            raise RuntimeError(f"Could not decode Camera RAW file: {e}")

class SvgDecoder:
    """Ultra-fast vector SVG renderer using Qt's native hardware-accelerated QSvgRenderer."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1200) -> PreviewResult:
        size = os.path.getsize(file_path)
        is_svgz = file_path.lower().endswith(".svgz")

        if is_svgz:
            with gzip.open(file_path, "rb") as f:
                svg_data = f.read()
        else:
            with open(file_path, "rb") as f:
                svg_data = f.read()

        renderer = QSvgRenderer(QByteArray(svg_data))
        if not renderer.isValid():
            raise RuntimeError("Invalid SVG vector markup.")

        default_size = renderer.defaultSize()
        w = default_size.width() if default_size.width() > 0 else 800
        h = default_size.height() if default_size.height() > 0 else 600

        aspect = w / max(h, 1)
        if w >= h:
            render_w = min(w, max_size)
            render_h = int(render_w / aspect)
        else:
            render_h = min(h, max_size)
            render_w = int(render_h * aspect)

        render_w = max(render_w, 100)
        render_h = max(render_h, 100)

        qim = QImage(render_w, render_h, QImage.Format.Format_ARGB32_Premultiplied)
        qim.fill(Qt.GlobalColor.transparent)

        painter = QPainter(qim)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        renderer.render(painter)
        painter.end()

        return PreviewResult(
            qimage=qim,
            width=w,
            height=h,
            mode="Scalable Vector",
            format_name="SVG",
            file_size=size
        )

class VideoDecoder:
    """Ultra-fast decoder and metadata extractor for all major video formats."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        ext = Path(file_path).suffix.lower()
        fmt_name = ext.replace(".", "").upper()

        # Native Windows Shell Video Thumbnail (Fast thumbnail cache lookup first)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size, thumbnail_only=True)
        if not shell_qim or shell_qim.isNull():
            shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size, thumbnail_only=False)
        
        w = shell_qim.width() if shell_qim else 1920
        h = shell_qim.height() if shell_qim else 1080

        if not shell_qim or shell_qim.isNull():
            card_w, card_h = 640, 360
            shell_qim = QImage(card_w, card_h, QImage.Format.Format_ARGB32_Premultiplied)
            shell_qim.fill(QColor(15, 23, 42))

        return PreviewResult(
            qimage=shell_qim,
            width=w,
            height=h,
            mode="Video Stream",
            format_name=fmt_name,
            file_size=size,
            is_video=True,
            video_path=file_path,
            extra_info="Live Video"
        )

class StandardImageDecoder:
    """Ultra-fast zero-lag decoder for standard web & raster images (JPG, PNG, GIF, ICO, WebP, BMP)."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        ext = Path(file_path).suffix.lower()
        fmt_name = ext.lstrip(".").upper()

        with Image.open(file_path) as img:
            orig_w, orig_h = img.size
            mode = img.mode

            # Auto-orient based on EXIF
            try:
                img = ImageOps.exif_transpose(img)
                orig_w, orig_h = img.size
            except Exception:
                pass

            if mode in ("RGBA", "LA") or (mode == "P" and "transparency" in img.info):
                render_img = img.convert("RGBA")
            elif mode in ("CMYK", "YCbCr", "LAB"):
                render_img = img.convert("RGB")
            elif mode == "1":
                render_img = img.convert("L")
            else:
                render_img = img.convert("RGB")

            if max(orig_w, orig_h) > max_size:
                render_img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)

            qim = pil_to_qimage(render_img)

            extra = ""
            if getattr(img, "is_animated", False):
                extra = f"Animated GIF ({getattr(img, 'n_frames', 1)} frames)"
            elif ext == ".ico":
                extra = f"Icon ({orig_w}×{orig_h})"
            elif ext in (".jpg", ".jpeg"):
                extra = f"{mode} Photo"
            elif ext == ".png":
                extra = "Lossless PNG"
            elif ext == ".webp":
                extra = "WebP Graphic"
            elif ext == ".bmp":
                extra = "Bitmap Image"

            return PreviewResult(
                qimage=qim,
                width=orig_w,
                height=orig_h,
                mode=mode,
                format_name=fmt_name,
                file_size=size,
                extra_info=extra
            )

def extract_doc_text(data: bytes, max_chars: int = 300) -> str:
    """Extracts readable text from Word 97-2003 (.doc) binary streams."""
    try:
        utf16_matches = re.findall(rb'(?:[\x20-\x7E]\x00){4,}', data)
        texts = []
        for m in utf16_matches:
            try:
                t = m.decode('utf-16le', errors='ignore').strip()
                if len(t) > 3 and not any(t.startswith(x) for x in ('Normal', 'Heading', 'Default', 'Times', 'Calibri', 'Arial', 'Symbol', 'Table')):
                    texts.append(t)
            except Exception:
                pass
        if texts:
            return " ".join(texts[:10])[:max_chars]
        ascii_matches = re.findall(rb'[\x20-\x7E\r\n\t]{6,}', data)
        ascii_texts = [m.decode('latin-1', errors='ignore').strip() for m in ascii_matches if len(m) > 5]
        return " ".join(ascii_texts[:10])[:max_chars]
    except Exception:
        return ""

def clean_rtf(rtf_text: str, max_chars: int = 300) -> str:
    """Strips RTF control sequences to extract clean readable plain text."""
    try:
        text = re.sub(r'\\[a-zA-Z]+(-?\d+)? ?', '', rtf_text)
        text = re.sub(r'[{}]', '', text)
        return " ".join(text.split())[:max_chars]
    except Exception:
        return ""

def extract_xls_sheets(data: bytes) -> list[str]:
    """Parses BIFF8 BOUNDSHEET (0x0085) records from Excel 97-2003 (.xls) files."""
    sheets = []
    idx = 0
    try:
        while idx < len(data) - 10:
            rec_id = struct.unpack_from('<H', data, idx)[0]
            if rec_id == 0x0085:
                rec_len = struct.unpack_from('<H', data, idx + 2)[0]
                if 6 <= rec_len <= 256 and idx + 4 + rec_len <= len(data):
                    rec_data = data[idx + 4 : idx + 4 + rec_len]
                    if len(rec_data) >= 8:
                        cch = rec_data[6]
                        flags = rec_data[7]
                        if flags == 0 and len(rec_data) >= 8 + cch:
                            name = rec_data[8 : 8 + cch].decode('latin-1', errors='ignore')
                            if name and name.isprintable():
                                sheets.append(name)
                        elif flags == 1 and len(rec_data) >= 8 + cch * 2:
                            name = rec_data[8 : 8 + cch * 2].decode('utf-16le', errors='ignore')
                            if name and name.isprintable():
                                sheets.append(name)
                idx += 4 + rec_len
            else:
                idx += 1
    except Exception:
        pass
    return sheets

class OfficeDocDecoder:
    """Ultra-fast decoder for Microsoft Word, Excel, PowerPoint, RTF, and CSV documents."""
    
    @staticmethod
    def _create_fallback_card(ext: str, file_path: str, size: int, meta: dict = None) -> QImage:
        w, h = 640, 420
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor("#090D16"))
        
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        e = ext.lower()
        if e in (".docx", ".doc", ".docm", ".dotx", ".dot", ".rtf"):
            grad_c1, grad_c2 = "#1E3A8A", "#172554"
            badge_bg, badge_fg = "#1E40AF", "#60A5FA"
            app_title = "Microsoft Word Document"
            icon_char = "W"
        elif e in (".xlsx", ".xls", ".xlsm", ".xlsb", ".xltx", ".csv"):
            grad_c1, grad_c2 = "#064E3B", "#022C22"
            badge_bg, badge_fg = "#065F46", "#34D399"
            app_title = "Microsoft Excel Spreadsheet"
            icon_char = "X"
        elif e in (".pptx", ".ppt", ".pptm", ".ppsx", ".potx"):
            grad_c1, grad_c2 = "#7C2D12", "#431407"
            badge_bg, badge_fg = "#9A3412", "#FB923C"
            app_title = "Microsoft PowerPoint Presentation"
            icon_char = "P"
        else:
            grad_c1, grad_c2 = "#0F172A", "#0B0F19"
            badge_bg, badge_fg = "#1E293B", "#38BDF8"
            app_title = "Office Document"
            icon_char = "D"

        # 1. Header Banner Gradient
        grad = QLinearGradient(0, 0, w, 84)
        grad.setColorAt(0.0, QColor(grad_c1))
        grad.setColorAt(1.0, QColor(grad_c2))
        painter.fillRect(0, 0, w, 84, grad)
        painter.fillRect(0, 83, w, 1, QColor(badge_fg))
        
        # Emblem Icon Box
        painter.setBrush(QColor(badge_bg))
        painter.setPen(QPen(QColor(badge_fg), 1.5))
        painter.drawRoundedRect(18, 16, 52, 52, 10, 10)
        
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.drawText(18, 16, 52, 52, Qt.AlignmentFlag.AlignCenter, icon_char)
        
        # Header Text
        painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        painter.drawText(82, 38, app_title)
        
        painter.setPen(QColor("#E2E8F0"))
        painter.setFont(QFont("Segoe UI", 11))
        fname = Path(file_path).name
        painter.drawText(82, 60, fname)
        
        # 2. File Metadata & Stats
        meta = meta or {}
        size_bytes = size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
        try:
            mtime = os.path.getmtime(file_path)
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            date_str = "Unknown"

        # Tile A: Primary Document Overview Tile
        painter.setBrush(QColor("#111625"))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        painter.drawRoundedRect(18, 100, w - 36, 140, 8, 8)
        
        painter.setPen(QColor(badge_fg))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(32, 126, "📄 Document Overview & Metadata")
        
        overview_rows = []
        if meta.get("title"):
            overview_rows.append(("Title:", str(meta["title"])))
        if meta.get("text_preview"):
            overview_rows.append(("Preview:", str(meta["text_preview"])[:65]))
        if meta.get("author"):
            overview_rows.append(("Author:", str(meta["author"])))
        if meta.get("sheets"):
            overview_rows.append(("Sheets:", str(meta["sheets"])))
        if meta.get("slides"):
            overview_rows.append(("Total Slides:", f"{meta['slides']} slides"))
        if meta.get("pages"):
            overview_rows.append(("Total Pages:", f"{meta['pages']} pages"))
        if meta.get("words"):
            overview_rows.append(("Word Count:", f"{int(meta['words']):,} words"))
            
        if not overview_rows:
            overview_rows.append(("Status:", "Ready for viewing in Microsoft Office"))
            
        y_ov = 154
        for label, val in overview_rows[:3]:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(32, y_ov, 110, 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            painter.setPen(QColor("#F8FAFC"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(150, y_ov, w - 180, 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, val[:65])
            y_ov += 26
            
        # Tile B: File Details Tile
        painter.setBrush(QColor("#111625"))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        painter.drawRoundedRect(18, 252, w - 36, 148, 8, 8)
        
        painter.setPen(QColor(badge_fg))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(32, 278, "📊 File Specifications")
        
        file_specs = [
            ("📁 File Size:", size_str),
            ("🕒 Last Modified:", date_str),
            ("🏷️ Format Type:", f"{e.upper().lstrip('.')} Document"),
        ]
        
        y_sp = 306
        for label, val in file_specs:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(32, y_sp, 120, 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            painter.setPen(QColor("#F1F5F9"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold if label != "🕒 Last Modified:" else QFont.Weight.Normal))
            painter.drawText(160, y_sp, w - 190, 22, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, val[:65])
            y_sp += 26
            
        painter.end()
        return img

    @classmethod
    def decode(cls, file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        ext = Path(file_path).suffix.lower()
        fmt_name = ext.lstrip(".").upper()
        
        meta = {}
        # 1. Try OpenXML ZIP thumbnail extraction for .docx, .xlsx, .pptx
        if ext in (".docx", ".xlsx", ".pptx", ".docm", ".dotx", ".xlsm", ".xltx", ".pptm", ".ppsx", ".potx"):
            try:
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as z:
                    names = z.namelist()
                    # A. Embedded document thumbnail
                    for thumb_name in ("docProps/thumbnail.jpeg", "docProps/thumbnail.jpg", "docProps/thumbnail.png"):
                        if thumb_name in names:
                            thumb_bytes = z.read(thumb_name)
                            qim = QImage.fromData(thumb_bytes)
                            if not qim.isNull() and qim.width() > 10:
                                return PreviewResult(
                                    qimage=qim,
                                    width=qim.width(),
                                    height=qim.height(),
                                    mode="RGB (Office Thumbnail)",
                                    format_name=fmt_name,
                                    file_size=size,
                                    extra_info="OpenXML Document"
                                )
                    
                    # B. Check for first slide/document embedded graphic
                    media_files = [n for n in names if (n.startswith("ppt/media/") or n.startswith("word/media/") or n.startswith("xl/media/")) and n.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                    if media_files:
                        first_img_bytes = z.read(sorted(media_files)[0])
                        qim = QImage.fromData(first_img_bytes)
                        if not qim.isNull() and qim.width() > 60 and qim.height() > 60:
                            return PreviewResult(
                                qimage=qim,
                                width=qim.width(),
                                height=qim.height(),
                                mode="RGB (Slide Visual)",
                                format_name=fmt_name,
                                file_size=size,
                                extra_info="Embedded Media"
                            )

                    # C. Metadata parsing
                    if "docProps/app.xml" in names:
                        app_xml = z.read("docProps/app.xml").decode("utf-8", errors="ignore")
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(app_xml)
                        for elem in root.iter():
                            tag = elem.tag.split("}")[-1]
                            if tag == "Pages" and elem.text:
                                meta["pages"] = elem.text
                            elif tag == "Slides" and elem.text:
                                meta["slides"] = elem.text
                            elif tag == "Words" and elem.text:
                                meta["words"] = elem.text
                            elif tag == "TitlesOfParts":
                                sheets = [c.text for c in elem.iter() if c.text and c.text.strip()]
                                if sheets:
                                    meta["sheets"] = ", ".join(sheets[:5])
                                    
                    if "docProps/core.xml" in names:
                        core_xml = z.read("docProps/core.xml").decode("utf-8", errors="ignore")
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(core_xml)
                        for elem in root.iter():
                            tag = elem.tag.split("}")[-1]
                            if tag == "title" and elem.text:
                                meta["title"] = elem.text
                            elif tag == "creator" and elem.text:
                                meta["author"] = elem.text
            except Exception:
                pass

        # 2. Extract text/metadata from legacy .doc, .rtf, .xls, .csv
        elif ext in (".doc", ".dot"):
            try:
                with open(file_path, "rb") as f:
                    doc_bytes = f.read(256 * 1024)
                meta["text_preview"] = extract_doc_text(doc_bytes)
                meta["title"] = Path(file_path).stem.replace("_", " ")
            except Exception:
                pass
        elif ext in (".rtf",):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    rtf_content = f.read(65536)
                meta["text_preview"] = clean_rtf(rtf_content)[:120]
                meta["title"] = Path(file_path).stem.replace("_", " ")
            except Exception:
                pass
        elif ext in (".xls",):
            try:
                with open(file_path, "rb") as f:
                    xls_bytes = f.read(512 * 1024)
                sheets = extract_xls_sheets(xls_bytes)
                if sheets:
                    meta["sheets"] = ", ".join(sheets[:5])
                meta["title"] = Path(file_path).stem.replace("_", " ")
            except Exception:
                pass
        elif ext in (".csv",):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = [f.readline().strip() for _ in range(3)]
                valid_lines = [l for l in lines if l]
                if valid_lines:
                    meta["text_preview"] = " | ".join(valid_lines[0].split(",")[:4])
                meta["title"] = Path(file_path).stem.replace("_", " ")
            except Exception:
                pass
                
        # 3. Try Windows Shell Image Factory (Cached thumbnail ONLY, never generic icon)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size, thumbnail_only=True)
        if shell_qim and not shell_qim.isNull() and shell_qim.width() > 20:
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="RGB (Office Preview)",
                format_name=fmt_name,
                file_size=size,
                extra_info="Office Document"
            )
            
        # 4. Fallback to Rich Branded Card with extracted metadata/text
        card = cls._create_fallback_card(ext, file_path, size, meta)
        return PreviewResult(
            qimage=card,
            width=card.width(),
            height=card.height(),
            mode="Document Card",
            format_name=fmt_name,
            file_size=size,
            extra_info="Office Document"
        )

class AdobeProjectDecoder:
    """Ultra-fast decoder for Adobe After Effects (.aep) and Premiere Pro (.prproj) projects."""
    
    @staticmethod
    def _parse_aep_details(file_path: str) -> dict:
        info = {'comps': [], 'assets': []}
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                
            items = []
            for match in re.finditer(rb'Utf8', data):
                idx = match.end()
                if idx + 4 <= len(data):
                    length = int.from_bytes(data[idx:idx+4], 'big')
                    if 1 < length < 100 and idx + 4 + length <= len(data):
                        val = data[idx+4:idx+4+length].decode('utf-8', errors='ignore').strip('\x00')
                        if val and len(val) > 1 and not val.startswith('{') and not val.startswith('$') and not val.startswith('http'):
                            if not re.match(r'^[0-9a-fA-F-]{30,}$', val) and not re.match(r'^[0-9a-fA-F]{8,}', val):
                                if val not in ('javascript-1.0', '{}', 'None', '-_0_/-', 'Solids', 'Rec. 709', 'Active', 'Auto', 'High Dynamic Range', 'Lumetri Color', 'Horizontal and Vertical|Horizontal|Vertical', 'Gaussian Blur (Legacy)'):
                                    if val not in items:
                                        items.append(val)
            
            comps = [x for x in items if not x.endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov', '.wav', '.mp3', '.ai', '.psd'))]
            assets = [x for x in items if x.endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov', '.wav', '.mp3', '.ai', '.psd')) or x == 'Solids']
            info['comps'] = comps[:4]
            info['assets'] = assets[:3]
        except Exception:
            pass
        return info

    @staticmethod
    def _create_fallback_card(ext: str, file_path: str, size: int, meta: dict = None) -> QImage:
        w, h = 640, 420
        img = QImage(w, h, QImage.Format.Format_RGB32)
        img.fill(QColor("#090D16"))
        
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        e = ext.lower()
        if e in (".aep", ".aet", ".aepx"):
            grad_c1, grad_c2 = "#31104D", "#1E112A"
            badge_bg, badge_fg = "#130924", "#C084FC"
            app_title = "Adobe After Effects Project"
            icon_char = "Ae"
            item_label = "🎬 Active Compositions & Layers"
        elif e in (".prproj", ".prset"):
            grad_c1, grad_c2 = "#3B0764", "#240046"
            badge_bg, badge_fg = "#20033B", "#F472B6"
            app_title = "Adobe Premiere Pro Project"
            icon_char = "Pr"
            item_label = "🎬 Active Sequences & Timelines"
        else:
            grad_c1, grad_c2 = "#1E293B", "#0F172A"
            badge_bg, badge_fg = "#0F172A", "#38BDF8"
            app_title = "Adobe Video Project"
            icon_char = "Ad"
            item_label = "🎬 Project Sequences"
            
        # 1. Header Banner Gradient
        grad = QLinearGradient(0, 0, w, 84)
        grad.setColorAt(0.0, QColor(grad_c1))
        grad.setColorAt(1.0, QColor(grad_c2))
        painter.fillRect(0, 0, w, 84, grad)
        painter.fillRect(0, 83, w, 1, QColor(badge_fg))
        
        # Emblem Icon Box
        painter.setBrush(QColor(badge_bg))
        painter.setPen(QPen(QColor(badge_fg), 1.5))
        painter.drawRoundedRect(18, 16, 52, 52, 10, 10)
        
        painter.setPen(QColor(badge_fg))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        painter.drawText(18, 16, 52, 52, Qt.AlignmentFlag.AlignCenter, icon_char)
        
        # Header Title
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        painter.drawText(82, 38, app_title)
        
        painter.setPen(QColor("#E2E8F0"))
        painter.setFont(QFont("Segoe UI", 11))
        fname = Path(file_path).name
        painter.drawText(82, 60, fname)
        
        # 2. Extract Project Items
        meta = meta or {}
        comps = meta.get("comps", [])
        if not comps and meta.get("sequence"):
            comps = [meta["sequence"]]
        if not comps:
            comps = [fname.rsplit('.', 1)[0]]
            
        # Section A: Compositions / Sequences Tile
        painter.setBrush(QColor("#111625"))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        painter.drawRoundedRect(18, 100, w - 36, 146, 8, 8)
        
        painter.setPen(QColor(badge_fg))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(32, 126, item_label)
        
        y_comp = 152
        for idx, c in enumerate(comps[:3]):
            painter.setBrush(QColor("#1E1B4B") if icon_char == "Ae" else QColor("#2A0845"))
            painter.setPen(QPen(QColor(badge_fg).darker(150), 1))
            painter.drawRoundedRect(32, y_comp - 15, w - 64, 26, 4, 4)
            
            painter.setPen(QColor(badge_fg))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(42, y_comp + 3, f"#{idx+1}")
            
            painter.setPen(QColor("#F8FAFC"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(72, y_comp + 3, str(c)[:60])
            y_comp += 30
            
        # Section B: Project Stats Tile
        painter.setBrush(QColor("#111625"))
        painter.setPen(QPen(QColor("#1E293B"), 1))
        painter.drawRoundedRect(18, 258, w - 36, 142, 8, 8)
        
        painter.setPen(QColor(badge_fg))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(32, 284, "📊 Project Specifications & Assets")
        
        size_bytes = size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
            
        try:
            mtime = os.path.getmtime(file_path)
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            date_str = "Unknown"
            
        assets = meta.get("assets", [])
        asset_str = ", ".join(assets) if assets else "Project Compositions"
        
        stats = [
            ("📁 File Size:", size_str),
            ("🕒 Modified:", date_str),
            ("📦 Footages / Assets:", asset_str),
        ]
        
        y_stat = 312
        for label, val in stats:
            painter.setPen(QColor("#94A3B8"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.drawText(32, y_stat, 140, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            
            painter.setPen(QColor("#F1F5F9"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold if label != "🕒 Modified:" else QFont.Weight.Normal))
            painter.drawText(180, y_stat, w - 210, 20, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, val[:65])
            y_stat += 26
            
        painter.end()
        return img

    @staticmethod
    def _find_linked_video(file_path: str) -> str:
        parent_dir = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Priority 1: Matching rendered/exported video in project dir or common subdirectories
        search_dirs = [
            parent_dir,
            os.path.join(parent_dir, 'Render'),
            os.path.join(parent_dir, 'Output'),
            os.path.join(parent_dir, 'Export'),
            os.path.join(parent_dir, 'Exports'),
            os.path.join(parent_dir, 'Fills'),
            os.path.join(parent_dir, 'Stock')
        ]
        for sdir in search_dirs:
            if os.path.isdir(sdir):
                for vext in ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'):
                    cand = os.path.join(sdir, base_name + vext)
                    if os.path.exists(cand):
                        return cand
                        
        # Priority 2: Video files referenced inside the project binary
        try:
            with open(file_path, 'rb') as fp:
                data = fp.read()
                
            # Direct absolute paths on disk
            path_refs = re.findall(rb'([A-Za-z]:\\[^:\*\?\"\<\>\|\r\n\x00-\x1f]{3,200}\.(?:mp4|mov|avi|mkv|webm|m4v|wmv))', data, re.IGNORECASE)
            for p_bytes in path_refs:
                cand = p_bytes.decode('utf-8', errors='ignore')
                if os.path.exists(cand):
                    return cand
                    
            # Relative video filenames searched in common folders
            video_refs = re.findall(rb'([A-Za-z0-9_\- ]+\.(?:mp4|mov|avi|mkv|webm|m4v|wmv))', data, re.IGNORECASE)
            for vname_bytes in video_refs:
                vname = vname_bytes.decode('utf-8', errors='ignore')
                for sdir in search_dirs:
                    cand = os.path.join(sdir, vname)
                    if os.path.exists(cand):
                        return cand
        except Exception:
            pass
        return None

    @classmethod
    def decode(cls, file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)
        ext = Path(file_path).suffix.lower()
        fmt_name = ext.lstrip(".").upper()
        
        # 1. Smart Linked Video Playback (Play live video if linked footage or render exists)
        linked_video = cls._find_linked_video(file_path)
        if linked_video and os.path.exists(linked_video):
            v_res = VideoDecoder.decode(linked_video)
            if v_res.is_video:
                return PreviewResult(
                    qimage=v_res.qimage,
                    width=v_res.width,
                    height=v_res.height,
                    mode="Live Footage",
                    format_name=fmt_name,
                    file_size=size,
                    is_video=True,
                    video_path=linked_video,
                    extra_info=f"Linked: {Path(linked_video).name}"
                )
        
        # 2. Extract Composition & Layer Metadata for Typography / Shape visualizer
        meta = {}
        if ext in (".aep", ".aet", ".aepx"):
            meta = cls._parse_aep_details(file_path)
        elif ext in (".prproj", ".prset"):
            try:
                import gzip
                with gzip.open(file_path, 'rb') as gz:
                    content = gz.read(65536).decode('utf-8', errors='ignore')
                    v_match = re.search(r'Version="(\d+)"', content)
                    if v_match:
                        meta["version"] = f"Premiere Pro (Schema v{v_match.group(1)})"
                    s_match = re.search(r'<Sequence[^>]*Name="([^"]+)"', content) or re.search(r'<Name>([^<]+)</Name>', content)
                    if s_match:
                        meta["sequence"] = s_match.group(1)
            except Exception:
                pass
                
        # 3. Try Windows Shell Image Factory STRICTLY for actual rendered project thumbnails (thumbnail_only=True)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size, thumbnail_only=True)
        if shell_qim and not shell_qim.isNull() and shell_qim.width() > 20:
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="RGB (Adobe Preview)",
                format_name=fmt_name,
                file_size=size,
                extra_info="Adobe Project"
            )
            
        # 4. Fallback to Rich Motion Graphics & Typography Showcase Card
        card = cls._create_fallback_card(ext, file_path, size, meta)
        return PreviewResult(
            qimage=card,
            width=card.width(),
            height=card.height(),
            mode="Project Card",
            format_name=fmt_name,
            file_size=size,
            extra_info="Creative Cloud Project"
        )

class DecoderManager:
    """Master decoder dispatching files to the appropriate zero-lag engine."""
    DECODERS = {
        # Photoshop
        ".psd": PsdDecoder,
        ".psb": PsdDecoder,
        # Illustrator & Vector
        ".ai": AiDecoder,
        ".eps": EpsDecoder,
        ".svg": SvgDecoder,
        ".svgz": SvgDecoder,
        # PDF
        ".pdf": PdfDecoder,
        # Microsoft Office & Documents
        ".docx": OfficeDocDecoder,
        ".doc": OfficeDocDecoder,
        ".docm": OfficeDocDecoder,
        ".dotx": OfficeDocDecoder,
        ".dot": OfficeDocDecoder,
        ".rtf": OfficeDocDecoder,
        ".xlsx": OfficeDocDecoder,
        ".xls": OfficeDocDecoder,
        ".xlsm": OfficeDocDecoder,
        ".xlsb": OfficeDocDecoder,
        ".xltx": OfficeDocDecoder,
        ".csv": OfficeDocDecoder,
        ".pptx": OfficeDocDecoder,
        ".ppt": OfficeDocDecoder,
        ".pptm": OfficeDocDecoder,
        ".ppsx": OfficeDocDecoder,
        ".potx": OfficeDocDecoder,
        # Adobe Video & Motion Graphics Projects
        ".aep": AdobeProjectDecoder,
        ".aet": AdobeProjectDecoder,
        ".aepx": AdobeProjectDecoder,
        ".prproj": AdobeProjectDecoder,
        ".prset": AdobeProjectDecoder,
        # Video Formats
        ".mp4": VideoDecoder,
        ".mkv": VideoDecoder,
        ".mov": VideoDecoder,
        ".avi": VideoDecoder,
        ".wmv": VideoDecoder,
        ".webm": VideoDecoder,
        ".m4v": VideoDecoder,
        ".flv": VideoDecoder,
        ".ts": VideoDecoder,
        ".3gp": VideoDecoder,
        ".mpg": VideoDecoder,
        ".mpeg": VideoDecoder,
        # TIFF
        ".tif": TiffDecoder,
        ".tiff": TiffDecoder,
        # Standard & Web Raster Images (Optional, disabled by default in settings)
        ".jpg": StandardImageDecoder,
        ".jpeg": StandardImageDecoder,
        ".png": StandardImageDecoder,
        ".webp": StandardImageDecoder,
        ".gif": StandardImageDecoder,
        ".ico": StandardImageDecoder,
        ".bmp": StandardImageDecoder,
        # Camera RAW
        ".dng": RawCameraDecoder,
        ".cr2": RawCameraDecoder,
        ".cr3": RawCameraDecoder,
        ".crw": RawCameraDecoder,
        ".nef": RawCameraDecoder,
        ".nrw": RawCameraDecoder,
        ".arw": RawCameraDecoder,
        ".srf": RawCameraDecoder,
        ".sr2": RawCameraDecoder,
        ".raf": RawCameraDecoder,
        ".orf": RawCameraDecoder,
        ".ori": RawCameraDecoder,
        ".rw2": RawCameraDecoder,
        ".pef": RawCameraDecoder,
        ".ptx": RawCameraDecoder,
        ".3fr": RawCameraDecoder,
        ".fff": RawCameraDecoder,
        ".iiq": RawCameraDecoder,
        ".raw": RawCameraDecoder,
        ".x3f": RawCameraDecoder,
    }

    @classmethod
    def decode(cls, file_path: str, max_size: int = 1440) -> PreviewResult:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = Path(file_path).suffix.lower()
        decoder = cls.DECODERS.get(ext)
        if not decoder:
            raise ValueError(f"Unsupported file format: {ext}")

        return decoder.decode(file_path, max_size=max_size)
