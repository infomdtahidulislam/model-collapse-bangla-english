#!/usr/bin/env python3
"""
Kaggle session automation (04_RUN_PLAN.md section 7). Requires the `kaggle` CLI configured with kaggle.json.

  python harness/kaggle/push_and_poll.py --prepare --session 03 --cells configs/session_03_cells.json --datasets user/cg1-prompts user/cg1-build-qwen-awq
  python harness/kaggle/push_and_poll.py --push --session 03
  python harness/kaggle/push_and_poll.py --poll --session 03        # polls every 10 min until complete, then downloads outputs

Verify the current Kaggle CLI syntax before first use (`kaggle kernels push -h`); record the version in logs/decisions.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def run(cmd: list[str]) -> str:
    print("RUN:", " ".join(cmd))
    out = subprocess.run(cmd, capture_output=True, text=True)
    print(out.stdout.strip()); print(out.stderr.strip(), file=sys.stderr)
    return out.stdout


def prepare(session: str, cells: Path, datasets: list[str], username: str) -> Path:
    d = HERE / f"session_{session}"
    d.mkdir(exist_ok=True)
    meta = json.load(open(HERE / "kernel-metadata.template.json", encoding="utf-8"))
    meta["id"] = f"{username}/cg4-session-{session}"
    meta["title"] = f"cg4-session-{session}"
    meta["code_file"] = "session.py"
    meta["dataset_sources"] = datasets
    json.dump(meta, open(d / "kernel-metadata.json", "w", encoding="utf-8"), indent=1)
    shutil.copy(cells, d / "cells.json")
    tpl = (HERE / "session_template.py").read_text(encoding="utf-8")
    (d / "session.py").write_text(tpl.replace("__SESSION_ID__", f"kaggle-{session}"), encoding="utf-8")
    # ship the harness alongside (Kaggle kernels can read sibling files only if uploaded as a dataset; simplest: inline copy)
    bundle = d / "harness_bundle"
    if bundle.exists():
        shutil.rmtree(bundle)
    shutil.copytree(ROOT / "harness", bundle, ignore=shutil.ignore_patterns("kaggle", "__pycache__"))
    shutil.copytree(ROOT / "configs", bundle / "configs", dirs_exist_ok=True)
    shutil.copytree(ROOT / "prompts", bundle / "prompts", dirs_exist_ok=True)
    print(f"[ok] prepared {d}; upload {bundle} as a Kaggle dataset too (or include it in the prompts dataset) and reference it in datasets")
    return d


def push(session: str) -> None:
    run(["kaggle", "kernels", "push", "-p", str(HERE / f"session_{session}")])


def poll(session: str, username: str, every: int = 600) -> None:
    slug = f"{username}/cg4-session-{session}"
    while True:
        out = run(["kaggle", "kernels", "status", slug])
        if "complete" in out.lower():
            break
        if "error" in out.lower() or "cancel" in out.lower():
            print("session ended with error; inspect the log with: kaggle kernels output", slug); return
        time.sleep(every)
    dest = ROOT / "results" / "shards"
    dest.mkdir(parents=True, exist_ok=True)
    run(["kaggle", "kernels", "output", slug, "-p", str(dest)])
    print("[ok] outputs downloaded; now run: python harness/run_grid.py --merge && python harness/run_grid.py --status --all")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true"); ap.add_argument("--push", action="store_true"); ap.add_argument("--poll", action="store_true")
    ap.add_argument("--session", required=True); ap.add_argument("--cells", type=Path); ap.add_argument("--datasets", nargs="*", default=[])
    ap.add_argument("--username", default="YOUR_KAGGLE_USERNAME")
    a = ap.parse_args()
    if a.prepare:
        if not a.cells:
            ap.error("--prepare needs --cells")
        prepare(a.session, a.cells, a.datasets, a.username)
    if a.push:
        push(a.session)
    if a.poll:
        poll(a.session, a.username)


if __name__ == "__main__":
    main()
