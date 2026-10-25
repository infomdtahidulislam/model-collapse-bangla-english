#!/usr/bin/env python3
"""
Plan Kaggle sessions for CG4 (04_RUN_PLAN.md): estimates quota hours from configs/chains.yaml and prints a
week-by-week plan for one account (30 quota hours/week, two T4s per session, two chains per session).

  python harness/kaggle/plan_sessions.py
  python harness/kaggle/plan_sessions.py --tokens 5000000 --generations 5     # scale-down scenario
Replace the ESTIMATES with measured numbers from logs/throughput.csv after the Gate 3 pilot and re-run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import load_chains_cfg, utf8_stdout  # noqa: E402

utf8_stdout()
ESTIMATES = {"gen_tokens_per_s": 5000.0, "train_tokens_per_s": 4800.0, "metrics_hours": 0.17}  # single T4, 270M model


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int); ap.add_argument("--generations", type=int); ap.add_argument("--weekly-quota", type=float, default=30.0)
    ap.add_argument("--slack", type=float, default=0.25); ap.add_argument("--session-hours", type=float, default=9.0)
    ap.add_argument("--speedup", type=float, default=1.0, help="GPU speed relative to a T4 (RTX 4090 ~3, A100 ~4.5); scales generation and training rates")
    a = ap.parse_args(); cfg = load_chains_cfg()
    T = a.tokens or cfg["tokens_per_generation"]; G = a.generations or cfg["generations"]
    gen_h = T / (ESTIMATES["gen_tokens_per_s"] * a.speedup) / 3600; train_h = T / (ESTIMATES["train_tokens_per_s"] * a.speedup) / 3600; m_h = ESTIMATES["metrics_hours"] / a.speedup
    per_chain = {}
    for reg in cfg["regimes"]:
        hours = 0.0
        for g in range(1, G + 1):
            mult = 1 if reg == "REPLACE" else (g + 1)      # accumulated set grows linearly
            hours += gen_h + train_h * mult + m_h
        per_chain[reg] = hours
    gen0 = train_h + m_h
    single_t4 = 2 * gen0 + sum(per_chain[r] for r in cfg["regimes"]) * len(cfg["languages"])
    quota = single_t4 / 2 * (1 + a.slack)                   # two chains per session, one per GPU
    print(f"Design: {len(cfg['languages'])} languages x {len(cfg['regimes'])} regimes, G={G}, {T:,} tokens/generation; GPU speedup vs T4 = {a.speedup}")
    print(f"Per generation step (single T4): generate {gen_h:.2f} h, train {train_h:.2f} h (x(g+1) for accumulation), metrics {m_h:.2f} h")
    for r, h in per_chain.items():
        print(f"  chain hours ({r}): {h:.1f} single-T4 h")
    print(f"Total single-T4 hours: {single_t4:.0f} -> quota hours with two chains per session and {int(a.slack * 100)}% slack: {quota:.0f}")
    print(f"Weeks at {a.weekly_quota:.0f} h/week: {quota / a.weekly_quota:.1f}")
    print("\nSession plan (pairs of chains, one per GPU):")
    pairs = [("EN-REPLACE", "BN-REPLACE"), ("EN-ACCUMULATE", "BN-ACCUMULATE"), ("EN-ACCUMULATE-FILTER", "BN-ACCUMULATE-FILTER")]
    week, used = 1, (2 * gen0 / 2 + 2 * (gen_h + train_h + m_h) / 2) * (1 + a.slack)
    print(f"  week 1: corpora/probes (CPU), gen-0 EN+BN, pilot step per language ({used:.1f} h)")
    for p in pairs:
        reg = p[0].split("-", 1)[1]; hours = per_chain[reg] * (1 + a.slack)
        n_sessions = max(1, round(hours / a.session_hours + 0.49))
        per = hours / n_sessions
        for s in range(n_sessions):
            if used + per > a.weekly_quota:
                week += 1; used = 0.0
            used += per
            print(f"  week {week}: session {p[0]} + {p[1]} part {s + 1}/{n_sessions} ({per:.1f} h)")
    print("\nAfter the pilot: replace ESTIMATES with measured values from logs/throughput.csv and re-run.")


if __name__ == "__main__":
    main()
