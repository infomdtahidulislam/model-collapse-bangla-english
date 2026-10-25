"""Write results/chains/manifest.json on the host: base model id, revision, licence, file hashes, library versions (G2 sign-off item)."""
import datetime
import glob
import hashlib
import json
import sys
from pathlib import Path

pkg = Path(sys.argv[1])
snaps = glob.glob("/root/.cache/huggingface/hub/models--google--gemma-3-270m/snapshots/*")
snap = Path(snaps[0])
ref = Path("/root/.cache/huggingface/hub/models--google--gemma-3-270m/refs/main").read_text().strip()
files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(snap.iterdir()) if p.is_file()}
vers = {}
for mod in ("torch", "transformers", "vllm", "tokenizers", "accelerate", "datasets", "huggingface_hub", "numpy"):
    try:
        vers[mod] = __import__(mod).__version__
    except Exception as e:  # noqa
        vers[mod] = f"unavailable: {type(e).__name__}"
man = {"recorded_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
       "base_model": {"hf_id": "google/gemma-3-270m", "revision": ref, "snapshot_dirs": [Path(s).name for s in snaps],
                      "licence": "Gemma Terms of Use (gated model; terms accepted on the Hugging Face account infomdtahidulislam, 2026-10-12)",
                      "files_sha256": files},
       "tokenizer_sha256": files.get("tokenizer.json"),
       "library_versions": vers,
       "notes": "every training document and generation prompt starts with <bos> (fix of 2026-10-13); micro-batch 4 via configs/runtime.yaml"}
out = pkg / "results" / "chains" / "manifest.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(man, indent=1), encoding="utf-8")
print(json.dumps({k: man[k] for k in ("base_model", "tokenizer_sha256", "library_versions")}, indent=1)[:1500])
