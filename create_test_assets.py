import os
from PIL import Image, ImageDraw
from psd_tools import PSDImage
import reportlab.pdfgen.canvas

os.makedirs('test_assets', exist_ok=True)

# 1. TIFF
img_tiff = Image.new('RGB', (1920, 1080), color=(24, 76, 120))
d = ImageDraw.Draw(img_tiff)
d.rectangle([50, 50, 1870, 1030], outline=(255, 255, 255), width=8)
d.text((100, 120), 'RawView TIFF 1080p High-Res Sample', fill=(255, 255, 255))
img_tiff.save('test_assets/sample.tiff', format='TIFF')
print('Created sample.tiff')

# 2. SVG
svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#FF007F;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#7928CA;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="800" height="600" rx="24" fill="url(#grad1)" />
  <circle cx="400" cy="300" r="140" fill="#00DFD8" opacity="0.85" />
  <text x="400" y="315" font-family="Segoe UI, sans-serif" font-size="36" fill="white" text-anchor="middle" font-weight="bold">RawView Vector SVG</text>
</svg>"""
with open('test_assets/sample.svg', 'w', encoding='utf-8') as f:
    f.write(svg_content)
print('Created sample.svg')

# 3. PSD
img_psd = Image.new('RGBA', (1440, 900), color=(46, 204, 113, 255))
d2 = ImageDraw.Draw(img_psd)
d2.rectangle([40, 40, 1400, 860], outline=(255, 255, 255), width=6)
d2.text((80, 100), 'RawView PSD Photoshop Composite Sample', fill=(255, 255, 255, 255))
psd = PSDImage.frompil(img_psd)
psd.save('test_assets/sample.psd')
print('Created sample.psd')

# 4. AI (PDF-compatible Illustrator file)
c = reportlab.pdfgen.canvas.Canvas('test_assets/sample.ai', pagesize=(1200, 800))
c.setFillColorRGB(0.85, 0.15, 0.35)
c.rect(0, 0, 1200, 800, fill=1)
c.setFillColorRGB(1, 1, 1)
c.setFont('Helvetica-Bold', 36)
c.drawString(100, 450, 'RawView Adobe Illustrator (.AI) Sample')
c.setFont('Helvetica', 22)
c.drawString(100, 390, 'Ultra-fast vector rasterization with zero lag')
c.save()
print('Created sample.ai')

# 5. EPS
eps_content = """%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 600 400
%%Title: RawView EPS Sample
%%Creator: RawView
%%Pages: 1
%%EndComments

0.15 0.35 0.75 setrgbcolor
0 0 600 400 rectfill
1 1 1 setrgbcolor
/Helvetica-Bold findfont 30 scalefont setfont
80 220 moveto
(RawView EPS Vector Sample) show
showpage
%%EOF
"""
with open('test_assets/sample.eps', 'w', encoding='utf-8') as f:
    f.write(eps_content)
print('Created sample.eps')

print('All 5 test assets created successfully!')
