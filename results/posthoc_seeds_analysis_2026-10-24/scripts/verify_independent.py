#!/usr/bin/env python3
"""Independent recomputation (2026-10-24, PC) of the key numbers of ANALYSIS.md by a separate code path: plain NumPy on the
raw records (metric records, held-out per-document records, the cross-decoder samples file, the full-sample tables),
without harness/analyze.py and without the bootstrap. Point estimates only. Writes out/validation/independent_check.csv
(block, quantity, value in the analysis outputs, independent value, absolute difference) and prints the largest difference
per block. The restricted samples file is read in memory; nothing from it is written. Numbers only.
usage: python -B verify_independent.py <package root> <analysis folder>"""
import gzip, json, re, sys, zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PKG, A = Path(sys.argv[1]), Path(sys.argv[2])
O, R = A / "out", PKG / "results"
T = R / "posthoc_seeds_2026-10-23"
SEEDS = ((0, ""), (2, "-s2"), (3, "-s3"))
rec = []
for p in (R / "metrics.jsonl", T / "host" / "results" / "metrics_posthoc_2026-10-23.jsonl"):
    with open(p, encoding="utf-8") as fh:
        rec += [json.loads(l) for l in fh if l.strip()]
m = pd.DataFrame(rec).drop_duplicates(["chain_id", "generation", "metric"], keep="last")
V = {(r.chain_id, r.metric, int(r.generation)): float(r.value) for r in m.itertuples()}
out = []


def y(chain, metric, gens, L, suf, log=False):
    g0 = f"GEN0-{L}{suf}"
    v = np.array([V[(g0 if g == 0 else chain, metric, g)] for g in gens])
    return np.log(v) if log else v


def slope(chain, metric, gens, L, suf, log=False, deg=1):
    return float(np.polyfit(np.array(gens, float), y(chain, metric, gens, L, suf, log), deg)[0])


def add(block, q, a, b):
    out.append(dict(block=block, quantity=q, analysis=a, independent=b, abs_diff=abs(a - b)))


sc = pd.read_csv(O / "seeds_controls.csv")
arms = pd.read_csv(O / "seeds_arms.csv")
G06, G16 = list(range(7)), list(range(1, 7))
for L in ("EN", "BN"):
    for s, suf in SEEDS:
        rep, rr, tp = f"{L}-REPLACE{suf}", f"{L}-REAL-REPEAT{suf}", f"{L}-REPLACE-topp95{suf}"
        for metric, log in (("log_ppl_heldout", False), ("bpb_heldout", False), ("distinct_2", True), ("tail_fact_recall_ALL", True)):
            ind = slope(rep, metric, G06, L, suf, log) - slope(rr, metric, G06, L, suf, log)
            name = metric + ("_logratio0" if log else "")
            a = sc[(sc.kind == "REPLACE minus REAL-REPEAT slope") & (sc.language == L) & (sc.seed == s) & (sc.metric == name)].estimate.iloc[0]
            add("net contrast", f"{L} seed {s} {name}", a, ind)
        for arm_, c in (("REPLACE", rep), ("REAL-REPEAT", rr)):
            for gens, lab in ((list(range(4)), "0..3"), (list(range(3, 7)), "3..6")):
                a = sc[(sc.kind == f"slope {arm_}") & (sc.language == L) & (sc.seed == s) & (sc.generations == lab)].estimate.iloc[0]
                add("shape", f"{L} seed {s} {arm_} slope {lab}", a, slope(c, "log_ppl_heldout", gens, L, suf))
            q = arms[(arms.language == L) & (arms.seed == s) & (arms.arm == arm_)].logppl_quadratic.iloc[0]
            add("shape", f"{L} seed {s} {arm_} quadratic", q, slope(c, "log_ppl_heldout", G06, L, suf, deg=2))
            yy = y(c, "log_ppl_heldout", G06, L, suf)
            a = sc[(sc.kind == f"rise to generation 6, {c}") & (sc.language == L) & (sc.seed == s)].estimate.iloc[0]
            add("shape", f"{L} seed {s} {arm_} rise", a, float(yy[6] - yy[0]))
        for metric in ("distinct_2", "sample_nll_ref_mean"):
            for c in (tp, rep):
                a = sc[(sc.kind == f"slope {c}") & (sc.language == L) & (sc.seed == s) & (sc.metric == metric)].estimate.iloc[0]
                add("decoder arm", f"{c} {metric} slope 1..6", a, slope(c, metric, G16, L, suf))
        a = sc[(sc.kind == f"repeat_4gram_rate at generation 6, {tp}") & (sc.language == L) & (sc.seed == s)].estimate.iloc[0]
        add("decoder arm", f"{tp} repeat_4gram_rate gen 6", a, V[(tp, "repeat_4gram_rate", 6)])
        d = arms[(arms.language == L) & (arms.seed == s) & (arms.arm == "REPLACE-topp95")].topp95_minus_REPLACE_logppl.iloc[0]
        add("decoder arm", f"{L} seed {s} topp95 minus REPLACE held-out slope", d,
            slope(tp, "log_ppl_heldout", G06, L, suf) - slope(rep, "log_ppl_heldout", G06, L, suf))

# per-document correlations
z = zipfile.ZipFile(R / "cg4_sidecars_from_G4b_2026-10-20.zip")
pdoc = pd.read_csv(O / "perdoc_seeds.csv")


def heldout(chain, gen):
    rel = f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl"
    name = "cg4_sidecars_bundle/results/chains/" + rel
    txt = z.read(name).decode("utf-8") if name in z.namelist() else (T / "host" / "results" / "chains" / rel).read_text(encoding="utf-8")
    d = {}
    for l in txt.splitlines():
        if l.strip():
            r = json.loads(l)
            if r["set"] == "heldout":
                d[r["doc_id"]] = r["nll_total"] / r["n_tokens"]
    return d


for L in ("EN", "BN"):
    for s, suf in SEEDS:
        g0 = heldout(f"GEN0-{L}{suf}", 0)
        ids = sorted(g0)
        sl = {}
        for c in (f"{L}-REPLACE{suf}", f"{L}-REAL-REPEAT{suf}"):
            cols = [g0] + [heldout(c, g) for g in G16]
            Y = np.array([[col[i] for col in cols] for i in ids])
            sl[c] = np.polyfit(np.arange(7.0), Y.T, 1)[0]
        a, b = sl[f"{L}-REPLACE{suf}"], sl[f"{L}-REAL-REPEAT{suf}"]
        row = pdoc[(pdoc.language == L) & (pdoc.seed == s)].iloc[0]
        add("per-document", f"{L} seed {s} correlation", row.pearson_REPLACE_vs_REAL_REPEAT, float(np.corrcoef(a, b)[0, 1]))
        add("per-document", f"{L} seed {s} share rising REAL-REPEAT", row.share_rising_REAL_REPEAT, float((b > 0).mean()))

# cross-decoder slopes straight from the samples file
cells = {}
with gzip.open(T / "host" / "results" / "posthoc2_cross_decoder" / "cross_decoder2_samples.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        if r["n_tokens"] > 0:
            cells.setdefault((r["chain"], r["gen"], r["decoder_top_p"]), []).append(r["nll"])
xs = pd.read_csv(O / "cross_decoder2_slope_ci.csv")
for q in xs[xs.quantity.str.startswith("slope ")].itertuples():
    c, dec = re.match(r"slope (\S+), eval top-p (\S+)", q.quantity).groups()
    means = [np.mean(cells[(c, g, float(dec))]) for g in G16]
    add("cross-decoder", q.quantity, q.point, float(np.polyfit(np.arange(1.0, 7.0), means, 1)[0]))

# distinct-2 of the continuations (full set of prefixes), plain sets
sys.path.insert(0, str(PKG / "harness"))
from common import words  # noqa: E402
txt = {}
with gzip.open(T / "host" / "results" / "posthoc2_cross_decoder" / "cross_decoder2_samples.jsonl.gz", "rt", encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        txt.setdefault((r["chain"], r["decoder_top_p"]), {}).setdefault(r["gen"], {})[r["prefix_id"]] = [w.lower() for w in words(r["text"])]
xd = pd.read_csv(O / "cross_decoder2_distinct2_K100_n200.csv")
for r in xd.itertuples():
    W = txt[(r.chain, float(r.evaluation.split()[-1]))]
    ids = sorted(W[1])
    Lp = {pid: min(100, min(len(W[g][pid]) for g in G16)) for pid in ids}
    v = []
    for g in G16:
        bg = [b for pid in ids for b in zip(W[g][pid][:Lp[pid]], W[g][pid][1:Lp[pid]])]
        v.append(len(set(bg)) / max(1, len(bg)))
    add("continuation distinct-2", f"{r.chain} eval {r.evaluation}", r.raw_slope_1_6, float(np.polyfit(np.arange(1.0, 7.0), v, 1)[0]))
del txt

# full-sample sign counts against the registered window slopes
fs = pd.read_csv(T / "full_sample_check" / "full_sample_equal_length_K100_n2000_m1600_B500_seed20261024.csv")
t2 = pd.read_csv(R / "analysis" / "T2_slopes.csv")
same, same_ci, n_ci = 0, 0, 0
reg = [c for c in fs.chain if not c.endswith(("-s2", "-s3")) or c.startswith(("EN-REPLACE-s", "BN-REPLACE-s"))]
for c in reg:
    full = float(fs[fs.chain == c].point.iloc[0])
    if "topp95" in c:
        L = c[:2]
        w = slope(c, "distinct_2", G16, L, "")
        lo, hi = -1, -1  # registered-code interval excludes zero (Table S12)
    else:
        t = t2[(t2.chain_id == c) & (t2.metric == "distinct_2_logratio0") & (t2.generations == "0..6")].iloc[0]
        w, lo, hi = t.slope, t.lo, t.hi
    excl = (lo > 0) or (hi < 0)
    same += np.sign(w) == np.sign(full)
    n_ci += excl
    same_ci += excl and np.sign(w) == np.sign(full)
fw = pd.read_csv(O / "full_sample_vs_window.csv")
r_ = fw[~fw.posthoc_chain]
add("full-sample", "registered chains with the same sign", float(r_.sign_full_equals_window.sum()), float(same))
add("full-sample", "registered chains with interval excluding zero", float(r_.window_ci_excludes_0.sum()), float(n_ci))
add("full-sample", "of those, same sign", float(r_[r_.window_ci_excludes_0].sign_full_equals_window.sum()), float(same_ci))
add("full-sample", "number of registered chains", float(len(r_)), float(len(reg)))

res = pd.DataFrame(out)
(O / "validation").mkdir(parents=True, exist_ok=True)
res.to_csv(O / "validation" / "independent_check.csv", index=False, float_format="%.12g")
for b, g in res.groupby("block", sort=False):
    print(f"{b:24s} {len(g):3d} quantities, largest |difference| {g.abs_diff.max():.3g}")
