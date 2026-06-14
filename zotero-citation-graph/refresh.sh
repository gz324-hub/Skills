#!/usr/bin/env bash
# refresh.sh — rebuild the citation graph from a Zotero export.
#
#   ./refresh.sh                                   # offline, cache-only, sample library
#   ./refresh.sh path/to/My Library.json           # your own CSL-JSON / BibTeX export
#   ONLINE=1 MAILTO=you@uni.edu ./refresh.sh in.json   # also fetch NEW citations from CrossRef
#
# Run it "every now and then": re-export from Zotero over the same file, then
# run this. With ONLINE=1 it tops up the citation cache; offline it rebuilds
# from whatever is already cached.
set -euo pipefail
cd "$(dirname "$0")"
INPUT="${1:-sample/library.json}"

ARGS=(--input "$INPUT" --out out --cache cache)
if [ "${ONLINE:-0}" = "1" ]; then
  ARGS+=(--online --mailto "${MAILTO:-anonymous@example.com}")
fi

python3 build_graph.py "${ARGS[@]}"
echo
echo "Done. Open the interactive graph in your browser:"
echo "    file://$(pwd)/index.html"
