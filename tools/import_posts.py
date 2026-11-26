"""Turn posts read from the live Ghost site into Hugo content files, keeping every address.

Usage:  python3 tools/import_posts.py _import/ghost-posts-200.json [--no-images] [--out DIR]

For each post it writes content/posts/<slug>.html with the title, publish time (Eastern), slug, author, section, tags,
the outlet of the first outside link, and the body HTML. The address stays https://immprof.com/<slug>/ because the slug is kept.

Body changes are mechanical only: Ghost's ?ref=immprof.com link suffix is removed, pasted <h1> headings become <h2>,
script tags and image size hints are dropped, and images hosted on immprof.com are copied into assets/media.

Section: taken from the hand sorting of the 200 most recent posts when the post is in it (../analysis), else guessed by rule.
Tags: assigned by the word lists in ../analysis/classify_posts.py (a first set for the editors to correct).
"""
import csv, hashlib, html, json, os, re, shutil, subprocess, sys
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_cf_email import restore as restore_emails

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSIS = os.path.join(os.path.dirname(HERE), "analysis")
ET = ZoneInfo("America/New_York")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
AUTHOR_SLUG = {"Kevin R. Johnson": "kevin", "Kevin Johnson": "kevin", "Kit Johnson": "kit", "Ingrid Eagly": "ingrid", "Bill Ong Hing": "bill", "Ming Chen": "ming", "Austin Kocher": "austin"}
# Posts whose byline is a guest. The guest goes in "contributors" and the editor who published it stays in "authors"; the guest has no login.
GUESTS = {"remembering-dolores-huerta-a-life-in-photos-essay-and-photography-by-david-bacon": ("David Bacon", "People")}

# Outlet names for the homepage, keyed by the web address of a post's first outside link.
SOURCES = {
 "npr.org": "NPR", "apnews.com": "Associated Press", "cbsnews.com": "CBS News", "whitehouse.gov": "The White House",
 "justice.gov": "Department of Justice", "thenation.com": "The Nation", "rutgersuniversitypress.org": "Rutgers University Press",
 "propublica.org": "ProPublica", "scotusblog.com": "SCOTUSblog", "theguardian.com": "The Guardian", "nbcnews.com": "NBC News",
 "cnn.com": "CNN", "e-elgar.com": "Edward Elgar Publishing", "law360.com": "Law360", "urban.org": "Urban Institute",
 "usatoday.com": "USA Today", "thehill.com": "The Hill", "nytimes.com": "The New York Times", "ssrn.com": "SSRN", "pbs.org": "PBS News",
 "pewresearch.org": "Pew Research Center", "americanimmigrationcouncil.org": "American Immigration Council",
 "refugeesinternational.org": "Refugees International", "nomoredeaths.org": "No More Deaths", "nationalacademies.org": "National Academies",
 "politico.com": "Politico", "upi.com": "UPI", "yalelawjournal.org": "Yale Law Journal", "cambridge.org": "Cambridge University Press",
 "themarshallproject.org": "The Marshall Project", "newsweek.com": "Newsweek", "bbc.com": "BBC", "latimes.com": "Los Angeles Times",
 "reuters.com": "Reuters", "washingtonpost.com": "The Washington Post", "wsj.com": "The Wall Street Journal", "vera.org": "Vera Institute of Justice",
 "migrationpolicy.org": "Migration Policy Institute", "tracreports.org": "TRAC", "dhs.gov": "Department of Homeland Security",
 "state.gov": "Department of State", "supremecourt.gov": "Supreme Court of the United States", "aila.org": "AILA", "aclu.org": "ACLU",
 "courthousenews.com": "Courthouse News Service", "newyorker.com": "The New Yorker", "salon.com": "Salon", "prospect.org": "The American Prospect",
 "documentedny.com": "Documented", "firrp.org": "Florence Immigrant and Refugee Rights Project", "uapress.arizona.edu": "University of Arizona Press",
 "journals.sagepub.com": "Journal on Migration and Human Security", "house.gov": "U.S. House of Representatives", "theconversation.com": "The Conversation",
 "sfchronicle.com": "San Francisco Chronicle", "axios.com": "Axios", "abcnews.go.com": "ABC News", "foxnews.com": "Fox News", "cato.org": "Cato Institute",
 "msn.com": "MSN",
}
# Newsletter and tracking links hide the real outlet, so they are passed over and the next link is tried.
TRACKING = ("list-manage.com", "everyaction.com", "click.", "link.", "t.co", "apple.news", "bit.ly", "lnkd.in", "mailchi.mp", "zoom.us", "bwbx.io")


def source_for(body):
    for url in re.findall(r'<a[^>]+href="(https?://[^"]+)"', body):
        host = urlparse(url).netloc.lower().replace("www.", "")
        if "immprof.com" in host or any(t in host for t in TRACKING):
            continue
        for dom, name in SOURCES.items():
            if host == dom or host.endswith("." + dom):
                return name, url, True
        return host, url, False
    return None, None, False


def load_tagger():
    """Reuse the tag word lists and section rules from the analysis script without running its report."""
    src = open(os.path.join(ANALYSIS, "classify_posts.py")).read()
    ns = {"re": re}
    exec(src[src.index("TAGS = ["):src.index("def tags_for(r):")], ns)
    exec(src[src.index("RULES = ["):src.index("out = []")], ns)
    return ns["TAGS"], ns["section_for"]


def plain_video(m):
    """Ghost draws its own play buttons on a video with a script this site does not have. Use the browser's own player,
    with the file and its still picture served from this site (copied into static/content/media)."""
    card = m.group(0)
    src = re.search(r'<video[^>]*\ssrc="([^"]+)"', card)
    if not src:
        return card
    local = lambda u: u.replace("https://immprof.com/", "/")
    thumb = re.search(r'data-kg-thumbnail="([^"]+)"', card)
    size = re.search(r'<video[^>]*\swidth="(\d+)"[^>]*\sheight="(\d+)"', card)
    cap = re.search(r"(?s)<figcaption>.*?</figcaption>", card)
    return ('<figure class="kg-card kg-video-card"><video controls playsinline preload="metadata" src="%s"%s%s></video>%s</figure>'
            % (local(src.group(1)), ' poster="%s"' % local(thumb.group(1)) if thumb else "",
               ' width="%s" height="%s"' % size.groups() if size else "", cap.group(0) if cap else ""))


def yq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    no_images = "--no-images" in sys.argv
    out_dir = os.path.join(HERE, "content", "posts")
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
        args = [a for a in args if a != out_dir]
    media = os.path.join(HERE, "assets", "media")
    # A picture is named for its contents, so one used by many posts (a signature, a logo) is kept once.
    # _import/media-map.json remembers which file each address became, so a second run downloads nothing twice.
    map_path = os.path.join(HERE, "_import", "media-map.json")
    seen = json.load(open(map_path)) if os.path.exists(map_path) else {}
    os.makedirs(out_dir, exist_ok=True); os.makedirs(media, exist_ok=True)
    posts = json.load(open(args[0]))
    TAGS, section_for = load_tagger()
    from section_rules import section_for as rules16   # tools/section_rules.py, the sixteen sections
    FINAL = {}
    # Tags and guest authors from the reading pass of November 26, 2026 (../analysis/tags-all-2026-11-26.csv). A post in
    # that list takes its tags from it; a post marked there as a guest piece shows the guest as its author.
    # One name for a guest printed under two spellings, so each has one author page (Austin, November 26, 2026:
    # "Choose any spelling ... just don't want two author pages"). The spelling is to be confirmed later.
    SAME_GUEST = {"Cristian E. Urzola Arrieta": "Cristian Urzola", "Rev. Sadie Stone": "Sadie Stone",
                  "Garret Webb": "Garrett Webb", "Nate Austria": "Nathaniel Austria"}
    READ_TAGS, READ_GUESTS = {}, {}
    tags_path = os.path.join(ANALYSIS, "tags-all-2026-11-26.csv")
    if os.path.exists(tags_path):
        for r in csv.DictReader(open(tags_path)):
            READ_TAGS[r["file"]] = [t.strip() for t in r["tags"].split(";") if t.strip()]
            if r.get("guest", "").strip():
                READ_GUESTS[r["file"]] = SAME_GUEST.get(r["guest"].strip(), r["guest"].strip())
    final_path = os.path.join(ANALYSIS, "sections-all-2026-11-26.csv")
    if os.path.exists(final_path):
        FINAL = {r["file"]: r["section"] for r in csv.DictReader(open(final_path))}
    hand = {}
    path = os.path.join(ANALYSIS, "last-200-posts-classified.csv")
    if os.path.exists(path):
        for r in csv.DictReader(open(path)):
            hand[re.sub(r"\s+", " ", r["title"]).strip()] = (r["section_by_hand"], r["kind_by_hand"])

    def fetch(url):
        if url in seen and os.path.exists(os.path.join(media, seen[url])):
            return "media/" + seen[url]
        ext = os.path.splitext(url.split("?")[0])[1].lower() or ".img"
        if no_images:
            return "media/" + hashlib.sha1(url.encode()).hexdigest()[:12] + ext
        tmp = os.path.join(media, ".download")
        cached = os.path.join(HERE, "_import", "cache", hashlib.sha1(url.encode()).hexdigest())
        if os.path.exists(cached) and os.path.getsize(cached):   # copied earlier by tools/prefetch_images.sh
            shutil.copyfile(cached, tmp)
        else:
            subprocess.run(["curl", "-sL", "-A", UA, "-o", tmp, url], check=False)
        if not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
            return url
        name = hashlib.sha1(open(tmp, "rb").read()).hexdigest()[:12] + ext
        os.replace(tmp, os.path.join(media, name))
        seen[url] = name
        json.dump(seen, open(map_path, "w"), indent=0, sort_keys=True)
        return "media/" + name

    stats = dict(named=0, unnamed=0, nosource=0, by_hand=0, by_rule=0)
    skipped = [p["slug"] for p in posts if not (p.get("body") or "").strip()]
    posts = [p for p in posts if (p.get("body") or "").strip()]   # a published post with no text at all is left out
    for p in posts:
        title = re.sub(r"\s+", " ", p["title"]).strip()
        body = re.sub(r"[?&]ref=immprof\.com", "", p["body"])
        body = re.sub(r"<(/?)h1\b", r"<\1h2", body)
        body = re.sub(r'(?s)<figure class="kg-card kg-video-card.*?</figure>', plain_video, body)
        # Links to the blog's own posts and files become links within this site, so they work on any address.
        body = re.sub(r'href="https://immprof\.com/content/files/', 'href="/content/files/', body)
        body = re.sub(r'href="https://immprof\.com/(?!content/|ghost/)([^"]*)"', r'href="/\1"', body)
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        body = restore_emails(body)[0]   # addresses Cloudflare hid on the live page (tools/fix_cf_email.py)
        body = re.sub(r'\s(?:srcset|sizes|onerror)="[^"]*"', "", body)
        body = re.sub(r"<img(?![^>]*\balt=)", '<img alt=""', body)   # a picture with no description is marked as decoration
        if no_images:
            body_out = body
        else:
            body_out = re.sub(r'src="(https://immprof\.com/content/images/[^"]+)"', lambda m: 'src="{{< media "' + fetch(m.group(1)) + '" >}}"', body)
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body))).strip()
        row = dict(title=title, body=text, author=p["author"])
        if title in hand:
            section, kind = hand[title]; stats["by_hand"] += 1
        else:
            section, kind = section_for(row), ""; stats["by_rule"] += 1
        section = {"Reports and Data": "Research and Data"}.get(section, section)
        # The sixteen sections of November 26, 2026. Posts sorted by hand that day keep that section; anything else
        # sorted under an old name moves to the name that replaced it.
        section = FINAL.get(p["slug"] + ".html") or rules16(title, text)   # read and sorted by hand, else the first-sort rules
        key = p["slug"] + ".html"   # a post that was read keeps the reader's tags, even when that is none at all
        tags = READ_TAGS[key] if key in READ_TAGS else [t for t, pat in TAGS if re.search(pat, title + " " + text[:350], flags=re.I)][:4]
        name, url, known = source_for(body)
        stats["named" if known else ("unnamed" if name else "nosource")] += 1
        when = datetime.fromisoformat(p["date"].replace("Z", "+00:00")).astimezone(ET)
        # Author names as the site shows them. Kevin R. Johnson is "Kevin Johnson" here (Austin, November 26, 2026).
        author, guest = {"Kevin R. Johnson": "Kevin Johnson"}.get(p["author"], p["author"]), None
        if p["slug"] + ".html" in READ_GUESTS:
            guest = READ_GUESTS[p["slug"] + ".html"]
        if p["slug"] in GUESTS:
            guest, section = GUESTS[p["slug"]]
            section = FINAL.get(p["slug"] + ".html", section)   # the hand sort of November 26, 2026 wins
        fm = ["---", "title: " + yq(title), "date: " + when.isoformat(), "slug: " + yq(p["slug"]),
              "url: " + yq("/" + p["slug"] + "/"),   # the live address, written out so nothing can alter it
              "sections: [" + yq(section) + "]", "tags: [" + ", ".join(yq(t) for t in tags) + "]",
              "authors: [" + yq(author) + "]"]   # the editor who published it
        if guest:
            fm.append("contributors: [" + yq(guest) + "]")   # the guest author, shown as the byline
        img = p.get("image") or ""
        if "/content/images/" in img and not no_images:
            fm.append("image: " + yq(fetch(img)))
        if name and known:
            fm += ["sources:", "  - name: " + yq(name), "    url: " + yq(url)]
        fm.append("---")
        open(os.path.join(out_dir, p["slug"] + ".html"), "w").write("\n".join(fm) + "\n" + body_out + "\n")
    print("wrote", len(posts), "posts;", stats, "| left out, no text:", skipped)


if __name__ == "__main__":
    main()
