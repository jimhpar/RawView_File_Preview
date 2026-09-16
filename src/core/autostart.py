import sys
import os
import shlex
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

if IS_WINDOWS:
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "RawView"
MAC_LAUNCH_AGENT_DIR = Path.home() / "Library" / "LaunchAgents"
MAC_PLIST_FILE = MAC_LAUNCH_AGENT_DIR / "com.blackbox.rawview.plist"

def get_executable_command() -> str:
    """Returns the full command line string to launch RawView with --minimized flag."""
    if getattr(sys, 'frozen', False):
        # Running as compiled PyInstaller executable or macOS app bundle
        exe_path = sys.executable
        return f'"{exe_path}" --minimized'
    else:
        # Running as python script
        py_exe = sys.executable
        script_path = str(Path(__file__).resolve().parent.parent / "app.py")
        return f'"{py_exe}" "{script_path}" --minimized'

def _mac_get_plist_content(exec_cmd: str) -> str:
    args = shlex.split(exec_cmd)
    args_xml = "\n".join(f"        <string>{arg}</string>" for arg in args)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.blackbox.rawview</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""

def is_autostart_enabled() -> bool:
    """Checks if RawView is registered to run on system startup."""
    if IS_MACOS:
        return MAC_PLIST_FILE.exists()
    
    if IS_WINDOWS and winreg:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(value)
        except (FileNotFoundError, OSError):
            return False
    return False

def set_autostart(enable: bool) -> bool:
    """Enables or disables autostart on Windows registry or macOS LaunchAgent."""
    if IS_MACOS:
        try:
            if enable:
                MAC_LAUNCH_AGENT_DIR.mkdir(parents=True, exist_ok=True)
                content = _mac_get_plist_content(get_executable_command())
                with open(MAC_PLIST_FILE, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                if MAC_PLIST_FILE.exists():
                    MAC_PLIST_FILE.unlink()
            return True
        except Exception as e:
            print(f"Failed to update macOS LaunchAgent: {e}")
            return False

    if IS_WINDOWS and winreg:
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

    return False
