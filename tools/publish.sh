#!/bin/sh
# Rebuild the site and publish it:  sh tools/publish.sh "what changed"
# Publishes only the files the built site uses (tools/publish_list.py).
set -e
cd "$(dirname "$0")/.."
python3 build.py
git rm -r -q --cached . 2>/dev/null || true          # start from an empty index so removed files disappear
python3 tools/publish_list.py | tr '\n' '\0' | xargs -0 git add -f --
git commit -q -m "${1:-Update site}" || { echo "Nothing changed."; exit 0; }
git push -q origin main
echo "Published. Live in about a minute."
