import os
import sys
import ctypes
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def get_dll_path() -> Path:
    # 1. Dist directory
    p1 = BASE_DIR / "dist" / "RawView" / "RawViewThumbnailProvider.dll"
    if p1.exists():
        return p1
    # 2. Source build directory
    p2 = BASE_DIR / "src" / "native" / "thumbnail_provider" / "RawViewThumbnailProvider.dll"
    if p2.exists():
        return p2
    return p1

def register_provider(dll_path: Path = None) -> bool:
    target = dll_path or get_dll_path()
    if not target.exists():
        print(f"[!] DLL not found at: {target}")
        from src.native.thumbnail_provider.build_dll import compile_dll
        print("[*] Attempting to compile DLL first...")
        if not compile_dll(target.parent):
            return False

    print(f"[*] Registering COM Shell Thumbnail Provider: {target}")
    try:
        dll = ctypes.WinDLL(str(target))
        hr = dll.DllRegisterServer()
        if hr == 0:
            print("[+] Successfully registered RawView Shell Thumbnail Provider for all supported extensions!")
            # Trigger Windows Shell change notification
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            return True
        else:
            print(f"[!] DllRegisterServer returned HRESULT: 0x{hr & 0xFFFFFFFF:08X}")
            return False
    except Exception as e:
        print(f"[!] Registration failed: {e}")
        return False

def unregister_provider(dll_path: Path = None) -> bool:
    target = dll_path or get_dll_path()
    if not target.exists():
        print(f"[!] DLL not found at: {target}")
        return False

    print(f"[*] Unregistering COM Shell Thumbnail Provider: {target}")
    try:
        dll = ctypes.WinDLL(str(target))
        hr = dll.DllUnregisterServer()
        if hr == 0:
            print("[+] Successfully unregistered RawView Shell Thumbnail Provider.")
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
            return True
        else:
            print(f"[!] DllUnregisterServer returned HRESULT: 0x{hr & 0xFFFFFFFF:08X}")
            return False
    except Exception as e:
        print(f"[!] Unregistration failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--unregister":
        success = unregister_provider()
    else:
        success = register_provider()
    sys.exit(0 if success else 1)
