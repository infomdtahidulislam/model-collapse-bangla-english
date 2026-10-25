#!/usr/bin/env bash
# posthoc_gpu_pack2 (2026-10-23) on the rented GPU. Runs in /workspace/CG4 (the package root on the host) after
# vps_route/upload_inputs2.py has copied batch A (and later batch B) there.
#
#   bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh setup          # unpack + check batch A, patch, pinned stack, tests, plan
#   bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh chains HOURS   # the eight post-hoc chains, new steps stop after HOURS
#   bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh xdec           # unpack + check batch B, then 02b_cross_decoder.py
#   bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh pack           # results for the pull (small) and for the archive (big)
#
# Every phase appends to logs/posthoc2_host.log and writes its state to STATUS_posthoc2. A failed phase stops with
# "FAILED at: ..." and leaves everything in place for inspection (12_VASTAI_RUNBOOK.md section 8). Each phase can be re-run:
# run_chain.py resumes from its cached stages, and the checks are idempotent.
set -uo pipefail
cd /workspace/CG4 || { echo "no /workspace/CG4"; exit 1; }
mkdir -p logs
exec > >(tee -a logs/posthoc2_host.log) 2>&1
PACK=posthoc_gpu_pack2_2026-10-23
CHAINS="EN-REAL-REPEAT-s2 BN-REAL-REPEAT-s2 EN-REPLACE-topp95-s2 BN-REPLACE-topp95-s2 EN-REAL-REPEAT-s3 BN-REAL-REPEAT-s3 EN-REPLACE-topp95-s3 BN-REPLACE-topp95-s3"
export CG4_CHAINS_CFG=configs/chains_posthoc_2026-10-23.yaml
fail() { echo "FAILED at: $1" | tee -a STATUS_posthoc2; exit 1; }
stamp() { date -u +%FT%TZ; }

unpack() {
  local b=$1
  [ -f "inputs_${b}_small.tar.gz" ] && [ -f "inputs_${b}.sha256" ] || fail "batch ${b} inputs missing (upload_inputs2.py --batch ${b})"
  tar -xzf "inputs_${b}_small.tar.gz" || fail "unpack batch ${b}"
  for d in $(grep -o 'results/chains/[^ ]*/checkpoint/tokenizer.json' "inputs_${b}.sha256" | xargs -n1 dirname); do
    [ -f "$d/tokenizer.json" ] || cp shared/tokenizer.json "$d/tokenizer.json" || fail "copy tokenizer.json to $d"
  done
  sha256sum -c --quiet "inputs_${b}.sha256" || fail "SHA-256 check of batch ${b}"
  echo "batch ${b}: all $(wc -l < "inputs_${b}.sha256") files match (pack manifest for archive members, run hashes for package files)"
}

case "${1:-}" in
setup)
  echo "== setup $(stamp) =="; echo SETUP_RUNNING > STATUS_posthoc2
  unpack A
  cp "$PACK/configs/chains_posthoc_2026-10-23.yaml" configs/ || fail "copy post-hoc config"
  sha256sum configs/chains.yaml configs/chains_posthoc_2026-10-23.yaml
  python3 "$PACK/harness_patch/apply_patch.py" . || fail "harness patch"
  bash harness/vast/bootstrap.sh || fail "bootstrap (pinned stack of the run, harness/vast/pins_gen0.txt)"
  python3 harness/tests/test_sanity.py || fail "test_sanity.py"
  python3 harness/tests/smoke_gpu.py || fail "smoke_gpu.py (needs HF_TOKEN in /workspace/.env, as in the run)"
  pip freeze > logs/posthoc2_pip_freeze.txt 2>/dev/null; nvidia-smi > logs/posthoc2_nvidia_smi.txt 2>/dev/null
  python3 harness/run_rented.py --plan --skip-gen0 --chains $CHAINS | tee logs/posthoc2_plan.txt
  n=$(grep -c "run_chain.py --chain" logs/posthoc2_plan.txt)
  [ "$n" -eq 8 ] || fail "the plan has ${n} chain jobs; expected exactly 8 (check CG4_CHAINS_CFG and the staged gen-0 step.json files)"
  if grep -q -- "--gen0\|--base" logs/posthoc2_plan.txt; then fail "the plan would train a generation-0 model or base metrics"; fi
  echo SETUP_OK > STATUS_posthoc2; echo "== setup OK $(stamp) ==" ;;
chains)
  H=${2:?usage: host_run2.sh chains MAX_HOURS}
  echo "== chains $(stamp), new steps stop after ${H} h ==" ; echo CHAINS_RUNNING > STATUS_posthoc2
  python3 harness/run_rented.py --gpus 1 --skip-gen0 --chains $CHAINS --max-hours "$H" || fail "run_rented.py"
  python3 harness/run_chain.py --status | tee logs/posthoc2_status.txt
  for c in $CHAINS; do [ -f "results/chains/$c/gen_6/step.json" ] || echo "NOT COMPLETE: $c"; done | tee logs/posthoc2_incomplete.txt
  echo CHAINS_DONE > STATUS_posthoc2; echo "== chains done $(stamp) ==" ;;
xdec)
  echo "== cross-decoder $(stamp) =="; echo XDEC_RUNNING > STATUS_posthoc2
  unpack B
  for c in EN-REPLACE-topp95-s2 EN-REPLACE-topp95-s3 BN-REPLACE-topp95-s2 BN-REPLACE-topp95-s3; do
    [ -f "results/chains/$c/gen_6/step.json" ] || fail "$c is not complete; run the chains first"
  done
  python3 "$PACK/host/02b_cross_decoder.py" --root . --out results/posthoc2_cross_decoder --n 200 --check-n 50 || fail "02b_cross_decoder.py"
  echo XDEC_DONE > STATUS_posthoc2; echo "== cross-decoder done $(stamp) ==" ;;
pack)
  echo "== pack $(stamp) =="
  SMALL=posthoc2_results_small.tar.gz; BIG=posthoc2_checkpoints_corpora.tar
  # small: every record of the eight chains except weights and synthetic corpora; the metric records; the 50-document files;
  # the cross-decoder outputs; this run's logs and the patched common.py. (sample.jsonl and the 50-document files hold
  # unscreened model text: private storage only.)
  ITEMS=()
  for c in $CHAINS; do [ -d "results/chains/$c" ] && ITEMS+=("results/chains/$c"); done
  for f in results/metrics.jsonl results/posthoc2_cross_decoder logs/decisions.md STATUS_posthoc2 configs/chains_posthoc_2026-10-23.yaml harness/common.py; do
    [ -e "$f" ] && ITEMS+=("$f")
  done
  for f in logs/posthoc2_* results/samples/*-s[23]_gen*_50.jsonl; do
    [ -e "$f" ] && case "$f" in *REAL-REPEAT*|*topp95*|logs/*) ITEMS+=("$f");; esac
  done
  tar -czf "$SMALL" --exclude='*/checkpoint' --exclude='*/synthetic*.jsonl' --exclude='*/trainer' "${ITEMS[@]}" || fail "pack small"
  # big: weights and synthetic training corpora of the eight chains, for the archive (beside the G4b pack)
  BIGITEMS=()
  for c in $CHAINS; do
    for p in results/chains/$c/gen_*/checkpoint results/chains/$c/gen_*/synthetic*.jsonl; do [ -e "$p" ] && BIGITEMS+=("$p"); done
  done
  tar -cf "$BIG" "${BIGITEMS[@]}" || fail "pack big"
  sha256sum "$SMALL" "$BIG" > posthoc2_packs.sha256
  { for c in $CHAINS; do [ -d "results/chains/$c" ] && find "results/chains/$c" -type f; done
    [ -e results/metrics.jsonl ] && echo results/metrics.jsonl
    [ -d results/posthoc2_cross_decoder ] && find results/posthoc2_cross_decoder -type f; } | sort | xargs -d '\n' sha256sum > posthoc2_files.sha256
  cat posthoc2_packs.sha256; echo "$(wc -l < posthoc2_files.sha256) files listed in posthoc2_files.sha256"
  echo PACKED > STATUS_posthoc2; echo "== pack done $(stamp) ==" ;;
*)
  echo "usage: bash $PACK/host/host_run2.sh setup|chains HOURS|xdec|pack"; exit 2 ;;
esac
