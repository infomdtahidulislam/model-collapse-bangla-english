"""Post-hoc (2026-10-22): prefix-paired bootstrap CIs for the cross-decoder slopes (OLS over generations 1..6) and for the
training-decoder contrast (top-p 1.0-trained minus top-p 0.95-trained slope, same language and evaluation decoder).
Input: cross_decoder_samples.jsonl.gz (restricted; only the numeric fields are read) or the public numbers-only
cross_decoder_per_continuation_nll.csv, which this script writes when given the .jsonl.gz.
Usage: python cross_decoder_slope_ci.py <input> <out_dir>"""
import gzip, json, sys, pathlib
import numpy as np, pandas as pd
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
if src.suffix == ".gz":
    rows = []
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line); rows.append({k: r[k] for k in ("chain", "gen", "decoder_top_p", "prefix_id", "nll", "n_tokens")})
    d = pd.DataFrame(rows); d.to_csv(out / "cross_decoder_per_continuation_nll.csv", index=False, float_format="%.6f")
else:
    d = pd.read_csv(src)
rng = np.random.default_rng(20261022); B = 5000
g = np.arange(1, 7) - 3.5; w = g / (g ** 2).sum()
res = []
for L in ["EN", "BN"]:
    M = {}
    for chain in [f"{L}-REPLACE", f"{L}-REPLACE-topp95"]:
        for dec in [1.0, 0.95]:
            piv = d[(d.chain == chain) & (d.decoder_top_p == dec) & (d.gen.between(1, 6))].pivot_table(index="prefix_id", columns="gen", values="nll")
            assert piv.shape == (50, 6) and not piv.isna().any().any()
            piv = piv.sort_index(); M[(chain, dec)] = piv.values
            idx = list(piv.index); ref = M.setdefault("_ids", idx)
            assert idx == ref, "prefix ids differ between cells; pairing would be invalid"
    ids = d[(d.chain == f"{L}-REPLACE") & (d.gen == 1)].prefix_id.unique()
    n = 50; draws = [rng.integers(0, n, n) for _ in range(B)]          # one prefix resample shared by every cell of the language
    M.pop("_ids")
    for (chain, dec), m in M.items():
        bs = np.array([m[i].mean(0) @ w for i in draws])
        res.append({"language": L, "quantity": f"slope {chain}, eval top-p {dec}", "point": float(m.mean(0) @ w),
                    "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
    for dec in [1.0, 0.95]:
        a, b = M[(f"{L}-REPLACE", dec)], M[(f"{L}-REPLACE-topp95", dec)]
        bs = np.array([(a[i].mean(0) - b[i].mean(0)) @ w for i in draws])
        res.append({"language": L, "quantity": f"training-decoder contrast (top-p 1.0 minus 0.95 trained), eval top-p {dec}",
                    "point": float((a.mean(0) - b.mean(0)) @ w), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
pd.DataFrame(res).to_csv(out / "cross_decoder_slope_ci.csv", index=False, float_format="%.5f")
print(pd.DataFrame(res).round(3).to_string())
