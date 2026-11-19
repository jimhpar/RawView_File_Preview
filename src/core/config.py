import os
import sys
import json
from pathlib import Path

APP_NAME = "RawView"
APP_VERSION = "v5.3.1"
APP_PUBLISHER = "BlackBox THC"
APP_MUTEX_NAME = "RawView_SingleInstance_Mutex_v5.3.1"
GITHUB_REPO = "jimhpar/RawView_File_Preview"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Standard Web & Raster Images (Disabled by default in settings)
STANDARD_IMAGE_EXTENSIONS = {
    ".jpg":  "JPEG Image",
    ".jpeg": "JPEG Image",
    ".png":  "Portable Network Graphics",
    ".webp": "WebP Image",
    ".gif":  "Graphics Interchange Format",
    ".ico":  "Windows Icon",
    ".bmp":  "Bitmap Image",
}

# Supported extensions
SUPPORTED_EXTENSIONS = {
    # Adobe Photoshop
    ".psd": "Photoshop Document",
    ".psb": "Photoshop Large Document",
    # Adobe Illustrator & Vectors
    ".ai":  "Adobe Illustrator Artwork",
    ".eps": "Encapsulated PostScript",
    ".svg": "Scalable Vector Graphics",
    ".svgz":"Compressed SVG",
    # Documents & Publishing
    ".pdf": "Portable Document Format",
    ".docx": "Microsoft Word",
    ".doc": "Microsoft Word Legacy",
    ".xlsx": "Microsoft Excel",
    ".xls": "Microsoft Excel Legacy",
    ".pptx": "Microsoft PowerPoint",
    ".ppt": "Microsoft PowerPoint Legacy",
    ".rtf": "Rich Text Format",
    # Archives & Compressed Packages
    ".zip": "ZIP Archive",
    ".rar": "RAR Archive",
    ".7z":  "7-Zip Archive",
    ".tar": "TAR Archive",
    ".gz":  "GZip Archive",
    ".tgz": "GZip Tar Archive",
    ".bz2": "BZip2 Archive",
    # Adobe Projects
    ".aep": "After Effects Project",
    ".aet": "After Effects Template",
    ".aepx": "After Effects XML Project",
    ".prproj": "Premiere Pro Project",
    ".prset": "Premiere Pro Preset",
    # Raster Images
    ".tif": "TIFF Image",
    ".tiff":"TIFF Image",
    # Standard & Web Raster Images
    **STANDARD_IMAGE_EXTENSIONS,
    # Video Formats
    ".mp4": "MPEG-4 Video",
    ".mkv": "Matroska Video",
    ".mov": "QuickTime Video",
    ".avi": "AVI Video",
    ".wmv": "Windows Media Video",
    ".webm":"WebM Video",
    ".m4v": "iTunes Video",
    ".flv": "Flash Video",
    ".ts":  "MPEG Transport Stream",
    ".3gp": "3GPP Video",
    ".mpg": "MPEG Video",
    ".mpeg":"MPEG Video",
    # Adobe / Universal Digital Negative
    ".dng": "Digital Negative RAW",
    # Canon Camera RAW
    ".cr2": "Canon RAW 2",
    ".cr3": "Canon RAW 3",
    ".crw": "Canon RAW",
    # Nikon Camera RAW
    ".nef": "Nikon Electronic Format",
    ".nrw": "Nikon RAW",
    # Sony Camera RAW
    ".arw": "Sony Alpha RAW",
    ".srf": "Sony RAW",
    ".sr2": "Sony RAW 2",
    # Fujifilm RAW
    ".raf": "Fujifilm RAW",
    # Olympus RAW
    ".orf": "Olympus RAW",
    ".ori": "Olympus RAW",
    # Panasonic Lumix RAW
    ".rw2": "Panasonic Lumix RAW",
    # Pentax RAW
    ".pef": "Pentax Electronic File",
    ".ptx": "Pentax RAW",
    # Hasselblad & Phase One
    ".3fr": "Hasselblad 3FR RAW",
    ".fff": "Hasselblad FFF RAW",
    ".iiq": "Phase One RAW",
    ".raw": "Camera RAW Image",
    ".x3f": "Sigma RAW"
}

# Online Licensing & BlackBox THC Platform Configuration
# (Update api_base_url / signup_url if your website endpoints change)
ONLINE_LICENSE_CONFIG = {
    "api_base_url": "https://www.blackboxthc.com/api/rawview",
    "buy_url": "https://www.blackboxthc.com/checkout?slug=rawview&type=subscription&plan=starter",
    "signup_url": "https://www.blackboxthc.com/signup",
    "support_phone": "01756678087",
    "verify_interval_hours": 6,
    "offline_grace_hours": 72,
}

# Payment & Support Information (Legacy metadata kept for reference)
PAYMENT_INFO = {
    "price_bdt": "120 TK",
    "bkash_number": "01756678087",
    "bkash_type": "Personal (Send Money)",
    "whatsapp_number": "+1 (202) 780-6050",
    "whatsapp_link": "https://wa.me/12027806050",
}

# Directories
if sys.platform == "darwin":
    APPDATA_DIR = Path.home() / "Library" / "Application Support" / "RawView"
elif sys.platform == "win32":
    APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "RawView"
else:
    APPDATA_DIR = Path.home() / ".config" / "RawView"
CACHE_DIR = APPDATA_DIR / "cache"
CONFIG_FILE = APPDATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "enabled": True,
    "hover_delay_ms": 120,       # Settle dwell time in milliseconds
    "preview_max_size": 640,     # Max width/height of preview window in px
    "autostart": True,           # Start with Windows boot
    "show_metadata": True,       # Show format badge, dimensions, size
    "enable_animations": True,   # Smooth fade/scale animations
    "cache_max_mb": 500,         # Max disk cache size
    # Updater settings
    "auto_check_updates": True,           # Automatically check for updates
    "update_check_interval_days": 7,     # Weekly interval
    "last_update_check_timestamp": 0.0,  # Unix timestamp of last check
    # Standard raster images (jpg, png, webp, gif, ico, bmp) are disabled by default
    "supported_formats": [k for k in SUPPORTED_EXTENSIONS.keys() if k not in STANDARD_IMAGE_EXTENSIONS]
}

def load_config() -> dict:
    os.makedirs(APPDATA_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    os.makedirs(APPDATA_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Failed to save config: {e}")

def get_ssl_context():
    """Returns a reliable SSLContext using certifi CA bundle (fixes PyInstaller CERTIFICATE_VERIFY_FAILED)."""
    import ssl
    try:
        import certifi
        ca_path = certifi.where()
        if ca_path and os.path.exists(ca_path):
            return ssl.create_default_context(cafile=ca_path)
    except Exception:
        pass
    try:
        return ssl.create_default_context()
    except Exception:
        return None

def notify_shell_refresh():
    """Broadcasts SHChangeNotify(SHCNE_ASSOCCHANGED) so Windows Explorer refreshes thumbnails/icons."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

def set_license_active_registry(active: bool):
    """Writes HKCU\\Software\\RawView\\LicenseActive (1/0) so the C++ Thumbnail DLL enforces licensing."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RawView") as key:
            winreg.SetValueEx(key, "LicenseActive", 0, winreg.REG_DWORD, 1 if active else 0)
    except Exception:
        pass

def set_user_exited_registry(exited: bool):
    """Writes HKCU\\Software\\RawView\\UserExited (1/0) so the C++ DLL never respawns RawView after manual Exit."""
    if sys.platform != "win32":
        return
    try:
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RawView") as key:
            winreg.SetValueEx(key, "UserExited", 0, winreg.REG_DWORD, 1 if exited else 0)
    except Exception:
        pass

def purge_thumbs_cache():
    """Purges thumbnail disk caches (both LocalAppData and AppData) to force Explorer to regenerate/clear thumbnails."""
    try:
        import shutil
        dirs_to_purge = [CACHE_DIR / "thumbs"]
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            dirs_to_purge.append(Path(local_app_data) / "RawView" / "cache" / "thumbs")
        for thumbs_dir in dirs_to_purge:
            if thumbs_dir.exists():
                shutil.rmtree(thumbs_dir, ignore_errors=True)
                thumbs_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def get_show_system_icon_overlay() -> bool:
    """Checks whether Windows Explorer ShowTypeOverlay (system icon badge on thumbnails) is enabled.
    False = Default (RawView stamps custom crisp format badges; Explorer overlays disabled)
    True  = Windows Explorer generates system icon overlays; RawView badges are disabled
    """
    if not sys.platform == "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, "ShowTypeOverlay")
            return bool(val)
    except Exception:
        return False

def set_show_system_icon_overlay(enabled: bool):
    """Enables or disables Windows Explorer ShowTypeOverlay in registry, purges thumbs cache, and refreshes Explorer."""
    if not sys.platform == "win32":
        return
    try:
        import winreg
        import ctypes
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ShowTypeOverlay", 0, winreg.REG_DWORD, 1 if enabled else 0)

        # Clear thumb cache so Explorer reloads in the new mode without mixing badges
        purge_thumbs_cache()

        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception as e:
        print(f"Failed to set ShowTypeOverlay: {e}")
