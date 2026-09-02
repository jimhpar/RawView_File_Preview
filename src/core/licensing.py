import os
import sys
import time
import json
import winreg
import hmac
import hashlib
import platform
from pathlib import Path
from src.core.config import APPDATA_DIR

LICENSE_FILE = APPDATA_DIR / "license.json"
MASTER_SECRET = b"RAWVIEW_PRO_OFFLINE_SECRET_KEY_BLACKBOX_2026_V2"
TRIAL_DURATION_DAYS = 7

def get_raw_hardware_guid() -> str:
    """Extracts Windows MachineGuid or hardware signature."""
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

def generate_pro_key(machine_id: str) -> str:
    """Generates the cryptographic HMAC-SHA256 Lifetime Pro License Key for a given Machine ID."""
    clean_id = machine_id.strip().upper()
    sig = hmac.new(MASTER_SECRET, clean_id.encode("utf-8"), hashlib.sha256).hexdigest().upper()
    return f"RVPRO-{sig[:4]}-{sig[4:8]}-{sig[8:12]}-{sig[12:16]}"

def verify_license_key(machine_id: str, license_key: str) -> bool:
    """Validates the license key mathematically against the machine ID."""
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

def get_license_status() -> dict:
    """
    Returns the comprehensive licensing state:
    - status: 'PRO_ACTIVE' | 'TRIAL_ACTIVE' | 'TRIAL_EXPIRED'
    - days_left: int (remaining trial days)
    - machine_id: str
    - is_unlocked: bool (True allows full previewing; False triggers activation card)
    - license_key: str
    """
    machine_id = get_machine_id()
    store = _load_license_store()

    # 1. Check if Lifetime Pro is activated
    saved_key = store.get("license_key", "")
    if saved_key and verify_license_key(machine_id, saved_key):
        return {
            "status": "PRO_ACTIVE",
            "days_left": 0,
            "machine_id": machine_id,
            "is_unlocked": True,
            "license_key": saved_key
        }

    # 2. Check / initialize 7-day Free Trial
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
        return {
            "status": "TRIAL_ACTIVE",
            "days_left": days_left,
            "machine_id": machine_id,
            "is_unlocked": True,
            "license_key": ""
        }
    else:
        return {
            "status": "TRIAL_EXPIRED",
            "days_left": 0,
            "machine_id": machine_id,
            "is_unlocked": False,
            "license_key": ""
        }

def activate_license(license_key: str) -> tuple[bool, str]:
    """
    Attempts to activate the application with a user-provided license key.
    Returns (success: bool, message: str).
    """
    machine_id = get_machine_id()
    clean_key = license_key.strip().upper()

    if not clean_key:
        return False, "Please enter a valid license key."

    if verify_license_key(machine_id, clean_key):
        store = _load_license_store()
        store["license_key"] = clean_key
        store["activated_at"] = time.time()
        store["machine_id"] = machine_id
        _save_license_store(store)
        return True, "RawView Lifetime Pro activated successfully!"
    else:
        return False, "Invalid License Key for this computer. Please check and try again."
