"""Read saved post pages from the live Ghost site into one JSON file the importer uses.

Usage:  python3 tools/read_ghost_pages.py FOLDER_OF_SAVED_PAGES OUT.json
Each saved page is the HTML of https://immprof.com/<slug>/ fetched with curl. Taken from each page: slug, title, publish time,
author name and address, feature image, and the post body as HTML, unchanged.
"""
import glob, html, json, os, re, sys

def read(path):
    h = open(path, errors="ignore").read()
    g = lambda pat: (re.search(pat, h, flags=re.S) or [None, ""])[1]
    url = g(r'<link rel="canonical" href="([^"]+)"')
    body = g(r'<section class="gh-content[^>]*>(.*?)</section>')
    return dict(slug=url.rstrip("/").split("/")[-1], url=url, title=html.unescape(g(r'<meta property="og:title" content="([^"]*)"')),
                date=g(r'article:published_time" content="([^"]*)"'), author=g(r'"author":\s*\{[^}]*?"name":\s*"([^"]+)"'),
                author_url=g(r'"author":\s*\{[^}]*?"url":\s*"([^"]+)"'), image=g(r'<meta property="og:image" content="([^"]*)"'),
                body=body.strip())

if __name__ == "__main__":
    rows = [read(f) for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.html")))]
    rows = [r for r in rows if r["slug"] and r["date"]]
    rows.sort(key=lambda r: r["date"], reverse=True)
    json.dump(rows, open(sys.argv[2], "w"))
    print(len(rows), "posts", rows[-1]["date"][:10], "to", rows[0]["date"][:10], round(os.path.getsize(sys.argv[2]) / 1e6, 1), "MB")
