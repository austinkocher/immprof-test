"""Check that every address on the live site has a page on the new site.

Usage:  python3 tools/check_addresses.py [PUBLIC_DIR] [--posts FILE_OF_URLS]
Reads the live site's own lists of addresses (its sitemaps, saved in _import/) and looks for each one in the built site.
A post counts as kept when public/<slug>/index.html exists. Prints what is missing.
"""
import os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pub = next((a for a in sys.argv[1:] if not a.startswith("--") and os.path.isdir(a)), os.path.join(HERE, "public"))

def locs(name):
    path = os.path.join(HERE, "_import", name)
    return re.findall(r"<loc>([^<]+)</loc>", open(path).read()) if os.path.exists(path) else []

def have(url):
    path = url.split("immprof.com", 1)[1]
    return os.path.exists(os.path.join(pub, path.strip("/"), "index.html")) or (path == "/" and os.path.exists(os.path.join(pub, "index.html")))

if "--posts" in sys.argv:
    posts = [u.strip() for u in open(sys.argv[sys.argv.index("--posts") + 1]) if u.strip()]
else:
    posts = locs("sitemap-posts.xml")
groups = [("posts", posts), ("pages", locs("sitemap-pages.xml")), ("authors", locs("sitemap-authors.xml")), ("tags", locs("sitemap-tags.xml")),
          ("feeds and lists", ["https://immprof.com/rss/", "https://immprof.com/page/2/"])]
bad = 0
for name, urls in groups:
    missing = [u for u in urls if not have(u)]
    bad += len(missing)
    print(f"{name}: {len(urls) - len(missing)} of {len(urls)} addresses kept")
    for u in missing[:12]:
        print("   missing:", u)
    if len(missing) > 12:
        print(f"   and {len(missing) - 12} more")
sys.exit(1 if bad else 0)
