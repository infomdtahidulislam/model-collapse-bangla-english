"""Post-hoc (2026-10-22): document-bootstrap CIs for the per-document slope correlations of
perdoc_heldout_slopes.py, and per-domain mean slopes. Usage: python perdoc_bootstrap_domains.py <sidecar zip> <out_dir>"""
import json, sys, zipfile, pathlib
import numpy as np, pandas as pd
z = zipfile.ZipFile(sys.argv[1]); out = pathlib.Path(sys.argv[2]); ROOT = "cg4_sidecars_bundle/results/chains/"
def load(chain, gen):
    p = ROOT + (f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl")
    rows = [json.loads(l) for l in z.read(p).decode("utf-8").splitlines() if l.strip()]
    return pd.Series({r["doc_id"]: r["nll_total"] / r["n_tokens"] for r in rows if r["set"] == "heldout"}).sort_index()
def slope(chain, gen0):
    df = pd.DataFrame({0: load(gen0, 0), **{g: load(chain, g) for g in range(1, 7)}})
    gc = np.arange(7) - 3.0
    return pd.Series((df.values * gc).sum(1) / (gc ** 2).sum(), index=df.index)
rng = np.random.default_rng(20261022); B = 2000
rows, dom = [], []
for L in ["EN", "BN"]:
    s = {"REPLACE": slope(f"{L}-REPLACE", f"GEN0-{L}"), "REPLACE-s2": slope(f"{L}-REPLACE-s2", f"GEN0-{L}-s2"),
         "REAL-REPEAT": slope(f"{L}-REAL-REPEAT", f"GEN0-{L}"), "ACCUMULATE": slope(f"{L}-ACCUMULATE", f"GEN0-{L}")}
    idx = s["REPLACE"].index
    for other in ["REPLACE-s2", "REAL-REPEAT", "ACCUMULATE"]:
        a = s["REPLACE"][idx].values; b = s[other][idx].values; n = len(a)
        bs = []
        for _ in range(B):
            i = rng.integers(0, n, n); bs.append(np.corrcoef(a[i], b[i])[0, 1])
        rows.append({"language": L, "comparison": f"REPLACE vs {other}", "pearson": np.corrcoef(a, b)[0, 1],
                     "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5), "draws": B})
    domain = pd.Series(np.where(idx.str.contains("wiki_articles"), "wikipedia", "web"), index=idx)
    for arm, v in s.items():
        for d, g in v.groupby(domain):
            dom.append({"language": L, "arm": arm, "domain": d, "n_docs": len(g), "mean_slope": g.mean()})
pd.DataFrame(rows).to_csv(out / "perdoc_slope_correlations_bootstrap.csv", index=False, float_format="%.6g")
pd.DataFrame(dom).to_csv(out / "perdoc_slopes_by_domain.csv", index=False, float_format="%.6g")
print(pd.DataFrame(rows).round(3).to_string()); print(pd.DataFrame(dom).round(4).to_string())
