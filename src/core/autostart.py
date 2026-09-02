import sys
import os
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "RawView"

def get_executable_command() -> str:
    """Returns the full command line string to launch RawView with --minimized flag."""
    if getattr(sys, 'frozen', False):
        # Running as compiled PyInstaller executable
        exe_path = sys.executable
        return f'"{exe_path}" --minimized'
    else:
        # Running as python script
        py_exe = sys.executable
        script_path = str(Path(__file__).resolve().parent.parent / "app.py")
        return f'"{py_exe}" "{script_path}" --minimized'

def is_autostart_enabled() -> bool:
    """Checks if RawView is registered to run on Windows startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except (FileNotFoundError, OSError):
        return False

def set_autostart(enable: bool) -> bool:
    """Enables or disables autostart in the Windows CurrentVersion\\Run registry key."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_WRITE) as key:
            if enable:
                cmd = get_executable_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Failed to update autostart registry: {e}")
        return False
