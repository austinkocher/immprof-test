"""Turn a Ghost export into the plain list of posts that tools/import_posts.py reads.

Usage:  python3 tools/ghost_export_to_posts.py EXPORT.json
Writes _import/ghost-export-posts.json (every published post) and _import/ghost-export-pages.json (the pages).

A Ghost export also holds the editors' email addresses, password hashes and the site's settings. This script reads
none of that: from the users table it takes only each person's id, name and address slug. Keep the export itself out of
the project folder.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://immprof.com"


def main():
    data = json.load(open(sys.argv[1]))["db"][0]["data"]
    people = {u["id"]: (u["name"], u["slug"]) for u in data["users"]}
    first = {}
    for pa in sorted(data["posts_authors"], key=lambda r: r["sort_order"]):
        first.setdefault(pa["post_id"], pa["author_id"])
    tags = {t["id"]: t["name"] for t in data["tags"]}
    post_tags = {}
    for pt in sorted(data["posts_tags"], key=lambda r: r["sort_order"]):
        post_tags.setdefault(pt["post_id"], []).append(tags.get(pt["tag_id"], ""))
    fix = lambda s: (s or "").replace("__GHOST_URL__", SITE)
    posts, pages = [], []
    for p in data["posts"]:
        if p["status"] != "published" or p["visibility"] != "public":
            continue
        name, slug = people.get(first.get(p["id"]), ("", ""))
        row = dict(slug=p["slug"], url=f"{SITE}/{p['slug']}/", title=p["title"], date=p["published_at"], author=name,
                   author_slug=slug, image=fix(p.get("feature_image")), body=fix(p.get("html")),
                   excerpt=p.get("custom_excerpt") or "", ghost_tags=post_tags.get(p["id"], []))
        (pages if p["type"] == "page" else posts).append(row)
    posts.sort(key=lambda r: r["date"], reverse=True)
    out = os.path.join(HERE, "_import")
    json.dump(posts, open(os.path.join(out, "ghost-export-posts.json"), "w"), ensure_ascii=False)
    json.dump(pages, open(os.path.join(out, "ghost-export-pages.json"), "w"), ensure_ascii=False)
    print(len(posts), "posts,", len(pages), "pages; first", posts[-1]["date"][:10], "last", posts[0]["date"][:10])


if __name__ == "__main__":
    main()
