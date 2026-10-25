"""Post-hoc (2026-10-22): per-document held-out loss trajectories.
Reads the released per-item sidecars (heldout_nll.jsonl) and compares, document by document,
how held-out NLL per token changes across generations 0..6 in different arms.
Descriptive only; no registered quantity, test or verdict is changed.
Usage: python perdoc_heldout_slopes.py <sidecar zip> <T1_metrics.csv> <out_dir>"""
import json, sys, zipfile, pathlib
import numpy as np, pandas as pd

zpath, t1path, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
z = zipfile.ZipFile(zpath)
ROOT = "cg4_sidecars_bundle/results/chains/"

def load(chain, gen):
    p = ROOT + (f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl")
    rows = [json.loads(l) for l in z.read(p).decode("utf-8").splitlines() if l.strip()]
    s = pd.Series({r["doc_id"]: r["nll_total"] / r["n_tokens"] for r in rows if r["set"] == "heldout"})
    return s.sort_index()

def traj(chain, gen0):
    cols = {0: load(gen0, 0)}
    for g in range(1, 7):
        cols[g] = load(chain, g)
    return pd.DataFrame(cols)

def slopes(df):
    g = np.arange(7, dtype=float); gc = g - g.mean()
    return pd.Series((df.values * gc).sum(1) / (gc ** 2).sum(), index=df.index)

def rank_corr(a, b):
    return float(np.corrcoef(a.rank(), b.rank())[0, 1])

t1 = pd.read_csv(t1path)
arms = {"EN": [("REPLACE", "EN-REPLACE", "GEN0-EN"), ("REPLACE-s2", "EN-REPLACE-s2", "GEN0-EN-s2"),
               ("REPLACE-s3", "EN-REPLACE-s3", "GEN0-EN-s3"), ("REAL-REPEAT", "EN-REAL-REPEAT", "GEN0-EN"),
               ("ACCUMULATE", "EN-ACCUMULATE", "GEN0-EN"), ("ACCUMULATE-SUBSAMPLE", "EN-ACCUMULATE-SUBSAMPLE", "GEN0-EN")],
        "BN": [("REPLACE", "BN-REPLACE", "GEN0-BN"), ("REPLACE-s2", "BN-REPLACE-s2", "GEN0-BN-s2"),
               ("REPLACE-s3", "BN-REPLACE-s3", "GEN0-BN-s3"), ("REAL-REPEAT", "BN-REAL-REPEAT", "GEN0-BN"),
               ("ACCUMULATE", "BN-ACCUMULATE", "GEN0-BN"), ("ACCUMULATE-SUBSAMPLE", "BN-ACCUMULATE-SUBSAMPLE", "GEN0-BN")]}
rows_out, check = [], []
for L, lst in arms.items():
    S, T = {}, {}
    for name, chain, gen0 in lst:
        df = traj(chain, gen0); T[name] = df; S[name] = slopes(df)
        for g in range(7):  # reproduction check against the registered document-macro means
            reg = t1[(t1.chain_id == chain) & (t1.generation == g) & (t1.metric == "log_ppl_heldout")].value
            if len(reg):
                check.append({"language": L, "arm": name, "generation": g, "recomputed": df[g].mean(), "registered": float(reg.iloc[0]),
                              "abs_diff": abs(df[g].mean() - float(reg.iloc[0]))})
    base = "REPLACE"
    for other in [k for k in S if k != base]:
        a, b = S[base], S[other]; idx = a.index.intersection(b.index)
        a, b = a[idx], b[idx]
        d6a = (T[base][6] - T[base][0])[idx]; d6b = (T[other][6] - T[other][0])[idx]
        rows_out.append({"language": L, "comparison": f"{base} vs {other}", "n_docs": len(idx),
                         "mean_slope_REPLACE": a.mean(), "mean_slope_other": b.mean(),
                         "pearson_slopes": float(np.corrcoef(a, b)[0, 1]), "spearman_slopes": rank_corr(a, b),
                         "pearson_change_0_to_6": float(np.corrcoef(d6a, d6b)[0, 1]),
                         "sd_slope_difference": float((a - b).std(ddof=1)),
                         "share_docs_REPLACE_slope_higher": float((a > b).mean())})
    for name, s in S.items():
        rows_out.append({"language": L, "comparison": f"{name} alone", "n_docs": len(s), "mean_slope_REPLACE": np.nan,
                         "mean_slope_other": s.mean(), "share_docs_rising": float((s > 0).mean()),
                         "sd_slope": float(s.std(ddof=1))})
out.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows_out).to_csv(out / "perdoc_heldout_slopes.csv", index=False, float_format="%.6g")
pd.DataFrame(check).to_csv(out / "perdoc_reproduction_check.csv", index=False, float_format="%.9g")
print(pd.DataFrame(rows_out).round(4).to_string())
print("max abs diff vs registered:", pd.DataFrame(check).abs_diff.max(), "rows", len(check))
