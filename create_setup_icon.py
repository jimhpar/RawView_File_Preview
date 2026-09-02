import os
from PIL import Image

src_img = Image.open("assets/source_logo.png").convert("RGBA")

# Create standard uncompressed ICO with standard sizes for Windows & Inno Setup
sizes = [(48, 48), (32, 32), (16, 16)]
ico_images = []

for w, h in sizes:
    scale = min((w * 0.85) / src_img.width, (h * 0.85) / src_img.height)
    new_w = max(int(src_img.width * scale), 4)
    new_h = max(int(src_img.height * scale), 4)
    
    resized = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    offset_x = (w - new_w) // 2
    offset_y = (h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y), mask=resized)
    ico_images.append(canvas)

ico_images[0].save("assets/setup_icon.ico", format="ICO", sizes=[(im.width, im.height) for im in ico_images])
print("assets/setup_icon.ico generated!")
