#!/bin/bash
# Build the ImmigrationProf Blog site with its search index.
#   0. The practice editor's settings are written from the real ones.
#   1. Hugo writes the pages into public/.
#   2. Pagefind reads those pages and writes the search index into static/pagefind/,
#      so that both "hugo server" and the final build carry it.
#   3. Hugo runs once more to copy the index into public/.
# Needs Hugo and Node (for npx). The first run downloads Pagefind.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I tools/make_practice_editor.py
hugo --cleanDestinationDir --quiet || { echo "BUILD FAILED: Hugo stopped with an error. Run hugo with no options to read it."; exit 1; }
npx -y pagefind@1.3.0 --site public --output-path static/pagefind | grep -E "Indexed .* pages|Finished"
hugo --cleanDestinationDir --quiet || { echo "BUILD FAILED: Hugo stopped with an error. Run hugo with no options to read it."; exit 1; }
echo "built: $(find public -name index.html | wc -l | tr -d ' ') pages, search index $(du -sh public/pagefind | cut -f1)"
