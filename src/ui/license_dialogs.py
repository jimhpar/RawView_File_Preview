"""
Online Licensing, Sign-In, Device Management & Legacy Migration Dialogs for RawView.
Integrates seamlessly with blackboxthc.com.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from src.core.config import APP_NAME, ONLINE_LICENSE_CONFIG
from src.core.licensing import (
    online_sign_in,
    fetch_registered_devices,
    logout_remote_device,
    get_machine_id,
    initiate_claim_ticket,
    LEGACY_MIGRATION_MESSAGE,
)

DIALOG_STYLE = """
    QDialog {
        background-color: #0B1120;
        color: #E2E8F0;
        font-family: 'Segoe UI', sans-serif;
    }
    QLabel {
        color: #E2E8F0;
    }
    QLineEdit {
        background-color: #111827;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 10px;
        color: #F8FAFC;
        font-size: 12px;
    }
    QLineEdit:focus {
        border-color: #38BDF8;
    }
    QPushButton {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px 14px;
        font-weight: 600;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #334155;
        border-color: #475569;
    }
    QPushButton:disabled {
        opacity: 0.5;
        color: #64748B;
    }
    QPushButton#primaryBtn {
        background-color: #0284C7;
        border-color: #0369A1;
        color: #FFFFFF;
    }
    QPushButton#primaryBtn:hover {
        background-color: #0369A1;
    }
    QPushButton#buyBtn {
        background-color: #10B981;
        border-color: #059669;
        color: #FFFFFF;
    }
    QPushButton#buyBtn:hover {
        background-color: #059669;
    }
    QPushButton#dangerBtn {
        background-color: #7F1D1D;
        border-color: #B91C1C;
        color: #FEE2E2;
        padding: 6px 10px;
        font-size: 11px;
    }
    QPushButton#dangerBtn:hover {
        background-color: #991B1B;
    }
"""


class _SignInWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, email: str, password: str, parent=None):
        super().__init__(parent)
        self.email = email
        self.password = password

    def run(self):
        res = online_sign_in(self.email, self.password)
        self.finished.emit(res)


class _DeviceLogoutWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, target_id: str, email: str = "", password: str = "", parent=None):
        super().__init__(parent)
        self.target_id = target_id
        self.email = email
        self.password = password

    def run(self):
        res = logout_remote_device(self.target_id, email=self.email, password=self.password)
        self.finished.emit(res)


class _FetchDevicesWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        res = fetch_registered_devices()
        self.finished.emit(res)


class DeviceLimitDialog(QDialog):
    """
    Shown when a user tries to sign in on a new PC but their BlackBox THC device limit is full.
    Allows logging out any existing device directly from the new PC and immediately signing in.
    """
    def __init__(self, email: str, password: str, devices: list, device_limit: int, parent=None):
        super().__init__(parent)
        self.email = email
        self.password = password
        self.devices = devices or []
        self.device_limit = device_limit
        self.signed_in_ok = False
        self._worker = None
        self._login_worker = None

        self.setWindowTitle(f"{APP_NAME} - Device Limit Reached")
        self.setFixedSize(480, 400)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        count = len(self.devices) if self.devices else self.device_limit
        header_txt = (
            "Already logged in to another device"
            if self.device_limit == 1
            else f"Already logged in to {count} / {self.device_limit} devices"
        )
        title = QLabel(f"⚠️ {header_txt}")
        title.setStyleSheet("color: #FBBF24; font-size: 15px; font-weight: 700;")
        layout.addWidget(title)

        sub = QLabel(
            "Your RawView license has reached its maximum device limit. "
            "Sign out an existing device below to register and activate this PC immediately."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(container)
        self.list_layout.setContentsMargins(0, 4, 4, 4)
        self.list_layout.setSpacing(8)

        for dev in self.devices:
            card = self._build_device_card(dev)
            self.list_layout.addWidget(card)
        self.list_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _build_device_card(self, dev: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        dev_name = dev.get("device_name") or dev.get("name") or "Registered PC"
        os_info = dev.get("os_info") or dev.get("os") or ""
        last_active = dev.get("last_active") or dev.get("created_at") or ""
        dev_id = str(dev.get("id") or dev.get("machine_id") or "")

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(f"💻 {dev_name}")
        name_lbl.setStyleSheet("color: #F8FAFC; font-weight: 600; font-size: 12px; border: none;")
        meta_parts = [p for p in [os_info, f"Last active: {last_active}" if last_active else ""] if p]
        meta_lbl = QLabel(" • ".join(meta_parts) if meta_parts else dev_id)
        meta_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none;")
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)

        logout_btn = QPushButton("Logout & Use Here")
        logout_btn.setObjectName("dangerBtn")
        logout_btn.clicked.connect(lambda checked=False, tid=dev_id, btn=logout_btn: self._do_replace_device(tid, btn))

        row.addLayout(info_col, stretch=1)
        row.addWidget(logout_btn)
        return card

    def _do_replace_device(self, target_device_id: str, btn: QPushButton):
        btn.setEnabled(False)
        btn.setText("Signing out...")
        self.status_lbl.setText("⏳ Signing out old device on BlackBox THC...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")

        self._worker = _DeviceLogoutWorker(target_device_id, email=self.email, password=self.password, parent=self)
        self._worker.finished.connect(self._on_old_device_logged_out)
        self._worker.start()

    def _on_old_device_logged_out(self, res: dict):
        if not res.get("ok"):
            self.status_lbl.setText(f"⚠️ {res.get('message', 'Failed to sign out device.')}")
            self.status_lbl.setStyleSheet("color: #FB7185; font-size: 11px;")
            return

        self.status_lbl.setText("✅ Old device removed! Registering this PC...")
        self._login_worker = _SignInWorker(self.email, self.password, parent=self)
        self._login_worker.finished.connect(self._on_relogin_finished)
        self._login_worker.start()

    def _on_relogin_finished(self, res: dict):
        if res.get("ok"):
            self.signed_in_ok = True
            self.accept()
        else:
            self.status_lbl.setText(f"⚠️ {res.get('message', 'Could not register this device.')}")
            self.status_lbl.setStyleSheet("color: #FB7185; font-size: 11px;")


class SignInDialog(QDialog):
    """Modern dark-themed Sign In dialog for BlackBox THC accounts."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signed_in_ok = False
        self._worker = None

        self.setWindowTitle(f"Sign In - {APP_NAME} (BlackBox THC)")
        self.setFixedSize(430, 310)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)

        title = QLabel("Sign In with BlackBox THC")
        title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        sub = QLabel("Enter your blackboxthc.com account email and password to activate RawView on this device.")
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(sub)

        layout.addSpacing(4)

        email_lbl = QLabel("Email Address")
        email_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #CBD5E1;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        layout.addWidget(email_lbl)
        layout.addWidget(self.email_input)

        pass_lbl = QLabel("Password")
        pass_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #CBD5E1;")
        pass_row = QHBoxLayout()
        pass_row.setSpacing(6)
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Enter your password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.returnPressed.connect(self._on_sign_in_clicked)

        self.show_pass_btn = QPushButton("👁")
        self.show_pass_btn.setFixedWidth(36)
        self.show_pass_btn.setCheckable(True)
        self.show_pass_btn.toggled.connect(
            lambda checked: self.pass_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        pass_row.addWidget(self.pass_input, stretch=1)
        pass_row.addWidget(self.show_pass_btn)
        layout.addWidget(pass_lbl)
        layout.addLayout(pass_row)

        self.error_lbl = QLabel("")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setStyleSheet("color: #FB7185; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.error_lbl)

        layout.addStretch()

        btn_row = QHBoxLayout()
        buy_btn = QPushButton("Buy Now")
        buy_btn.setObjectName("buyBtn")
        buy_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(ONLINE_LICENSE_CONFIG["buy_url"]))
        )
        btn_row.addWidget(buy_btn)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.signin_btn = QPushButton("Sign In")
        self.signin_btn.setObjectName("primaryBtn")
        self.signin_btn.clicked.connect(self._on_sign_in_clicked)
        btn_row.addWidget(self.signin_btn)

        layout.addLayout(btn_row)

    def _on_sign_in_clicked(self):
        email = self.email_input.text().strip()
        password = self.pass_input.text()
        if not email or not password:
            self.error_lbl.setText("Please enter your email and password.")
            return

        self.signin_btn.setEnabled(False)
        self.signin_btn.setText("Signing in...")
        self.error_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        self.error_lbl.setText("⏳ Verifying credentials with BlackBox THC...")

        self._worker = _SignInWorker(email, password, parent=self)
        self._worker.finished.connect(self._on_sign_in_result)
        self._worker.start()

    def _on_sign_in_result(self, res: dict):
        self.signin_btn.setEnabled(True)
        self.signin_btn.setText("Sign In")

        if res.get("ok"):
            self.signed_in_ok = True
            self.accept()
            return

        code = res.get("code", "")
        if code == "DEVICE_LIMIT_REACHED":
            self.error_lbl.setText("")
            limit_dlg = DeviceLimitDialog(
                email=self.email_input.text().strip(),
                password=self.pass_input.text(),
                devices=res.get("devices", []),
                device_limit=res.get("device_limit", 1),
                parent=self,
            )
            if limit_dlg.exec() == QDialog.DialogCode.Accepted and limit_dlg.signed_in_ok:
                self.signed_in_ok = True
                self.accept()
            return

        self.error_lbl.setStyleSheet("color: #FB7185; font-size: 11px; font-weight: 600;")
        self.error_lbl.setText(res.get("message") or "Sign-in failed.")


class DeviceManagementDialog(QDialog):
    """Allows a signed-in user to view and remotely sign out any device under their RawView license."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.self_logged_out = False
        self._fetch_worker = None
        self._logout_worker = None
        self.current_mid = get_machine_id()

        self.setWindowTitle(f"{APP_NAME} - Device Management")
        self.setFixedSize(500, 420)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()
        self._load_devices()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("💻 Device Management")
        title.setStyleSheet("color: #F8FAFC; font-size: 16px; font-weight: 700;")
        self.quota_lbl = QLabel("Loading...")
        self.quota_lbl.setStyleSheet("color: #38BDF8; font-weight: 600; font-size: 12px;")
        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.quota_lbl)
        layout.addLayout(header_row)

        sub = QLabel(
            "Manage all PCs currently signed in with your RawView license. "
            "Signing out a device immediately revokes its access."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 4, 4)
        self.list_layout.setSpacing(8)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll, stretch=1)

        self.status_lbl = QLabel("")
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._load_devices)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _load_devices(self):
        self.status_lbl.setText("⏳ Loading registered devices from BlackBox THC...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")
        self._fetch_worker = _FetchDevicesWorker(parent=self)
        self._fetch_worker.finished.connect(self._on_devices_loaded)
        self._fetch_worker.start()

    def _on_devices_loaded(self, res: dict):
        self._clear_list()
        devices = res.get("devices", [])
        limit = res.get("device_limit", 1)
        self.quota_lbl.setText(f"{len(devices)} / {limit} Devices")

        if not res.get("ok"):
            if res.get("code") == "REVOKED":
                self.self_logged_out = True
                QMessageBox.warning(self, "Signed Out", "This device has been signed out remotely.")
                self.accept()
                return
            self.status_lbl.setText(f"⚠️ {res.get('message', 'Could not refresh devices.')}")
            self.status_lbl.setStyleSheet("color: #FB7185; font-size: 11px;")
        else:
            self.status_lbl.setText("")

        if not devices:
            empty = QLabel("No active devices found.")
            empty.setStyleSheet("color: #64748B; font-size: 12px; padding: 12px;")
            self.list_layout.addWidget(empty)
        else:
            for dev in devices:
                self.list_layout.addWidget(self._build_device_card(dev))
        self.list_layout.addStretch()

    def _build_device_card(self, dev: dict) -> QFrame:
        card = QFrame()
        dev_mid = str(dev.get("machine_id") or "")
        dev_id = str(dev.get("id") or dev_mid)
        is_current = (dev_mid.upper() == self.current_mid.upper())

        border_color = "#0284C7" if is_current else "#1E293B"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #111827;
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        dev_name = dev.get("device_name") or dev.get("name") or "Registered PC"
        badge = " (This Device)" if is_current else ""
        os_info = dev.get("os_info") or dev.get("os") or ""
        last_active = dev.get("last_active") or dev.get("created_at") or ""

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(f"💻 {dev_name}{badge}")
        name_lbl.setStyleSheet(
            f"color: {'#38BDF8' if is_current else '#F8FAFC'}; font-weight: 600; font-size: 12px; border: none;"
        )
        meta_parts = [p for p in [os_info, f"Last active: {last_active}" if last_active else ""] if p]
        meta_lbl = QLabel(" • ".join(meta_parts) if meta_parts else dev_mid)
        meta_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; border: none;")
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)

        signout_btn = QPushButton("Sign Out")
        signout_btn.setObjectName("dangerBtn")
        signout_btn.clicked.connect(lambda checked=False, tid=dev_id, cur=is_current, btn=signout_btn: self._do_signout_device(tid, cur, btn))

        row.addLayout(info_col, stretch=1)
        row.addWidget(signout_btn)
        return card

    def _do_signout_device(self, target_id: str, is_current: bool, btn: QPushButton):
        btn.setEnabled(False)
        btn.setText("Removing...")
        self.status_lbl.setText("⏳ Signing out device...")
        self.status_lbl.setStyleSheet("color: #38BDF8; font-size: 11px;")

        self._logout_worker = _DeviceLogoutWorker(target_id, parent=self)
        self._logout_worker.finished.connect(lambda res: self._on_device_signed_out(res, is_current))
        self._logout_worker.start()

    def _on_device_signed_out(self, res: dict, is_current: bool):
        if res.get("ok"):
            if is_current:
                self.self_logged_out = True
                self.accept()
                return
            self._load_devices()
        else:
            self.status_lbl.setText(f"⚠️ {res.get('message', 'Failed to sign out device.')}")
            self.status_lbl.setStyleSheet("color: #FB7185; font-size: 11px;")


class LegacyMigrationDialog(QDialog):
    """
    'Read Carefully' notification dialog for existing offline-license users.
    Allows them to keep using their offline license until they sign up & sign in online.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signed_in_ok = False
        self.setWindowTitle(f"{APP_NAME} - Read Carefully")
        self.setFixedSize(480, 260)
        self.setStyleSheet(DIALOG_STYLE)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        badge = QLabel("📢 Read Carefully")
        badge.setStyleSheet("color: #FBBF24; font-size: 16px; font-weight: 700;")
        layout.addWidget(badge)

        msg_box = QFrame()
        msg_box.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #B45309;
                border-radius: 8px;
            }
        """)
        msg_layout = QVBoxLayout(msg_box)
        msg_layout.setContentsMargins(14, 12, 14, 12)
        msg_lbl = QLabel(LEGACY_MIGRATION_MESSAGE)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #F8FAFC; font-size: 12px; line-height: 1.4; border: none;")
        msg_layout.addWidget(msg_lbl)
        layout.addWidget(msg_box)

        note = QLabel("Your existing offline license will continue working normally until you sign in.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(note)

        layout.addStretch()

        btn_row = QHBoxLayout()
        later_btn = QPushButton("Later")
        later_btn.clicked.connect(self.reject)
        btn_row.addWidget(later_btn)
        btn_row.addStretch()

        signin_btn = QPushButton("Sign In")
        signin_btn.clicked.connect(self._open_signin)
        btn_row.addWidget(signin_btn)

        self.update_btn = QPushButton("Update License")
        self.update_btn.setObjectName("primaryBtn")
        self.update_btn.clicked.connect(self._open_signup)
        btn_row.addWidget(self.update_btn)

        layout.addLayout(btn_row)

    def _open_signup(self):
        launch_claim_url_with_ticket(parent_widget=self, btn=self.update_btn)

    def _open_signin(self):
        dlg = SignInDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.signed_in_ok:
            self.signed_in_ok = True
            self.accept()

class _ClaimTicketWorker(QThread):
    finished = pyqtSignal(dict)

    def run(self):
        try:
            res = initiate_claim_ticket()
            self.finished.emit(res)
        except Exception as e:
            self.finished.emit({"ok": False, "claim_url": "", "message": str(e)})

def launch_claim_url_with_ticket(parent_widget=None, btn=None):
    """
    Requests a single-use 15-minute claim ticket from blackboxthc.com directly from RawView
    and launches the verified browser claim page.
    """
    orig_text = btn.text() if btn else ""
    if btn:
        btn.setEnabled(False)
        btn.setText("Generating Link...")

    def on_res(res: dict):
        if btn:
            btn.setEnabled(True)
            btn.setText(orig_text)

        claim_url = res.get("claim_url", "")
        if res.get("ok") and claim_url:
            QDesktopServices.openUrl(QUrl(claim_url))
        else:
            msg = res.get("message") or "Could not generate secure claim link."
            if parent_widget:
                QMessageBox.warning(parent_widget, "Claim License", msg)
            else:
                fallback = ONLINE_LICENSE_CONFIG.get("signup_url", "https://www.blackboxthc.com/signup")
                QDesktopServices.openUrl(QUrl(fallback))

    worker = _ClaimTicketWorker(parent=parent_widget)
    worker.finished.connect(on_res)
    if parent_widget:
        parent_widget._claim_worker = worker
    worker.start()
