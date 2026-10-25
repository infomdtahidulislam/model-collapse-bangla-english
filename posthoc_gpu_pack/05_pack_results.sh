#!/usr/bin/env bash
# Re-pack the results by hand (RUN_ALL.sh already does this at its step 6).
set -euo pipefail
RES=cg4_posthoc_gpu_results
rm -rf "$RES"; mkdir -p "$RES"
cp out/* "$RES"/ 2>/dev/null || true
cp toc.txt extract_warnings.log "$RES"/ 2>/dev/null || true
tar -czf "$RES.tar.gz" "$RES"
sha256sum "$RES.tar.gz" | tee "$RES.sha256"
echo "packed: $RES.tar.gz"
