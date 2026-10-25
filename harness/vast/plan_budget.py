#!/usr/bin/env python3
"""
GPU-hours and dollars for the CG4 GPU phase on a rented Vast.ai host (04_RUN_PLAN.md section 4b), by phase and priority.

  python harness/vast/plan_budget.py                                  # defaults: RTX 4090 (3x a T4), 1 GPU, US$0.40/h
  python harness/vast/plan_budget.py --gpus 2 --price-usd-h 0.35
  python harness/vast/plan_budget.py --tokens 5000000 --generations 5  # scale-down scenario (needs a deviations.md entry)
  python harness/vast/plan_budget.py --measured                        # replace the estimates with rates from results/chains/*/gen_*/step.json
Prints the hours of: P0 (base metrics + gen-0), P1 (six confirmatory chains), then every robustness priority with the
CUMULATIVE total, so the authors can draw the cap line; and the --budget-usd / --max-hours to request (cumulative x 1.25).
--measured also writes logs/throughput.csv. Estimates: generation and training rates in tokens/s (single-T4 figures x --speedup),
metrics 0.17 T4-hours per step, sample generation per step, FILTER scoring and top-up, REAL-REPEAT without generation.
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CHAINS, CORPORA, LOGS, confirmatory_chains, load_chains_cfg, read_json, robustness_chains, utf8_stdout  # noqa: E402

utf8_stdout()
ESTIMATES = {"gen_tokens_per_s": 5000.0, "train_tokens_per_s": 4800.0, "metrics_hours": 0.17, "engine_start_hours": 0.02,
             "filter_score_fraction": 0.35, "filter_topup_fraction": 0.3}   # single T4, 270M model (pre-pilot guesses)


def measured_rates() -> dict | None:
    gen, tr = [], []
    for sj in sorted(CHAINS.glob("*/gen_*/step.json")) + sorted(CHAINS.glob("GEN0-*/step.json")):
        st = read_json(sj) or {}
        g, t = st.get("generate") or {}, st.get("train") or {}
        if g.get("tokens") and g.get("generate_seconds"):
            gen.append(g["tokens"] / g["generate_seconds"])
        if t.get("train_tokens") and t.get("train_seconds"):
            tr.append(t["train_tokens"] / t["train_seconds"])
    if not gen and not tr:
        return None
    rates = {"gen_tokens_per_s": sum(gen) / len(gen) if gen else None, "train_tokens_per_s": sum(tr) / len(tr) if tr else None, "n_gen_steps": len(gen), "n_train_steps": len(tr)}
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "throughput.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["metric", "value", "n_steps", "note"])
        w.writerow(["gen_tokens_per_s", rates["gen_tokens_per_s"], len(gen), "measured on the current host"])
        w.writerow(["train_tokens_per_s", rates["train_tokens_per_s"], len(tr), "measured on the current host"])
    return rates


class Cost:
    def __init__(self, cfg: dict, T: int, G: int, gen_tps: float, train_tps: float, m_h: float, speedup: float):
        self.cfg, self.T, self.G = cfg, T, G
        self.gen_h = T / gen_tps / 3600; self.train_h = T / train_tps / 3600; self.m_h = m_h
        self.sample_h = cfg["metrics"]["n_sample_docs"] * (cfg["max_new_tokens"] + cfg["prefix_tokens"]) / gen_tps / 3600 + ESTIMATES["engine_start_hours"] / speedup
        self.engine_h = ESTIMATES["engine_start_hours"] / speedup

    def step(self, regime: str, g: int, tokens_scale: float = 1.0) -> float:
        gen = (self.gen_h + self.engine_h) * tokens_scale; train = self.train_h * tokens_scale; tail = self.sample_h + self.m_h
        if regime == "REPLACE":
            return gen + train + tail
        if regime == "REAL-REPEAT":
            return train + tail
        if regime == "ACCUMULATE":
            return gen + train * (g + 1) + tail
        if regime == "ACCUMULATE-SUBSAMPLE":
            return gen + train + tail
        if regime == "ACCUMULATE-FILTER":
            return gen * (1 + ESTIMATES["filter_topup_fraction"]) + train * ESTIMATES["filter_score_fraction"] + train * (g + 1) + tail
        raise SystemExit(f"unknown regime {regime}")

    def chain(self, regime: str, g_from: int, g_to: int, tokens_scale: float = 1.0) -> float:
        return sum(self.step(regime, g, tokens_scale) for g in range(g_from, g_to + 1))

    def gen0(self, tokens_scale: float = 1.0) -> float:
        return self.train_h * tokens_scale + self.sample_h + self.m_h

    def base(self) -> float:
        return self.sample_h + self.m_h


def tokens_scale_for(cfg: dict, chain: dict) -> float:
    t = chain.get("tokens")
    if t is None:
        return 1.0
    if isinstance(t, int):
        return t / cfg["tokens_per_generation"]
    man = read_json(CORPORA / "manifest.json")
    if man and str(t).startswith("match_words_of_"):
        other = str(t).rsplit("_", 1)[-1]; L = man["languages"]
        words_other = L[other].get("seed_words") or L[other]["seed_tokens"] * L[other]["words_per_token"]
        return (words_other / L[chain["language"]]["words_per_token"]) / cfg["tokens_per_generation"]
    return 0.45   # pre-Gate-1 guess for a word-matched English chain (Bangla fertility about 2.2x English)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", type=int); ap.add_argument("--generations", type=int)
    ap.add_argument("--speedup", type=float, default=3.0, help="GPU speed relative to a T4 (RTX 4090 about 3, RTX 3090 about 2, A100 about 4.5)")
    ap.add_argument("--gpus", type=int, default=1); ap.add_argument("--price-usd-h", type=float, default=0.40, help="price per GPU-hour")
    ap.add_argument("--slack", type=float, default=0.25); ap.add_argument("--measured", action="store_true")
    a = ap.parse_args(); cfg = load_chains_cfg()
    T = a.tokens or cfg["tokens_per_generation"]; G = a.generations or cfg["generations"]
    gen_tps, train_tps, m_h = ESTIMATES["gen_tokens_per_s"] * a.speedup, ESTIMATES["train_tokens_per_s"] * a.speedup, ESTIMATES["metrics_hours"] / a.speedup
    source = f"pre-pilot estimates x speedup {a.speedup}"
    if a.measured:
        r = measured_rates()
        if r:
            gen_tps = r["gen_tokens_per_s"] or gen_tps; train_tps = r["train_tokens_per_s"] or train_tps
            source = f"measured from {r['n_gen_steps']} generation and {r['n_train_steps']} training steps (logs/throughput.csv)"
        else:
            print("[note] no completed steps yet; using estimates")
    c = Cost(cfg, T, G, gen_tps, train_tps, m_h, a.speedup)
    n_lang = len(cfg["languages"])
    print(f"Design: {n_lang} languages x {len(cfg['regimes'])} regimes, G={G}, {T:,} generated tokens/generation; rates: {source}")
    print(f"Per step: generate {c.gen_h:.2f} h (+{c.engine_h:.2f} engine start), train {c.train_h:.2f} h (x(g+1) for accumulation), sample {c.sample_h:.2f} h, metrics {c.m_h:.2f} h")
    rows = []
    p0 = n_lang * (c.base() + c.gen0())
    rows.append(("P0 base metrics + gen-0 (2 languages)", p0))
    p1 = sum(c.chain(ch["regime"], 1, G) for ch in confirmatory_chains(cfg))
    rows.append(("P1 six confirmatory chains to G", p1))
    ext_prio = int(cfg.get("replace_extension_priority", 4)); ext_G = int(cfg.get("replace_extension_generations", 0) or 0)
    rob = robustness_chains(cfg)
    prios = sorted({ch["priority"] for ch in rob} | ({ext_prio} if ext_G > G else set()))
    for p in prios:
        group = [ch for ch in rob if ch["priority"] == p]; h = 0.0; parts = []
        seen_gen0 = set()
        for ch in group:
            scale = tokens_scale_for(cfg, ch)
            if ch.get("gen0") and ch["gen0"] not in seen_gen0:
                seen_gen0.add(ch["gen0"]); h += c.gen0(scale)
            h += c.chain(ch["regime"], 1, int(ch.get("until") or G), scale); parts.append(ch["id"])
        if p == ext_prio and ext_G > G:
            h += n_lang * c.chain("REPLACE", G + 1, ext_G); parts.append(f"REPLACE pair {G + 1}..{ext_G}")
        rows.append((f"P{p} " + ", ".join(parts), h))
    cum = 0.0
    print("\nphase                                                                      hours   cumulative  x1.25   cost(cum x1.25)")
    for name, h in rows:
        cum += h
        print(f"{name[:72]:72s} {h:7.1f} {cum:11.1f} {cum * (1 + a.slack):7.1f}   US${cum * (1 + a.slack) * a.price_usd_h:5.0f}")
    conf = rows[0][1] + rows[1][1]
    print(f"\nConfirmatory only (P0+P1): {conf:.1f} GPU-h -> cap --budget-usd {math.ceil(conf * (1 + a.slack) * a.price_usd_h * 1.25)} --max-hours {math.ceil(conf * (1 + a.slack) * 1.25)}")
    print(f"Everything (all priorities): {cum:.1f} GPU-h -> cap --budget-usd {math.ceil(cum * (1 + a.slack) * a.price_usd_h)} --max-hours {math.ceil(cum * (1 + a.slack))}")
    wall = cum * (1 + a.slack) / a.gpus
    print(f"Wall-clock with {a.gpus} GPU(s): about {wall:.0f} h = {wall / 24:.1f} days (chains are sequential; a second GPU only parallelises across chains)")
    # scale-down scenario
    c2 = Cost(cfg, 5_000_000, G, gen_tps, train_tps, m_h, a.speedup)
    conf2 = n_lang * (c2.base() + c2.gen0()) + sum(c2.chain(ch["regime"], 1, G) for ch in confirmatory_chains(cfg))
    print(f"Scale-down rule (5M tokens/generation): confirmatory {conf2:.1f} GPU-h; rule 2 (G=5) saves a further ~{(1 - sum(c.chain(ch['regime'], 1, 5) for ch in confirmatory_chains(cfg)) / p1) * 100:.0f}% of chain hours.")
    print("After the Gate 3 pilot: re-run with --measured; the authors' cap decides how many priorities run (pre-registered stopping rule).")


if __name__ == "__main__":
    main()
