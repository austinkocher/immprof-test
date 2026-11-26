#!/bin/bash
# Copy every picture the posts use from the live site into _import/cache, four at a time. Run before import_posts.py,
# which then takes each picture from the cache instead of asking the live site again. A picture already in the cache
# is skipped, so the script can be stopped and started again.
#   bash tools/prefetch_images.sh        (reads _import/image-urls.txt, one address per line)
set -u
cd "$(dirname "$0")/.."
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
one(){ u="$1"; h="$(printf '%s' "$u" | shasum | cut -c1-40)"; f="_import/cache/$h"
  [ -s "$f" ] && return 0
  curl -sL --max-time 90 --retry 2 -A "$UA" -o "$f.part" "$u" && [ -s "$f.part" ] && mv "$f.part" "$f" || { rm -f "$f.part"; echo "FAILED $u" >> _import/cache/failed.txt; }
}
export -f one; export UA
: > _import/cache/failed.txt
grep -v '^$' _import/image-urls.txt | xargs -P 4 -I{} bash -c 'one "$@"' _ {}
echo "cached: $(ls _import/cache | grep -vc 'failed.txt\|part$') of $(grep -vc '^$' _import/image-urls.txt); failed: $(grep -c FAILED _import/cache/failed.txt)"
