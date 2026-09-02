import shutil
import os
from PIL import Image

src_ico = "Rawview.ico"
os.makedirs("assets", exist_ok=True)

# Copy Rawview.ico to assets/app_icon.ico
shutil.copyfile(src_ico, "assets/app_icon.ico")
print("Copied Rawview.ico to assets/app_icon.ico")

# Generate 256x256 PNG for Qt/Tray
img = Image.open(src_ico)
img.save("assets/app_icon_256.png")
print("Saved assets/app_icon_256.png")
