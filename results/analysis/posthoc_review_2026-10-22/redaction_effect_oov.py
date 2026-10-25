"""Post-hoc (2026-10-23): effect of the release redaction on the out-of-vocabulary (OOV) proxy.
Recomputes the token-level OOV share of every 50-sample file from the original and from the redacted copy, against the
language's seed vocabulary (registered word split, lower-cased), and checks the originals against the published shares.
Usage: python redaction_effect_oov.py <original samples dir> <redacted samples dir> <seed corpora dir> <published shares csv> <out_dir>"""
import json, sys, pathlib
import pandas as pd, regex
WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
orig, red, seeds, pub, out = map(pathlib.Path, sys.argv[1:6])
vocab = {}
for L in ("EN", "BN"):
    v = set()
    for line in open(seeds / f"{L}_seed.jsonl", encoding="utf-8"):
        v.update(w.lower() for w in WORD.findall(json.loads(line)["text"]))
    vocab[L] = v
def share(path):
    L = path.name.split("_")[0].replace("GEN0-", "").replace("BASE-", "")[:2]
    n = o = 0
    for line in open(path, encoding="utf-8"):
        for w in WORD.findall(json.loads(line)["text"]):
            n += 1; o += w.lower() not in vocab[L]
    return n, o, o / n
p = pd.read_csv(pub).set_index("file")
rows = []
for f in sorted(orig.glob("*.jsonl")):
    n0, o0, s0 = share(f); n1, o1, s1 = share(red / f.name)
    rows.append({"file": f.name, "published_share": p.loc[f.name, "token_oov_share"], "original_share": s0, "redacted_share": s1,
                 "abs_diff_redacted_vs_original": abs(s1 - s0), "tokens_original": n0, "tokens_redacted": n1})
d = pd.DataFrame(rows); d.to_csv(out / "redaction_effect_oov.csv", index=False, float_format="%.6f")
print("max |original - published|:", round((d.original_share - d.published_share).abs().max(), 6))
print("files changed by redaction:", int((d.abs_diff_redacted_vs_original > 0).sum()), " max |redacted - original|:", round(d.abs_diff_redacted_vs_original.max(), 6))
print(d[d.abs_diff_redacted_vs_original > 0][["file", "original_share", "redacted_share"]].to_string())
