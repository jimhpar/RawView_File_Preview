"""
Instant On-Screen Status HUD Toast for RawView
Displays an ultra-responsive, sleek glassmorphic pill badge when hover preview is toggled.
"""
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect, QApplication
from PyQt6.QtGui import QColor, QFont, QCursor, QPainter, QBrush, QPen

class StatusToastHUD(QWidget):
    _instance = None

    @classmethod
    def show_status(cls, enabled: bool):
        """Static helper to show or update the singleton on-screen toast."""
        if cls._instance is not None:
            try:
                cls._instance.close()
            except Exception:
                pass
            cls._instance = None

        toast = cls(enabled)
        cls._instance = toast
        toast.show_animated()

    def __init__(self, enabled: bool, parent=None):
        super().__init__(parent)
        self.enabled = enabled

        # Frameless, transparent, always-on-top, non-activating tooltip
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        # Status Dot
        self.dot = QLabel(self)
        self.dot.setFixedSize(10, 10)
        dot_color = "#10B981" if self.enabled else "#F59E0B"
        self.dot.setStyleSheet(f"""
            background-color: {dot_color};
            border-radius: 5px;
            border: 1px solid rgba(255, 255, 255, 0.4);
        """)
        layout.addWidget(self.dot)

        # Status Text
        self.label = QLabel(self)
        status_text = "RawView Hover Preview: Active" if self.enabled else "RawView Hover Preview: Paused"
        text_color = "#F8FAFC" if self.enabled else "#CBD5E1"
        self.label.setText(status_text)
        font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        self.label.setFont(font)
        self.label.setStyleSheet(f"color: {text_color}; background: transparent;")
        layout.addWidget(self.label)

        # Hotkey Badge
        self.badge = QLabel("Ctrl + `", self)
        self.badge.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.badge.setStyleSheet("""
            color: #94A3B8;
            background-color: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 4px;
            padding: 2px 6px;
        """)
        layout.addWidget(self.badge)

        self.adjustSize()

        # Opacity effect for animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Position on the screen where cursor currently dwells
        self._position_on_screen()

    def _position_on_screen(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + 45
            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dark glassmorphic capsule background
        bg_color = QColor(15, 23, 42, 235) # Slate 900 with high opacity
        border_color = QColor(56, 189, 248, 80) if self.enabled else QColor(100, 116, 139, 80)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2.0

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(rect, radius, radius)

    def show_animated(self):
        self.show()

        # Fade in
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(120)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_in.start()

        # Hold timer before fade-out
        QTimer.singleShot(1100, self._start_fade_out)

    def _start_fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(250)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.Type.InQuad)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()
