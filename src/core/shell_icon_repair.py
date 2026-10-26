import os
import sys
import glob
import subprocess
import winreg
from pathlib import Path

import stat as stat_module

IS_WINDOWS = sys.platform == "win32"

def get_assets_dir() -> Path:
    try:
        from src.core.icons import get_asset_path
        p = get_asset_path("ps_badge.ico")
        if p and os.path.exists(p):
            return Path(p).parent
    except Exception:
        pass
    return Path(__file__).resolve().parent.parent.parent / "assets"

def find_installed_photoshop() -> str:
    """Discovers installed Photoshop.exe across all system drives."""
    drives = ["C", "D", "E"]
    for drive in drives:
        base = f"{drive}:\\Program Files\\Adobe"
        if os.path.isdir(base):
            for pattern in [f"{base}\\Adobe Photoshop *\\Photoshop.exe", f"{base}\\*Photoshop*\\Photoshop.exe"]:
                matches = glob.glob(pattern)
                if matches:
                    matches.sort(reverse=True)
                    return matches[0]
    return ""

def find_installed_illustrator() -> str:
    """Discovers installed Illustrator.exe across all system drives."""
    drives = ["C", "D", "E"]
    for drive in drives:
        base = f"{drive}:\\Program Files\\Adobe"
        if os.path.isdir(base):
            for pattern in [
                f"{base}\\Adobe Illustrator *\\Support Files\\Contents\\Windows\\Illustrator.exe",
                f"{base}\\*Illustrator*\\Support Files\\Contents\\Windows\\Illustrator.exe",
                f"{base}\\Adobe Illustrator *\\Illustrator.exe"
            ]:
                matches = glob.glob(pattern)
                if matches:
                    matches.sort(reverse=True)
                    return matches[0]
    return ""

def clean_user_shadow_keys():
    """
    Cleans up any corrupted HKCU\\Software\\Classes keys that shadow HKLM and cause
    Windows Explorer to display white blank document icons instead of Ps, Ai, etc.
    """
    if not IS_WINDOWS:
        return

    exts = [
        ".psd", ".psb", ".ai", ".eps", ".pdf", ".tif", ".tiff",
        ".cr2", ".cr3", ".crw", ".nef", ".nrw", ".arw", ".srf", ".sr2",
        ".raf", ".orf", ".rw2", ".pef", ".ptx", ".3fr", ".fff", ".iiq", ".raw", ".x3f", ".dng",
        ".svg", ".svgz", ".zip", ".rar", ".7z"
    ]

    # 1. Clean extension keys in HKCU
    for ext in exts:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\ShellEx\\{{e357fccd-a995-4576-b01f-234630154e96}}")
        except Exception:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}\\ShellEx")
        except Exception:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\SystemFileAssociations\\{ext}\\ShellEx\\{{e357fccd-a995-4576-b01f-234630154e96}}")
        except Exception:
            pass
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\SystemFileAssociations\\{ext}\\ShellEx")
        except Exception:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}", 0, winreg.KEY_READ) as k:
                subkeys, values, _ = winreg.QueryInfoKey(k)
                has_default = False
                try:
                    def_val, _ = winreg.QueryValueEx(k, "")
                    if def_val and str(def_val).strip():
                        has_default = True
                except Exception:
                    pass
            if not has_default and subkeys == 0:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}")
        except Exception:
            pass

    adobe_progids = (
        [f"Photoshop.Image.{v}" for v in range(15, 35)] +
        [f"Photoshop.PSBFile.{v}" for v in range(15, 35)] +
        [f"Adobe.Illustrator.{v}" for v in range(15, 35)] +
        ["Adobe.Illustrator.EPS", "Photoshop.Image", "Photoshop.PSBFile", "Adobe.Illustrator"]
    )

    for pid in adobe_progids:
        path = f"Software\\Classes\\{pid}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as k:
                has_icon = False
                try:
                    with winreg.OpenKey(k, "DefaultIcon"):
                        has_icon = True
                except Exception:
                    pass

                has_cmd = False
                try:
                    with winreg.OpenKey(k, r"shell\open\command"):
                        has_cmd = True
                except Exception:
                    pass

            if not has_icon and not has_cmd:
                def _del_tree(root, subkey):
                    try:
                        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
                            sub_count, _, _ = winreg.QueryInfoKey(key)
                            for _ in range(sub_count):
                                child = winreg.EnumKey(key, 0)
                                _del_tree(key, child)
                        winreg.DeleteKey(root, subkey)
                    except Exception:
                        pass
                _del_tree(winreg.HKEY_CURRENT_USER, path)
        except Exception:
            pass

def repair_adobe_associations():
    """
    Ensures that .psd, .psb, .ai, .eps have valid DefaultIcon associations in Windows Registry.
    If Adobe software is installed, points directly to Photoshop/Illustrator icons.
    If Adobe is NOT installed, registers RawView's built-in authentic Ps and Ai badge icons
    so Windows never shows a blank white document icon!
    """
    if not IS_WINDOWS:
        return

    assets_dir = get_assets_dir()
    ps_ico = str((assets_dir / "ps_badge.ico").resolve())
    ai_ico = str((assets_dir / "ai_badge.ico").resolve())

    ps_exe = find_installed_photoshop()
    ai_exe = find_installed_illustrator()

    ps_icon_path = f'"{ps_exe}",1' if ps_exe else f'"{ps_ico}",0'
    ai_icon_path = f'"{ai_exe}",1' if ai_exe else f'"{ai_ico}",0'

    # 1. Repair Photoshop ProgIDs & .psd / .psb
    ps_progids = [f"Photoshop.Image.{v}" for v in range(15, 35)] + ["Photoshop.Image"]
    for pid in ps_progids:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{pid}\\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ps_icon_path)
        except Exception:
            pass

    psb_progids = [f"Photoshop.PSBFile.{v}" for v in range(15, 35)] + ["Photoshop.PSBFile"]
    for pid in psb_progids:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{pid}\\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ps_icon_path)
        except Exception:
            pass

    # Ensure .psd has a valid ProgID or DefaultIcon
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.psd") as k:
            cur_val = ""
            try:
                cur_val, _ = winreg.QueryValueEx(k, "")
            except Exception:
                pass
            if not cur_val:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Photoshop.Image.24")
                winreg.SetValueEx(k, "Content Type", 0, winreg.REG_SZ, "image/vnd.adobe.photoshop")
    except Exception:
        pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.psd\\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ps_icon_path)
    except Exception:
        pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.psb\\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ps_icon_path)
    except Exception:
        pass

    # 2. Repair Illustrator ProgIDs & .ai / .eps
    ai_progids = [f"Adobe.Illustrator.{v}" for v in range(15, 35)] + ["Adobe.Illustrator", "Adobe.Illustrator.EPS"]
    for pid in ai_progids:
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{pid}\\DefaultIcon") as k:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ai_icon_path)
        except Exception:
            pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.ai") as k:
            cur_val = ""
            try:
                cur_val, _ = winreg.QueryValueEx(k, "")
            except Exception:
                pass
            if not cur_val:
                winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "Adobe.Illustrator.24")
                winreg.SetValueEx(k, "Content Type", 0, winreg.REG_SZ, "application/illustrator")
    except Exception:
        pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.ai\\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ai_icon_path)
    except Exception:
        pass

    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\Classes\\.eps\\DefaultIcon") as k:
            winreg.SetValueEx(k, "", 0, winreg.REG_SZ, ai_icon_path)
    except Exception:
        pass

    # 3. Ensure ShowTypeOverlay is enabled
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced") as k:
            winreg.SetValueEx(k, "ShowTypeOverlay", 0, winreg.REG_DWORD, 1)
    except Exception:
        pass

def flush_shell_icon_cache():
    """Flushes Windows icon cache and triggers full Explorer association update."""
    if not IS_WINDOWS:
        return

    ie4uinit = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "ie4uinit.exe"
    if ie4uinit.exists():
        try:
            subprocess.run([str(ie4uinit), "-show"], capture_output=True, timeout=2.0)
        except Exception:
            pass

    try:
        import ctypes
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "shell32"):
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass

def touch_file_for_shell_regeneration(file_path: str) -> bool:
    """
    Slightly modifies a file's last modified time (+1 second).
    This invalidates Windows Explorer's internal cache in thumbcache_*.db across
    all local (NTFS/FAT32) and remote (SMB/NAS) filesystems, forcing Windows
    to regenerate the thumbnail with the clean, authentic application icon badge!
    """
    try:
        if not os.path.isfile(file_path):
            return False
        st = os.stat(file_path)
        new_mtime = st.st_mtime + 1.0
        try:
            os.utime(file_path, (st.st_atime, new_mtime))
        except PermissionError:
            try:
                os.chmod(file_path, stat_module.S_IWRITE)
                os.utime(file_path, (st.st_atime, new_mtime))
            except Exception:
                return False

        if IS_WINDOWS:
            try:
                import ctypes
                w_path = ctypes.c_wchar_p(str(Path(file_path).resolve()))
                ctypes.windll.shell32.SHChangeNotify(0x00002000, 0x0005, w_path, None)  # SHCNE_UPDATEITEM
            except Exception:
                pass
        return True
    except Exception:
        return False

def run_full_shell_repair():
    """Runs the complete self-healing suite for Windows Explorer shell icons."""
    clean_user_shadow_keys()
    repair_adobe_associations()
    flush_shell_icon_cache()
