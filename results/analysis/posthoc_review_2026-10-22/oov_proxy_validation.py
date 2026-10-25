"""Post-hoc (2026-10-22): length-normalized and within-file checks of the out-of-seed-vocabulary (OOV) proxy
against the authors' nonword counts (600 human-read samples). Input: posthoc_review_2026-10-19/nonword_human_join.csv.
Usage: python oov_proxy_validation.py <nonword_human_join.csv> <out_dir>"""
import sys, pathlib
import numpy as np, pandas as pd
d = pd.read_csv(sys.argv[1]); out = pathlib.Path(sys.argv[2])
d["nonword_share"] = d.human_nonwords / d.n_tokens
pe = lambda a, b: float(np.corrcoef(np.asarray(a, float), np.asarray(b, float))[0, 1])
sp = lambda a, b: pe(pd.Series(a).rank(), pd.Series(b).rank())
def within(g, a, b):
    ra = g.groupby("file")[a].rank(); rb = g.groupby("file")[b].rank()
    return pe(ra - ra.groupby(g.file).transform("mean"), rb - rb.groupby(g.file).transform("mean"))
rows = []
for L, g in [("ALL", d)] + list(d.groupby("language")):
    rows.append({"scope": L, "check": "per-sample counts (as published)", "spearman": sp(g.oov_tokens, g.human_nonwords), "pearson": pe(g.oov_tokens, g.human_nonwords), "n": len(g)})
    rows.append({"scope": L, "check": "per-sample shares (length-normalized)", "spearman": sp(g.oov_share, g.nonword_share), "pearson": pe(g.oov_share, g.nonword_share), "n": len(g)})
    rows.append({"scope": L, "check": "within-file ranks of shares (file held fixed)", "spearman": within(g, "oov_share", "nonword_share"), "pearson": np.nan, "n": len(g)})
per_file = {f: sp(g.oov_share, g.nonword_share) for f, g in d.groupby("file")}
for f, r in per_file.items():
    rows.append({"scope": f, "check": "per-file Spearman of shares", "spearman": r, "pearson": np.nan, "n": 50})
fl = d.groupby(["file", "language"]).agg(nw=("human_nonwords", "sum"), oov=("oov_tokens", "sum"), tok=("n_tokens", "sum")).reset_index()
fl["nonword_share"] = fl.nw / fl.tok; fl["oov_share"] = fl.oov / fl.tok
for L, g in fl.groupby("language"):
    rows.append({"scope": L, "check": "file-level shares (6 files)", "spearman": sp(g.oov_share, g.nonword_share), "pearson": pe(g.oov_share, g.nonword_share), "n": len(g)})
pd.DataFrame(rows).to_csv(out / "oov_proxy_validation.csv", index=False, float_format="%.4f")
fl.to_csv(out / "oov_proxy_file_level.csv", index=False, float_format="%.5f")
print(pd.DataFrame(rows).round(3).to_string()); print("median per-file:", round(float(np.median(list(per_file.values()))), 3), "range", round(min(per_file.values()), 3), round(max(per_file.values()), 3))
