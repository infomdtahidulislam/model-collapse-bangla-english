#!/usr/bin/env bash
# One-time setup on a rented Vast.ai host for CG4 (training + generation; no quantization libraries needed).
# Run from anywhere; it cds to the package root. Typical call from the control machine:
#   python harness/vast/vast_ops.py run --instance <id> --name bootstrap -- bash harness/vast/bootstrap.sh
# Secrets: /workspace/.env (pushed with `vast_ops.py push-env`) is exported; its values are never echoed.
# Structure mirrors ../../../shared/vast/bootstrap.sh; record the installed versions in logs/decisions.md after the pilot.
set -euo pipefail
cd "$(dirname "$0")/../.."
PKG_ROOT="$(pwd)"
mkdir -p logs
echo "[bootstrap] $(date -u +%FT%TZ) package root: $PKG_ROOT"

# 0. secrets (HF_TOKEN: the account must have accepted the Gemma licence for google/gemma-3-270m)
if [ -f /workspace/.env ]; then set -a; . /workspace/.env; set +a; echo "[bootstrap] /workspace/.env loaded (values not shown)"; fi

# 1. OS tools (image is Debian/Ubuntu based)
if command -v apt-get >/dev/null 2>&1; then
  (apt-get update -qq && apt-get install -y -qq --no-install-recommends tmux rsync git curl ca-certificates > /dev/null) || echo "[bootstrap] apt-get failed (non-fatal)"
fi
nvidia-smi || { echo "[bootstrap] nvidia-smi failed: wrong image or no GPU"; exit 1; }
python3 --version
df -h /workspace | tail -1

# 2. Python stack. vLLM pins its own torch; install it first so the torch version is consistent, then the rest.
# The generation-0 versions are pinned (harness/vast/pins_gen0.txt, 2026-10-13): a replacement host must run the chains on
# the same stack as generation 0.
PINS="harness/vast/pins_gen0.txt"
GEN0_TORCH_CUDA="13.0"      # generation 0 ran torch 2.13.0+cu130 (driver 580.95.05): rent hosts whose driver supports CUDA 13.0
CONS=""
if [ -f "$PINS" ]; then CONS="-c $PINS"; echo "[bootstrap] pinning library versions from $PINS"; fi
python3 -m pip install -q -U pip wheel
python3 -m pip install -q -r harness/requirements.txt $CONS
python3 -m pip install -q vllm $CONS --extra-index-url https://download.pytorch.org/whl/cu128          # synthetic generation; HF generate is the fallback
python3 -m pip install -q "transformers>=4.56" accelerate datasets huggingface_hub hf_transfer sentencepiece protobuf $CONS
# vLLM pins torch and torchaudio; through the cu128 extra index pip can choose a torchaudio built for another CUDA than torch,
# and `from transformers import Trainer` then fails on `import torchaudio` (2026-10-13: torch 2.13.0+cu130 with torchaudio
# 2.11.0+cu128). Reinstall the same torchaudio version built for torch's CUDA, then fail loudly if the Trainer still breaks.
if ! python3 -c "import torchaudio" >/dev/null 2>&1; then
  TA_VER=$(python3 -c "import importlib.metadata as m; print(m.version('torchaudio').split('+')[0])")
  TORCH_CU=$(python3 -c "import torch; print('cu' + torch.version.cuda.replace('.', ''))")
  echo "[bootstrap] torchaudio does not match torch (${TORCH_CU}): reinstalling torchaudio ${TA_VER} from the ${TORCH_CU} index"
  python3 -m pip install -q --no-deps --force-reinstall "torchaudio==${TA_VER}" --index-url "https://download.pytorch.org/whl/${TORCH_CU}"
fi
if [ -n "$CONS" ]; then
  python3 - "$PINS" "$GEN0_TORCH_CUDA" <<'PY'
import importlib.metadata as m
import sys
bad = []
try:
    import torch
    if torch.version.cuda != sys.argv[2]:
        bad.append(f"torch CUDA build wants {sys.argv[2]}, installed {torch.version.cuda}")
except ImportError:
    bad.append("torch not importable")
for line in open(sys.argv[1], encoding="utf-8"):
    spec = line.split("#")[0].strip()
    if "==" not in spec:
        continue
    name, want = (s.strip() for s in spec.split("==", 1))
    try:
        have = m.version(name)
    except m.PackageNotFoundError:
        have = None
    if have is None or have.split("+")[0] != want:
        bad.append(f"{name} wants {want}, installed {have}")
if bad:
    sys.exit("[bootstrap] PIN MISMATCH (log it; a changed stack goes to results/deviations.md): " + "; ".join(bad))
print("[bootstrap] pinned versions installed")
PY
fi
python3 -c "from transformers import Trainer, TrainingArguments; print('[bootstrap] transformers Trainer import ok')"
python3 -c "import torch, transformers; print('[bootstrap] torch', torch.__version__, 'cuda', torch.cuda.is_available(), 'transformers', transformers.__version__)"
python3 -c "import vllm; print('[bootstrap] vllm', vllm.__version__)" || echo "[bootstrap] vllm import failed: generation falls back to HF generate (slower); log it"

# 3. Hugging Face login (gated base model google/gemma-3-270m needs the accepted licence on the token's account)
if [ -n "${HF_TOKEN:-}" ]; then
  python3 - <<'PY'
import os
from huggingface_hub import login, whoami
login(token=os.environ["HF_TOKEN"], add_to_git_credential=False)
print("[bootstrap] HF login ok as", whoami().get("name"))
PY
else
  echo "[bootstrap] HF_TOKEN not set: google/gemma-3-270m will fail to download (file a LICENCE request)"
fi
export HF_HUB_ENABLE_HF_TRANSFER=1

# 4. Record the environment and run the offline sanity test
python3 - <<'PY'
import json, platform, subprocess, sys, datetime
env = {"captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform()}
for name, cmd in (("pip_freeze", [sys.executable, "-m", "pip", "freeze"]), ("nvidia_smi", ["nvidia-smi"]),
                  ("gpu", ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,power.limit", "--format=csv"])):
    try: env[name] = subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout
    except Exception as e: env[name] = f"unavailable: {e}"
json.dump(env, open("logs/environment.json", "w", encoding="utf-8"), indent=1)
print("[bootstrap] logs/environment.json written")
PY
python3 harness/tests/test_sanity.py && echo "[bootstrap] sanity test passed"
echo "[bootstrap] done $(date -u +%FT%TZ). Next (12_VASTAI_RUNBOOK.md section 3): python harness/fetch_sources.py --all"
