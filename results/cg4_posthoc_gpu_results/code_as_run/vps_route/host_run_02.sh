#!/usr/bin/env bash
# CG4 post-hoc #17 on the rented GPU (VPS route, 2026-10-20). Runs in /workspace/posthoc_gpu_pack after upload_inputs.py has
# copied 02_cross_decoder.py, inputs.sha256, inputs_small.tar.gz and the 26 model.safetensors files there.
# Steps: unpack the small inputs; put the shared tokenizer.json (identical in all 117 checkpoints, one SHA-256 in the pack
# manifest) into every checkpoint folder; check every input file against the pack manifest (inputs.sha256); install the run's
# library versions (harness/vast/pins_gen0.txt; torch stays the image's); run 02_cross_decoder.py; pack out/.
set -uo pipefail
cd "$(dirname "$0")"
exec > >(tee -a run.log) 2>&1          # a copy of this output stays beside the results (the job log is vast_ops' logs/<name>.log)
echo RUNNING > STATUS
fail() { echo "FAILED at: $1" | tee -a STATUS; exit 1; }

echo "== [1/5] unpack the small inputs $(date -u +%FT%TZ) =="
tar -xzf inputs_small.tar.gz || fail "unpack inputs_small.tar.gz"
for d in $(grep -o 'extracted/[^ ]*/checkpoint/tokenizer.json' inputs.sha256 | xargs -n1 dirname); do
  [ -f "$d/tokenizer.json" ] || cp shared/tokenizer.json "$d/tokenizer.json" || fail "copy tokenizer.json to $d"
done

echo "== [2/5] check every input against the pack manifest $(date -u +%FT%TZ) =="
sha256sum -c --quiet inputs.sha256 || fail "input SHA-256 check"
echo "all $(wc -l < inputs.sha256) input files match the pack manifest"

echo "== [3/5] libraries: the run's transformers stack, the image's torch $(date -u +%FT%TZ) =="
pip install -q transformers==5.17.0 tokenizers==0.23.3 safetensors==0.8.0 huggingface_hub==1.33.0 regex==2026.9.29 || fail "pip install"
python3 -c "import torch, transformers; print('torch', torch.__version__, '| cuda', torch.version.cuda, '| gpu', torch.cuda.get_device_name(0), '| transformers', transformers.__version__)" || fail "import check"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

echo "== [4/5] 02_cross_decoder.py $(date -u +%FT%TZ) =="
python3 02_cross_decoder.py || fail "02_cross_decoder.py"

echo "== [5/5] pack $(date -u +%FT%TZ) =="
pip freeze > out/host_pip_freeze.txt 2>/dev/null
nvidia-smi > out/host_nvidia_smi.txt 2>/dev/null
tar -czf out_host.tar.gz out run.log || fail "pack"
sha256sum out_host.tar.gz out/* > out_host.sha256
echo DONE > STATUS
echo "== ALL DONE $(date -u +%FT%TZ) =="
