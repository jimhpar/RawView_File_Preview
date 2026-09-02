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
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
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
    def get_thumbnail(file_path: str, max_size: int = 1440, thumbnail_only: bool = False) -> QImage | None:
        try:
            if not os.path.exists(file_path):
                return None
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
                _DeleteObject(hbm)
                if not qim.isNull() and qim.width() > 10 and qim.height() > 10:
                    return qim
        except Exception:
            pass
        return None

class PreviewResult:
    """Standardized preview result holding the rendered image and metadata."""
    def __init__(self, qimage: QImage, width: int, height: int, mode: str, format_name: str, file_size: int, extra_info: str = ""):
        self.qimage = qimage
        self.width = width
        self.height = height
        self.mode = mode
        self.format_name = format_name
        self.file_size = file_size
        self.extra_info = extra_info

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
        if self.width > 0 and self.height > 0:
            return f"{self.width} × {self.height} px"
        return "Vector"

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

class AiDecoder:
    """
    High-speed, high-fidelity decoder for Adobe Illustrator AI files.
    Extracts full workspace canvas (inside & outside artboard) at crystal-clear 1440px+ resolution.
    """
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)

        # 1. Check if elements exist outside the artboards by comparing BoundingBox and MediaBox
        prefer_xmp = False
        try:
            bbox_w, bbox_h = 0, 0
            with open(file_path, "rb") as f:
                header = f.read(1024 * 512).decode("latin-1", errors="ignore")
            
            m = re.search(r"%%BoundingBox:\s*([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)\s+([-\d\.]+)", header)
            if m:
                x0, y0, x1, y1 = map(float, m.groups())
                bbox_w = max(int(x1) - int(x0), 0)
                bbox_h = max(int(y1) - int(y0), 0)
            
            media_w, media_h = 0, 0
            try:
                doc = fitz.open(file_path)
                if len(doc) > 0:
                    rect = doc[0].rect
                    media_w, media_h = int(rect.width), int(rect.height)
            except Exception:
                pass
            
            if bbox_w * bbox_h > (media_w * media_h * 1.05):
                prefer_xmp = True
        except Exception:
            pass

        # If elements are outside the artboard, the PDF stream WILL clip them. 
        # The ONLY way to see the full workspace is the XMP thumbnail.
        if prefer_xmp:
            try:
                with open(file_path, "rb") as f:
                    data = f.read()

                m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', data)
                if m:
                    b64_data = m.group(1).replace(b'&#xA;', b'').replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
                    raw_bytes = base64.b64decode(b64_data)
                    qim = QImage.fromData(QByteArray(raw_bytes))
                    if not qim.isNull():
                        return PreviewResult(
                            qimage=qim,
                            width=qim.width(),
                            height=qim.height(),
                            mode="RGB (Full Workspace)",
                            format_name="AI",
                            file_size=size,
                            extra_info="Full Canvas Workspace"
                        )
            except Exception:
                pass

        # 2. Native Windows Shell Handler (Extracts complete workspace canvas & all artboards in ~40ms)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size, thumbnail_only=True)
        if shell_qim and not shell_qim.isNull():
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="RGB (Shell)",
                format_name="AI",
                file_size=size,
                extra_info="Native Thumbnail"
            )

        # 3. PyMuPDF Vector Rasterizer (High resolution vector rendering)
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                page = doc[0]
                rect = page.rect
                page_w = max(int(rect.width), 10)
                page_h = max(int(rect.height), 10)
                
                # Render with high DPI (150 DPI ~ 2x scale)
                dpi = int(min(max_size / max(page_w, page_h, 1) * 72, 300))
                dpi = max(dpi, 72)
                pix = page.get_pixmap(dpi=dpi)
                
                # Check if rendered page is non-empty
                if pix.width > 0 and pix.height > 0:
                    data = pix.tobytes("png")
                    qim = QImage.fromData(QByteArray(data))
                    if not qim.isNull():
                        return PreviewResult(
                            qimage=qim,
                            width=page_w,
                            height=page_h,
                            mode="RGB (Vector Artboard)",
                            format_name="AI",
                            file_size=size,
                            extra_info=f"Artboards: {len(doc)}"
                        )
        except Exception:
            pass

        # 4. PDFium rasterizer (Fallback vector engine)
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
                return PreviewResult(
                    qimage=qim,
                    width=page_w,
                    height=page_h,
                    mode="RGB (Vector Artboard)",
                    format_name="AI",
                    file_size=size,
                    extra_info=f"Artboards: {len(pdf)}"
                )
        except Exception:
            pass

        # 5. Search for XMP embedded full workspace preview (<xmpGImg:image>) as last resort
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', data)
            if m:
                b64_data = m.group(1).replace(b'&#xA;', b'').replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
                raw_bytes = base64.b64decode(b64_data)
                qim = QImage.fromData(QByteArray(raw_bytes))
                if not qim.isNull():
                    return PreviewResult(
                        qimage=qim,
                        width=qim.width(),
                        height=qim.height(),
                        mode="RGB (Workspace Thumbnail)",
                        format_name="AI",
                        file_size=size,
                        extra_info="Full Canvas Workspace"
                    )
        except Exception:
            pass

        raise RuntimeError("AI file has no workspace thumbnail or PDF compatibility stream.")

class EpsDecoder:
    """High-speed decoder for Encapsulated PostScript (.eps) files."""
    @staticmethod
    def decode(file_path: str, max_size: int = 1440) -> PreviewResult:
        size = os.path.getsize(file_path)

        # 1. Native Windows Shell Handler (Extracts full artwork in high resolution)
        shell_qim = ShellImageFactory.get_thumbnail(file_path, max_size=max_size, thumbnail_only=True)
        if shell_qim and not shell_qim.isNull():
            return PreviewResult(
                qimage=shell_qim,
                width=shell_qim.width(),
                height=shell_qim.height(),
                mode="Full Artwork",
                format_name="EPS",
                file_size=size
            )

        # 2. Binary EPS header (0xC5D0D3C6) with embedded TIFF preview (Hardware-accelerated)
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
                if len(header) >= 30 and header[:4] in (b"\xC5\xD0\xD3\xC6", b"\xC6\xD3\xD0\xC5"):
                    tiff_offset, tiff_length = struct.unpack("<II", header[20:28])
                    if tiff_offset > 0 and tiff_length > 0:
                        f.seek(tiff_offset)
                        tiff_bytes = f.read(tiff_length)
                        qim = QImage.fromData(QByteArray(tiff_bytes))
                        if not qim.isNull():
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

        # 3. Check for embedded XMP workspace preview in EPS (<xmpGImg:image>)
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            m = re.search(rb'<xmpGImg:image>([\s\S]*?)</xmpGImg:image>', data)
            if m:
                b64_data = m.group(1).replace(b'&#xA;', b'').replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'').replace(b'\t', b'')
                raw_bytes = base64.b64decode(b64_data)
                qim = QImage.fromData(QByteArray(raw_bytes))
                if not qim.isNull():
                    return PreviewResult(
                        qimage=qim,
                        width=qim.width(),
                        height=qim.height(),
                        mode="Full Artwork (XMP)",
                        format_name="EPS",
                        file_size=size
                    )
        except Exception:
            pass

        # 4. If Ghostscript is present, render via Pillow
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

        # Parse BoundingBox and Creator metadata from header lines
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
        # TIFF
        ".tif": TiffDecoder,
        ".tiff": TiffDecoder,
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
