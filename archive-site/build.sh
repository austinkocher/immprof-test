#!/bin/bash
# Build the ImmigrationProf Blog Archive with its search index.
#   1. Hugo writes the pages into public/.
#   2. Pagefind reads those pages and writes the search index into static/pagefind/.
#   3. Hugo runs once more to copy the index into public/.
# Needs Hugo and Node (for npx). The first run downloads Pagefind.
#
# The test copy:  HUGO_PARAMS_TEST=1 HUGO_BASEURL=https://austinkocher.github.io/immprof-test/historical/ bash build.sh
# HUGO_PARAMS_TEST is on unless it is set to 0, so a build made without thinking is never listed by search engines.
set -euo pipefail
cd "$(dirname "$0")"
export HUGO_PARAMS_TEST="${HUGO_PARAMS_TEST-1}"
export HUGO_PARAMS_CSSV="$(date +%s)"
n=$(find content/post -name '*.html' | wc -l | tr -d ' ')
[ "$n" -gt 0 ] || { echo "No posts in content/post. Run tools/import_archive.py first (see README.md)."; exit 1; }
start=$(date +%s)
hugo --cleanDestinationDir --quiet || { echo "BUILD FAILED: Hugo stopped with an error. Run hugo with no options to read it."; exit 1; }
rm -rf static/pagefind
npx -y pagefind@1.3.0 --site public --output-path static/pagefind | grep -E "Indexed .* pages|Finished|rror" || true
[ -f static/pagefind/pagefind.js ] || { echo "BUILD FAILED: Pagefind wrote no index."; exit 1; }
hugo --cleanDestinationDir --quiet || { echo "BUILD FAILED: Hugo stopped with an error. Run hugo with no options to read it."; exit 1; }
echo "built in $(( $(date +%s) - start )) seconds: $(find public/post -mindepth 2 -name index.html | wc -l | tr -d ' ') post pages, $(find public -type f | wc -l | tr -d ' ') files, $(du -sh public | cut -f1) in all, search index $(du -sh public/pagefind | cut -f1)"
