#!/bin/bash
# Download every record from the archive's public data service, 100 at a time, with a pause between requests.
#   bash tools/fetch_archive.sh RAW_DIR
# RAW_DIR must be OUTSIDE every repository: the records include readers' email addresses (see README.md).
# It writes RAW_DIR/pages/page-NNN.json and stops at the first error. Pages already saved are skipped, so it can be resumed.
# Join the pages into one file afterwards with:  python3 -I tools/join_pages.py RAW_DIR
set -euo pipefail
RAW="${1:?give a folder outside the repository}"
case "$(cd "$RAW" && pwd -P)" in "$(cd "$(dirname "$0")/.." && pwd -P)"*) echo "RAW_DIR is inside the site folder. Choose a folder outside every repository."; exit 1;; esac
UA="Mozilla/5.0 (compatible; immprof-archive-import)"
API="https://archive.immprof.com/api/posts"
mkdir -p "$RAW/pages"
page=1; total=1
while [ "$page" -le "$total" ]; do
  f="$RAW/pages/page-$(printf %03d "$page").json"
  if [ ! -s "$f" ]; then
    code=$(curl -sS -A "$UA" --max-time 90 -o "$f.part" -w '%{http_code}' "$API?page=$page&limit=100") || { echo "STOPPED: request failed on page $page"; exit 1; }
    if [ "$code" != "200" ]; then echo "STOPPED: the service answered $code on page $page"; rm -f "$f.part"; exit 1; fi
    mv "$f.part" "$f"
    sleep 1.5
  fi
  total=$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["pagination"]["totalPages"])' "$f")
  page=$((page+1))
done
echo "done: $total pages in $RAW/pages"
