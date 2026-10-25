#!/usr/bin/env python3
"""Post-hoc (posthoc_gpu_pack2; written 2026-10-24 on the PC): the out-of-seed-vocabulary (OOV) share of Supplementary
Table S6 for the 48 new 50-sample files (EN/BN-REAL-REPEAT-s2/-s3 and EN/BN-REPLACE-topp95-s2/-s3, generations 1 to 6).
Same statistic as results/analysis/posthoc_review_2026-10-22/redaction_effect_oov.py: the share of continuation word tokens
(the registered word split, harness/common.py words(), lower-cased) whose type does not occur in the language's seed corpus
(data/corpora/<L>_seed.jsonl). Check: the same function on the 119 archived 50-sample files of the registered run
(results/samples/ in this package holds the originals; the release holds the redacted copies) against the published
shares (results/analysis/posthoc_review_2026-10-19/nonword_oov_shares.csv, 5 decimals). Reads the restricted text in
memory; writes numbers only.
usage: python -B oov_new_chains.py <package root> <out dir> [--cache <dir outside the package>]
"""
import argparse, json, pickle, sys
from pathlib import Path

import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("pkg"); ap.add_argument("out"); ap.add_argument("--cache")
a = ap.parse_args()
PKG, OUT = Path(a.pkg), Path(a.out)
sys.path.insert(0, str(PKG / "harness"))
from common import words  # noqa: E402

cache = Path(a.cache) / "seed_vocab.pkl" if a.cache else None
if cache and cache.exists():
    vocab = pickle.loads(cache.read_bytes())
else:
    vocab = {}
    for L in ("EN", "BN"):
        v = set()
        with open(PKG / "data" / "corpora" / f"{L}_seed.jsonl", encoding="utf-8") as f:
            for line in f:
                v.update(w.lower() for w in words(json.loads(line)["text"]))
        vocab[L] = v
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True); cache.write_bytes(pickle.dumps(vocab))


def share(path, L):
    n = o = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            for w in words(json.loads(line)["text"]):
                n += 1; o += w.lower() not in vocab[L]
    return n, o


rows = []
for p in sorted((PKG / "results" / "posthoc_seeds_2026-10-23" / "host" / "results" / "samples").glob("*_50.jsonl")):
    chain, gen = p.name.rsplit("_gen", 1)[0], int(p.name.rsplit("_gen", 1)[1].split("_")[0])
    n, o = share(p, chain[:2])
    rows.append(dict(file=p.name, chain=chain, generation=gen, n_tokens=n, oov_tokens=o, token_oov_share=o / n))
OUT.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows).to_csv(OUT / "oov_share_new_chains.csv", index=False, float_format="%.10f")
pub = pd.read_csv(PKG / "results" / "analysis" / "posthoc_review_2026-10-19" / "nonword_oov_shares.csv").set_index("file")
chk = []
for p in sorted((PKG / "results" / "samples").glob("*_50.jsonl")):
    L = p.name.split("_")[0].replace("GEN0-", "").replace("BASE-", "")[:2]
    n, o = share(p, L)
    chk.append(dict(file=p.name, recomputed_share=o / n, published_share=pub.loc[p.name, "token_oov_share"]))
c = pd.DataFrame(chk); c["abs_diff"] = (c.recomputed_share - c.published_share).abs()
(OUT / "validation").mkdir(parents=True, exist_ok=True)
c.to_csv(OUT / "validation" / "oov_share_recomputed_vs_published.csv", index=False, float_format="%.10f")
print(f"new files {len(rows)}; registered files checked {len(c)}: max |recomputed - published| {c.abs_diff.max():.6f}, "
      f"files above 0.00001: {int((c.abs_diff > 1e-5).sum())}")
