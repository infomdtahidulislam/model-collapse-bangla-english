"""Post-hoc (posthoc_gpu_pack2; written 2026-10-23): distinct-2 of the cross-decoder continuations for every REPLACE-family
chain present (seeds 0, 2, 3 under each training decoder), generations 1..6, both evaluation decoders. Generalises
../posthoc_review_2026-10-22/cross_decoder_distinct2.py: each prefix contributes the same number of words at every generation
of a row (L_p = min(K, its shortest continuation in that row)); bigrams within documents; stability ranges = 2.5th and 97.5th
percentiles over B subsets of m of the n prefixes (without replacement, default_rng(seed), shared by all cells of a
language, EN drawn first). With --n 50 --m 40 --B 2000 --seed 20261023 on the 2026-10-20 file it reproduces
cross_decoder_distinct2_K100.csv (Supplementary Table S9) exactly. Reads the restricted text in memory; writes numbers only.
usage: python cross_decoder2_distinct2.py <samples.jsonl.gz> <out_dir> [--K 100] [--n 200] [--m 160] [--B 2000] [--seed 20261024]
       [--engine count|python]

Changed 2026-10-24 (PC), the only change to the copy in results/analysis/posthoc_seeds_2026-10-23/: a faster engine for the
subset statistic, because the PC's shell stops any job after three minutes. --engine count (default) computes the same
integers (distinct bigram types and bigram count of each subset) by counting: a bigram type found in one prefix counts when
that prefix is in the subset, and a type shared by several prefixes counts when any of them is (bit masks); the ratio, the
slope and the percentiles then follow the original lines. --engine python runs the original loop. Both engines give
identical files (checked on the 2026-10-20 file at Table S9 settings and on the 2026-10-24 file with --B 50). The CSV carries
10 decimals instead of 5, so that values rounded for the report are rounded once."""
import argparse, gzip, json
from pathlib import Path
import numpy as np, pandas as pd, regex

WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--K", type=int, default=100); ap.add_argument("--n", type=int, default=200); ap.add_argument("--m", type=int, default=160)
ap.add_argument("--B", type=int, default=2000); ap.add_argument("--seed", type=int, default=20261024); ap.add_argument("--tag", default="cross_decoder2")
ap.add_argument("--engine", choices=["count", "python"], default="count")
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
cells = {}
with gzip.open(a.src, "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        cells.setdefault((r["chain"], r["gen"], r["decoder_top_p"]), {})[r["prefix_id"]] = [w.lower() for w in WORD.findall(r["text"])]
rng = np.random.default_rng(a.seed)
subsets = {L: [rng.choice(a.n, a.m, replace=False) for _ in range(a.B)] for L in ("EN", "BN")}
g = np.arange(1, 7, dtype=float); w = (g - g.mean()) / ((g - g.mean()) ** 2).sum()


def bits(subs, n):
    """Subsets as bit masks (one bit per prefix) and as 0/1 indicator rows."""
    sb = np.zeros((len(subs), (n + 63) // 64), dtype=np.uint64); si = np.zeros((len(subs), n), dtype=np.int64)
    for b, sel in enumerate(subs):
        si[b, sel] = 1
        for i in sel:
            sb[b, int(i) >> 6] |= np.uint64(1 << (int(i) & 63))
    return sb, si


SB = {L: bits(subsets[L], a.n) for L in ("EN", "BN")}


def fast(big, sbits, sind):
    """The quantities of slope() for the full set and for every subset, by exact integer counting."""
    n = sind.shape[1]; V = np.empty((len(sind), 6)); v = np.empty(6)
    for col, k in enumerate(range(1, 7)):
        owners = {}
        for i, bl in enumerate(big[k]):
            for bg in set(bl):
                owners.setdefault(bg, []).append(i)
        lens = np.array([len(bl) for bl in big[k]], dtype=np.int64)
        u1 = np.zeros(n, dtype=np.int64); multi = []
        for own in owners.values():
            if len(own) == 1:
                u1[own[0]] += 1
            else:
                multi.append(own)
        mb = np.zeros((len(multi), sbits.shape[1]), dtype=np.uint64)
        for j, own in enumerate(multi):
            for i in own:
                mb[j, i >> 6] |= np.uint64(1 << (i & 63))
        d = sind @ u1
        for s0 in range(0, len(sbits), 64):
            d[s0:s0 + 64] += ((mb[None, :, :] & sbits[s0:s0 + 64, None, :]) != 0).any(axis=2).sum(axis=1)
        V[:, col] = d / np.maximum(1, sind @ lens)
        v[col] = len(owners) / max(1, int(lens.sum()))
    return float(v @ w), v, np.array([float(V[b] @ w) for b in range(len(V))])

rows = []
for L in ("EN", "BN"):
    for seed, suf in (("0", ""), ("2", "-s2"), ("3", "-s3")):
        for chain in (f"{L}-REPLACE{suf}", f"{L}-REPLACE-topp95{suf}"):
            for dec in (1.0, 0.95):
                if not all((chain, k, dec) in cells for k in range(1, 7)):
                    continue
                W = {k: cells[(chain, k, dec)] for k in range(1, 7)}
                ids = sorted(W[1])
                if len(ids) != a.n or not all(sorted(W[k]) == ids for k in W):
                    raise SystemExit(f"{chain} top-p {dec}: {len(ids)} prefixes or ids differ across generations (expected {a.n})")
                Lp = {p: min(a.K, min(len(W[k][p]) for k in W)) for p in ids}
                big = {k: [list(zip(W[k][p][:Lp[p]], W[k][p][1:Lp[p]])) for p in ids] for k in W}

                def slope(sel):
                    v = np.array([len(set(b for i in sel for b in big[k][i])) / max(1, sum(len(big[k][i]) for i in sel)) for k in range(1, 7)])
                    return float(v @ w), v
                if a.engine == "python":
                    pt, v = slope(range(a.n)); bs = np.array([slope(s)[0] for s in subsets[L]])
                else:
                    pt, v, bs = fast(big, *SB[L])
                rows.append({"language": L, "seed": seed, "chain": chain, "training_text": "top-p 0.95" if "topp95" in chain else "top-p 1.0",
                             "evaluation": f"top-p {dec}", "d2_gen1": v[0], "d2_gen6": v[5], "raw_slope_1_6": pt,
                             "range_lo": np.percentile(bs, 2.5), "range_hi": np.percentile(bs, 97.5), "words_per_generation": int(sum(Lp.values()))})
res = pd.DataFrame(rows); res.to_csv(out / f"{a.tag}_distinct2_K{a.K}_n{a.n}.csv", index=False, float_format="%.10f")
print(res.round(4).to_string())
