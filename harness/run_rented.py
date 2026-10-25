#!/usr/bin/env python3
"""
Run the whole CG4 GPU phase on one rented machine (Vast.ai, RunPod, Lambda, etc.) with 1..N GPUs, in the pre-registered order.

  python harness/run_rented.py --plan                                  # print the phases and stop (no GPU)
  python harness/run_rented.py --gpus 1 --max-hours 50                 # everything, stop starting new steps after 50 h
  python harness/run_rented.py --gpus 1 --chains EN-REPLACE BN-REPLACE --until 1    # the Gate 3 pilot
  python harness/run_rented.py --gpus 1 --max-priority 3               # confirmatory + robustness priorities 1..3 only
  python harness/run_rented.py --status

Phases (configs/chains.yaml): P0 base-model metrics + gen-0 per language -> P1 the six confirmatory chains to `generations` ->
then each robustness priority in order (its gen-0 variants first, then its chains) -> the REPLACE extension (priority
`replace_extension_priority`, default 4) -> remaining priorities. Jobs inside a phase are assigned round-robin to GPU queues;
phases run sequentially. Every job is `run_chain.py`, which resumes from cached stages, so re-running the same command after an
interruption is safe. The agent checks `vast_ops.py status` at least every 2 h; --max-hours is the wall-clock guard that stops
NEW steps once the approved cap is near (a step in progress still finishes).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAINS, LOGS, confirmatory_chains, load_chains_cfg, now_iso, read_json, robustness_chains, utf8_stdout, log_decision  # noqa: E402

utf8_stdout()
HERE = Path(__file__).resolve().parent


def done_gen0(gid: str) -> bool:
    return (CHAINS / gid / "step.json").exists()


def chain_done(cid: str, until: int) -> bool:
    st = read_json(CHAINS / cid / "state.json", {"completed": []})
    return bool(st["completed"]) and max(st["completed"]) >= until


def build_plan(cfg: dict, a) -> list[tuple[str, list[list[str]]]]:
    """List of (phase name, jobs); a job is the argument list for run_chain.py."""
    G = int(a.until or cfg["generations"])
    conf = confirmatory_chains(cfg); rob = robustness_chains(cfg)
    if a.chains:
        conf = [c for c in conf if c["id"] in a.chains]; rob = [c for c in rob if c["id"] in a.chains]
    phases: list[tuple[str, list[list[str]]]] = []
    if not a.skip_gen0:
        jobs = []
        for lang in cfg["languages"]:
            if not (CHAINS / f"BASE-{lang}" / "base" / "step.json").exists():
                jobs.append(["--base", lang])
            if not done_gen0(f"GEN0-{lang}"):
                jobs.append(["--gen0", f"GEN0-{lang}"])
        phases.append(("P0 base metrics + gen-0", jobs))
    phases.append(("P1 confirmatory chains", [["--chain", c["id"], "--until", str(G)] for c in conf if not chain_done(c["id"], G)]))
    if not a.skip_robustness:
        ext_prio = int(cfg.get("replace_extension_priority", 4)); ext_G = int(cfg.get("replace_extension_generations", 0) or 0)
        prios = sorted({c["priority"] for c in rob} | ({ext_prio} if ext_G > G else set()))
        for p in prios:
            if a.max_priority is not None and p > a.max_priority:
                break
            jobs = []
            group = [c for c in rob if c["priority"] == p]
            # gen-0 variants needed by this priority first (they are cheap and the chains depend on them)
            for c in group:
                gid = c.get("gen0")
                if gid and not done_gen0(gid) and ["--gen0", gid] not in jobs:
                    jobs.append(["--gen0", gid])
            if jobs:
                phases.append((f"P{p}a gen-0 variants", jobs)); jobs = []
            for c in group:
                until = int(c.get("until") or G)
                if not chain_done(c["id"], until):
                    jobs.append(["--chain", c["id"], "--until", str(until)])
            if p == ext_prio and ext_G > G:
                for c in conf:
                    if c["regime"] == "REPLACE" and not chain_done(c["id"], ext_G):
                        jobs.append(["--chain", c["id"], "--until", str(ext_G)])
            phases.append((f"P{p} robustness priority {p}", jobs))
    return [(name, jobs) for name, jobs in phases if jobs]


def run_queue(gpu: int, cmds: list[list[str]], session_id: str, deadline: float | None) -> int:
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
    rc = 0
    for cmd in cmds:
        if deadline and time.time() > deadline:
            print(f"[gpu{gpu}] {now_iso()} deadline reached; not starting {' '.join(cmd)}", flush=True); break
        full = [sys.executable, str(HERE / "run_chain.py")] + cmd + ["--session-id", session_id] + (["--deadline", str(deadline)] if deadline else [])
        print(f"[gpu{gpu}] {now_iso()} START {' '.join(cmd)}", flush=True)
        r = subprocess.run(full, env=env)
        print(f"[gpu{gpu}] {now_iso()} END rc={r.returncode} {' '.join(cmd)}", flush=True)
        rc = rc or r.returncode
        if r.returncode:
            break  # a failed stage must be looked at (12_VASTAI_RUNBOOK.md §8); the queue stops here
    return rc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpus", type=int, default=1); ap.add_argument("--chains", nargs="*"); ap.add_argument("--until", type=int)
    ap.add_argument("--skip-gen0", action="store_true"); ap.add_argument("--skip-robustness", action="store_true")
    ap.add_argument("--max-priority", type=int, default=None, help="run robustness priorities up to this number only")
    ap.add_argument("--max-hours", type=float, default=None, help="stop starting new steps after this many wall-clock hours")
    ap.add_argument("--status", action="store_true"); ap.add_argument("--plan", action="store_true")
    a = ap.parse_args(); cfg = load_chains_cfg()
    if a.status:
        subprocess.run([sys.executable, str(HERE / "run_chain.py"), "--status"]); return
    phases = build_plan(cfg, a)
    if a.plan:
        for name, jobs in phases:
            print(f"{name}:")
            for j in jobs:
                print("   run_chain.py " + " ".join(j))
        if not phases:
            print("nothing to do")
        return
    LOGS.mkdir(parents=True, exist_ok=True)
    session_id = f"rented-{int(time.time())}"
    deadline = time.time() + a.max_hours * 3600 if a.max_hours else None
    log_decision(f"rented run {session_id}: {a.gpus} GPU(s), phases {[n for n, _ in phases]}, max_hours {a.max_hours}")
    for name, jobs in phases:
        if deadline and time.time() > deadline:
            print(f"deadline reached before {name}; resume later with the same command"); break
        print(f"=== {name}: {len(jobs)} job(s)", flush=True)
        queues: dict[int, list[list[str]]] = {g: [] for g in range(a.gpus)}
        for i, j in enumerate(jobs):
            queues[i % a.gpus].append(j)
        results: dict[int, int] = {}
        threads = [threading.Thread(target=lambda g=g, q=q: results.__setitem__(g, run_queue(g, q, session_id, deadline))) for g, q in queues.items() if q]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if any(results.values()):
            print(f"phase {name} had a failed job; fix the cause (12_VASTAI_RUNBOOK.md §8) and re-run the same command", flush=True)
            sys.exit(1)
    subprocess.run([sys.executable, str(HERE / "run_chain.py"), "--status"])
    print("Done. Pack and pull results/ (11_TEARDOWN_CHECKLIST.md) before the instance is stopped.")


if __name__ == "__main__":
    main()
