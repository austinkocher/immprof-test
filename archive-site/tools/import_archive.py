"""Turn the 2005 to 2025 archive (the TypePad export served by archive.immprof.com) into this site's content files.

Usage:  python3 -I tools/import_archive.py RAW_DIR/archive.json
        python3 -I tools/import_archive.py RAW_DIR/archive.json --check     (reads and counts, writes nothing)
        add --keep-printed-emails to leave in the 8 readers' addresses that posts themselves printed (see below)

archive.json is every record from https://archive.immprof.com/api/posts, joined by tools/join_pages.py. It stays OUTSIDE
every repository: in about 900 records the author field holds a reader's comment with the reader's name, email address and
internet address. This script never writes the author field, the author_email field or anything taken from them.

What it writes, all inside this site's folder:
  content/post/<basename>.html        one file per post, at /post/<basename>/, with the old TypePad address as an alias
  content/year/<YYYY>/_index.md       one page per year
  content/category/<slug>/_index.md   one page per TypePad category, named exactly as TypePad named it
  data/import_stats.json              the counts from this run (no personal information)
  data/left_out.json                  the basenames of records left out, with the reason

Repairs:
  * The export turned every line break in the stored HTML into "<br>", even inside tags. Those are turned back into line
    breaks. A break the editors typed is stored as "<br />" and is kept.
  * A record with no usable date takes its year and month from its old address; the page then shows month and year only.
  * The byline of every post is "Immigration Prof", which is what every intact record has. The author field is never used.
  * A damaged record with no title or no text of its own is left out (none so far).
  * An email address from a damaged author field is taken out of post text too, where a post itself printed it.
  * <img> tags on the two dead hosts are removed, with a link that wraps only that image. Every other image is kept.
  * Links from one old post to another (lawprofessors.typepad.com/immigration/YYYY/MM/name.html) point to /post/<basename>/
    when that post is in the archive.
"""
import html, json, os, re, sys, glob, collections
from urllib.parse import unquote, quote

BYLINE = "Immigration Prof"
# The author names the export gives on records that are intact. Anything else in the author field is not used.
KNOWN_AUTHORS = ("Immigration Prof", "Law Professor Blogs LLC")
# Images on these hosts no longer load (ClaudeImmProf/MIGRATION.md, "The archive, 2005 to 2025"): a recommendation service
# that no longer answers, and TypePad's own servers, which closed and now redirect instead of serving the picture.
DEAD_HOSTS = ("i.zemanta.com", "lawprofessors.typepad.com")
CATEGORY_SLUG = {
    "Books": "books", "Conferences and Call for Papers": "conferences-and-call-for-papers", "Current Affairs": "current-affairs",
    "Data and Research": "data-and-research", "Film & Television": "film-and-television", "Food and Drinks": "food-and-drinks",
    "Immigration Law Clinics": "immigration-law-clinics", "Jobs and Fellowships": "jobs-and-fellowships",
    "Law Review Articles & Essays": "law-review-articles-and-essays", "Music": "music", "Photos": "photos", "Religion": "religion",
    "Sports": "sports", "Teaching Resources": "teaching-resources"}
ADDR = re.compile(r"/immigration/(\d{4})/(\d\d)/([^/]+)\.html$")
GOOD_DATE = re.compile(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEB = re.compile(r"https?://[^\s\"'<>]+", re.I)
IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
SPACE = r"(?:\s|&nbsp;|&#0*160;|<br\s*/?>)*"
MARK = "\x00DEADIMG\x00"


def yq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def host_of(src):
    m = re.match(r"(?:https?:)?//([^/?#]+)", src.strip(), re.I)
    return m.group(1).lower().split(":")[0] if m else ""


def is_dead(src):
    h = host_of(src)
    return any(h == d or h.endswith("." + d) for d in DEAD_HOSTS)


def restore_breaks(body, convert):
    """The export wrote each line break as <br>. Editors' own breaks are <br />."""
    if convert in ("wysiwyg", "0", "richtext"):
        return body.replace("<br>", "\n")
    # Text stored with "line breaks count": a <br> between pieces of text is a real break; one inside a tag is not.
    out = []; depth_in_tag = False; i = 0
    for part in re.split(r"(<br>)", body):
        if part == "<br>":
            out.append("\n" if depth_in_tag else "<br />\n")
            continue
        out.append(part)
        lt, gt = part.rfind("<"), part.rfind(">")
        if lt > gt:
            depth_in_tag = True
        elif gt > lt:
            depth_in_tag = False
    return "".join(out)


def drop_dead_images(body, stats):
    n = [0]

    def img(m):
        s = re.search(r"""\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", m.group(0), re.I | re.S)
        src = (s.group(1) or s.group(2) or s.group(3) or "") if s else ""
        if is_dead(html.unescape(src)):
            n[0] += 1; stats["dead_images_by_host"][host_of(html.unescape(src))] += 1
            return MARK
        stats["images_kept"] += 1
        return m.group(0)
    body = re.sub(r"<img\b[^>]*>", img, body, flags=re.I | re.S)
    if n[0]:
        body, w = re.subn(r"<a\b[^>]*>" + SPACE + r"(?:" + re.escape(MARK) + SPACE + r")+</a>", "", body, flags=re.I | re.S)
        stats["dead_image_links_removed"] += w
        body = body.replace(MARK, "")
        stats["dead_images_removed"] += n[0]; stats["posts_with_dead_images"] += 1
    return body


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    if len(args) != 1:
        print(__doc__); sys.exit(2)
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = os.path.abspath(args[0])
    if raw.startswith(site + os.sep):
        sys.exit("The raw file is inside the site folder. Keep it outside every repository.")
    posts = json.load(open(raw, encoding="utf-8"))
    stats = dict(records=len(posts), written=0, left_out=0, damaged_author=0, date_from_address=0,
        damaged_date=0, links_rewritten=0, links_to_posts_not_in_archive=0, dead_images_removed=0, dead_image_links_removed=0,
        posts_with_dead_images=0, images_kept=0, breaks_restored=0)
    stats["dead_images_by_host"] = collections.Counter()

    # old address name -> basename, for links between posts
    by_name = {}
    for p in posts:
        m = ADDR.search(p.get("unique_url") or "")
        if m:
            by_name[unquote(m.group(3)).lower()] = p["basename"]

    def relink(m):
        name = unquote(html.unescape(m.group(2))).lower()
        if name in by_name:
            stats["links_rewritten"] += 1
            return 'href="/post/' + quote(by_name[name]) + '/"'
        stats["links_to_posts_not_in_archive"] += 1
        return m.group(0)
    LINK = re.compile(r"""href\s*=\s*["'](?:https?:)?(?://(?:www\.)?lawprofessors\.typepad\.com)?/immigration/(\d{4}/\d\d)/([^"'/?#]+)\.html[^"']*["']""", re.I)

    out_posts = os.path.join(site, "content", "post")
    secrets = collections.defaultdict(set)   # pieces of damaged author fields, by kind
    comment_of = {}                          # basename -> start of the reader's comment found in its date field
    left_out = []; years = collections.Counter(); cats = collections.Counter(); files = {}
    for p in posts:
        base = p.get("basename") or ""
        m = ADDR.search(p.get("unique_url") or "")
        if not m or not base:
            left_out.append(dict(basename=base, reason="no old address")); continue
        y, mo, _ = m.groups()
        author = p.get("author") or ""
        damaged = author.strip() not in KNOWN_AUTHORS
        byline = author.strip() if not damaged else BYLINE
        title = html.unescape(re.sub(r"\s+", " ", p.get("title") or "")).strip()
        body = (p.get("body") or "") + (p.get("extended_body") or "")
        if damaged:
            stats["damaged_author"] += 1
            # The damaged field reads: name<br>EMAIL: address<br>IP: number<br>URL: address. Each piece is remembered
            # only to prove afterwards that none of it is in what this script writes.
            pieces = [x.strip() for x in author.split("<br>")]
            if "<br>" in author:
                if len(pieces[0]) >= 4: secrets["name"].add(pieces[0].lower())
                secrets["author field"].add(re.sub(r"\s+", " ", author.replace("<br>", " ")).strip().lower())
                secrets["author field"].add(author.lower())
            for e in EMAIL.findall(author): secrets["email"].add(e.lower())
            for u in WEB.findall(author): secrets["web address"].add(u.lower().rstrip("/.,;)"))
            for i in IPV4.findall(author): secrets["IP number"].add(i)
        # A damaged date field holds the date of a reader's comment, then the comment itself.
        date_raw = p.get("date") or ""
        if "<br>" in date_raw:
            stats["damaged_date"] += 1
            tail = re.sub(r"\s+", " ", date_raw.split("<br>", 1)[1].replace("<br>", " ")).strip().lower()
            if len(tail) >= 40: comment_of[base] = tail[:80]
        reason = left_out_reason(p, title, body, damaged)
        if reason:
            left_out.append(dict(basename=base, reason=reason)); continue
        d = p.get("date_parsed") or ""
        from_addr = False
        g = GOOD_DATE.match(d)
        if not g or not (1990 < int(g.group(1)) < 2027):
            d = f"{y}-{mo}-01T12:00:00"; from_addr = True; stats["date_from_address"] += 1
        elif (g.group(1), g.group(2)) != (y, mo):
            stats["date_differs_from_address"] = stats.get("date_differs_from_address", 0) + 1
        year = d[:4]
        cat = p.get("category") or ""
        if cat not in CATEGORY_SLUG:
            left_out.append(dict(basename=base, reason="category not one of the 14")); continue
        stats["breaks_restored"] += body.count("<br>")
        body = restore_breaks(body, p.get("convert_breaks"))
        body = drop_dead_images(body, stats)
        body = LINK.sub(relink, body)
        body = body.replace("{{", "&#123;&#123;").replace("{%", "&#123;%")
        fm = ["---", "title: " + yq(title or base), "date: " + d, "url: " + yq(f"/post/{base}/"),
              "aliases: [" + yq(f"/immigration/{y}/{mo}/{base}.html") + "]", "type: post", "year: " + yq(year),
              "category: " + yq(cat), "category_slug: " + yq(CATEGORY_SLUG[cat]), "byline: " + yq(byline)]
        if from_addr: fm.append("date_from_address: true")
        fm.append("---")
        files[base] = "\n".join(fm) + "\n" + body.strip() + "\n"
        years[year] += 1; cats[cat] += 1

    # Proof that nothing from a damaged field is in what is written. Every file's text is searched for every piece.
    # The text written comes only from the title, body, category and old address of a record, so a piece found here was
    # in the post's own text on TypePad (a reader who is named in the post, or an address the post itself printed).
    # A reader's email address that the post itself printed (a contact address in a call for papers, an address inside a
    # link) is taken out as well, so that no address from a damaged field is anywhere on the site.
    if "--keep-printed-emails" not in sys.argv:
        masked = collections.Counter()
        known = secrets["email"]
        def hide(inside_tag):
            def f(m):
                if m.group(0).lower() in known:
                    hide.n += 1
                    return "removed" if inside_tag else "[email address removed]"
                return m.group(0)
            return f
        for b, t in files.items():
            if not any(e.lower() in known for e in EMAIL.findall(t)): continue
            hide.n = 0
            head, _, rest = t.partition("\n---\n")
            out = [EMAIL.sub(hide(part.startswith("<")), part) for part in re.split(r"(<[^>]*>)", rest)]
            files[b] = EMAIL.sub(hide(False), head) + "\n---\n" + "".join(out)
            masked[b] = hide.n
        stats["printed_emails_removed"] = sum(masked.values()); stats["posts_with_printed_emails_removed"] = len([b for b in masked if masked[b]])
    low = {b: t.lower() for b, t in files.items()}
    found = {k: collections.Counter() for k in ("email", "IP number", "author field", "web address")}
    web_by_host = collections.defaultdict(list)
    for u in secrets["web address"]: web_by_host[re.sub(r"https?://", "", u).split("/")[0]].append(u)
    for b, t in low.items():
        if any(e in secrets["email"] for e in EMAIL.findall(t)): found["email"][b] += 1
        if any(i in secrets["IP number"] for i in IPV4.findall(t)): found["IP number"][b] += 1
        # every damaged author field has an "IP:" line, so only a text with that label can hold a whole field
        if "ip: " in t and any(x in t for x in secrets["author field"]): found["author field"][b] += 1
        for u in WEB.findall(t):
            if any(u.startswith(x) for x in web_by_host.get(re.sub(r"https?://", "", u).split("/")[0], ())):
                found["web address"][b] += 1; break
    # A reader's name is not searched for across the archive: several readers share names with the editors and with
    # people the blog wrote about. tools/check_leaks.py counts the posts whose own text names the reader who commented.
    comment_hits = [b for b, tail in comment_of.items() if b in low and tail in low[b]]
    stats["written"] = len(files); stats["left_out"] = len(left_out)
    stats["years"] = dict(sorted(years.items())); stats["categories"] = dict(sorted(cats.items()))
    stats["dead_images_by_host"] = dict(stats["dead_images_by_host"].most_common())
    stats["leak_check"] = {"pieces checked": {k: len(v) for k, v in secrets.items()},
                           "posts holding a piece": {k: len(v) for k, v in found.items()},
                           "posts holding the start of the reader's comment from their date field": len(comment_hits)}
    print(json.dumps(stats, indent=1, ensure_ascii=False))
    for kind, hits in found.items():
        if hits:
            print(f"{kind}: found in the post text of", len(hits), "posts, for example:", ", ".join(sorted(hits)[:5]))
    if comment_hits: print("the start of a reader's comment matches the post's own text (the reader quoted the post) in:", comment_hits)
    if found["email"] or found["IP number"] or found["author field"]:
        if "--keep-printed-emails" not in sys.argv or found["IP number"] or found["author field"]:
            print("STOPPED: see the lines above. Nothing was written."); sys.exit(1)
    if check:
        print("check only: nothing written"); return

    os.makedirs(out_posts, exist_ok=True)
    for f in glob.glob(os.path.join(out_posts, "*.html")): os.remove(f)
    for base, text in files.items():
        open(os.path.join(out_posts, base + ".html"), "w", encoding="utf-8").write(text)
    for f in glob.glob(os.path.join(site, "content", "year", "*", "_index.md")): os.remove(f)
    for yv in years:
        os.makedirs(os.path.join(site, "content", "year", yv), exist_ok=True)
        open(os.path.join(site, "content", "year", yv, "_index.md"), "w").write(f'---\ntitle: "{yv}"\nyear: "{yv}"\nlayout: year\n---\n')
    for f in glob.glob(os.path.join(site, "content", "category", "*", "_index.md")): os.remove(f)
    for c in cats:
        os.makedirs(os.path.join(site, "content", "category", CATEGORY_SLUG[c]), exist_ok=True)
        open(os.path.join(site, "content", "category", CATEGORY_SLUG[c], "_index.md"), "w").write(f"---\ntitle: {yq(c)}\ncategory: {yq(c)}\nlayout: category\n---\n")
    os.makedirs(os.path.join(site, "data"), exist_ok=True)
    json.dump(stats, open(os.path.join(site, "data", "import_stats.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(sorted(left_out, key=lambda r: r["basename"]), open(os.path.join(site, "data", "left_out.json"), "w"), indent=1, ensure_ascii=False)
    print("written:", len(files), "posts,", len(years), "years,", len(cats), "categories; left out:", len(left_out))


def left_out_reason(p, title, body, damaged):
    """A record is left out when it is not a post: see README.md, "Left out".
    In a damaged record the reader's comment went into the author and date fields; the title and text are still the
    post's own. A damaged record with no title or no text at all would have nothing of the post left, and is left out."""
    if damaged and (not title or not body.strip()):
        return "damaged record with no title or no text"
    return ""


if __name__ == "__main__":
    main()
