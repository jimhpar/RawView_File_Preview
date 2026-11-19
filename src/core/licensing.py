import os
import sys
import time
import json
import re
import hmac
import hashlib
import platform
import socket
import urllib.request
import urllib.error
from pathlib import Path
from src.core.config import (
    APPDATA_DIR,
    APP_VERSION,
    ONLINE_LICENSE_CONFIG,
    get_ssl_context,
    set_license_active_registry,
    purge_thumbs_cache,
    notify_shell_refresh,
)

if sys.platform == "win32":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

LICENSE_FILE = APPDATA_DIR / "license.json"
MASTER_SECRET = b"RAWVIEW_PRO_OFFLINE_SECRET_KEY_BLACKBOX_2026_V2"
TRIAL_DURATION_DAYS = 7

LEGACY_MIGRATION_MESSAGE = (
    "Dear User, Thank you for the purchase, We are shifting to more secured licencing platform, "
    "please sign up to claim your universal cross device licencing signature. "
    f"for support Call: {ONLINE_LICENSE_CONFIG.get('support_phone', '01756678087')}"
)

def get_raw_hardware_guid() -> str:
    """Extracts Windows MachineGuid, macOS Hardware UUID, or hardware signature."""
    if sys.platform == "darwin":
        try:
            import subprocess
            out = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], timeout=2.0).decode("utf-8", errors="ignore")
            m = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            if m:
                return m.group(1).strip().lower()
        except Exception:
            pass
        try:
            import subprocess
            out = subprocess.check_output(["sysctl", "-n", "hw.uuid"], timeout=2.0).decode("utf-8", errors="ignore").strip()
            if out:
                return out.lower()
        except Exception:
            pass

    elif sys.platform == "win32" and winreg:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    return str(guid).strip().lower()
        except Exception:
            pass

    # Fallback to system node name and processor
    node = platform.node() or "RAWVIEW_DEFAULT_NODE"
    proc = platform.processor() or "RAWVIEW_DEFAULT_PROC"
    return f"{node}-{proc}".lower()

def get_machine_id() -> str:
    """Generates a standardized 16-character Machine Code (e.g. RV-A89F-7B21-99CE)."""
    raw_guid = get_raw_hardware_guid()
    h = hashlib.sha256(raw_guid.encode("utf-8")).hexdigest().upper()
    return f"RV-{h[:4]}-{h[4:8]}-{h[8:12]}"

def get_device_name() -> str:
    """Returns a friendly device name for cross-device management."""
    try:
        name = socket.gethostname() or platform.node()
        if name:
            return name.strip()
    except Exception:
        pass
    return "Unknown PC"

def get_os_info() -> str:
    """Returns a readable OS string (e.g. 'Windows 11', 'macOS 15.1')."""
    try:
        if sys.platform == "win32":
            ver = sys.getwindowsversion()
            win_ver = "Windows 11" if ver.build >= 22000 else f"Windows {platform.release()}"
            return f"{win_ver} ({platform.machine() or 'x64'})"
        elif sys.platform == "darwin":
            mac_ver = platform.mac_ver()[0] or platform.release()
            return f"macOS {mac_ver} ({platform.machine()})"
        return f"{platform.system()} {platform.release()}"
    except Exception:
        return sys.platform

def generate_pro_key(machine_id: str) -> str:
    """Legacy offline HMAC-SHA256 Lifetime Pro key generator (kept for verifying existing offline users)."""
    clean_id = machine_id.strip().upper()
    sig = hmac.new(MASTER_SECRET, clean_id.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return f"RVPRO-{sig[:4]}-{sig[4:8]}-{sig[8:12]}-{sig[12:16]}"

def verify_license_key(machine_id: str, license_key: str) -> bool:
    """Validates a legacy offline license key mathematically against the machine ID."""
    if not machine_id or not license_key:
        return False
    expected = generate_pro_key(machine_id)
    return hmac.compare_digest(expected.strip().upper(), license_key.strip().upper())

def _load_license_store() -> dict:
    os.makedirs(APPDATA_DIR, exist_ok=True)
    if LICENSE_FILE.exists():
        try:
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_license_store(data: dict):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    try:
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Failed to save license store: {e}")

def _api_request(endpoint: str, method: str = "POST", payload: dict | None = None, token: str = "", timeout: float = 10.0) -> tuple[int, dict]:
    """
    Executes an HTTPS JSON request against the blackboxthc.com RawView Licensing API.
    Returns (http_status_code, parsed_json_dict). http_status_code == 0 indicates a network/connection error.
    """
    base_url = ONLINE_LICENSE_CONFIG.get("api_base_url", "https://www.blackboxthc.com/api/rawview").rstrip("/")
    url = f"{base_url}/{endpoint.lstrip('/')}"

    headers = {
        "User-Agent": f"RawView-Client/{APP_VERSION}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    ssl_ctx = get_ssl_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw.strip() else {}
            except Exception:
                data = {"raw": raw}
            return resp.status, data
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        try:
            data = json.loads(raw) if raw.strip() else {}
        except Exception:
            data = {"message": raw or str(e)}
        return e.code, data
    except Exception as e:
        return 0, {"code": "NETWORK_ERROR", "message": f"Unable to connect to BlackBox THC server: {e}"}

def get_license_status(sync_registry: bool = True) -> dict:
    """
    Returns the comprehensive licensing state:
    - status: 'ONLINE_PRO_ACTIVE' | 'LEGACY_OFFLINE_PRO' | 'TRIAL_ACTIVE' | 'TRIAL_EXPIRED'
    - days_left: int (remaining trial days)
    - machine_id: str
    - is_unlocked: bool (True allows hover preview & Explorer thumbnails; False locks both)
    - needs_migration: bool (True for legacy offline users so the 'Read Carefully' notice displays)
    - user_email / user_name / plan / device_limit / devices / session_token / license_key
    """
    machine_id = get_machine_id()
    store = _load_license_store()

    # 1. Check active Online BlackBox THC session
    session_token = store.get("session_token", "")
    session_mid = store.get("session_machine_id", "")
    if session_token and (not session_mid or session_mid == machine_id):
        result = {
            "status": "ONLINE_PRO_ACTIVE",
            "days_left": 0,
            "machine_id": machine_id,
            "is_unlocked": True,
            "needs_migration": False,
            "user_email": store.get("user_email", ""),
            "user_name": store.get("user_name", ""),
            "plan": store.get("plan", "RawView Pro"),
            "device_limit": int(store.get("device_limit", 1) or 1),
            "devices": store.get("devices", []),
            "session_token": session_token,
            "license_key": "",
        }
        if sync_registry:
            set_license_active_registry(True)
        return result

    # 2. Check Legacy Offline Pro Key (grandfathered — remains unlocked until user signs in online)
    saved_key = store.get("license_key", "")
    if saved_key and verify_license_key(machine_id, saved_key):
        result = {
            "status": "LEGACY_OFFLINE_PRO",
            "days_left": 0,
            "machine_id": machine_id,
            "is_unlocked": True,
            "needs_migration": True,
            "user_email": "",
            "user_name": "",
            "plan": "Legacy Offline Pro",
            "device_limit": 1,
            "devices": [],
            "session_token": "",
            "license_key": saved_key,
        }
        if sync_registry:
            set_license_active_registry(True)
        return result

    # 3. Check / initialize 7-day Free Trial (no sign-in or license required during trial)
    install_time = store.get("install_time")
    now = time.time()

    if not install_time:
        install_time = now
        store["install_time"] = install_time
        store["machine_id"] = machine_id
        _save_license_store(store)

    elapsed_seconds = max(0, now - float(install_time))
    elapsed_days = int(elapsed_seconds // 86400)
    days_left = max(0, TRIAL_DURATION_DAYS - elapsed_days)

    if days_left > 0:
        result = {
            "status": "TRIAL_ACTIVE",
            "days_left": days_left,
            "machine_id": machine_id,
            "is_unlocked": True,
            "needs_migration": False,
            "user_email": "",
            "user_name": "",
            "plan": "7-Day Free Trial",
            "device_limit": 1,
            "devices": [],
            "session_token": "",
            "license_key": "",
        }
        if sync_registry:
            set_license_active_registry(True)
        return result
    else:
        result = {
            "status": "TRIAL_EXPIRED",
            "days_left": 0,
            "machine_id": machine_id,
            "is_unlocked": False,
            "needs_migration": False,
            "user_email": "",
            "user_name": "",
            "plan": "",
            "device_limit": 0,
            "devices": [],
            "session_token": "",
            "license_key": "",
        }
        if sync_registry:
            set_license_active_registry(False)
        return result

def online_sign_in(email: str, password: str) -> dict:
    """
    Authenticates user credentials against blackboxthc.com and registers this device under their RawView license.
    Returns a structured dict with:
    - ok: bool
    - code: 'OK' | 'NOT_REGISTERED' | 'INVALID_PASSWORD' | 'NO_LICENSE' | 'DEVICE_LIMIT_REACHED' | 'NETWORK_ERROR' | 'ERROR'
    - message: str
    - devices: list (populated on OK or DEVICE_LIMIT_REACHED)
    - device_limit: int
    """
    clean_email = (email or "").strip()
    if not clean_email or not password:
        return {"ok": False, "code": "ERROR", "message": "Please enter both email and password."}

    machine_id = get_machine_id()
    payload = {
        "email": clean_email,
        "password": password,
        "machine_id": machine_id,
        "device_name": get_device_name(),
        "os_info": get_os_info(),
        "app_version": APP_VERSION,
    }

    status_code, data = _api_request("auth/login", method="POST", payload=payload)
    api_code = str(data.get("code", "")).upper()

    if status_code == 200 and data.get("session_token"):
        store = _load_license_store()
        store["session_token"] = data["session_token"]
        store["session_machine_id"] = machine_id
        store["user_email"] = data.get("user", {}).get("email") or clean_email
        store["user_name"] = data.get("user", {}).get("name", "")
        lic_obj = data.get("license", {})
        store["plan"] = lic_obj.get("plan") or data.get("plan") or "RawView Pro"
        store["device_limit"] = int(lic_obj.get("device_limit") or data.get("device_limit") or 1)
        store["devices"] = data.get("devices", [])
        store["last_verified_at"] = time.time()
        store["machine_id"] = machine_id
        _save_license_store(store)

        set_license_active_registry(True)
        notify_shell_refresh()

        return {
            "ok": True,
            "code": "OK",
            "message": "Signed in successfully! RawView Pro is now active on this device.",
            "devices": store["devices"],
            "device_limit": store["device_limit"],
        }

    if status_code == 404 or api_code in ("NOT_REGISTERED", "USER_NOT_FOUND"):
        return {
            "ok": False,
            "code": "NOT_REGISTERED",
            "message": "You are not a registered user of BlackBox THC.",
        }

    if status_code == 403 or api_code in ("NO_LICENSE", "LICENSE_INACTIVE", "LICENSE_EXPIRED"):
        return {
            "ok": False,
            "code": "NO_LICENSE",
            "message": "You don't have a license for this software.",
        }

    if status_code == 409 or api_code in ("DEVICE_LIMIT_REACHED", "MAX_DEVICES"):
        return {
            "ok": False,
            "code": "DEVICE_LIMIT_REACHED",
            "message": data.get("message") or "Device limit reached. Please sign out an existing device to continue.",
            "device_limit": int(data.get("device_limit") or 1),
            "devices": data.get("devices", []),
        }

    if status_code == 401 or api_code in ("INVALID_PASSWORD", "INVALID_CREDENTIALS"):
        return {
            "ok": False,
            "code": "INVALID_PASSWORD",
            "message": data.get("message") or "Invalid email or password.",
        }

    if status_code == 0:
        return {
            "ok": False,
            "code": "NETWORK_ERROR",
            "message": data.get("message") or "Could not reach BlackBox THC server. Please check your internet connection.",
        }

    return {
        "ok": False,
        "code": api_code or "ERROR",
        "message": data.get("message") or f"Sign-in failed (HTTP {status_code}).",
    }

def _clear_local_online_session():
    """Removes the stored online session token and refreshes Explorer license gating."""
    store = _load_license_store()
    for k in ("session_token", "session_machine_id", "user_email", "user_name", "plan", "device_limit", "devices", "last_verified_at"):
        store.pop(k, None)
    _save_license_store(store)

    # Re-evaluate license state (sets LicenseActive=0 if expired/unlicensed)
    new_state = get_license_status(sync_registry=True)
    if not new_state.get("is_unlocked"):
        purge_thumbs_cache()
        notify_shell_refresh()

def verify_online_session() -> dict:
    """
    Verifies the active online session with blackboxthc.com.
    If remotely signed out (from another device or Admin Console), automatically signs out this device
    and disables thumbnails + hover preview.
    """
    store = _load_license_store()
    token = store.get("session_token", "")
    if not token:
        return {"status": "NO_SESSION", "revoked": False}

    machine_id = get_machine_id()
    status_code, data = _api_request(
        "auth/verify",
        method="POST",
        payload={"session_token": token, "machine_id": machine_id},
        token=token,
        timeout=8.0,
    )
    api_code = str(data.get("code", "")).upper()

    if status_code == 200 and data.get("valid", True):
        store["last_verified_at"] = time.time()
        if "devices" in data:
            store["devices"] = data["devices"]
        if "device_limit" in data:
            store["device_limit"] = int(data["device_limit"] or 1)
        if "plan" in data:
            store["plan"] = data["plan"]
        _save_license_store(store)
        set_license_active_registry(True)
        return {"status": "VALID", "revoked": False}

    if status_code in (401, 403) or api_code in ("REVOKED", "SESSION_INVALID", "DEVICE_REMOVED", "NO_LICENSE"):
        _clear_local_online_session()
        return {
            "status": "REVOKED",
            "revoked": True,
            "message": data.get("message") or "Your session was signed out from another device or administrator.",
        }

    # Network failure: allow offline grace period
    grace_hours = float(ONLINE_LICENSE_CONFIG.get("offline_grace_hours", 72))
    last_verified = float(store.get("last_verified_at") or 0)
    if last_verified and (time.time() - last_verified) <= grace_hours * 3600:
        return {"status": "OFFLINE_GRACE", "revoked": False}

    return {"status": "NETWORK_ERROR", "revoked": False}

def fetch_registered_devices() -> dict:
    """Fetches the list of currently registered devices for the signed-in user."""
    store = _load_license_store()
    token = store.get("session_token", "")
    if not token:
        return {"ok": False, "message": "Not signed in.", "devices": [], "device_limit": 0}

    status_code, data = _api_request("devices", method="GET", token=token, timeout=8.0)
    if status_code == 200:
        devices = data.get("devices", [])
        device_limit = int(data.get("device_limit") or store.get("device_limit") or 1)
        store["devices"] = devices
        store["device_limit"] = device_limit
        _save_license_store(store)
        return {"ok": True, "devices": devices, "device_limit": device_limit}

    if status_code in (401, 403):
        _clear_local_online_session()
        return {"ok": False, "code": "REVOKED", "message": "Session expired or signed out.", "devices": [], "device_limit": 0}

    return {"ok": False, "message": data.get("message") or "Could not fetch device list.", "devices": store.get("devices", []), "device_limit": store.get("device_limit", 1)}

def logout_remote_device(target_device_id: str, email: str = "", password: str = "") -> dict:
    """
    Logs out a specific registered device on blackboxthc.com.
    Supports both authenticated sessions (via session_token) and pre-login limit-reached flows (via email+password).
    """
    store = _load_license_store()
    token = store.get("session_token", "")
    machine_id = get_machine_id()

    payload = {
        "target_device_id": target_device_id,
        "machine_id": machine_id,
    }
    if email and password:
        payload["email"] = email.strip()
        payload["password"] = password

    status_code, data = _api_request("devices/logout", method="POST", payload=payload, token=token, timeout=10.0)

    if status_code == 200:
        # If the user logged out THIS device, clear local session
        if target_device_id == machine_id or data.get("self_logged_out"):
            _clear_local_online_session()
        elif "devices" in data:
            store["devices"] = data["devices"]
            _save_license_store(store)
        return {"ok": True, "message": data.get("message") or "Device signed out successfully.", "devices": data.get("devices", [])}

    return {"ok": False, "message": data.get("message") or f"Failed to sign out device (HTTP {status_code})."}

def sign_out_current_device() -> tuple[bool, str]:
    """Signs out the current device from blackboxthc.com and clears local session."""
    store = _load_license_store()
    token = store.get("session_token", "")
    machine_id = get_machine_id()

    if token:
        try:
            _api_request(
                "devices/logout",
                method="POST",
                payload={"target_device_id": machine_id, "machine_id": machine_id},
                token=token,
                timeout=6.0,
            )
        except Exception:
            pass

    _clear_local_online_session()
    return True, "Signed out of this device."

def activate_license(license_key: str) -> tuple[bool, str]:
    """Legacy offline activation helper (retained for backward compatibility)."""
    machine_id = get_machine_id()
    clean_key = license_key.strip().upper()
    if not clean_key:
        return False, "Please enter a valid license key."
    if verify_license_key(machine_id, clean_key):
        store = _load_license_store()
        store["license_key"] = clean_key
        store["machine_id"] = machine_id
        store["activated_at"] = time.time()
        _save_license_store(store)
        set_license_active_registry(True)
        return True, "RawView Pro activated!"
    return False, "Invalid license key."
