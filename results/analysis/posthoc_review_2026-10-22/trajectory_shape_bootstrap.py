"""Post-hoc (2026-10-22): shape of the held-out log-perplexity trajectory (generations 0..6) per arm, from the released
per-document sidecars: OLS slope, quadratic coefficient, and slopes over generations 0..3 and 3..6, each with a
document-bootstrap 95% CI (the same 2,000 held-out documents are resampled jointly across generations and arms).
Usage: python trajectory_shape_bootstrap.py <sidecar zip> <out_dir>"""
import json, sys, zipfile, pathlib
import numpy as np, pandas as pd
z = zipfile.ZipFile(sys.argv[1]); out = pathlib.Path(sys.argv[2]); ROOT = "cg4_sidecars_bundle/results/chains/"
def load(chain, gen):
    p = ROOT + (f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl")
    rows = [json.loads(l) for l in z.read(p).decode("utf-8").splitlines() if l.strip()]
    return pd.Series({r["doc_id"]: r["nll_total"] / r["n_tokens"] for r in rows if r["set"] == "heldout"}).sort_index()
g = np.arange(7.0)
X1 = np.vstack([np.ones(7), g]).T; X2 = np.vstack([np.ones(7), g, g ** 2]).T
P1 = np.linalg.pinv(X1); P2 = np.linalg.pinv(X2)
Pa = np.linalg.pinv(X1[:4]); Pb = np.linalg.pinv(X1[3:])
def shape(mean_traj):
    return {"ols_slope": (P1 @ mean_traj)[1], "quadratic": (P2 @ mean_traj)[2],
            "slope_g0_3": (Pa @ mean_traj[:4])[1], "slope_g3_6": (Pb @ mean_traj[3:])[1]}
rng = np.random.default_rng(20261022); B = 2000; rows = []
for L in ["EN", "BN"]:
    arms = {"REPLACE": (f"{L}-REPLACE", f"GEN0-{L}"), "REAL-REPEAT": (f"{L}-REAL-REPEAT", f"GEN0-{L}"),
            "ACCUMULATE": (f"{L}-ACCUMULATE", f"GEN0-{L}"), "ACCUMULATE-SUBSAMPLE": (f"{L}-ACCUMULATE-SUBSAMPLE", f"GEN0-{L}")}
    M = {a: pd.DataFrame({0: load(g0, 0), **{k: load(ch, k) for k in range(1, 7)}}).values for a, (ch, g0) in arms.items()}
    n = next(iter(M.values())).shape[0]
    idx = [rng.integers(0, n, n) for _ in range(B)]
    for a, m in M.items():
        pt = shape(m.mean(0) - m.mean(0)[0])
        bs = pd.DataFrame([shape(m[i].mean(0) - m[i].mean(0)[0]) for i in idx])
        for k, v in pt.items():
            rows.append({"language": L, "arm": a, "quantity": k, "point": v, "ci_lo": bs[k].quantile(0.025), "ci_hi": bs[k].quantile(0.975)})
    # difference REPLACE minus REAL-REPEAT in the same draws
    for k in ["ols_slope", "quadratic", "slope_g0_3", "slope_g3_6"]:
        f = lambda i: shape(M["REPLACE"][i].mean(0) - M["REPLACE"][i].mean(0)[0])[k] - shape(M["REAL-REPEAT"][i].mean(0) - M["REAL-REPEAT"][i].mean(0)[0])[k]
        full = np.arange(n); bs = np.array([f(i) for i in idx])
        rows.append({"language": L, "arm": "REPLACE minus REAL-REPEAT", "quantity": k, "point": f(full), "ci_lo": np.percentile(bs, 2.5), "ci_hi": np.percentile(bs, 97.5)})
pd.DataFrame(rows).to_csv(out / "trajectory_shape_bootstrap.csv", index=False, float_format="%.5f")
print(pd.DataFrame(rows).round(4).to_string())
