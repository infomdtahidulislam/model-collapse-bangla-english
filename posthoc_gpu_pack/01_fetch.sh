#!/usr/bin/env bash
# CG4 post-hoc GPU pack, step 1: download the archive from Google Drive and
# extract only the members the diagnostics need.
# Usage: bash 01_fetch.sh "<google drive share link>"
set -euo pipefail

LINK="${1:?Usage: bash 01_fetch.sh \"<google drive share link for cg4_pack_20261016-232223.tar.gz>\"}"
ARCHIVE="cg4_pack.tar.gz"

if [ ! -s "$ARCHIVE" ]; then
  echo "== downloading archive (55.7 GB) =="
  python3 -m gdown --fuzzy "$LINK" -O "$ARCHIVE"
else
  echo "== archive already present, skipping download =="
fi
ls -lh "$ARCHIVE"

echo "== writing table of contents (one pass through the stream) =="
if [ ! -s toc.txt ]; then
  tar -tzf "$ARCHIVE" > toc.txt
fi
wc -l toc.txt

echo "== extracting needed members (second pass) =="
mkdir -p extracted
tar -xzf "$ARCHIVE" -C extracted --wildcards \
  '*GEN0-EN*' '*GEN0-BN*' \
  '*EN-REPLACE*' '*BN-REPLACE*' \
  '*_seed.jsonl' '*seed*.jsonl' \
  '*harness*' '*sample*.jsonl' '*manifest*' \
  2> extract_warnings.log || true
echo "(warnings, if any, are in extract_warnings.log)"

echo "== summary =="
CKPTS=$(find extracted -name config.json | wc -l)
SAMPLES=$(find extracted -name '*sample*.jsonl' | wc -l)
SEEDS=$(find extracted -name '*seed*.jsonl' | wc -l)
echo "checkpoint dirs (config.json found): $CKPTS"
echo "sample jsonl files:                  $SAMPLES"
echo "seed corpus files:                   $SEEDS"
du -sh extracted
if [ "$CKPTS" -eq 0 ]; then
  echo "ERROR: no checkpoints extracted. Send toc.txt back for corrected patterns." >&2
  exit 1
fi
echo "OK: proceed with 02_cross_decoder.py"
