"""Post-hoc (2026-10-22): prefix-paired, length-controlled distinct-2 sensitivity check.
For every step, each continuation is cut to its first K words (registered word split, lower-cased); bigrams are counted
within documents only (none across document boundaries); distinct-2 = unique bigrams / all bigrams over the window of
selected documents. Every step uses the same prefix ids, so the window holds the same prompts at every step. Intervals:
m-out-of-n subsampling of prefix ids WITHOUT replacement (avoids the duplicate-document bias of a with-replacement
bootstrap), drawn jointly for all steps. Works on the released 50-sample files or on the full 2,000-document samples.
Usage: python prefix_paired_diversity.py <samples_dir> <out_dir> [K=100] [m_frac=0.8] [draws=2000]"""
import json, sys, pathlib, re
import numpy as np, pandas as pd, regex
WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
sd, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
K = int(sys.argv[3]) if len(sys.argv) > 3 else 100
m_frac = float(sys.argv[4]) if len(sys.argv) > 4 else 0.8
B = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
def gen0_of(chain):
    L = chain[:2]
    if chain.endswith("-s2"): return f"GEN0-{L}-s2"
    if chain.endswith("-s3"): return f"GEN0-{L}-s3"
    if chain.endswith("-WM"): return f"GEN0-{L}-WM"
    return f"GEN0-{L}"
def load(path):
    docs = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        w = [x.lower() for x in WORD.findall(r["text"])][:K]
        docs[r["prefix_id"]] = list(zip(w, w[1:]))
    return docs
chains = ["EN-REPLACE", "EN-REPLACE-s2", "EN-REPLACE-s3", "EN-ACCUMULATE", "EN-ACCUMULATE-FILTER", "EN-ACCUMULATE-SUBSAMPLE",
          "EN-REAL-REPEAT", "EN-REPLACE-WM", "EN-REPLACE-topp95", "BN-REPLACE", "BN-REPLACE-s2", "BN-REPLACE-s3", "BN-ACCUMULATE",
          "BN-ACCUMULATE-FILTER", "BN-ACCUMULATE-SUBSAMPLE", "BN-REAL-REPEAT", "BN-REPLACE-topp95"]
steps = {}
for ch in chains:
    for g in range(0, 7):
        f = sd / (f"{gen0_of(ch)}_gen0_50.jsonl" if g == 0 else f"{ch}_gen{g}_50.jsonl")
        if not f.exists():
            f2 = sd / (f"{gen0_of(ch)}_gen0.jsonl" if g == 0 else f"{ch}_gen{g}.jsonl")
            f = f2 if f2.exists() else None
        if f is None: raise SystemExit(f"missing file for {ch} gen {g}")
        steps[(ch, g)] = load(f)
IDS = {}
for (ch, k), v in steps.items():
    IDS.setdefault(ch[:2], sorted(v.keys()))
    assert sorted(v.keys()) == IDS[ch[:2]], f"prefix ids differ between steps ({ch} gen {k})"
assert len(IDS["EN"]) == len(IDS["BN"])
ids = IDS["EN"]
def d2(step, sel):
    lid = IDS[step[0][:2]]
    grams = [b for i in sel for b in steps[step][lid[i]]]
    return len(set(grams)) / max(1, len(grams))
g = np.arange(7.0); gc = g - g.mean(); w06 = gc / (gc ** 2).sum()
g16 = np.arange(1, 7.0); c16 = g16 - g16.mean(); w16 = c16 / (c16 ** 2).sum()
def summarize(sel):
    out = {}
    for ch in chains:
        v = np.array([d2((ch, k), sel) for k in range(7)])
        out[(ch, "log_ratio_slope_0_6")] = float(np.log(v / v[0]) @ w06)
        out[(ch, "raw_slope_1_6")] = float(v[1:] @ w16)
        out[(ch, "d2_gen0")] = float(v[0]); out[(ch, "d2_gen6")] = float(v[6])
    return out
n = len(ids); m = int(round(m_frac * n)); rng = np.random.default_rng(20261022)
point = summarize(range(n))
draws = [summarize(rng.choice(n, m, replace=False)) for _ in range(B)]
rows = []
for key, val in point.items():
    arr = np.array([d[key] for d in draws])
    rows.append({"chain": key[0], "quantity": key[1], "point": val, "ci_lo": np.percentile(arr, 2.5), "ci_hi": np.percentile(arr, 97.5),
                 "share_draws_positive": float((arr > 0).mean())})
short = {f"{ch}_gen{k}": sum(1 for p in IDS[ch[:2]] if len(steps[(ch, k)][p]) + 1 < K) for ch in chains for k in range(7)}
res = pd.DataFrame(rows)
res.attrs["meta"] = dict(K=K, n_prefixes=n, m=m, draws=B)
out.mkdir(parents=True, exist_ok=True)
res.to_csv(out / f"prefix_paired_diversity_K{K}_n{n}.csv", index=False, float_format="%.5f")
pd.Series(short).to_csv(out / f"prefix_paired_diversity_short_docs_K{K}_n{n}.csv", header=["docs_shorter_than_K"])
print(f"K={K} n={n} m={m} B={B}")
print(res[res.quantity.isin(["log_ratio_slope_0_6", "raw_slope_1_6"])].round(4).to_string())
