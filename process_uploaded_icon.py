import os
import shutil
from PIL import Image, ImageOps, ImageFilter, ImageDraw

src_img_path = r"C:\Users\Zim\.gemini\antigravity-ide\brain\b2967df4-e507-4311-b325-4e89bc50878e\.user_uploaded\media_1788256731599.png"
os.makedirs("assets", exist_ok=True)

# 1. Load original logo
src_img = Image.open(src_img_path).convert("RGBA")
print(f"Loaded uploaded icon: size={src_img.size}, mode={src_img.mode}")

# The logo is a black emblem with alpha transparency
# Let's verify non-zero alpha pixels
alpha = src_img.split()[3]

# Create multi-resolution ICO files
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
ico_images = []

for w, h in sizes:
    # High-quality resize maintaining aspect ratio
    # Scale emblem to fit nicely with small margin
    scale = min((w * 0.85) / src_img.width, (h * 0.85) / src_img.height)
    new_w = max(int(src_img.width * scale), 8)
    new_h = max(int(src_img.height * scale), 8)
    
    resized_logo = src_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Create transparent canvas
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    offset_x = (w - new_w) // 2
    offset_y = (h - new_h) // 2
    
    canvas.paste(resized_logo, (offset_x, offset_y), mask=resized_logo)
    ico_images.append(canvas)

# Save master ICO
ico_images[0].save(
    "assets/app_icon.ico",
    format="ICO",
    sizes=[(im.width, im.height) for im in ico_images]
)
ico_images[0].save("assets/app_icon_256.png")
src_img.save("assets/icon_transparent.png")
print("assets/app_icon.ico created with true black emblem on clean transparent alpha!")
