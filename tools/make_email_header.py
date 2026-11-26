"""Draw the picture at the top of each email: the site's logo centered on the header cream, as it is on the site.
1200 by 240 pixels, shown at 600 by 120. Written to static/brand/email-header.png, which is where the emails look for it
(https://immprof.com/brand/email-header.png), and copied to ../email/assets/ for the samples.
Run with a Python that has Pillow:  ~/Documents/EditorialPipeline/venv/bin/python3 tools/make_email_header.py
"""
import os, shutil
from PIL import Image

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logo = Image.open(os.path.join(HERE, "static", "brand", "logo.png")).convert("RGBA")
band = Image.new("RGBA", (1200, 240), "#f7f1e5")
w = 860
logo = logo.resize((w, round(logo.height * w / logo.width)), Image.LANCZOS)
band.alpha_composite(logo, ((1200 - w) // 2, (240 - logo.height) // 2 + 6))
out = os.path.join(HERE, "static", "brand", "email-header.png")
band.convert("RGB").save(out, optimize=True)
samples = os.path.join(HERE, "..", "email", "assets")
if os.path.isdir(samples):
    shutil.copy(out, os.path.join(samples, "email-header.png"))
print("wrote", out)
