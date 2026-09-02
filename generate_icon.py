import os
from src.core.icons import save_app_ico_file

os.makedirs("assets", exist_ok=True)
save_app_ico_file("assets/app_icon.ico")
print("assets/app_icon.ico created successfully!")
