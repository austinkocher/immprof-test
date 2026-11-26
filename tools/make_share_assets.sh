#!/bin/bash
# Draw the fixed pieces of the share card: the blank card with the name and address at its foot, and one small
# label per section. Run it again only when the logo, the colors or the list of sections change.
set -euo pipefail
cd "$(dirname "$0")/.."
C="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
T="$(mktemp -d)"
shot(){ "$C" --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --virtual-time-budget=3000 --window-size=1200,630 --screenshot="$2" "$1" 2>/dev/null; }
mkdir -p assets/brand/kicker
shot "file://$PWD/tools/share-card-base.html" assets/brand/share-base.png
for s in "Books" "Commentary" "Conferences and Calls" "Creative Works" "Elections" "Enforcement" "Immigration Courts" "International" "Jobs" "Lawsuits" "Legislation" "News" "People" "Policy" "Research and Data" "Scholarship"; do
  slug="$(echo "$s" | tr 'A-Z ' 'a-z-')"
  enc="$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$s")"
  shot "file://$PWD/tools/share-card-kicker.html#$enc" "$T/$slug.png"
  sips -c 30 600 --cropOffset 8 8 "$T/$slug.png" --out "assets/brand/kicker/$slug.png" >/dev/null
done
echo "share card pieces drawn: assets/brand/share-base.png and $(ls assets/brand/kicker | wc -l | tr -d ' ') section labels"
