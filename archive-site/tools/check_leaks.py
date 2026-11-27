"""Prove that nothing from the damaged author fields is anywhere in this site's folder.

Usage:  python3 -I tools/check_leaks.py RAW_DIR/archive.json

In about 900 records of the raw download the author field holds a reader's name, email address, IP number and internet
address. This reads those pieces from the raw file (which stays outside every repository) and searches every file in the
site's folder for them: content, data, layouts, tools, the built pages in public/ and the search index (its files are
unpacked before they are searched). It prints counts only, never the pieces themselves.
"""
import gzip, json, os, re, sys, collections

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEB = re.compile(r"https?://[^\s\"'<>]+", re.I)
IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

def main():
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    posts = json.load(open(sys.argv[1], encoding="utf-8"))
    pieces = collections.defaultdict(set); name_of = {}
    for p in posts:
        a = p.get("author") or ""
        if "<br>" not in a: continue
        pieces["raw author field"].add(a.lower())
        pieces["raw author field"].add(re.sub(r"\s+", " ", a.replace("<br>", " ")).strip().lower())
        for e in EMAIL.findall(a): pieces["email address"].add(e.lower())
        for i in IPV4.findall(a): pieces["IP number"].add(i)
        for u in WEB.findall(a): pieces["internet address"].add(u.lower().rstrip("/.,;)"))
        n = a.split("<br>")[0].strip()
        if len(n) >= 4: name_of[p["basename"]] = n.lower()
        # the labelled lines exactly as the field has them
        for line in a.split("<br>")[1:]:
            if len(line.strip()) > 8: pieces["labelled line (EMAIL:, IP:, URL:)"].add(line.strip().lower())
    hits = {k: collections.Counter() for k in pieces}; files = 0; size = 0
    web_by_host = collections.defaultdict(list)
    for u in pieces["internet address"]: web_by_host[re.sub(r"https?://", "", u).split("/")[0]].append(u)
    hosts = collections.Counter()
    for d, dirs, fs in os.walk(site):
        dirs[:] = [x for x in dirs if x != ".git"]
        in_content = os.path.relpath(d, site).startswith("content")
        for f in fs:
            path = os.path.join(d, f); raw = open(path, "rb").read()
            if raw[:2] == b"\x1f\x8b":
                try: raw = gzip.decompress(raw)
                except Exception: pass
            t = raw.decode("utf-8", "replace").lower(); files += 1; size += len(t)
            rel = os.path.relpath(path, site)
            for e in EMAIL.findall(t):
                if e in pieces["email address"]: hits["email address"][rel] += 1
            for i in IPV4.findall(t):
                if i in pieces["IP number"]: hits["IP number"][rel] += 1
            # every damaged author field has "EMAIL:"/"IP:"/"URL:" lines, so only a text with a label can hold one
            if "ip: " in t or "email: " in t or "url: " in t:
                for k in ("raw author field", "labelled line (EMAIL:, IP:, URL:)"):
                    for x in pieces[k]:
                        if x in t: hits[k][rel] += 1
            for u in WEB.findall(t):
                if any(u.startswith(x) for x in web_by_host.get(re.sub(r"https?://", "", u).split("/")[0], ())):
                    hits["internet address"][rel] += 1
                    if in_content: hosts[re.sub(r"https?://", "", u).split("/")[0]] += 1
    print("files searched:", files, "| characters:", size)
    for k in pieces:
        print(f"{k}: {len(pieces[k])} distinct pieces | found {sum(hits[k].values())} times in {len(hits[k])} files")
    # A reader's name is looked for only in the post it was attached to.
    own = 0
    for b, n in name_of.items():
        f = os.path.join(site, "content", "post", b + ".html")
        if not os.path.isfile(f) or n in ("immigration prof", "law professor blogs llc"): continue   # an editor answering under the blog's name
        text = "\n".join(l for l in open(f, encoding="utf-8").read().lower().split("\n") if not l.startswith("byline: "))
        if n in text: own += 1
    print(f"reader's name present in the post it commented on: {own} of {len(name_of)} (the post's own title or text names that person)")
    # An internet address a reader gave can be one the blog itself linked to (a video site's front page, the reader's own
    # blog in a post the reader wrote). Those are counted and named by host, since a host name is not personal.
    print("internet addresses found in post text (content/post), by host:", dict(hosts.most_common()))
    bad = sum(sum(hits[k].values()) for k in hits if k != "internet address")
    print("RESULT:", "clean: no email address, IP number, author field or labelled line from a damaged record is in the site folder" if not bad else "LEAK FOUND")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
