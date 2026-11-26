"""Take pictures of one page of each kind, at desktop and phone width, for before-and-after comparison.
   python3 -I shots.py OUTDIR [BASE]        (BASE defaults to http://localhost:4176)
   python3 shots.py --compare DIR_A DIR_B   (needs Pillow; prints the share of pixels that differ on each picture)"""
import subprocess, sys, os
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAGES = {"home": "/", "archive": "/archive/", "archive-q": "/archive/?q=asylum&tags=1&tag=Detention", "editors": "/author/",
         "editor": "/author/kevin/", "guest": "/author/david-bacon/", "section": "/enforcement/", "tag": "/tag/detention/", "tags": "/tag/",
         "sections": "/sections/", "library": "/library/", "libpage": "/immigration-syllabi/", "about": "/about/",
         "old-search": "/search/?q=asylum", "subscribe": "/subscribe/", "post": None, "post2": None}
def main():
    if sys.argv[1] == "--compare":
        from PIL import Image, ImageChops
        a, b = sys.argv[2], sys.argv[3]
        for f in sorted(os.listdir(a)):
            x, y = Image.open(os.path.join(a, f)).convert("RGB"), Image.open(os.path.join(b, f)).convert("RGB")
            if x.size != y.size: print(f, "SIZE", x.size, y.size); continue
            d = ImageChops.difference(x, y).convert("L").point(lambda v: 255 if v > 24 else 0)
            n = d.histogram()[255]; box = d.getbbox()
            print(f"{f:28s} {100 * n / (x.size[0] * x.size[1]):6.3f}%  {box if n else ''}")
        return
    out, base = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "http://localhost:4176")
    os.makedirs(out, exist_ok=True)
    pages = dict(PAGES)
    pages["post"] = os.environ.get("POST1", "/"); pages["post2"] = os.environ.get("POST2", "/")
    for name, path in pages.items():
        for w, h in ((1300, 2600), (500, 3200)):
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--disk-cache-size=1", f"--window-size={w},{h}",
                            "--virtual-time-budget=9000", f"--screenshot={out}/{name}-{w}.png", base + path], capture_output=True, timeout=120)
main()
