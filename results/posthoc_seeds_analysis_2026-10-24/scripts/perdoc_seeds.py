"""Post-hoc (posthoc_gpu_pack2; written 2026-10-23): per-document held-out loss slopes (generations 0..6) for REPLACE-sK and
REAL-REPEAT-sK in each language and seed k in {0, 2, 3}: Pearson correlation of the per-document slopes between the two
arms of a seed (with a document-bootstrap 95% CI, 2,000 draws, default_rng(20261022)), the share of documents whose loss
rose, and the mean slopes. Same statistic as ../posthoc_review_2026-10-22/perdoc_heldout_slopes.py (per-token NLL of each
regular held-out document from heldout_nll.jsonl); seed 0 reproduces its values (EN 0.472, BN -0.097).
Sources: the registered sidecar bundle (zip) and, for the post-hoc chains, the take-home folder of posthoc_gpu_pack2.
usage: python perdoc_seeds.py <sidecar zip> <posthoc chains root or "none"> <out_dir>

Changed 2026-10-24 (PC), the only change to the copy in results/analysis/posthoc_seeds_2026-10-23/: the CSV carries 10
decimals instead of 5, so that values rounded for the report are rounded once."""
import json, sys, zipfile
from pathlib import Path
import numpy as np, pandas as pd

zpath, proot, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
z = zipfile.ZipFile(zpath); ZR = "cg4_sidecars_bundle/results/chains/"
PR = None if proot == "none" else Path(proot)


def read(chain, gen):
    rel = f"{chain}/heldout_nll.jsonl" if chain.startswith("GEN0") else f"{chain}/gen_{gen}/heldout_nll.jsonl"
    try:
        txt = z.read(ZR + rel).decode("utf-8")
    except KeyError:
        if PR is None or not (PR / rel).exists():
            return None
        txt = (PR / rel).read_text(encoding="utf-8")
    rows = [json.loads(l) for l in txt.splitlines() if l.strip()]
    return pd.Series({r["doc_id"]: r["nll_total"] / r["n_tokens"] for r in rows if r["set"] == "heldout"}).sort_index()


def slopes(chain, gen0):
    cols = {0: read(gen0, 0)}
    for g in range(1, 7):
        cols[g] = read(chain, g)
    if any(v is None for v in cols.values()):
        return None
    df = pd.DataFrame(cols); gg = np.arange(7, dtype=float); gc = gg - gg.mean()
    return pd.Series((df.values * gc).sum(1) / (gc ** 2).sum(), index=df.index)


rng = np.random.default_rng(20261022); rows = []
for L in ("EN", "BN"):
    for seed, suf in (("0", ""), ("2", "-s2"), ("3", "-s3")):
        g0 = f"GEN0-{L}{suf}"
        a, b = slopes(f"{L}-REPLACE{suf}", g0), slopes(f"{L}-REAL-REPEAT{suf}", g0)
        if a is None or b is None:
            rows.append({"language": L, "seed": seed, "note": "missing"}); continue
        idx = a.index.intersection(b.index); a, b = a[idx].values, b[idx].values; n = len(idx)
        r = float(np.corrcoef(a, b)[0, 1])
        bs = np.array([np.corrcoef(a[i], b[i])[0, 1] for i in (rng.integers(0, n, n) for _ in range(2000))])
        rows.append({"language": L, "seed": seed, "n_docs": n, "pearson_REPLACE_vs_REAL_REPEAT": r,
                     "ci_lo": float(np.percentile(bs, 2.5)), "ci_hi": float(np.percentile(bs, 97.5)),
                     "share_rising_REPLACE": float((a > 0).mean()), "share_rising_REAL_REPEAT": float((b > 0).mean()),
                     "mean_slope_REPLACE": float(a.mean()), "mean_slope_REAL_REPEAT": float(b.mean())})
res = pd.DataFrame(rows); res.to_csv(out / "perdoc_seeds.csv", index=False, float_format="%.10f")
print(res.round(3).to_string())
