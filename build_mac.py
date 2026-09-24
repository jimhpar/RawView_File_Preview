#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
INSTALLER_OUT = BASE_DIR / "dist_installer"
APP_BUNDLE = DIST_DIR / "RawView.app"

def build():
    from src.core.config import APP_VERSION, APP_PUBLISHER
    print("=" * 60)
    print(f" RawView {APP_VERSION} - macOS App Bundle & DMG Build Pipeline")
    print(f" Publisher: {APP_PUBLISHER}")
    print("=" * 60)

    if sys.platform != "darwin":
        print("\n[WARNING] This script is designed to run natively on macOS.")
        print(f"Current OS: {sys.platform}")
        print("To build macOS DMG from Windows, use the GitHub Actions workflow:")
        print(" -> .github/workflows/build_macos.yml")
        print("\nExiting.")
        sys.exit(1)

    # 1. Clean previous build artifacts
    print("\n[1/4] Cleaning previous build artifacts...")
    for d in [DIST_DIR, BUILD_DIR, INSTALLER_OUT]:
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d, exist_ok=True)

    # 2. Ensure macOS ICNS Icon exists
    icns_path = BASE_DIR / "assets" / "app_icon.icns"
    if not icns_path.exists():
        print("\n[2/4] Generating assets/app_icon.icns...")
        from create_icns import generate_icns
        generate_icns()
    else:
        print(f"\n[2/4] Found icon: {icns_path}")

    # 3. Compile RawView.app with PyInstaller
    print("\n[3/4] Compiling RawView.app using PyInstaller...")
    spec_path = BASE_DIR / "RawView_mac.spec"
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_path)
    ]
    res = subprocess.run(pyinstaller_cmd, cwd=str(BASE_DIR))
    app_bundle = APP_BUNDLE
    if not app_bundle.exists() and (DIST_DIR / "RawView" / "RawView.app").exists():
        app_bundle = DIST_DIR / "RawView" / "RawView.app"

    if res.returncode != 0 or not app_bundle.exists():
        print("\nERROR: PyInstaller failed to compile RawView.app")
        sys.exit(1)

    print(f"\nSUCCESS: App bundle created at: {app_bundle}")

    # 3.5 Set executable permissions and apply deep ad-hoc code signature
    print("\n[3.5/4] Ensuring executable permissions & applying deep ad-hoc codesign...")
    macos_bin_dir = app_bundle / "Contents" / "MacOS"
    if macos_bin_dir.exists():
        subprocess.run(["chmod", "-R", "+x", str(macos_bin_dir)])

    # Deep ad-hoc codesign required for macOS Gatekeeper & Apple Silicon / Intel AMFI
    codesign_cmd = [
        "codesign",
        "--force",
        "--deep",
        "--sign", "-",
        str(app_bundle)
    ]
    res_sign = subprocess.run(codesign_cmd)
    if res_sign.returncode == 0:
        print("SUCCESS: Deep ad-hoc codesigning complete!")
    else:
        print(f"Notice: codesign returned code {res_sign.returncode}")

    # 4. Create DMG Package using hdiutil
    dmg_name = f"RawView_{APP_VERSION}.dmg"
    dmg_path = INSTALLER_OUT / dmg_name
    print(f"\n[4/4] Creating Apple Disk Image ({dmg_name}) with Applications symlink...")

    dmg_staging = BASE_DIR / "build" / "dmg_staging"
    if dmg_staging.exists():
        shutil.rmtree(dmg_staging, ignore_errors=True)
    os.makedirs(dmg_staging, exist_ok=True)

    # Copy App Bundle to staging
    shutil.copytree(app_bundle, dmg_staging / "RawView.app", symlinks=True)

    # Create Applications alias
    app_link = dmg_staging / "Applications"
    try:
        os.symlink("/Applications", str(app_link))
    except Exception as e:
        print(f"Notice: Applications symlink creation: {e}")

    # Run hdiutil create
    hdiutil_cmd = [
        "hdiutil", "create",
        "-volname", "RawView",
        "-srcfolder", str(dmg_staging),
        "-ov",
        "-format", "UDZO",
        str(dmg_path)
    ]
    res_dmg = subprocess.run(hdiutil_cmd)
    
    # Cleanup staging
    shutil.rmtree(dmg_staging, ignore_errors=True)

    if res_dmg.returncode == 0 and dmg_path.exists():
        dmg_mb = dmg_path.stat().st_size / (1024.0 * 1024.0)
        print("\n" + "=" * 60)
        print(f" SUCCESS! macOS DMG Installer created successfully:")
        print(f" -> {dmg_path}")
        print(f" -> Size: {dmg_mb:.2f} MB")
        print("=" * 60)
    else:
        print("\nERROR: Failed to create DMG using hdiutil.")
        sys.exit(1)

if __name__ == "__main__":
    build()
