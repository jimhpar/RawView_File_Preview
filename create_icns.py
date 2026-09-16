import os
from pathlib import Path
from PIL import Image

def generate_icns():
    project_root = Path(__file__).resolve().parent
    assets_dir = project_root / "assets"
    output_icns = assets_dir / "app_icon.icns"

    if output_icns.exists() and output_icns.stat().st_size > 1000:
        print(f"app_icon.icns already exists: {output_icns} ({output_icns.stat().st_size} bytes)")
        return

    candidates = [
        assets_dir / "icon_transparent.png",
        assets_dir / "source_logo.png",
        assets_dir / "app_icon_256.png",
        assets_dir / "app_icon.ico",
    ]
    source_img = None
    for c in candidates:
        if c.exists():
            source_img = c
            break

    if not source_img:
        print("Notice: No icon image found to generate ICNS.")
        return

    print(f"Generating macOS ICNS from: {source_img}")
    base = Image.open(source_img).convert("RGBA")
    
    # Fit into a 512x512 canvas maintaining aspect ratio
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    base.thumbnail((460, 460), Image.Resampling.LANCZOS)
    x = (512 - base.width) // 2
    y = (512 - base.height) // 2
    canvas.paste(base, (x, y), base)

    # Save as multi-resolution macOS ICNS icon
    canvas.save(output_icns, format="ICNS")
    print(f"Successfully generated: {output_icns} ({output_icns.stat().st_size} bytes)")

if __name__ == "__main__":
    generate_icns()
