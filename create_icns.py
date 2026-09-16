import os
from pathlib import Path
from PIL import Image

def generate_icns():
    project_root = Path(__file__).resolve().parent
    assets_dir = project_root / "assets"
    source_png = assets_dir / "icon_transparent.png"
    if not source_png.exists():
        source_png = assets_dir / "source_logo.png"

    output_icns = assets_dir / "app_icon.icns"
    print(f"Generating macOS ICNS from: {source_png}")

    base = Image.open(source_png).convert("RGBA")
    
    # Fit into a 512x512 canvas maintaining aspect ratio
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    base.thumbnail((460, 460), Image.Resampling.LANCZOS)
    x = (512 - base.width) // 2
    y = (512 - base.height) // 2
    canvas.paste(base, (x, y), base)

    # Save as multi-resolution macOS ICNS icon
    canvas.save(
        output_icns,
        format="ICNS",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256), (512, 512)]
    )
    print(f"Successfully generated: {output_icns} ({output_icns.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_icns()
