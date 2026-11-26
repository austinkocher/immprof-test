#!/usr/bin/env python3
"""List the tags in use and point out the ones the editors have not reviewed.

The editors' tag list is data/tags.json: each tag with its one-line description. The Tags field in the editor is open
text, so a new tag can appear at any time. Run this from time to time, and after importing old posts:

    python3 tools/check_tags.py

It prints every tag that is in a post and not on the list (with the posts that use it), tags that differ from a listed
tag only by capitals or spacing, posts with more than four tags or none, and listed tags that no post uses.
To accept a new tag, add it to data/tags.json with a description. To fold it into an existing tag, edit the posts.
"""
import glob, json, os, re, sys
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
listed = json.load(open(os.path.join(here, "data", "tags.json"), encoding="utf-8"))
norm = lambda t: re.sub(r"[^a-z0-9]+", "", t.lower())
by_norm = {norm(t): t for t in listed}
used, none, many = {}, [], []
for f in sorted(glob.glob(os.path.join(here, "content", "posts", "*"))):
    head = open(f, encoding="utf-8").read(3000)
    m = re.search(r"^tags: (\[.*\])", head, flags=re.M)
    tags = json.loads(m.group(1)) if m else []
    name = os.path.basename(f)
    if not tags: none.append(name)
    if len(tags) > 4: many.append(name)
    for t in tags: used.setdefault(t, []).append(name)
new = {t: p for t, p in used.items() if t not in listed}
print(f"{len(used)} tags in use, {len(listed)} on the editors' list.")
print(f"\nTags not on the list: {len(new)}")
for t, posts in sorted(new.items()):
    near = by_norm.get(norm(t))
    print(f"  {t}  ({len(posts)} posts)" + (f"  same as listed tag: {near}" if near else ""))
    for p in posts[:5]: print(f"      {p}")
print(f"\nListed tags no post uses: {', '.join(t for t in listed if t not in used) or 'none'}")
print(f"Posts with no tag: {len(none)}")
print(f"Posts with more than four tags: {len(many)}")
for p in many: print(f"  {p}")
sys.exit(1 if new else 0)
