"""Post-hoc (2026-10-23): prefix-paired distinct-2 with each prefix's contribution held constant across a chain's steps.
For every chain and prefix, L_p = min(K, the shortest continuation that prefix received at any of the chain's compared steps);
at every step the prefix contributes exactly its first L_p words (registered word split, lower-cased), and bigrams are
counted within documents only. Every step of a chain therefore has the same prompts and the same number of words per
prompt. Ranges come from subsets of 40 of the 50 prefixes drawn without replacement and shared by all steps of a language
(a sensitivity range for this subset, not a confidence interval for the registered statistic).
Usage: python prefix_paired_diversity_equal.py <samples_dir> <out_dir> [K=100] [draws=2000]"""
import json, sys, pathlib
import numpy as np, pandas as pd, regex
WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
sd, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
K = int(sys.argv[3]) if len(sys.argv) > 3 else 100
B = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
def gen0_of(ch):
    L = ch[:2]
    for suf in ("-s2", "-s3", "-WM"):
        if ch.endswith(suf): return f"GEN0-{L}{suf}"
    return f"GEN0-{L}"
def words(path):
    return {json.loads(l)["prefix_id"]: [w.lower() for w in WORD.findall(json.loads(l)["text"])] for l in open(path, encoding="utf-8")}
chains = ["EN-REPLACE", "EN-REPLACE-s2", "EN-REPLACE-s3", "EN-ACCUMULATE", "EN-ACCUMULATE-FILTER", "EN-ACCUMULATE-SUBSAMPLE",
          "EN-REAL-REPEAT", "EN-REPLACE-WM", "EN-REPLACE-topp95", "BN-REPLACE", "BN-REPLACE-s2", "BN-REPLACE-s3", "BN-ACCUMULATE",
          "BN-ACCUMULATE-FILTER", "BN-ACCUMULATE-SUBSAMPLE", "BN-REAL-REPEAT", "BN-REPLACE-topp95"]
rng = np.random.default_rng(20261023); n = 50; m = 40
subsets = {L: [rng.choice(n, m, replace=False) for _ in range(B)] for L in ("EN", "BN")}
rows = []
for ch in chains:
    gens = list(range(1, 7)) if ch.endswith("topp95") else list(range(0, 7))
    W = {g: words(sd / (f"{gen0_of(ch)}_gen0_50.jsonl" if g == 0 else f"{ch}_gen{g}_50.jsonl")) for g in gens}
    ids = sorted(W[gens[0]]); assert all(sorted(W[g]) == ids for g in gens) and len(ids) == n
    Lp = {p: min(K, min(len(W[g][p]) for g in gens)) for p in ids}
    big = {g: [list(zip(W[g][p][:Lp[p]], W[g][p][1:Lp[p]])) for p in ids] for g in gens}
    def d2(g, sel):
        grams = [b for i in sel for b in big[g][i]]
        return len(set(grams)) / max(1, len(grams))
    x = np.array(gens, float); xc = x - x.mean(); w = xc / (xc ** 2).sum()
    def slope(sel):
        v = np.array([d2(g, sel) for g in gens])
        return float((np.log(v / v[0]) if gens[0] == 0 else v) @ w)
    pt = slope(range(n)); bs = np.array([slope(s) for s in subsets[ch[:2]]])
    rows.append({"chain": ch, "quantity": "log_ratio_slope_0_6" if gens[0] == 0 else "raw_slope_1_6", "point": pt,
                 "range_lo": np.percentile(bs, 2.5), "range_hi": np.percentile(bs, 97.5), "words_per_step": int(sum(Lp.values())),
                 "prefixes_at_full_K": int(sum(1 for v in Lp.values() if v == K)), "median_words_per_prefix": float(np.median(list(Lp.values())))})
res = pd.DataFrame(rows); res.to_csv(out / f"prefix_paired_diversity_equal_K{K}.csv", index=False, float_format="%.5f")
print(res.round(4).to_string())
