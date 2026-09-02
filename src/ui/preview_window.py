import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsDropShadowEffect,
    QApplication, QFrame
)
from PyQt6.QtCore import (
    Qt, QPoint, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QFont, QBrush, QPen, QImage, QPainterPath,
    QKeySequence, QShortcut, QLinearGradient
)
from src.core.decoders import PreviewResult
from src.utils.win32_helper import calculate_popup_position

FORMAT_COLORS = {
    "PSD": ("#00C8FF", "#002B4D"),
    "PSB": ("#00C8FF", "#002B4D"),
    "AI":  ("#FF9A00", "#4A2400"),
    "EPS": ("#A855F7", "#3B0764"),
    "PDF": ("#EF4444", "#450A0A"),
    "TIFF":("#10B981", "#064E3B"),
    "TIF": ("#10B981", "#064E3B"),
    "SVG": ("#F43F5E", "#4C0519"),
    "SVGZ":("#F43F5E", "#4C0519"),
    # Camera RAW
    "DNG": ("#F59E0B", "#451A03"),
    "CR2": ("#F59E0B", "#451A03"),
    "CR3": ("#F59E0B", "#451A03"),
    "CRW": ("#F59E0B", "#451A03"),
    "NEF": ("#F59E0B", "#451A03"),
    "NRW": ("#F59E0B", "#451A03"),
    "ARW": ("#F59E0B", "#451A03"),
    "SRF": ("#F59E0B", "#451A03"),
    "SR2": ("#F59E0B", "#451A03"),
    "RAF": ("#F59E0B", "#451A03"),
    "ORF": ("#F59E0B", "#451A03"),
    "ORI": ("#F59E0B", "#451A03"),
    "RW2": ("#F59E0B", "#451A03"),
    "PEF": ("#F59E0B", "#451A03"),
    "PTX": ("#F59E0B", "#451A03"),
    "3FR": ("#F59E0B", "#451A03"),
    "FFF": ("#F59E0B", "#451A03"),
    "IIQ": ("#F59E0B", "#451A03"),
    "RAW": ("#F59E0B", "#451A03"),
    "X3F": ("#F59E0B", "#451A03"),
}

class ImageCanvas(QLabel):
    """
    High-definition viewport widget displaying images with alpha checkerboard,
    zero-pixelation scaling from full-resolution master buffer, and mouse drag-to-pan.
    """
    zoom_changed = pyqtSignal(int) # Emits zoom percentage (e.g. 100, 150, 200)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(280, 200)
        self.setMouseTracking(True)

        self._source_qimage = QImage()
        self._cached_pixmap = QPixmap()
        self.zoom_factor = 1.0
        self.max_display_w = 640
        self.max_display_h = 480

        self._pan_offset = QPoint(0, 0)
        self._is_panning = False
        self._drag_start_pos = QPoint()
        self._drag_start_offset = QPoint()

    def set_image(self, qimage: QImage, max_w: int = 640, max_h: int = 480):
        self._source_qimage = qimage.copy() if not qimage.isNull() else QImage()
        self.max_display_w = max_w
        self.max_display_h = max_h
        self.reset_view()

    def reset_view(self):
        self.zoom_factor = 1.0
        self._pan_offset = QPoint(0, 0)
        self._is_panning = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._update_scaled_pixmap()
        self.zoom_changed.emit(100)
        self.update()

    def _get_base_fitted_size(self) -> QSize:
        if self._source_qimage.isNull():
            return QSize(self.max_display_w, self.max_display_h)
        orig_w = self._source_qimage.width()
        orig_h = self._source_qimage.height()
        if orig_w <= 0 or orig_h <= 0:
            return QSize(self.max_display_w, self.max_display_h)

        aspect = orig_w / orig_h
        if (self.max_display_w / max(self.max_display_h, 1)) > aspect:
            h = min(orig_h, self.max_display_h)
            w = int(h * aspect)
        else:
            w = min(orig_w, self.max_display_w)
            h = int(w / aspect)
        return QSize(max(w, 50), max(h, 50))

    def _update_scaled_pixmap(self):
        if self._source_qimage.isNull():
            self._cached_pixmap = QPixmap()
            return

        base_sz = self._get_base_fitted_size()
        target_w = max(int(base_sz.width() * self.zoom_factor), 10)
        target_h = max(int(base_sz.height() * self.zoom_factor), 10)

        # Scale directly from full-resolution master buffer with smooth bilinear antialiasing
        scaled_qim = self._source_qimage.scaled(
            target_w, target_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._cached_pixmap = QPixmap.fromImage(scaled_qim)

    def zoom(self, factor: float, center_point: QPoint = None):
        old_zoom = self.zoom_factor
        self.zoom_factor = max(0.5, min(self.zoom_factor * factor, 8.0))
        
        if abs(self.zoom_factor - old_zoom) > 0.001:
            self._update_scaled_pixmap()
            self._clamp_pan()
            self.zoom_changed.emit(int(round(self.zoom_factor * 100)))
            
            if self.zoom_factor > 1.0:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def _clamp_pan(self):
        if self._cached_pixmap.isNull():
            self._pan_offset = QPoint(0, 0)
            return

        vw = self.width()
        vh = self.height()
        pw = self._cached_pixmap.width()
        ph = self._cached_pixmap.height()

        if pw <= vw:
            max_x = 0
            min_x = 0
        else:
            max_x = (pw - vw) // 2
            min_x = -max_x

        if ph <= vh:
            max_y = 0
            min_y = 0
        else:
            max_y = (ph - vh) // 2
            min_y = -max_y

        clamped_x = max(min_x, min(self._pan_offset.x(), max_x))
        clamped_y = max(min_y, min(self._pan_offset.y(), max_y))
        self._pan_offset = QPoint(clamped_x, clamped_y)

    def mousePressEvent(self, event):
        if event.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton):
            if self.zoom_factor > 1.0:
                self._is_panning = True
                self._drag_start_pos = event.pos()
                self._drag_start_offset = QPoint(self._pan_offset)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.pos() - self._drag_start_pos
            self._pan_offset = self._drag_start_offset + delta
            self._clamp_pan()
            self.update()
            event.accept()
            return
        elif self.zoom_factor > 1.0:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_panning:
            self._is_panning = False
            if self.zoom_factor > 1.0:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Double click resets zoom and pan
        self.reset_view()
        event.accept()

    def sizeHint(self) -> QSize:
        if self._source_qimage.isNull():
            return QSize(self.max_display_w, self.max_display_h)
        return self._get_base_fitted_size()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw subtle checkerboard pattern for alpha transparency
        rect = self.rect()
        tile_size = 12
        light_color = QColor(25, 29, 40)
        dark_color = QColor(18, 21, 30)

        for x in range(0, rect.width(), tile_size):
            for y in range(0, rect.height(), tile_size):
                color = light_color if ((x // tile_size) + (y // tile_size)) % 2 == 0 else dark_color
                painter.fillRect(x, y, tile_size, tile_size, color)

        # Draw high-definition scaled pixmap with pan offset
        if not self._cached_pixmap.isNull():
            draw_x = (rect.width() - self._cached_pixmap.width()) // 2 + self._pan_offset.x()
            draw_y = (rect.height() - self._cached_pixmap.height()) // 2 + self._pan_offset.y()
            painter.drawPixmap(draw_x, draw_y, self._cached_pixmap)

        painter.end()

class FloatingPreviewHUD(QWidget):
    """
    Hardware-accelerated, glassmorphic floating preview window for RawView.
    """
    pin_state_changed = pyqtSignal(bool)
    visibility_changed = pyqtSignal(bool)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.max_view_size = config.get("preview_max_size", 640)
        self.is_pinned = False
        self.current_file_path = ""
        self.current_result = None

        self._init_window_flags()
        self._init_ui()
        self._init_animations()
        self._init_shortcuts()

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.ToolTip |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _init_ui(self):
        # Main Outer Container
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame(self)
        self.container.setObjectName("container")
        self.container.setStyleSheet("""
            #container {
                background-color: rgba(15, 18, 28, 0.96);
                border: 1px solid rgba(80, 120, 200, 0.35);
                border-radius: 14px;
            }
        """)

        # Drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 12, 14, 12)
        container_layout.setSpacing(10)

        # 1. Header Bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Format Badge
        self.format_badge = QLabel("PSD", self)
        self.format_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.format_badge.setStyleSheet("""
            background-color: #002B4D;
            color: #00C8FF;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 5px;
            border: 1px solid rgba(0, 200, 255, 0.3);
        """)
        header_layout.addWidget(self.format_badge)

        # File Name Label
        self.title_label = QLabel("file_preview.psd", self)
        self.title_label.setStyleSheet("""
            color: #F0F4F8;
            font-size: 13px;
            font-weight: 600;
        """)
        header_layout.addWidget(self.title_label, stretch=1)

        # Pin Status Indicator
        self.pin_label = QLabel("Space to Pin", self)
        self.pin_label.setStyleSheet("""
            color: #64748B;
            font-size: 10px;
            font-weight: 500;
            padding: 2px 6px;
            border-radius: 4px;
            background-color: rgba(255, 255, 255, 0.05);
        """)
        header_layout.addWidget(self.pin_label)

        container_layout.addLayout(header_layout)

        # 2. Main Viewport
        self.canvas = ImageCanvas(self)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        self.canvas.setStyleSheet("""
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            background-color: #12151E;
        """)
        container_layout.addWidget(self.canvas, stretch=1)

        # 3. Metadata Footer Bar
        self.footer_layout = QHBoxLayout()
        self.footer_layout.setSpacing(12)

        self.dim_label = QLabel("3840 × 2160 px", self)
        self.dim_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        self.footer_layout.addWidget(self.dim_label)

        self.mode_label = QLabel("RGB", self)
        self.mode_label.setStyleSheet("color: #94A3B8; font-size: 11px; font-weight: 500;")
        self.footer_layout.addWidget(self.mode_label)

        # Zoom Level Badge
        self.zoom_badge = QLabel("100%", self)
        self.zoom_badge.setStyleSheet("""
            color: #A78BFA;
            font-size: 10px;
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 3px;
            background-color: rgba(167, 139, 250, 0.15);
        """)
        self.footer_layout.addWidget(self.zoom_badge)

        self.footer_layout.addStretch()

        self.size_label = QLabel("14.5 MB", self)
        self.size_label.setStyleSheet("color: #38BDF8; font-size: 11px; font-weight: 600;")
        self.footer_layout.addWidget(self.size_label)

        container_layout.addLayout(self.footer_layout)
        self.main_layout.addWidget(self.container)

    def _init_animations(self):
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(120)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _init_shortcuts(self):
        # Space: Pin / Unpin
        self.pin_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.pin_shortcut.activated.connect(self.toggle_pin)

        # Esc: Dismiss
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.activated.connect(self.dismiss)

        # Ctrl+C: Copy Image
        self.copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        self.copy_shortcut.activated.connect(self.copy_image_to_clipboard)

        # Ctrl+O / Return: Open File
        self.open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.open_shortcut.activated.connect(self.open_current_file)

    def _on_zoom_changed(self, percent: int):
        self.zoom_badge.setText(f"{percent}%")
        if percent != 100:
            self.zoom_badge.setStyleSheet("""
                color: #F59E0B;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 5px;
                border-radius: 3px;
                background-color: rgba(245, 158, 11, 0.2);
            """)
        else:
            self.zoom_badge.setStyleSheet("""
                color: #A78BFA;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 5px;
                border-radius: 3px;
                background-color: rgba(167, 139, 250, 0.15);
            """)

    def display_preview(self, file_path: str, result: PreviewResult, cursor_x: int, cursor_y: int):
        self.current_file_path = file_path
        self.current_result = result

        # Update Header
        fname = Path(file_path).name if not file_path.startswith("ftp://") else file_path.split("/")[-1]
        self.title_label.setText(fname)
        self.title_label.setToolTip(file_path)

        fmt = result.format_name.upper()
        self.format_badge.setText(fmt)
        fg_col, bg_col = FORMAT_COLORS.get(fmt, ("#F59E0B", "#451A03"))
        self.format_badge.setStyleSheet(f"""
            background-color: {bg_col};
            color: {fg_col};
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 5px;
            border: 1px solid {fg_col}55;
        """)

        # Update Image Canvas with high-resolution master buffer
        self.canvas.set_image(result.qimage, max_w=self.max_view_size, max_h=int(self.max_view_size * 0.75))

        # Update Metadata
        self.dim_label.setText(result.dimensions_str)
        self.mode_label.setText(result.mode)
        self.size_label.setText(result.formatted_size)

        # Auto-adjust window size
        self.adjustSize()
        w = self.width()
        h = self.height()

        # Position cleanly near cursor
        pos = calculate_popup_position(cursor_x, cursor_y, w, h)
        self.move(pos)

        # Display window
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self.visibility_changed.emit(True)

    def toggle_pin(self):
        if not self.isVisible():
            return
        self.is_pinned = not self.is_pinned
        self.pin_state_changed.emit(self.is_pinned)
        
        if self.is_pinned:
            self.pin_label.setText("PINNED (Space to Unpin)")
            self.pin_label.setStyleSheet("""
                color: #38BDF8;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 4px;
                background-color: rgba(56, 189, 248, 0.2);
                border: 1px solid rgba(56, 189, 248, 0.4);
            """)
            self.activateWindow()
        else:
            self.pin_label.setText("Space to Pin")
            self.pin_label.setStyleSheet("""
                color: #64748B;
                font-size: 10px;
                font-weight: 500;
                padding: 2px 6px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.05);
            """)
            # Immediately dismiss preview upon unpinning
            self.dismiss()

    def dismiss(self):
        self.is_pinned = False
        self.pin_state_changed.emit(False)
        self.canvas.reset_view()
        self.hide()
        self.visibility_changed.emit(False)

    def copy_image_to_clipboard(self):
        if self.current_result and not self.current_result.qimage.isNull():
            clipboard = QApplication.clipboard()
            clipboard.setImage(self.current_result.qimage)

    def open_current_file(self):
        if self.current_file_path and os.path.exists(self.current_file_path):
            os.startfile(self.current_file_path)
            self.dismiss()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.canvas.zoom(1.2)
        elif delta < 0:
            self.canvas.zoom(0.83)
        event.accept()
