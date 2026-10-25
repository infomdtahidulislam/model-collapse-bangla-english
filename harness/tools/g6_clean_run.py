#!/usr/bin/env python
"""G6 reproducibility check (08_GATES_AND_CHECKLISTS.md, G6: "tables and figures regenerated from a clean run"; "Reproducible").

Copies harness/ and configs/ and the analysis inputs into a fresh folder results/g6_clean_run_<UTC stamp>/ (metrics.jsonl and
screening_metrics.jsonl taken from the G4b archive copies in results/g6_extract/; the G6 robustness files from results/), runs
`analyze.py --robustness --no-log` there, and compares every table (.csv) and analysis_report.md byte for byte with the main run in
results/analysis/. Figures are not compared byte for byte (SVG files embed a creation date); they are drawn from the same tables.
Writes results/analysis/reproducibility_check.md. Run it after the main `analyze.py --robustness`.

usage: python harness/tools/g6_clean_run.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, ROOT, log_decision, now_iso, utf8_stdout  # noqa: E402

utf8_stdout()
MAIN = RESULTS / "analysis"
EXT = RESULTS / "g6_extract"


def main() -> None:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    clean = RESULTS / f"g6_clean_run_{stamp}"
    clean.mkdir(parents=False, exist_ok=False)
    shutil.copytree(ROOT / "harness", clean / "harness", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "configs", clean / "configs")
    (clean / "results").mkdir()
    (clean / "logs").mkdir()
    inputs = {EXT / "results" / "metrics.jsonl": "metrics.jsonl", EXT / "results" / "screening_metrics.jsonl": "screening_metrics.jsonl",
              RESULTS / "tokenizer_metrics.jsonl": "tokenizer_metrics.jsonl", RESULTS / "semantic_dispersion.jsonl": "semantic_dispersion.jsonl",
              RESULTS / "novelty_duplicates.jsonl": "novelty_duplicates.jsonl"}
    for src, name in inputs.items():
        shutil.copy2(src, clean / "results" / name)
    r = subprocess.run([sys.executable, str(clean / "harness" / "analyze.py"), "--robustness", "--no-log", "--extract",
                        str(EXT / "results" / "chains")], cwd=clean, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-3000:])
        raise SystemExit("clean run failed")
    out = clean / "results" / "analysis"
    rows, same = [], 0
    files = sorted(p.name for p in MAIN.iterdir() if p.suffix in (".csv", ".md") and p.name != "reproducibility_check.md")
    for name in files:
        a, b = MAIN / name, out / name
        ok = b.exists() and a.read_bytes() == b.read_bytes()
        same += ok
        rows.append(f"| `{name}` | {'identical' if ok else ('MISSING in the clean run' if not b.exists() else 'DIFFERENT')} |")
    extra = sorted(p.name for p in out.iterdir() if p.suffix in (".csv", ".md") and p.name not in files)
    rep = ["# G6 reproducibility check (numbers only)", "",
           f"Made by `harness/tools/g6_clean_run.py` at {now_iso()}: a clean copy of `harness/` and `configs/` in "
           f"`results/{clean.name}/`, with `metrics.jsonl` and `screening_metrics.jsonl` taken from the G4b archive copies and the G6 "
           "robustness inputs from `results/`; `analyze.py --robustness --no-log` run there and compared with `results/analysis/`.", "",
           f"**{same} of {len(files)} tables and reports are byte-identical.**" + (f" Only in the clean run: {extra}." if extra else ""), "",
           "| File | Clean run vs main run |", "|---|---|"] + rows
    (MAIN / "reproducibility_check.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep[:6]))
    log_decision(f"G6 reproducibility check: analyze.py --robustness re-run in a clean copy (results/{clean.name}/, inputs from the G4b archive "
                 f"copies and the G6 robustness files): {same} of {len(files)} tables and reports byte-identical to results/analysis/ "
                 "(results/analysis/reproducibility_check.md).")


if __name__ == "__main__":
    main()
