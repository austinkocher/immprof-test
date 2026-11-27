"""Check the built site in public/: every link, picture, stylesheet and script address that points inside the site
leads to a file, every page of the test copy asks not to be listed, and the search index is there.

Usage:  python3 -I tools/check_build.py [BASE_PATH]
BASE_PATH is the folder part of the address the site was built for, for example /immprof-test/historical/ (the default).
"""
import os, re, sys, collections
from urllib.parse import unquote

def main():
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pub = os.path.join(site, "public")
    base = sys.argv[1] if len(sys.argv) > 1 else "/immprof-test/historical/"
    ATTR = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#?]*)""", re.I)
    kinds = collections.Counter(); bad = collections.Counter(); bad_ex = {}; noindex_missing = []; root_abs = collections.Counter(); inside = 0
    for d, _, fs in os.walk(pub):
        if os.sep + "pagefind" in d: continue
        for f in fs:
            if not f.endswith(".html"): continue
            p = os.path.join(d, f); rel = os.path.relpath(p, pub)
            t = open(p, encoding="utf-8", errors="replace").read()
            kind = "alias" if rel.startswith("immigration") else "post" if rel.startswith("post") else "other"
            kinds[kind] += 1
            if 'name="robots" content="noindex' not in t: noindex_missing.append(rel)
            if kind == "alias":
                m = re.search(r'url=([^"]+)"', t); links = [re.sub(r"^https?://[^/]+", "", m.group(1))] if m else []
            else:
                # the frame of the page (everything outside the post's own text) and links between posts
                links = ATTR.findall(t)
            for u in links:
                if u.startswith(base):
                    inside += 1
                    target = os.path.join(pub, unquote(u[len(base):]))
                    if u.endswith("/") or os.path.isdir(target): target = os.path.join(target, "index.html")
                    if not os.path.isfile(target):
                        bad[kind] += 1; bad_ex.setdefault(kind, []).append((rel, u))
                elif u.startswith("/") and not u.startswith("//"):
                    root_abs[kind] += 1; bad_ex.setdefault("root:" + kind, []).append((rel, u))
    print("pages read:", dict(kinds))
    print("links inside the site checked:", inside, "| leading nowhere:", dict(bad))
    for k, v in bad_ex.items():
        if not k.startswith("root:"): print("  ", k, v[:5])
    print("addresses that start at the top of the host and so leave the site's folder (old TypePad paths inside post text):", dict(root_abs))
    for k, v in bad_ex.items():
        if k.startswith("root:"): print("  ", k, v[:4])
    print("pages without the noindex line:", len(noindex_missing), noindex_missing[:5])
    pf = os.path.join(pub, "pagefind")
    print("search index:", os.path.isfile(os.path.join(pf, "pagefind.js")), "| fragments:", len(os.listdir(os.path.join(pf, "fragment"))) if os.path.isdir(os.path.join(pf, "fragment")) else 0)
    sys.exit(1 if bad or noindex_missing else 0)

if __name__ == "__main__":
    main()
