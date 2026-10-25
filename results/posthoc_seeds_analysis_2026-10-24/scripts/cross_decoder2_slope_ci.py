"""Post-hoc (posthoc_gpu_pack2; written 2026-10-23): prefix-paired bootstrap CIs for the cross-decoder slopes (OLS over
generations 1..6) of every REPLACE-family chain present (seeds 0, 2, 3 under each training decoder), for the per-seed
training-decoder contrast (REPLACE-sK minus REPLACE-topp95-sK, same language and evaluation decoder) and for its mean over
the seeds present. Generalises ../posthoc_review_2026-10-22/cross_decoder_slope_ci.py: same statistic, same bootstrap
(B draws of the prefixes with replacement, one draw set shared by every cell of a language, EN drawn first, default_rng
seed 20261022). On the 2026-10-20 file (seed 0 only, 50 prefixes) it reproduces cross_decoder_slope_ci.csv exactly.
Reads only the numeric fields of the restricted samples file; writes numbers only.
usage: python cross_decoder2_slope_ci.py <samples.jsonl.gz | per_continuation.csv> <out_dir> [--B 5000] [--tag cross_decoder2]
       [--empty mean|drop]

Changed 2026-10-24 (PC), the only change to the copy in results/analysis/posthoc_seeds_2026-10-23/: the 2026-10-24 file has
three empty continuations (0 tokens, no NLL), where that version stopped with "incomplete cell". --empty mean (default) takes
each cell's mean over its usable draws, as cross_decoder2_summary.csv does, in the point estimate and in every bootstrap
draw; --empty drop removes the affected prefixes from every cell of that language (prefix pairing kept). A file without
empty continuations takes the unchanged code path, so the 2026-10-20 reproduction stays exact. The slope file carries 10
decimals instead of 5, so that values rounded for the report are rounded once."""
import argparse, gzip, json
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--B", type=int, default=5000); ap.add_argument("--seed", type=int, default=20261022); ap.add_argument("--tag", default="cross_decoder2")
ap.add_argument("--empty", choices=["mean", "drop"], default="mean")
a = ap.parse_args(); src, out = Path(a.src), Path(a.out); out.mkdir(parents=True, exist_ok=True)
if src.suffix == ".gz":
    rows = []
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line); rows.append({k: r[k] for k in ("chain", "gen", "decoder_top_p", "prefix_id", "nll", "n_tokens")})
    d = pd.DataFrame(rows); d.to_csv(out / f"{a.tag}_per_continuation_nll.csv", index=False, float_format="%.6f")
else:
    d = pd.read_csv(src)
rng = np.random.default_rng(a.seed)
g = np.arange(1, 7) - 3.5; w = g / (g ** 2).sum()


def cm(x):
    """Per-generation mean over prefixes; over the usable draws only when a cell has an empty continuation."""
    return np.nanmean(x, 0) if np.isnan(x).any() else x.mean(0)

SEEDS = (("0", ""), ("2", "-s2"), ("3", "-s3"))
res = []
for L in ["EN", "BN"]:
    M, ids_ref = {}, None
    for seed, suf in SEEDS:
        for chain in (f"{L}-REPLACE{suf}", f"{L}-REPLACE-topp95{suf}"):
            for dec in (1.0, 0.95):
                sub = d[(d.chain == chain) & (d.decoder_top_p == dec) & (d.gen.between(1, 6))]
                if sub.empty:
                    continue
                piv = sub.pivot_table(index="prefix_id", columns="gen", values="nll").sort_index()
                if piv.shape[1] != 6:
                    raise SystemExit(f"{chain} top-p {dec}: incomplete cell ({piv.shape})")
                if ids_ref is None:
                    ids_ref = list(piv.index)
                if list(piv.index) != ids_ref:
                    raise SystemExit("prefix ids differ between cells of a language; pairing would be invalid")
                M[(seed, chain, dec)] = piv.values
    if not M:
        continue
    if a.empty == "drop":
        keep = ~np.any([np.isnan(m).any(1) for m in M.values()], axis=0)
        M = {k: m[keep] for k, m in M.items()}; ids_ref = [i for i, k in zip(ids_ref, keep) if k]
    n = len(ids_ref); draws = [rng.integers(0, n, n) for _ in range(a.B)]
    for (seed, chain, dec), m in M.items():
        bs = np.array([cm(m[i]) @ w for i in draws])
        res.append({"language": L, "seed": seed, "quantity": f"slope {chain}, eval top-p {dec}", "n_prefixes": n,
                    "point": float(cm(m) @ w), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
    for dec in (1.0, 0.95):
        pairs = []
        for seed, suf in SEEDS:
            k1, k2 = (seed, f"{L}-REPLACE{suf}", dec), (seed, f"{L}-REPLACE-topp95{suf}", dec)
            if k1 in M and k2 in M:
                pairs.append((seed, M[k1], M[k2]))
                bs = np.array([(cm(M[k1][i]) - cm(M[k2][i])) @ w for i in draws])
                res.append({"language": L, "seed": seed, "quantity": f"training-decoder contrast (top-p 1.0 minus 0.95 trained), eval top-p {dec}",
                            "n_prefixes": n, "point": float((cm(M[k1]) - cm(M[k2])) @ w),
                            "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
        if len(pairs) > 1:
            pt = float(np.mean([(cm(p1) - cm(p2)) @ w for _, p1, p2 in pairs]))
            bs = np.array([np.mean([(cm(p1[i]) - cm(p2[i])) @ w for _, p1, p2 in pairs]) for i in draws])
            res.append({"language": L, "seed": "mean of " + ",".join(s for s, _, _ in pairs),
                        "quantity": f"training-decoder contrast, mean over seeds, eval top-p {dec}", "n_prefixes": n,
                        "point": pt, "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
r = pd.DataFrame(res); r.to_csv(out / f"{a.tag}_slope_ci.csv", index=False, float_format="%.10f")
print(r.round(3).to_string())
