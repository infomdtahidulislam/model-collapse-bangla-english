#!/usr/bin/env bash
# CG4 post-hoc GPU run: everything, end to end, ON THE GPU HOST.
# Usage: bash RUN_ALL.sh ["<google drive share link>"]
# (the link defaults to the one baked in below)
set -uo pipefail

LINK="${1:-https://drive.google.com/file/d/1oRr9UzrYKITDJx5u6LqLSEfrBi3LekCS/view?usp=sharing}"
echo RUNNING > STATUS

fail() { echo "FAILED at: $1" | tee -a STATUS; exit 1; }

echo "== [1/6] python dependencies =="
pip install -q -U gdown regex transformers accelerate sentence-transformers || fail "pip install"

echo "== [2/6] fetch + selective extract (55.7 GB download; 30-50 min) =="
bash 01_fetch.sh "$LINK" || fail "01_fetch.sh"

echo "== [3/6] cross-decoder evaluation (#17; ~45-60 min) =="
python3 02_cross_decoder.py || fail "02_cross_decoder.py"

echo "== [4/6] LaBSE sensitivity (#19; ~15 min) =="
python3 03_labse_sensitivity.py || fail "03_labse_sensitivity.py"

echo "== [5/6] nonword/bigram corpus analysis (#18 full; ~20-30 min) =="
python3 04_nonword_bigram.py || fail "04_nonword_bigram.py"

echo "== [6/6] packing results =="
RES=cg4_posthoc_gpu_results
rm -rf "$RES"; mkdir -p "$RES"
cp out/* "$RES"/ 2>/dev/null
cp toc.txt extract_warnings.log "$RES"/ 2>/dev/null
{
  echo "# CG4 post-hoc GPU results ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo "Diagnostics #17 (cross_decoder_*), #19 (labse_*), #18 full (nonword_*)."
  echo "Post-hoc, run after the internal audit; not pre-registered; no registered number changed."
  echo "Produced by posthoc_gpu_pack RUN_ALL.sh on a rented RTX 4090."
  python3 -c "import torch,transformers,sentence_transformers as st; print(f'torch {torch.__version__}, transformers {transformers.__version__}, sentence-transformers {st.__version__}, gpu: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"none\"}')"
} > "$RES"/INFO.md
tar -czf "$RES.tar.gz" "$RES"
sha256sum "$RES.tar.gz" | tee "$RES.sha256"
echo DONE > STATUS
echo "== ALL DONE: results in $RES/ and $RES.tar.gz =="
