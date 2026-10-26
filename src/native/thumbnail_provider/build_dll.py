import os
import sys
import subprocess
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def find_zig() -> str:
    # 1. PATH
    z = shutil.which("zig")
    if z and os.path.exists(z):
        return z
    # 2. WinGet package directory
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_dir = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_dir.exists():
            matches = list(winget_dir.glob("**/zig.exe"))
            if matches:
                return str(matches[0])
    return ""

def compile_dll(output_dir: Path = None) -> bool:
    zig_exe = find_zig()
    if not zig_exe:
        print("[!] Error: zig.exe not found.")
        return False

    out_dir = output_dir or BASE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dll = out_dir / "RawViewThumbnailProvider.dll"

    cmd = [
        zig_exe, "c++",
        "-O3",
        "-shared",
        "-target", "x86_64-windows-gnu",
        "-municode",
        str(BASE_DIR / "RawViewThumbnailProvider.cpp"),
        str(BASE_DIR / "dllmain.cpp"),
        str(BASE_DIR / "RawViewThumbnailProvider.def"),
        "-o", str(out_dll),
        "-lshlwapi",
        "-ladvapi32",
        "-lole32",
        "-lshell32",
        "-lgdi32",
        "-luser32",
        "-luuid"
    ]

    print(f"[*] Compiling RawViewThumbnailProvider.dll with Zig ({zig_exe})...")
    proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)

    if proc.returncode != 0:
        print("[!] Compilation failed!")
        print(proc.stdout)
        print(proc.stderr)
        return False

    if out_dll.exists():
        print(f"[+] Successfully compiled: {out_dll} ({out_dll.stat().st_size} bytes)")
        return True
    else:
        print(f"[!] Output DLL not found: {out_dll}")
        return False

if __name__ == "__main__":
    success = compile_dll()
    sys.exit(0 if success else 1)
