#!/usr/bin/env python3
"""Post-hoc (posthoc_gpu_pack2; written 2026-10-24 on the PC): the remaining seed comparisons for the analysis, numbers only.

Same machinery as seeds_controls.py (harness/analyze.py: load, add_normalised, Boot with the registered seed, 1,000 draws;
the post-hoc config adds the eight chains; nothing registered is written). Six outputs in <out>:
  full_sample_vs_window.csv   all 25 chains: the distinct-2 window slope (log ratio over generations 0..6; raw slope over
                              1..6 for the top-p 0.95 chains) with its 95% measurement CI, against the equal-length check on
                              the 50-document files (Table S12, 17 chains) and on the full 2,000-document samples. For the 17
                              registered chains the window slopes are checked against results/analysis/T2_slopes.csv.
  seeds_arms.csv              per language, seed and arm (REPLACE, REAL-REPEAT, REPLACE-topp95): held-out log-perplexity and
                              bits-per-byte slopes over 0..6, quadratic coefficient, rise to generation 6, lowest point
                              relative to generation 0; topp95 minus REPLACE slope differences.
  seeds_decoder_extras.csv    per language and seed: sample NLL slope over 0..6 (the registered window) and SD slope over
                              1..6, distinct-2 at generations 1 and 6, highest repeated-4-gram rate of the REPLACE chain.
  perdoc_seeds_extra.csv      per-document held-out slopes: mean slope on the web and Wikipedia halves per arm and seed, and
                              correlations between seeds of the same arm (document bootstrap, 2,000 draws, default_rng(20261024)).
  cross_decoder2_first50.csv  seed-0 cross-decoder slopes over generations 1..6 on the first 50 prefixes (the 2026-10-20
                              prefixes, new draws) and on all 200, beside the 2026-10-20 values (Table 5).
  cross_decoder2_levels.csv   mean NLL of each chain's cells at generations 1 and 6 and of its generation-0 model, per
                              evaluation decoder (the columns of Table 5, three seeds).
usage: python -B seeds_extra.py <package root> <out dir>
"""
import json, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PKG, OUT = Path(sys.argv[1]), Path(sys.argv[2])
R = PKG / "results"
T = R / "posthoc_seeds_2026-10-23"
sys.path.insert(0, str(PKG / "harness"))
import analyze as A  # noqa: E402
from common import load_chains_cfg  # noqa: E402

cfg = load_chains_cfg(PKG / "posthoc_gpu_pack2_2026-10-23" / "configs" / "chains_posthoc_2026-10-23.yaml")
df, base, meta, missing0 = A.load(cfg, R / "metrics.jsonl", [T / "host" / "results" / "metrics_posthoc_2026-10-23.jsonl"])
df = A.add_normalised(df)
boot = A.Boot(df, cfg["seed"])
G06, G16 = range(0, 7), range(1, 7)
SEEDS = (("0", ""), ("2", "-s2"), ("3", "-s3"))
NEW = {c for c, m in meta.items() if m.get("posthoc")}
OUT.mkdir(parents=True, exist_ok=True)


def fitrow(chain, metric, gens, deg=1):
    f = boot.fit(chain, metric, gens, deg)
    lo, hi = f.ci()
    return f, lo, hi


def val(chain, metric, g):
    s = df[(df.chain_id == chain) & (df.metric == metric) & (df.generation == g)]["value"]
    return float(s.iloc[0]) if len(s) else float("nan")


# ---------------------------------------------------------------- 1. window vs equal-length checks
fs = pd.read_csv(T / "full_sample_check" / "full_sample_equal_length_K100_n2000_m1600_B500_seed20261024.csv")
s12 = pd.read_csv(R / "analysis" / "posthoc_review_2026-10-22" / "prefix_paired_diversity_equal_K100.csv").set_index("chain")
t2 = pd.read_csv(R / "analysis" / "T2_slopes.csv")
rows, t2_diff = [], []
for r in fs.itertuples():
    c, topp = r.chain, "topp95" in r.chain
    metric, gens = ("distinct_2", G16) if topp else ("distinct_2_logratio0", G06)
    f, lo, hi = fitrow(c, metric, gens)
    if c not in NEW and not topp:
        t = t2[(t2.chain_id == c) & (t2.metric == metric) & (t2.generations == "0..6")].iloc[0]
        t2_diff.append(max(abs(t.slope - f.est), abs(t.lo - lo), abs(t.hi - hi)))
    s = s12.loc[c] if c in s12.index else None
    rows.append(dict(chain=c, language=c[:2], posthoc_chain=c in NEW, statistic=r.quantity, window_slope=f.est, window_ci_lo=lo,
                     window_ci_hi=hi, window_ci_excludes_0=bool(lo > 0 or hi < 0),
                     S12_point=(s.point if s is not None else np.nan), S12_range_lo=(s.range_lo if s is not None else np.nan),
                     S12_range_hi=(s.range_hi if s is not None else np.nan),
                     full_point=r.point, full_range_lo=r.range_lo, full_range_hi=r.range_hi, full_words_per_step=r.words_per_step,
                     sign_full_equals_window=bool(np.sign(r.point) == np.sign(f.est)),
                     sign_S12_equals_window=(bool(np.sign(s.point) == np.sign(f.est)) if s is not None else None),
                     full_inside_window_ci=bool(lo <= r.point <= hi)))
fw = pd.DataFrame(rows)
fw.to_csv(OUT / "full_sample_vs_window.csv", index=False, float_format="%.10f")
print(f"window slopes vs T2_slopes.csv, {len(t2_diff)} registered log-ratio chains: max |diff| {max(t2_diff):.2e}")

# ---------------------------------------------------------------- 2. arms per seed
arms = []
for L in ("EN", "BN"):
    for seed, suf in SEEDS:
        rep, rr, tp = f"{L}-REPLACE{suf}", f"{L}-REAL-REPEAT{suf}", f"{L}-REPLACE-topp95{suf}"
        for arm, c in (("REPLACE", rep), ("REAL-REPEAT", rr), ("REPLACE-topp95", tp)):
            f1, l1, h1 = fitrow(c, "log_ppl_heldout", G06)
            fb, lb, hb = fitrow(c, "bpb_heldout", G06)
            fq, lq, hq = fitrow(c, "log_ppl_heldout", G06, deg=2)
            e = boot.endpoint(c, "log_ppl_heldout", 6)
            rel = [val(c, "log_ppl_heldout_rel0", g) for g in G06]
            row = dict(language=L, seed=seed, arm=arm, chain=c, logppl_slope_0_6=f1.est, logppl_ci_lo=l1, logppl_ci_hi=h1,
                       bpb_slope_0_6=fb.est, bpb_ci_lo=lb, bpb_ci_hi=hb, logppl_quadratic=fq.est, quad_ci_lo=lq, quad_ci_hi=hq,
                       rise_to_gen6=e.est, rise_ci_lo=A.ci(e.draws)[0], rise_ci_hi=A.ci(e.draws)[1],
                       lowest_rel0=min(rel), lowest_gen=int(np.argmin(rel)))
            if arm == "REPLACE-topp95":
                fr1, frb = boot.fit(rep, "log_ppl_heldout", G06), boot.fit(rep, "bpb_heldout", G06)
                d1, db = f1.draws - fr1.draws, fb.draws - frb.draws
                row.update(topp95_minus_REPLACE_logppl=f1.est - fr1.est, diff_ci_lo=A.ci(d1)[0], diff_ci_hi=A.ci(d1)[1],
                           diff_p=A.p_two(d1), topp95_minus_REPLACE_bpb=fb.est - frb.est, diff_bpb_ci_lo=A.ci(db)[0],
                           diff_bpb_ci_hi=A.ci(db)[1])
            arms.append(row)
pd.DataFrame(arms).to_csv(OUT / "seeds_arms.csv", index=False, float_format="%.10f")

# ---------------------------------------------------------------- 3. decoder extras per seed
ext = []
for L in ("EN", "BN"):
    for seed, suf in SEEDS:
        rep, tp = f"{L}-REPLACE{suf}", f"{L}-REPLACE-topp95{suf}"
        row = dict(language=L, seed=seed)
        for lab, c in (("topp95", tp), ("REPLACE", rep)):
            f, lo, hi = fitrow(c, "sample_nll_ref_mean", G06)
            g, glo, ghi = fitrow(c, "sample_nll_ref_sd", G16)
            row.update({f"{lab}_sample_nll_slope_0_6": f.est, f"{lab}_sample_nll_0_6_ci_lo": lo, f"{lab}_sample_nll_0_6_ci_hi": hi,
                        f"{lab}_sample_nll_sd_slope_1_6": g.est, f"{lab}_sd_ci_lo": glo, f"{lab}_sd_ci_hi": ghi,
                        f"{lab}_distinct2_gen1": val(c, "distinct_2", 1), f"{lab}_distinct2_gen6": val(c, "distinct_2", 6),
                        f"{lab}_repeat4_max_gen1_6": max(val(c, "repeat_4gram_rate", k) for k in G16)})
        ext.append(row)
pd.DataFrame(ext).to_csv(OUT / "seeds_decoder_extras.csv", index=False, float_format="%.10f")

# ---------------------------------------------------------------- 4. per-document extras
z = zipfile.ZipFile(R / "cg4_sidecars_from_G4b_2026-10-20.zip")
ZR = "cg4_sidecars_bundle/results/chains/"
PR = T / "host" / "results" / "chains"


def read(chain, gen):
    rel = f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl"
    try:
        txt = z.read(ZR + rel).decode("utf-8")
    except KeyError:
        txt = (PR / rel).read_text(encoding="utf-8")
    rows_ = [json.loads(l) for l in txt.splitlines() if l.strip()]
    return pd.Series({r["doc_id"]: r["nll_total"] / r["n_tokens"] for r in rows_ if r["set"] == "heldout"}).sort_index()


def slopes(chain, gen0):
    d = pd.DataFrame({0: read(gen0, 0), **{g: read(chain, g) for g in G16}})
    gc = np.arange(7, dtype=float) - 3.0
    return pd.Series((d.values * gc).sum(1) / (gc ** 2).sum(), index=d.index)


rng = np.random.default_rng(20261024)
pdx = []
for L in ("EN", "BN"):
    S = {}
    for seed, suf in SEEDS:
        g0 = f"GEN0-{L}{suf}"
        S[("REPLACE", seed)] = slopes(f"{L}-REPLACE{suf}", g0)
        S[("REAL-REPEAT", seed)] = slopes(f"{L}-REAL-REPEAT{suf}", g0)
    idx = S[("REPLACE", "0")].index
    dom = pd.Series(np.where(idx.str.contains("wiki_articles"), "wikipedia", "web"), index=idx)
    for (arm, seed), v in S.items():
        v = v[idx]
        pdx.append(dict(language=L, kind="mean slope by domain", arm=arm, seed=seed, web=float(v[dom == "web"].mean()),
                        wikipedia=float(v[dom == "wikipedia"].mean()), n_web=int((dom == "web").sum()),
                        n_wikipedia=int((dom == "wikipedia").sum())))
    n = len(idx)
    draws = [rng.integers(0, n, n) for _ in range(2000)]
    for arm1, arm2 in (("REPLACE", "REPLACE"), ("REAL-REPEAT", "REAL-REPEAT"), ("REPLACE", "REAL-REPEAT")):
        for s1, s2 in (("0", "2"), ("0", "3"), ("2", "3")) if arm1 == arm2 else (("0", "0"), ("2", "2"), ("3", "3"), ("0", "2"), ("2", "0")):
            a_, b_ = S[(arm1, s1)][idx].values, S[(arm2, s2)][idx].values
            bs = np.array([np.corrcoef(a_[i], b_[i])[0, 1] for i in draws])
            pdx.append(dict(language=L, kind="per-document slope correlation", arm=f"{arm1} seed {s1} vs {arm2} seed {s2}",
                            seed=f"{s1},{s2}", pearson=float(np.corrcoef(a_, b_)[0, 1]),
                            ci_lo=float(np.percentile(bs, 2.5)), ci_hi=float(np.percentile(bs, 97.5)), n_docs=n))
pd.DataFrame(pdx).to_csv(OUT / "perdoc_seeds_extra.csv", index=False, float_format="%.10f")

# ---------------------------------------------------------------- 5. cross-decoder: seed-0 cells, first 50 prefixes
pc = pd.read_csv(OUT / "cross_decoder2_per_continuation_nll.csv")
old = pd.read_csv(R / "analysis" / "posthoc_review_2026-10-22" / "cross_decoder_slope_ci.csv")
w = (np.arange(1, 7) - 3.5) / ((np.arange(1, 7) - 3.5) ** 2).sum()
fx = []
for c in ("EN-REPLACE", "EN-REPLACE-topp95", "BN-REPLACE", "BN-REPLACE-topp95"):
    for dec in (1.0, 0.95):
        sub = pc[(pc.chain == c) & (pc.decoder_top_p == dec) & pc.gen.between(1, 6)]
        ids50 = sorted(sub.prefix_id.unique())[:50]
        m200 = sub.groupby("gen").nll.mean().reindex(range(1, 7)).to_numpy()
        m50 = sub[sub.prefix_id.isin(ids50)].groupby("gen").nll.mean().reindex(range(1, 7)).to_numpy()
        o = old[(old.language == c[:2]) & (old.quantity == f"slope {c}, eval top-p {dec}")].iloc[0]
        fx.append(dict(chain=c, eval_top_p=dec, slope_first50_new_draws=float(m50 @ w), slope_200=float(m200 @ w),
                       slope_2026_10_20=o.point, ci_lo_2026_10_20=o.ci_lo, ci_hi_2026_10_20=o.ci_hi,
                       first50_inside_2026_10_20_ci=bool(o.ci_lo <= float(m50 @ w) <= o.ci_hi)))
pd.DataFrame(fx).to_csv(OUT / "cross_decoder2_first50.csv", index=False, float_format="%.10f")
# ---------------------------------------------------------------- 6. cross-decoder levels (Table 5 columns, three seeds)
sm = pd.read_csv(T / "host" / "results" / "posthoc2_cross_decoder" / "cross_decoder2_summary.csv")
lv = []
for c in sorted(sm[~sm.chain.str.startswith("GEN0")].chain.unique()):
    for dec in (1.0, 0.95):
        x = sm[(sm.chain == c) & (sm.decoder_top_p == dec)].set_index("gen")
        g0 = sm[(sm.chain == x.gen0.iloc[0]) & (sm.decoder_top_p == dec)].mean_nll_nats.iloc[0]
        lv.append(dict(chain=c, training_text="top-p 0.95" if "topp95" in c else "top-p 1.0", eval_top_p=dec, gen0_model=x.gen0.iloc[0],
                       gen0_level=g0, gen1=x.loc[1, "mean_nll_nats"], gen6=x.loc[6, "mean_nll_nats"]))
lv = pd.DataFrame(lv)
lv.to_csv(OUT / "cross_decoder2_levels.csv", index=False, float_format="%.10f")
sh = sm.pivot_table(index=["chain", "gen"], columns="decoder_top_p", values="mean_nll_nats")
d = (sh[1.0] - sh[0.95])
print(f"evaluation-decoder level shift (top-p 1.0 minus 0.95, same checkpoint), {len(d)} steps: min {d.min():.2f}, "
      f"median {d.median():.2f}, max {d.max():.2f}")
print("wrote full_sample_vs_window.csv, seeds_arms.csv, seeds_decoder_extras.csv, perdoc_seeds_extra.csv, cross_decoder2_first50.csv, "
      "cross_decoder2_levels.csv")
