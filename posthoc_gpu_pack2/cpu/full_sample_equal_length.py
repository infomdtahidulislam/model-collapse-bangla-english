#!/usr/bin/env python3
"""CG4 post-hoc (posthoc_gpu_pack2, 2026-10-23): prefix-paired, equal-length distinct-2 on the FULL 2,000-document samples.

The same statistic as results/analysis/posthoc_review_2026-10-22/prefix_paired_diversity_equal.py (Supplementary
Section S14), run on every step's archived 2,000-document fixed-prefix sample instead of the released 50-document files:
for each chain and prefix, L_p = min(K, the shortest continuation that prefix received at any of the chain's compared
steps); at every step the prefix contributes exactly its first L_p words (registered word split, lower-cased); bigrams are
counted within documents only; distinct-2 = unique bigrams / all bigrams over the prefixes used. Compared steps: generations
0 to 6 (generation 0 = the chain's own generation-0 model) with the log ratio to generation 0; for the top-p 0.95 chains
generations 1 to 6 with raw values (no generation-0 sample exists under that decoder).
Stability ranges: the 2.5th and 97.5th percentiles of the slope over B random subsets of m of the n prefixes, drawn
without replacement with NumPy default_rng(seed) and shared by all steps and chains of a language (EN drawn first). They
describe the stability of this statistic, not confidence intervals for it or for the registered statistic.

Reads only numbers and words in memory; writes numbers only (no text). The sample files hold unscreened model output:
run it where the archive extraction lives (the VPS) and keep the inputs private.

Validation mode: with --n 50 --m 40 --B 2000 --seed 20261023 on a tree built from the released 50-document files it
reproduces Supplementary Table S12 exactly (see README_RUN.md).

usage: python full_sample_equal_length.py --roots ROOT [ROOT ...] --out DIR [--K 100] [--n 2000] [--m 1600] [--B 500]
                                          [--seed 20261024] [--chains ...]
  ROOT: folders holding results/chains/<chain>/gen_<g>/sample.jsonl and results/chains/<GEN0-...>/sample.jsonl
        (e.g. results/g6_extract and the post-hoc host results); the first root holding a step wins.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import regex

WORD = regex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")        # harness/common.py words()
REGISTERED = ["EN-REPLACE", "EN-REPLACE-s2", "EN-REPLACE-s3", "EN-ACCUMULATE", "EN-ACCUMULATE-FILTER", "EN-ACCUMULATE-SUBSAMPLE",
              "EN-REAL-REPEAT", "EN-REPLACE-WM", "EN-REPLACE-topp95", "BN-REPLACE", "BN-REPLACE-s2", "BN-REPLACE-s3", "BN-ACCUMULATE",
              "BN-ACCUMULATE-FILTER", "BN-ACCUMULATE-SUBSAMPLE", "BN-REAL-REPEAT", "BN-REPLACE-topp95"]
POSTHOC = ["EN-REAL-REPEAT-s2", "EN-REAL-REPEAT-s3", "EN-REPLACE-topp95-s2", "EN-REPLACE-topp95-s3",
           "BN-REAL-REPEAT-s2", "BN-REAL-REPEAT-s3", "BN-REPLACE-topp95-s2", "BN-REPLACE-topp95-s3"]

ap = argparse.ArgumentParser()
ap.add_argument("--roots", nargs="+", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--K", type=int, default=100)
ap.add_argument("--n", type=int, default=2000, help="prefixes per step (2,000 = the full fixed-prefix sample)")
ap.add_argument("--m", type=int, default=1600, help="prefixes per stability subset")
ap.add_argument("--B", type=int, default=500, help="stability subsets")
ap.add_argument("--seed", type=int, default=20261024)
ap.add_argument("--chains", nargs="*", default=REGISTERED + POSTHOC)
ap.add_argument("--allow-missing", action="store_true", help="skip chains whose files are absent (reported) instead of failing")
a = ap.parse_args()
roots = [Path(r) for r in a.roots]
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)


def find(rel: str) -> Path | None:
    for r in roots:
        p = r / rel
        if p.exists():
            return p
    return None


def gen0_of(chain: str) -> str:
    p = find(f"results/chains/{chain}/gen_1/step.json")
    if p is not None:
        g0 = json.load(open(p, encoding="utf-8")).get("gen0_id")
        if g0:
            return g0
    L = chain[:2]
    for suf in ("-s2", "-s3", "-WM"):
        if chain.endswith(suf):
            return f"GEN0-{L}{suf}"
    return f"GEN0-{L}"


def step_file(chain: str, g: int) -> Path | None:
    return find(f"results/chains/{gen0_of(chain)}/sample.jsonl" if g == 0 else f"results/chains/{chain}/gen_{g}/sample.jsonl")


def read_words(path: Path) -> dict:
    W = {}
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= a.n:
                break
            d = json.loads(line)
            W[d["prefix_id"]] = [w.lower() for w in WORD.findall(d["text"])]
    if len(W) != a.n:
        sys.exit(f"{path}: {len(W)} distinct prefixes in the first {a.n} rows, expected {a.n}")
    return W


rng = np.random.default_rng(a.seed)
subsets = {L: [rng.choice(a.n, a.m, replace=False) for _ in range(a.B)] for L in ("EN", "BN")}
masks = {L: np.zeros((a.B, a.n), bool) for L in subsets}
for L, subs in subsets.items():
    for b, s in enumerate(subs):
        masks[L][b, s] = True
lang_ids: dict[str, list] = {}
rows, per_step, skipped = [], [], []
for ch in a.chains:
    topp = "topp95" in ch
    gens = list(range(1, 7)) if topp else list(range(0, 7))
    files = {g: step_file(ch, g) for g in gens}
    if any(v is None for v in files.values()):
        miss = [g for g, v in files.items() if v is None]
        if a.allow_missing:
            skipped.append(f"{ch}: missing generations {miss}"); print(f"skip {ch}: missing generations {miss}", flush=True); continue
        sys.exit(f"{ch}: missing sample.jsonl for generations {miss} under {a.roots}")
    W = {g: read_words(files[g]) for g in gens}
    ids = sorted(W[gens[0]])
    if not all(sorted(W[g]) == ids for g in gens):
        sys.exit(f"{ch}: the steps do not hold the same prefixes")
    L = ch[:2]
    if L in lang_ids and lang_ids[L] != ids:
        sys.exit(f"{ch}: prefix ids differ from the other {L} chains, so the shared subsets would not be paired")
    lang_ids.setdefault(L, ids)
    Lp = np.array([min(a.K, min(len(W[g][p]) for g in gens)) for p in ids])
    code: dict = {}
    flat, nb = {}, {}
    for g in gens:
        seqs, lens = [], []
        for p, k in zip(ids, Lp):
            w = W[g][p][:k]
            bg = [code.setdefault(t, len(code)) for t in zip(w[:-1], w[1:])]
            seqs.extend(bg); lens.append(len(bg))
        flat[g] = np.asarray(seqs, dtype=np.int64); nb[g] = np.asarray(lens, dtype=np.int64)
    V = len(code)

    def d2(g: int, docmask: np.ndarray | None) -> float:
        ids_g = flat[g] if docmask is None else flat[g][np.repeat(docmask, nb[g])]
        if ids_g.size == 0:
            return float("nan")
        present = np.zeros(V, bool); present[ids_g] = True
        return float(present.sum()) / float(ids_g.size)

    x = np.array(gens, float); xc = x - x.mean(); wts = xc / (xc ** 2).sum()

    def slope(docmask: np.ndarray | None) -> float:
        v = np.array([d2(g, docmask) for g in gens])
        return float((np.log(v / v[0]) if gens[0] == 0 else v) @ wts)

    full = {g: d2(g, None) for g in gens}
    pt = slope(None)
    bs = np.array([slope(masks[L][b]) for b in range(a.B)])
    rows.append({"chain": ch, "quantity": "raw_slope_1_6" if topp else "log_ratio_slope_0_6", "point": pt,
                 "range_lo": float(np.percentile(bs, 2.5)), "range_hi": float(np.percentile(bs, 97.5)),
                 "n_prefixes": len(ids), "words_per_step": int(Lp.sum()), "prefixes_at_full_K": int((Lp == a.K).sum()),
                 "median_words_per_prefix": float(np.median(Lp)), "gen0": gen0_of(ch) if not topp else ""})
    for g in gens:
        per_step.append({"chain": ch, "generation": g, "distinct2_equal_length": full[g], "bigrams": int(flat[g].size)})
    print(f"{ch:24s} {rows[-1]['quantity']:20s} {pt:+.5f} [{rows[-1]['range_lo']:+.5f}, {rows[-1]['range_hi']:+.5f}] "
          f"words/step {rows[-1]['words_per_step']}", flush=True)

tag = f"K{a.K}_n{a.n}_m{a.m}_B{a.B}_seed{a.seed}"
for name, data in ((f"full_sample_equal_length_{tag}.csv", rows), (f"full_sample_equal_length_steps_{tag}.csv", per_step)):
    if data:
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys())); w.writeheader()
            for r in data:
                w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in r.items()})
if skipped:
    (out / f"full_sample_equal_length_skipped_{tag}.txt").write_text("\n".join(skipped) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} chains to {out}", flush=True)
