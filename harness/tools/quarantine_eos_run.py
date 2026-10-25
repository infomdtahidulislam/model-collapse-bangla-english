"""Move the generation-0 and pilot results trained with the <eos>-target bug (fixed 2026-10-14, run_chain.pack) into a
quarantine folder, keeping the base-model results (no training involved). results/metrics.jsonl is rewritten without the
moved chains' rows; the full old file goes into the quarantine folder first. Nothing is deleted.

  python harness/tools/quarantine_eos_run.py <package_dir> <quarantine_dir>
"""
import json
import shutil
import sys
from pathlib import Path

pkg, q = Path(sys.argv[1]), Path(sys.argv[2])
res = pkg / "results"
chains = ["GEN0-EN", "GEN0-BN", "EN-REPLACE", "BN-REPLACE"]
samples = ["GEN0-EN_gen0_50.jsonl", "GEN0-BN_gen0_50.jsonl", "EN-REPLACE_gen1_50.jsonl", "BN-REPLACE_gen1_50.jsonl"]
if q.exists() and any(q.iterdir()):
    raise SystemExit(f"[FAIL] {q} is not empty; nothing moved")
(q / "chains").mkdir(parents=True, exist_ok=True)
(q / "samples").mkdir(parents=True, exist_ok=True)
moved = []
for c in chains:
    if (res / "chains" / c).exists():
        shutil.move(str(res / "chains" / c), str(q / "chains" / c)); moved.append(f"chains/{c}")
for s in samples:
    if (res / "samples" / s).exists():
        shutil.move(str(res / "samples" / s), str(q / "samples" / s)); moved.append(f"samples/{s}")
sheet = res / "human_read" / "G3_pilot_read_2026-10-14.html"
if sheet.exists():
    shutil.move(str(sheet), str(q / sheet.name)); moved.append(f"human_read/{sheet.name}")
m = res / "metrics.jsonl"
rows = [line for line in open(m, encoding="utf-8") if line.strip()]
shutil.copy2(m, q / "metrics.jsonl")
keep = [line for line in rows if json.loads(line)["chain_id"].startswith("BASE-")]
with open(m, "w", encoding="utf-8") as f:
    f.writelines(keep)
(q / "README.txt").write_text(
    "Generation-0 and pilot (REPLACE generation 1) results of 2026-10-14, trained before the <eos>-target bug was fixed in\n"
    "harness/run_chain.py pack(): <eos> was a training target after every document, also after continuations cut at the\n"
    "length cap and real documents cut at 1,024 tokens by the corpus builder. REPLACE generation 1 learned to end documents\n"
    "at the cap (English: 73% of its probability on <eos> beyond that length in real text). Discarded and re-run with the fix;\n"
    "kept for traceability only, never packed or analysed. The samples are unscreened synthetic text; do not share them.\n",
    encoding="utf-8")
print(json.dumps({"moved": moved, "metric_rows_before": len(rows), "metric_rows_kept_BASE": len(keep)}))
