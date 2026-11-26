"""Turn the 2005 to 2025 archive (the TypePad export served by archive.immprof.com) into Hugo content files. A test of the migration.

Usage:  python3 tools/import_archive.py ARCHIVE.json OUT_DIR
ARCHIVE.json is every record from https://archive.immprof.com/api/posts (title, body, category, basename, unique_url, date).

Each post is written at /post/<basename>/, the address it has on archive.immprof.com today, and its old TypePad address
(/immigration/YYYY/MM/<basename>.html) is kept as an alias. TypePad categories are mapped to the new sections.
A record whose date field is damaged takes the year and month from its old address.
"""
import html, json, os, re, sys

SECTION = {"Current Affairs": "News", "Law Review Articles & Essays": "Scholarship", "Books": "Books", "Conferences and Call for Papers": "Conferences and Calls",
           "Data and Research": "Research and Data", "Jobs and Fellowships": "Jobs", "Immigration Law Clinics": "Jobs",
           "Film & Television": "Creative Works", "Music": "Creative Works", "Sports": "Creative Works", "Photos": "Creative Works", "Food and Drinks": "Creative Works", "Religion": "Creative Works",
           "Teaching Resources": "Scholarship"}

def yq(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def main():
    posts = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    stats = dict(written=0, date_from_address=0, old_links=0)
    for p in posts:
        m = re.search(r"/immigration/(\d{4})/(\d\d)/([^/]+)\.html", p.get("unique_url") or "")
        if not m:
            continue
        y, mo, base = m.groups()
        d = p.get("date_parsed") or ""
        if not re.match(r"\d{4}-\d\d-\d\dT", d):
            d = f"{y}-{mo}-01T12:00:00"; stats["date_from_address"] += 1
        body = (p.get("body") or "") + (p.get("extended_body") or "")
        # links between old posts: point them at the new addresses
        body, n = re.subn(r'href="https?://lawprofessors\.typepad\.com/immigration/\d{4}/\d\d/([^"/]+)\.html[^"]*"', r'href="/post/\1/"', body)
        stats["old_links"] += n
        body = body.replace("{{", "&#123;&#123;").replace("{%", "&#123;%")
        title = html.unescape(re.sub(r"\s+", " ", p.get("title") or "")).strip() or base
        fm = ["---", "title: " + yq(title), "date: " + d + "-05:00", "slug: " + yq(base), "url: " + yq(f"/post/{base}/"),
              "aliases: [" + yq(f"/immigration/{y}/{mo}/{base}.html") + "]", "sections: [" + yq(SECTION.get(p.get("category"), "News")) + "]",
              "typepad_category: " + yq(p.get("category") or ""), "archive: true", "---"]
        open(os.path.join(out, base[:180] + ".html"), "w").write("\n".join(fm) + "\n" + body + "\n")
        stats["written"] += 1
    print(stats)

if __name__ == "__main__":
    main()
