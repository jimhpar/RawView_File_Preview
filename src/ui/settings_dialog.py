import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QGroupBox, QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QPalette
from src.core.config import (
    save_config, SUPPORTED_EXTENSIONS, CACHE_DIR, APP_NAME, APP_VERSION
)
from src.core.autostart import set_autostart, is_autostart_enabled

class SettingsDialog(QDialog):
    """Modern dark-themed preferences dialog for RawView."""
    config_changed = pyqtSignal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} - Settings")
        self.setFixedSize(480, 520)
        self._init_style()
        self._init_ui()

    def _init_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0F121C;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #1E293B;
                border-radius: 8px;
                margin-top: 18px;
                padding-top: 14px;
                font-weight: 600;
                color: #38BDF8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QLabel {
                color: #CBD5E1;
                font-size: 12px;
            }
            QCheckBox {
                color: #F1F5F9;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1E293B;
            }
            QCheckBox::indicator:checked {
                background-color: #38BDF8;
                border-color: #38BDF8;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #1E293B;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #38BDF8;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 2px solid #38BDF8;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #64748B;
            }
            QPushButton#saveBtn {
                background-color: #0284C7;
                border: 1px solid #38BDF8;
            }
            QPushButton#saveBtn:hover {
                background-color: #0369A1;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. General Settings
        gen_group = QGroupBox("General Options", self)
        gen_layout = QVBoxLayout(gen_group)
        gen_layout.setSpacing(12)

        self.enable_cb = QCheckBox("Enable Mouse Hover Previews", self)
        self.enable_cb.setChecked(self.config.get("enabled", True))
        gen_layout.addWidget(self.enable_cb)

        self.autostart_cb = QCheckBox("Start RawView automatically with Windows", self)
        self.autostart_cb.setChecked(is_autostart_enabled())
        gen_layout.addWidget(self.autostart_cb)

        layout.addWidget(gen_group)

        # 2. Timing & Performance
        perf_group = QGroupBox("Hover Responsiveness", self)
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.setSpacing(8)

        slider_header = QHBoxLayout()
        slider_label = QLabel("Hover Settle Delay:")
        self.delay_val_label = QLabel(f"{self.config.get('hover_delay_ms', 150)} ms")
        self.delay_val_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
        slider_header.addWidget(slider_label)
        slider_header.addStretch()
        slider_header.addWidget(self.delay_val_label)
        perf_layout.addLayout(slider_header)

        self.delay_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.delay_slider.setRange(50, 400)
        self.delay_slider.setSingleStep(10)
        self.delay_slider.setValue(self.config.get("hover_delay_ms", 150))
        self.delay_slider.valueChanged.connect(lambda val: self.delay_val_label.setText(f"{val} ms"))
        perf_layout.addWidget(self.delay_slider)

        layout.addWidget(perf_group)

        # 3. Supported Formats
        fmt_group = QGroupBox("Enabled File Formats", self)
        fmt_layout = QGridLayout(fmt_group)
        fmt_layout.setSpacing(10)

        self.format_cbs = {}
        active_fmts = set(self.config.get("supported_formats", SUPPORTED_EXTENSIONS.keys()))

        ext_list = [".psd", ".psb", ".ai", ".eps", ".tiff", ".svg"]
        row, col = 0, 0
        for ext in ext_list:
            cb = QCheckBox(f"{ext.upper()} ({SUPPORTED_EXTENSIONS.get(ext, '')})", self)
            cb.setChecked(ext in active_fmts)
            self.format_cbs[ext] = cb
            fmt_layout.addWidget(cb, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        layout.addWidget(fmt_group)

        # 4. Cache & Storage
        cache_group = QGroupBox("Cache Management", self)
        cache_layout = QHBoxLayout(cache_group)

        cache_size_mb = self._get_cache_size_mb()
        self.cache_info_label = QLabel(f"Current Cache: {cache_size_mb:.1f} MB", self)
        cache_layout.addWidget(self.cache_info_label)
        cache_layout.addStretch()

        clear_btn = QPushButton("Clear Cache", self)
        clear_btn.clicked.connect(self._clear_cache)
        cache_layout.addWidget(clear_btn)

        layout.addWidget(cache_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save & Apply", self)
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _get_cache_size_mb(self) -> float:
        total = 0
        if CACHE_DIR.exists():
            for f in CACHE_DIR.glob("*"):
                if f.is_file():
                    total += f.stat().st_size
        return total / (1024.0 * 1024.0)

    def _clear_cache(self):
        try:
            for f in CACHE_DIR.glob("*"):
                if f.is_file():
                    f.unlink(missing_ok=True)
            self.cache_info_label.setText("Current Cache: 0.0 MB")
            QMessageBox.information(self, "Cache Cleared", "Thumbnail cache has been successfully wiped.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to clear cache: {e}")

    def _save_and_apply(self):
        self.config["enabled"] = self.enable_cb.isChecked()
        self.config["hover_delay_ms"] = self.delay_slider.value()

        # Update formats
        selected = []
        for ext, cb in self.format_cbs.items():
            if cb.isChecked():
                selected.append(ext)
                if ext == ".tiff":
                    selected.append(".tif")
                elif ext == ".svg":
                    selected.append(".svgz")
        self.config["supported_formats"] = selected

        # Autostart
        autostart_wanted = self.autostart_cb.isChecked()
        self.config["autostart"] = autostart_wanted
        set_autostart(autostart_wanted)

        save_config(self.config)
        self.config_changed.emit(self.config)
        self.accept()
