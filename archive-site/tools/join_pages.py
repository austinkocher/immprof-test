"""Join the downloaded pages into one file, RAW_DIR/archive.json, one record per _id.

Usage:  python3 -I tools/join_pages.py RAW_DIR
RAW_DIR is the folder given to fetch_archive.sh. It stays outside every repository.
"""
import glob, json, os, sys

def main():
    raw = sys.argv[1]
    seen = {}; total = None
    for f in sorted(glob.glob(os.path.join(raw, "pages", "page-*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        total = d["pagination"]["total"]
        for p in d["posts"]:
            seen[p["_id"]] = p
    json.dump(list(seen.values()), open(os.path.join(raw, "archive.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"records: {len(seen)}  the service says: {total}")
    if total is not None and len(seen) != total:
        print("WARNING: the counts differ. Download again before importing."); sys.exit(1)

if __name__ == "__main__":
    main()
