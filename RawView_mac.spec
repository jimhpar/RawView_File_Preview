# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

BASE_DIR = Path(os.getcwd()).resolve()

datas = [('assets', 'assets')]
binaries = []
hiddenimports = [
    'rawpy',
    'PyQt6.QtSvg',
    'PyQt6.QtMultimedia',
    'PyQt6.QtMultimediaWidgets',
    'pypdfium2',
    'pymupdf',
    'fitz',
    'psd_tools',
    'PIL',
    'PIL.Image',
    'PIL.TiffImagePlugin',
    'PIL.PsdImagePlugin',
    'striprtf',
    'src.core.bijoy_converter',
    'src.core.updater',
    'src.ui.update_dialog'
]

# Collect essential packages
for pkg in ['pypdfium2', 'pymupdf', 'psd_tools', 'PyQt6', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets', 'reportlab', 'rawpy']:
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception as e:
        print(f"Notice: collect_all for {pkg} skipped or failed: {e}")

a = Analysis(
    ['src/app.py'],
    pathex=[str(BASE_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'uiautomation', 'win32gui', 'win32con', 'win32api', 'win32com', 'comtypes'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RawView',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='RawView',
)

app = BUNDLE(
    coll,
    name='RawView.app',
    icon='assets/app_icon.icns',
    bundle_identifier='com.blackbox.rawview',
    info_plist={
        'CFBundleName': 'RawView',
        'CFBundleDisplayName': 'RawView',
        'CFBundleIdentifier': 'com.blackbox.rawview',
        'CFBundleVersion': '3.9.5',
        'CFBundleShortVersionString': '3.9.5',
        'NSHumanReadableCopyright': 'Copyright © 2026 BlackBox THC. All rights reserved.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
        'LSUIElement': False,
    },
)
