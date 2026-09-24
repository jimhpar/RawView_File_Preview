import os
import sys
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap

def get_asset_path(filename: str) -> str:
    """Returns absolute path to an asset whether running from source or frozen binary."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        candidates = [
            base_dir / "assets" / filename,
            base_dir / "_internal" / "assets" / filename,
            base_dir / filename,
            base_dir.parent / "Resources" / filename,
            Path(sys.executable).parent / "assets" / filename,
            Path(sys.executable).parent / "_internal" / "assets" / filename,
        ]
        for c in candidates:
            if c.exists():
                return str(c)
    # Source mode
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "assets" / filename)

def create_app_icon(size: int = 256) -> QIcon:
    """Loads the RawView application icon with platform-specific priority."""
    if sys.platform == "darwin":
        for name in ["app_icon_256.png", "icon_transparent.png", "app_icon.icns", "app_icon.ico"]:
            p = get_asset_path(name)
            if p and os.path.exists(p):
                return QIcon(p)
    else:
        for name in ["app_icon.ico", "app_icon_256.png"]:
            p = get_asset_path(name)
            if p and os.path.exists(p):
                return QIcon(p)

    return QIcon()

def save_app_ico_file(output_path: str):
    """Ensures app_icon.ico exists."""
    if not os.path.exists(output_path):
        from process_uploaded_icon import main as proc_main
        pass
