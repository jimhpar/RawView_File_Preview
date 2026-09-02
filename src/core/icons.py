import os
import sys
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap

def get_asset_path(filename: str) -> str:
    """Returns absolute path to an asset whether running from source or frozen binary."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys._MEIPASS)
        candidate = base_dir / "assets" / filename
        if candidate.exists():
            return str(candidate)
        candidate_root = base_dir / filename
        if candidate_root.exists():
            return str(candidate_root)
    # Source mode
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / "assets" / filename)

def create_app_icon(size: int = 256) -> QIcon:
    """Loads the RawView application icon."""
    ico_path = get_asset_path("app_icon.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    
    png_path = get_asset_path("app_icon_256.png")
    if os.path.exists(png_path):
        return QIcon(png_path)

    # Fallback empty icon
    return QIcon()

def save_app_ico_file(output_path: str):
    """Ensures app_icon.ico exists."""
    if not os.path.exists(output_path):
        from process_uploaded_icon import main as proc_main
        pass
