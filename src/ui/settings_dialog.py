import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox,
    QPushButton, QGroupBox, QGridLayout, QMessageBox, QScrollArea, QWidget,
    QLineEdit, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QPalette
from src.core.config import (
    save_config, SUPPORTED_EXTENSIONS, CACHE_DIR, APP_NAME, APP_VERSION
)
from src.core.autostart import set_autostart, is_autostart_enabled
from src.core.licensing import get_license_status, activate_license, get_machine_id

class SettingsDialog(QDialog):
    """Modern dark-themed preferences dialog for RawView v2.0.1."""
    config_changed = pyqtSignal(dict)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION} - Settings")
        self.setFixedSize(540, 760)
        self._init_style()
        self._init_ui()

    def _init_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0B0E17;
                color: #E2E8F0;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #1E293B;
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 12px;
                font-weight: 600;
                font-size: 13px;
                color: #38BDF8;
                background-color: rgba(15, 23, 42, 0.6);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
            QLabel {
                color: #CBD5E1;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
            QCheckBox {
                color: #F1F5F9;
                font-size: 12px;
                font-weight: 500;
                min-height: 24px;
                padding: 2px 4px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1E293B;
            }
            QCheckBox::indicator:hover {
                border-color: #38BDF8;
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
                padding: 7px 16px;
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
                color: #FFFFFF;
            }
            QPushButton#saveBtn:hover {
                background-color: #0369A1;
            }
            QPushButton#activateBtn {
                background-color: #059669;
                border: 1px solid #10B981;
                color: #FFFFFF;
                font-weight: 700;
            }
            QPushButton#activateBtn:hover {
                background-color: #047857;
            }
        """)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # 1. Pro License & Activation Section
        lic_group = QGroupBox("RawView Pro License (50 TK)", self)
        lic_layout = QVBoxLayout(lic_group)
        lic_layout.setContentsMargins(14, 14, 14, 12)
        lic_layout.setSpacing(8)

        lic_info = get_license_status()

        # Status Header Row
        status_row = QHBoxLayout()
        status_label_title = QLabel("Status:")
        status_label_title.setStyleSheet("font-weight: 600;")
        status_row.addWidget(status_label_title)

        self.status_badge = QLabel(self)
        self.status_badge.setStyleSheet("padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 11px;")
        status_row.addWidget(self.status_badge)
        status_row.addStretch()
        lic_layout.addLayout(status_row)

        # Machine ID Row
        mid_row = QHBoxLayout()
        mid_label = QLabel("Machine Code:")
        self.mid_val = QLineEdit(lic_info.get("machine_id", get_machine_id()))
        self.mid_val.setReadOnly(True)
        self.mid_val.setStyleSheet("color: #38BDF8; font-weight: bold; font-family: monospace;")
        copy_mid_btn = QPushButton("📋 Copy Code")
        copy_mid_btn.clicked.connect(self._copy_machine_id)
        mid_row.addWidget(mid_label)
        mid_row.addWidget(self.mid_val, stretch=1)
        mid_row.addWidget(copy_mid_btn)
        lic_layout.addLayout(mid_row)

        # License Key Input Row (Active if not Pro)
        self.key_input_layout = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Enter Lifetime Pro License Key (e.g. RVPRO-XXXX-XXXX-XXXX)...")
        self.activate_btn = QPushButton("⚡ Activate Pro")
        self.activate_btn.setObjectName("activateBtn")
        self.activate_btn.clicked.connect(self._do_activate_license)
        self.key_input_layout.addWidget(self.key_input, stretch=1)
        self.key_input_layout.addWidget(self.activate_btn)
        lic_layout.addLayout(self.key_input_layout)

        # Payment / Purchase instructions note
        self.pay_note = QLabel(
            "Send 50 TK via bKash / Nagad Personal: <b>017xxxxxxxx</b> (Ref: Your Machine Code), then paste key above."
        )
        self.pay_note.setStyleSheet("color: #94A3B8; font-size: 11px;")
        self.pay_note.setWordWrap(True)
        lic_layout.addWidget(self.pay_note)

        self._refresh_license_ui()
        main_layout.addWidget(lic_group)

        # 2. General Settings
        gen_group = QGroupBox("General Preferences", self)
        gen_layout = QVBoxLayout(gen_group)
        gen_layout.setContentsMargins(14, 12, 14, 10)
        gen_layout.setSpacing(8)

        self.enable_cb = QCheckBox("Enable Mouse Hover Previews", self)
        self.enable_cb.setChecked(self.config.get("enabled", True))
        gen_layout.addWidget(self.enable_cb)

        self.autostart_cb = QCheckBox("Start RawView automatically on Windows boot", self)
        self.autostart_cb.setChecked(is_autostart_enabled())
        gen_layout.addWidget(self.autostart_cb)

        main_layout.addWidget(gen_group)

        # 3. Timing & Performance
        perf_group = QGroupBox("Hover Responsiveness", self)
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.setContentsMargins(14, 12, 14, 10)
        perf_layout.setSpacing(6)

        slider_header = QHBoxLayout()
        slider_label = QLabel("Hover Settle Delay:")
        self.delay_val_label = QLabel(f"{self.config.get('hover_delay_ms', 120)} ms")
        self.delay_val_label.setStyleSheet("color: #38BDF8; font-weight: bold;")
        slider_header.addWidget(slider_label)
        slider_header.addStretch()
        slider_header.addWidget(self.delay_val_label)
        perf_layout.addLayout(slider_header)

        self.delay_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.delay_slider.setRange(40, 350)
        self.delay_slider.setSingleStep(10)
        self.delay_slider.setValue(self.config.get("hover_delay_ms", 120))
        self.delay_slider.valueChanged.connect(lambda val: self.delay_val_label.setText(f"{val} ms"))
        perf_layout.addWidget(self.delay_slider)

        main_layout.addWidget(perf_group)

        # 4. Graphics & Vector Formats
        gfx_group = QGroupBox("Graphics & Design Formats", self)
        gfx_layout = QGridLayout(gfx_group)
        gfx_layout.setContentsMargins(14, 12, 14, 10)
        gfx_layout.setHorizontalSpacing(20)
        gfx_layout.setVerticalSpacing(6)

        self.format_cbs = {}
        active_fmts = set(self.config.get("supported_formats", SUPPORTED_EXTENSIONS.keys()))

        gfx_items = [
            (".psd", "PSD (Adobe Photoshop)"),
            (".psb", "PSB (Large Document)"),
            (".ai",  "AI (Adobe Illustrator)"),
            (".eps", "EPS (PostScript Vector)"),
            (".pdf", "PDF (Vector Document)"),
            (".tiff","TIFF (High-Res Image)"),
            (".svg", "SVG (Scalable Vector)"),
            (".dng", "RAW (Camera RAW Files)"),
        ]

        for idx, (ext, label) in enumerate(gfx_items):
            cb = QCheckBox(label, self)
            cb.setChecked(ext in active_fmts)
            self.format_cbs[ext] = cb
            row = idx // 2
            col = idx % 2
            gfx_layout.addWidget(cb, row, col)

        main_layout.addWidget(gfx_group)

        # 5. Live Video Formats
        vid_group = QGroupBox("Live Video Formats", self)
        vid_layout = QGridLayout(vid_group)
        vid_layout.setContentsMargins(14, 12, 14, 10)
        vid_layout.setHorizontalSpacing(20)
        vid_layout.setVerticalSpacing(6)

        vid_items = [
            (".mp4", "MP4 (MPEG-4 Video)"),
            (".mkv", "MKV (Matroska Video)"),
            (".mov", "MOV (QuickTime Movie)"),
            (".avi", "AVI (Audio Video)"),
            (".webm","WebM (Web Video)"),
            (".wmv", "WMV (Windows Media)"),
            (".flv", "FLV (Flash Video)"),
            (".ts",  "TS (MPEG Stream)"),
        ]

        for idx, (ext, label) in enumerate(vid_items):
            cb = QCheckBox(label, self)
            cb.setChecked(ext in active_fmts)
            self.format_cbs[ext] = cb
            row = idx // 2
            col = idx % 2
            vid_layout.addWidget(cb, row, col)

        main_layout.addWidget(vid_group)

        # 6. Cache Management
        cache_group = QGroupBox("Cache & Storage", self)
        cache_layout = QHBoxLayout(cache_group)
        cache_layout.setContentsMargins(14, 10, 14, 10)

        cache_size_mb = self._get_cache_size_mb()
        self.cache_info_label = QLabel(f"Thumbnail Cache: {cache_size_mb:.1f} MB", self)
        cache_layout.addWidget(self.cache_info_label)
        cache_layout.addStretch()

        clear_btn = QPushButton("Clear Cache", self)
        clear_btn.clicked.connect(self._clear_cache)
        cache_layout.addWidget(clear_btn)

        main_layout.addWidget(cache_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel", self)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save & Apply", self)
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self._save_and_apply)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

    def _refresh_license_ui(self):
        lic_info = get_license_status()
        status = lic_info.get("status")

        if status == "PRO_ACTIVE":
            self.status_badge.setText("✨ LIFETIME PRO ACTIVATED")
            self.status_badge.setStyleSheet("background-color: #064E3B; color: #34D399; border: 1px solid #10B981; padding: 3px 8px; border-radius: 4px; font-weight: 700;")
            self.key_input.setVisible(False)
            self.activate_btn.setVisible(False)
            self.pay_note.setText("Your copy of RawView is fully activated with Lifetime Pro access. Thank you!")
            self.pay_note.setStyleSheet("color: #34D399; font-size: 11px; font-weight: 600;")
        elif status == "TRIAL_ACTIVE":
            days = lic_info.get("days_left", 7)
            self.status_badge.setText(f"⏳ 7-DAY FREE TRIAL ({days} DAYS LEFT)")
            self.status_badge.setStyleSheet("background-color: #0C4A6E; color: #38BDF8; border: 1px solid #0284C7; padding: 3px 8px; border-radius: 4px; font-weight: 700;")
            self.key_input.setVisible(True)
            self.activate_btn.setVisible(True)
        else:
            self.status_badge.setText("🔒 TRIAL EXPIRED (ACTIVATION REQUIRED)")
            self.status_badge.setStyleSheet("background-color: #4C0519; color: #FB7185; border: 1px solid #E11D48; padding: 3px 8px; border-radius: 4px; font-weight: 700;")
            self.key_input.setVisible(True)
            self.activate_btn.setVisible(True)

    def _copy_machine_id(self):
        mid = self.mid_val.text()
        QApplication.clipboard().setText(mid)
        QMessageBox.information(self, "Copied", f"Machine Code '{mid}' copied to clipboard!\nSend this code to the seller via WhatsApp/SMS after 50 TK bKash/Nagad payment.")

    def _do_activate_license(self):
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Input Required", "Please enter the Pro License Key sent by the seller.")
            return

        success, msg = activate_license(key)
        if success:
            QMessageBox.information(self, "Congratulations!", msg)
            self._refresh_license_ui()
        else:
            QMessageBox.warning(self, "Activation Failed", msg)

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
            self.cache_info_label.setText("Thumbnail Cache: 0.0 MB")
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
                elif ext == ".mp4":
                    selected.append(".m4v")
                elif ext == ".dng":
                    selected.extend([".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2", ".raf", ".orf", ".ori", ".rw2", ".pef", ".ptx", ".3fr", ".fff", ".iiq", ".raw", ".x3f"])
        self.config["supported_formats"] = selected

        # Autostart
        autostart_wanted = self.autostart_cb.isChecked()
        self.config["autostart"] = autostart_wanted
        set_autostart(autostart_wanted)

        save_config(self.config)
        self.config_changed.emit(self.config)
        self.accept()


