"""Post-hoc (posthoc_gpu_pack2; written 2026-10-23, run when the eight post-hoc chains are back): the two single-seed
controls with three seeds each, computed with the registered measurement bootstrap (harness/analyze.py: Boot, 1,000 draws,
one fixed draw set per metric x source checkpoint x generation, so a generation-0 point shared by two chains moves together).

Per language and seed k in {0, 2, 3} (seed 0 = the registered chains; seeds 2 and 3 = REPLACE-sK from the registration and
REAL-REPEAT-sK / REPLACE-topp95-sK from posthoc_gpu_pack2, all starting from GEN0-<lang>[-sK]):
  - REPLACE-sK minus REAL-REPEAT-sK slope (generations 0..6) on log held-out perplexity, bits per byte, log distinct-2 ratio,
    log recall ratio, with 95% measurement CI and two-sided bootstrap p (the registered "REPLACE net of REAL-REPEAT" control
    for k = 0, reproduced exactly as a check);
  - generation-6 rise over generation 0 (log held-out perplexity) and slopes over generations 0..3 and 3..6 of both arms;
  - REPLACE-topp95-sK over generations 1..6: raw distinct-2 slope, sample NLL under the generation-0 model (mean) slope,
    repeated-4-gram rate at generation 6, and the same quantities for REPLACE-sK; difference REPLACE-sK minus topp95-sK.
Descriptive and post-hoc; no registered quantity, test or verdict changes. Numbers only.

usage: python seeds_controls.py <package root> <posthoc metrics jsonl or "none"> <out dir>

Changed 2026-10-24 (PC), the only change to the copy in results/analysis/posthoc_seeds_2026-10-23/: the CSV files carry
10 decimals instead of 6, so that values rounded for the report are rounded once."""
import csv, sys
from pathlib import Path

import numpy as np

PKG, PM, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(PKG / "harness"))
import analyze as A                      # noqa: E402
from common import load_chains_cfg       # noqa: E402

cfg = load_chains_cfg(PKG / "posthoc_gpu_pack2_2026-10-23" / "configs" / "chains_posthoc_2026-10-23.yaml")
extra = [Path(PM)] if PM != "none" and Path(PM).exists() else []
df, base, meta, missing0 = A.load(cfg, PKG / "results" / "metrics.jsonl", extra)
df = A.add_normalised(df)
boot = A.Boot(df, cfg["seed"])
G06, G16, G03, G36 = range(0, 7), range(1, 7), range(0, 4), range(3, 7)
NET = ["log_ppl_heldout", "bpb_heldout", "distinct_2_logratio0", "tail_fact_recall_ALL_logratio0"]
rows = []


def add(kind, L, seed, metric, gens, est, draws, extra=None):
    lo, hi = A.ci(draws) if draws is not None else (float("nan"), float("nan"))
    r = {"kind": kind, "language": L, "seed": seed, "metric": metric, "generations": f"{gens.start}..{gens.stop - 1}",
         "estimate": est, "ci_lo": lo, "ci_hi": hi, "p_boot": A.p_two(draws) if draws is not None else float("nan")}
    r.update(extra or {}); rows.append(r)


def val(chain, metric, g):
    s = df[(df.chain_id == chain) & (df.metric == metric) & (df.generation == g)]["value"]
    return float(s.iloc[0]) if len(s) else float("nan")


for L in ("EN", "BN"):
    for seed, suf in (("0", ""), ("2", "-s2"), ("3", "-s3")):
        rep, rr, tp = f"{L}-REPLACE{suf}", f"{L}-REAL-REPEAT{suf}", f"{L}-REPLACE-topp95{suf}"
        for m in NET:
            fr, fq = boot.fit(rep, m, G06), boot.fit(rr, m, G06)
            if fr and fq:
                add("REPLACE minus REAL-REPEAT slope", L, seed, m, G06, fr.est - fq.est, fr.draws - fq.draws,
                    {"slope_REPLACE": fr.est, "slope_REAL_REPEAT": fq.est})
        for arm in (rep, rr):
            for gens in (G03, G36):
                f = boot.fit(arm, "log_ppl_heldout", gens)
                if f:
                    add(f"slope {arm.replace(L + '-', '').replace(suf, '') or 'REPLACE'}", L, seed, "log_ppl_heldout", gens, f.est, f.draws)
            e = boot.endpoint(arm, "log_ppl_heldout", 6)
            if e:
                add(f"rise to generation 6, {arm}", L, seed, "log_ppl_heldout", range(0, 7), e.est, e.draws)
        for m in ("distinct_2", "sample_nll_ref_mean"):
            ft, fr = boot.fit(tp, m, G16), boot.fit(rep, m, G16)
            if ft:
                add(f"slope {tp}", L, seed, m, G16, ft.est, ft.draws)
            if fr:
                add(f"slope {rep}", L, seed, m, G16, fr.est, fr.draws)
            if ft and fr:
                add("REPLACE minus REPLACE-topp95 slope", L, seed, m, G16, fr.est - ft.est, fr.draws - ft.draws)
        for arm in (rep, tp):
            v = val(arm, "repeat_4gram_rate", 6)
            if not np.isnan(v):
                add(f"repeat_4gram_rate at generation 6, {arm}", L, seed, "repeat_4gram_rate", range(6, 7), v, None)

OUT.mkdir(parents=True, exist_ok=True)
keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
with open(OUT / "seeds_controls.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
    for r in rows:
        w.writerow({k: (f"{v:.10f}" if isinstance(v, float) else v) for k, v in r.items()})
# seed summary of the net contrast
summ = []
for L in ("EN", "BN"):
    for m in NET:
        ests = [r["estimate"] for r in rows if r["kind"] == "REPLACE minus REAL-REPEAT slope" and r["language"] == L and r["metric"] == m]
        if ests:
            summ.append({"language": L, "metric": m, "n_seeds": len(ests), "mean": float(np.mean(ests)), "min": float(min(ests)),
                         "max": float(max(ests)), "sd": float(np.std(ests, ddof=1)) if len(ests) > 1 else float("nan")})
with open(OUT / "seeds_controls_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader()
    for r in summ:
        w.writerow({k: (f"{v:.10f}" if isinstance(v, float) else v) for k, v in r.items()})
for r in rows:
    if r["kind"] == "REPLACE minus REAL-REPEAT slope" and r["metric"] in ("log_ppl_heldout", "bpb_heldout"):
        print(f"{r['language']} seed {r['seed']} {r['metric']:16s} {r['estimate']:+.4f} [{r['ci_lo']:+.4f}, {r['ci_hi']:+.4f}] p {r['p_boot']:.3f}")
print(f"{len(rows)} rows; seeds summary: {[(s['language'], s['metric'][:8], s['n_seeds']) for s in summ]}")
