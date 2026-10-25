"""Post-hoc (2026-10-23): distinct-2 of the cross-decoder continuations (REPLACE-family checkpoints, generations 1..6,
50 fresh continuations per cell, both evaluation decoders). Each prefix contributes the same number of words at every
generation of a row (L_p = min(K, its shortest continuation in that row)); bigrams are counted within documents only.
Ranges: subsets of 40 of the 50 prefixes without replacement, shared by all cells of a language.
Reads only the text and ids of the restricted cross_decoder_samples.jsonl.gz and writes numbers only.
Usage: python cross_decoder_distinct2.py <cross_decoder_samples.jsonl.gz> <out_dir> [K=100] [draws=2000]"""
import gzip, json, sys, pathlib
import numpy as np, pandas as pd, regex
WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
K = int(sys.argv[3]) if len(sys.argv) > 3 else 100
B = int(sys.argv[4]) if len(sys.argv) > 4 else 2000
cells = {}
with gzip.open(src, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        cells.setdefault((r["chain"], r["gen"], r["decoder_top_p"]), {})[r["prefix_id"]] = [w.lower() for w in WORD.findall(r["text"])]
rng = np.random.default_rng(20261023); n, m = 50, 40
subsets = {L: [rng.choice(n, m, replace=False) for _ in range(B)] for L in ("EN", "BN")}
g = np.arange(1, 7, dtype=float); w = (g - g.mean()) / ((g - g.mean()) ** 2).sum()
rows = []
for L in ("EN", "BN"):
    for chain in (f"{L}-REPLACE", f"{L}-REPLACE-topp95"):
        for dec in (1.0, 0.95):
            W = {k: cells[(chain, k, dec)] for k in range(1, 7)}
            ids = sorted(W[1]); assert len(ids) == n and all(sorted(W[k]) == ids for k in W)
            Lp = {p: min(K, min(len(W[k][p]) for k in W)) for p in ids}
            big = {k: [list(zip(W[k][p][:Lp[p]], W[k][p][1:Lp[p]])) for p in ids] for k in W}
            def slope(sel):
                v = np.array([len(set(b for i in sel for b in big[k][i])) / max(1, sum(len(big[k][i]) for i in sel)) for k in range(1, 7)])
                return float(v @ w), v
            pt, v = slope(range(n)); bs = np.array([slope(s)[0] for s in subsets[L]])
            rows.append({"language": L, "training_text": "top-p 0.95" if chain.endswith("topp95") else "top-p 1.0", "evaluation": f"top-p {dec}",
                         "d2_gen1": v[0], "d2_gen6": v[5], "raw_slope_1_6": pt, "range_lo": np.percentile(bs, 2.5), "range_hi": np.percentile(bs, 97.5),
                         "words_per_generation": int(sum(Lp.values()))})
res = pd.DataFrame(rows); res.to_csv(out / f"cross_decoder_distinct2_K{K}.csv", index=False, float_format="%.5f")
print(res.round(4).to_string())
