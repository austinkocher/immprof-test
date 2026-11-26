#!/bin/bash
# Copy this site into its own repository for the public test copy, https://austinkocher.github.io/immprof-test/.
# The copy leaves out built files, the import folder and caches. The Library contact's email address is left out of
# the test copy, so the "contact" line there is plain text. GitHub builds and publishes the site when the copy is
# pushed (.github/workflows/pages.yml in that repository). This script only copies; committing and pushing are done
# with EditorialPipeline's tools/commit_script.py from inside the test repository.
set -euo pipefail
cd "$(dirname "$0")/.."
DEST="${1:-$HOME/Documents/immprof-test}"
mkdir -p "$DEST"
rsync -a --delete \
  --exclude .git --exclude .github --exclude .gitignore --exclude .nojekyll \
  --exclude public --exclude resources --exclude _import --exclude static/pagefind \
  --exclude .hugo_build.lock --exclude __pycache__ --exclude .DS_Store \
  --exclude tools/tests/t --exclude 'tools/tests/*.json' --exclude assets/media/.download \
  ./ "$DEST/"
python3 -I - "$DEST/data/library.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["contact"]["email"] = ""
json.dump(d, open(p, "w"), indent=1, ensure_ascii=False)
PY
echo "copied to $DEST: $(find "$DEST" -type f -not -path '*/.git/*' | wc -l | tr -d ' ') files, $(du -sh "$DEST" | cut -f1)"
