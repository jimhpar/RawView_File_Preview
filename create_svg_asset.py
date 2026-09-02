import base64
from pathlib import Path

# Load icon_transparent.png and embed in SVG
with open("assets/icon_transparent.png", "rb") as f:
    b64_data = base64.b64encode(f.read()).decode("utf-8")

svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122 150" width="122" height="150">
  <image href="data:image/png;base64,{b64_data}" width="122" height="150" />
</svg>"""

with open("assets/app_icon.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print("assets/app_icon.svg generated!")
