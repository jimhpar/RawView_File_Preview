import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
INSTALLER_OUT = BASE_DIR / "dist_installer"
VERSION_INFO_FILE = BASE_DIR / "file_version_info.txt"

def find_iscc() -> str:
    """Locates Inno Setup Compiler ISCC.exe."""
    possible_paths = [
        shutil.which("iscc"),
        r"C:\Users\Zim\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    for p in possible_paths:
        if p and os.path.exists(p):
            return p
    return ""

def find_signtool() -> str:
    """Locates Microsoft signtool.exe if available."""
    tool = shutil.which("signtool")
    if tool:
        return tool
    kits_dir = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    if kits_dir.exists():
        matches = list(kits_dir.glob("**/x64/signtool.exe"))
        if matches:
            return str(matches[-1])
    return ""

def generate_version_info(output_path: Path, version_str: str, publisher: str):
    """Generates Windows PE file version information resource for PyInstaller."""
    clean_ver = version_str.lstrip("v")
    parts = clean_ver.split(".")
    while len(parts) < 4:
        parts.append("0")
    try:
        ver_tuple = tuple(int(p) for p in parts[:4])
    except ValueError:
        ver_tuple = (3, 9, 6, 0)
    ver_joined = ".".join(str(p) for p in ver_tuple)

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{publisher}'),
            StringStruct('FileDescription', 'RawView - File Preview Utility for Windows'),
            StringStruct('FileVersion', '{ver_joined}'),
            StringStruct('InternalName', 'RawView'),
            StringStruct('LegalCopyright', 'Copyright (c) {publisher}. All rights reserved.'),
            StringStruct('OriginalFilename', 'RawView.exe'),
            StringStruct('ProductName', 'RawView'),
            StringStruct('ProductVersion', '{clean_ver}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    output_path.write_text(content, encoding="utf-8")
    print(f"[+] Generated Windows PE Version Info: {output_path.name}")

def sign_binary(target_path: Path, cert_path: str = "", cert_pass: str = "") -> bool:
    """Signs an executable using either signtool.exe or PowerShell Set-AuthenticodeSignature."""
    if not target_path.exists():
        print(f"[!] Cannot sign: {target_path} does not exist.")
        return False

    cert = cert_path or os.environ.get("RAWVIEW_CERT_PATH") or ""
    pwd = cert_pass or os.environ.get("RAWVIEW_CERT_PASS") or ""

    # Check common fallback locations if not explicitly supplied
    if not cert:
        candidate_certs = [
            BASE_DIR / "cert.pfx",
            BASE_DIR / "installer" / "cert.pfx",
        ]
        for c in candidate_certs:
            if c.exists():
                cert = str(c)
                break

    if not cert or not os.path.exists(cert):
        return False

    print(f"[*] Digitally signing: {target_path.name} with certificate...")
    signtool = find_signtool()
    if signtool:
        cmd = [
            signtool, "sign",
            "/f", cert,
            "/tr", "http://timestamp.digicert.com",
            "/td", "sha256",
            "/fd", "sha256",
        ]
        if pwd:
            cmd.extend(["/p", pwd])
        cmd.append(str(target_path))
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print(f"[+] Successfully signed {target_path.name} using signtool.exe!")
            return True
        else:
            print(f"[-] signtool failed: {res.stderr or res.stdout}. Trying PowerShell fallback...")

    # Fallback to PowerShell Set-AuthenticodeSignature
    ps_cmd = f"""
    $pwd = ConvertTo-SecureString '{pwd}' -AsPlainText -Force
    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2('{cert}', $pwd)
    $res = Set-AuthenticodeSignature -FilePath '{str(target_path)}' -Certificate $cert -TimestampServer 'http://timestamp.digicert.com' -HashAlgorithm SHA256
    if ($res.Status -eq 'Valid') {{ exit 0 }} else {{ Write-Host $res.StatusMessage; exit 1 }}
    """
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[+] Successfully signed {target_path.name} using PowerShell Authenticode!")
        return True
    else:
        print(f"[-] PowerShell signing failed: {res.stderr or res.stdout}")
        return False

def build(cert_path: str = "", cert_pass: str = ""):
    from src.core.config import APP_VERSION, APP_PUBLISHER
    print("=" * 60)
    print(f" RawView {APP_VERSION} - Release & Installer Build Pipeline")
    print(f" Publisher: {APP_PUBLISHER}")
    print("=" * 60)

    # 1. Clean previous build artifacts
    for d in [DIST_DIR, BUILD_DIR, INSTALLER_OUT]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    # 2. Generate Version Info Resource
    generate_version_info(VERSION_INFO_FILE, APP_VERSION, APP_PUBLISHER)

    # 3. Compile with PyInstaller
    icon_path = BASE_DIR / "assets" / "app_icon.ico"
    print("\n[1/2] Compiling RawView.exe with PyInstaller (Anti-False-Positive settings)...")
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--noupx",  # Disable UPX compression to avoid heuristic antivirus detection
        f"--name=RawView",
        f"--icon={icon_path}",
        "--onedir",
        f"--version-file={VERSION_INFO_FILE}",
        "--add-data=assets;assets",
        "--collect-all=pypdfium2",
        "--collect-all=pymupdf",
        "--collect-all=psd_tools",
        "--collect-all=PyQt6",
        "--collect-all=PyQt6.QtMultimedia",
        "--collect-all=PyQt6.QtMultimediaWidgets",
        "--collect-all=reportlab",
        "--collect-all=rawpy",
        "--hidden-import=rawpy",
        "--hidden-import=PyQt6.QtSvg",
        "--hidden-import=PyQt6.QtMultimedia",
        "--hidden-import=PyQt6.QtMultimediaWidgets",
        "--hidden-import=pypdfium2",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=psd_tools",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.TiffImagePlugin",
        "--hidden-import=PIL.PsdImagePlugin",
        "--hidden-import=uiautomation",
        "--hidden-import=comtypes",
        "--hidden-import=win32gui",
        "--hidden-import=win32process",
        "--hidden-import=win32api",
        "--hidden-import=win32con",
        "--hidden-import=striprtf",
        "--hidden-import=src.core.bijoy_converter",
        "--hidden-import=src.core.updater",
        "--hidden-import=src.ui.update_dialog",
        str(BASE_DIR / "src" / "app.py")
    ]

    res = subprocess.run(pyinstaller_cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print("ERROR: PyInstaller compilation failed.")
        sys.exit(1)

    print("PyInstaller build complete: dist/RawView/RawView.exe exists!")

    # Copy assets into dist/RawView/assets
    shutil.copytree(BASE_DIR / "assets", DIST_DIR / "RawView" / "assets", dirs_exist_ok=True)

    # 4. Optional Sign: Sign RawView.exe before installer wraps it
    rawview_exe = DIST_DIR / "RawView" / "RawView.exe"
    signed_rawview = sign_binary(rawview_exe, cert_path, cert_pass)

    # 5. Compile Installer with Inno Setup
    print(f"\n[2/2] Generating RawView_{APP_VERSION}_Setup.exe with Inno Setup...")
    iscc_exe = find_iscc()
    if not iscc_exe:
        print("ERROR: ISCC.exe not found.")
        sys.exit(1)

    iss_path = BASE_DIR / "installer" / "RawView.iss"
    iscc_cmd = [iscc_exe, str(iss_path)]
    res_iss = subprocess.run(iscc_cmd, cwd=str(BASE_DIR / "installer"))
    if res_iss.returncode == 0:
        setup_exe = INSTALLER_OUT / f"RawView_{APP_VERSION}_Setup.exe"
        if not setup_exe.exists():
            # In case name without 'v' or with 'v'
            fallback_name = INSTALLER_OUT / f"RawView_v{APP_VERSION.lstrip('v')}_Setup.exe"
            if fallback_name.exists():
                setup_exe = fallback_name

        print("\n" + "=" * 60)
        print(f" SUCCESS! Installer created successfully:")
        print(f" -> {setup_exe}")
        if setup_exe.exists():
            size_mb = setup_exe.stat().st_size / (1024.0 * 1024.0)
            print(f" -> Size: {size_mb:.2f} MB")
            print(f" -> Publisher: {APP_PUBLISHER}")

            # Sign the installer executable as well
            signed_installer = sign_binary(setup_exe, cert_path, cert_pass)
            if not signed_installer:
                print("\n[NOTE] Executable is NOT digitally signed.")
                print("To sign, provide a certificate via:")
                print("  python build_release.py --cert path/to/cert.pfx --password yourpassword")
                print("or place cert.pfx in the project root.")
        print("=" * 60)
    else:
        print("ERROR: Inno Setup compilation failed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RawView Release & Installer Build Pipeline")
    parser.add_argument("--cert", default="", help="Path to code signing .pfx certificate")
    parser.add_argument("--password", default="", help="Password for the .pfx certificate")
    args = parser.parse_args()

    build(cert_path=args.cert, cert_pass=args.password)
