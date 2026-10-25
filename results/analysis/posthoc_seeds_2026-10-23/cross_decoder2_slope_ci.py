"""Post-hoc (posthoc_gpu_pack2; written 2026-10-23): prefix-paired bootstrap CIs for the cross-decoder slopes (OLS over
generations 1..6) of every REPLACE-family chain present (seeds 0, 2, 3 under each training decoder), for the per-seed
training-decoder contrast (REPLACE-sK minus REPLACE-topp95-sK, same language and evaluation decoder) and for its mean over
the seeds present. Generalises ../posthoc_review_2026-10-22/cross_decoder_slope_ci.py: same statistic, same bootstrap
(B draws of the prefixes with replacement, one draw set shared by every cell of a language, EN drawn first, default_rng
seed 20261022). On the 2026-10-20 file (seed 0 only, 50 prefixes) it reproduces cross_decoder_slope_ci.csv exactly.
Reads only the numeric fields of the restricted samples file; writes numbers only.
usage: python cross_decoder2_slope_ci.py <samples.jsonl.gz | per_continuation.csv> <out_dir> [--B 5000] [--tag cross_decoder2]"""
import argparse, gzip, json
from pathlib import Path
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--B", type=int, default=5000); ap.add_argument("--seed", type=int, default=20261022); ap.add_argument("--tag", default="cross_decoder2")
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
                if piv.shape[1] != 6 or piv.isna().any().any():
                    raise SystemExit(f"{chain} top-p {dec}: incomplete cell ({piv.shape}, NaN {int(piv.isna().sum().sum())})")
                if ids_ref is None:
                    ids_ref = list(piv.index)
                if list(piv.index) != ids_ref:
                    raise SystemExit("prefix ids differ between cells of a language; pairing would be invalid")
                M[(seed, chain, dec)] = piv.values
    if not M:
        continue
    n = len(ids_ref); draws = [rng.integers(0, n, n) for _ in range(a.B)]
    for (seed, chain, dec), m in M.items():
        bs = np.array([m[i].mean(0) @ w for i in draws])
        res.append({"language": L, "seed": seed, "quantity": f"slope {chain}, eval top-p {dec}", "n_prefixes": n,
                    "point": float(m.mean(0) @ w), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
    for dec in (1.0, 0.95):
        pairs = []
        for seed, suf in SEEDS:
            k1, k2 = (seed, f"{L}-REPLACE{suf}", dec), (seed, f"{L}-REPLACE-topp95{suf}", dec)
            if k1 in M and k2 in M:
                pairs.append((seed, M[k1], M[k2]))
                bs = np.array([(M[k1][i].mean(0) - M[k2][i].mean(0)) @ w for i in draws])
                res.append({"language": L, "seed": seed, "quantity": f"training-decoder contrast (top-p 1.0 minus 0.95 trained), eval top-p {dec}",
                            "n_prefixes": n, "point": float((M[k1].mean(0) - M[k2].mean(0)) @ w),
                            "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
        if len(pairs) > 1:
            pt = float(np.mean([(p1.mean(0) - p2.mean(0)) @ w for _, p1, p2 in pairs]))
            bs = np.array([np.mean([(p1[i].mean(0) - p2[i].mean(0)) @ w for _, p1, p2 in pairs]) for i in draws])
            res.append({"language": L, "seed": "mean of " + ",".join(s for s, _, _ in pairs),
                        "quantity": f"training-decoder contrast, mean over seeds, eval top-p {dec}", "n_prefixes": n,
                        "point": pt, "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
r = pd.DataFrame(res); r.to_csv(out / f"{a.tag}_slope_ci.csv", index=False, float_format="%.5f")
print(r.round(3).to_string())
