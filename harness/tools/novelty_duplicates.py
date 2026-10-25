#!/usr/bin/env python
"""Robustness (viii) and the exploratory n-gram novelty, as fixed by the authors in REQ-027 (2026-10-18; 07_ANALYSIS_PLAN.md §5),
for each of the 98 synthetic training corpora (the generated continuations of the 86 non-FILTER steps; the kept documents of the
12 ACCUMULATE-FILTER steps; REAL-REPEAT steps have no synthetic text):

- novelty_n (n = 1..4): share of the corpus's word n-gram occurrences (lower-cased, the registered word split `common.words`,
  n-grams within a document) whose n-gram never occurs in the language's seed corpus. N-grams are compared through stable 64-bit
  hashes (blake2b of each word, combined in order); a false match needs a 64-bit collision.
- near-duplicate rate: share of documents that the pipeline's own near-duplicate test finds in the seed: `common.minhash` over word
  3-grams of the first 400 words (64 permutations), `common.NearDupIndex` (8 bands, estimated Jaccard >= 0.80) loaded with the stored
  seed signatures only (`data/corpora/<L>_seed_minhash.npy`, checked against the seed file first), queried with `is_dup` (nothing added).
- exact-duplicate rate: share of documents whose first 400 words (lower-cased) equal those of a seed document.

Inputs: results/g6_extract/ (the G4b archive, SHA-256 checked). Writes results/novelty_duplicates.jsonl and a cache of seed n-gram
hashes in results/g6_extract/cache/. usage: python harness/tools/novelty_duplicates.py [--workers 4] [--only GLOB]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CORPORA, RESULTS, NearDupIndex, load_chains_cfg, log_decision, minhash, now_iso, read_jsonl, utf8_stdout, words  # noqa: E402

utf8_stdout()
EXT = RESULTS / "g6_extract"
ROOT = EXT / "results" / "chains"
SEED = EXT / "data" / "corpora"
CACHE = EXT / "cache"
K = np.uint64(0x9E3779B97F4A7C15)
_W: dict[str, int] = {}
_STATE: dict[str, dict] = {}


def whash(w: str) -> int:
    h = _W.get(w)
    if h is None:
        h = _W[w] = int.from_bytes(hashlib.blake2b(w.encode("utf-8"), digest_size=8).digest(), "little")
    return h


def ngram_codes(ws: list[str], n: int) -> np.ndarray:
    if len(ws) < n:
        return np.zeros(0, dtype=np.uint64)
    h = np.array([whash(w) for w in ws], dtype=np.uint64)
    code = h[: len(h) - n + 1].copy()
    with np.errstate(over="ignore"):
        for j in range(1, n):
            code = code * K + h[j: len(h) - n + 1 + j]
    return code


def seed_tables(lang: str) -> None:
    """Seed n-gram hash tables (sorted unique uint64 per n), cached as .npy."""
    CACHE.mkdir(parents=True, exist_ok=True)
    if all((CACHE / f"{lang}_seed_ngram{n}.npy").exists() for n in (1, 2, 3, 4)):
        return
    acc = {n: [] for n in (1, 2, 3, 4)}
    for d in read_jsonl(SEED / f"{lang}_seed.jsonl"):
        ws = [w.lower() for w in words(d["text"])]
        for n in acc:
            acc[n].append(ngram_codes(ws, n))
    for n, parts in acc.items():
        np.save(CACHE / f"{lang}_seed_ngram{n}.npy", np.unique(np.concatenate(parts)))


def state(lang: str) -> dict:
    if lang not in _STATE:
        sigs = np.load(CORPORA / f"{lang}_seed_minhash.npy")
        index = NearDupIndex(perms=sigs.shape[1], threshold=float(load_chains_cfg()["filter"]["near_dup_jaccard"]))
        for s in sigs:
            index.add(s)
        exact = {" ".join(w.lower() for w in words(d["text"])[:400]) for d in read_jsonl(SEED / f"{lang}_seed.jsonl")}
        _STATE[lang] = {"index": index, "exact": exact, "ngrams": {n: np.load(CACHE / f"{lang}_seed_ngram{n}.npy") for n in (1, 2, 3, 4)}}
    return _STATE[lang]


def check_seed_signatures(lang: str, k: int = 200) -> str:
    sigs = np.load(CORPORA / f"{lang}_seed_minhash.npy")
    docs = list(read_jsonl(SEED / f"{lang}_seed.jsonl"))
    if len(docs) != len(sigs):
        raise SystemExit(f"{lang}: {len(sigs)} stored seed signatures for {len(docs)} seed documents; stop")
    idx = random.Random(20261018).sample(range(len(docs)), min(k, len(docs)))
    bad = sum(1 for i in idx if not np.array_equal(minhash(words(docs[i]["text"])[:400], sigs.shape[1]), sigs[i]))
    if bad:
        raise SystemExit(f"{lang}: {bad} of {len(idx)} recomputed seed signatures differ from the stored ones; stop")
    return f"{lang}: {len(sigs)} stored signatures = seed documents; {len(idx)} recomputed, all identical"


def corpora() -> list[tuple[str, int, Path]]:
    out = []
    for d in sorted(ROOT.glob("*/gen_*")):
        chain, g = d.parts[-2], int(d.name.split("_")[1])
        f = d / ("synthetic_kept.jsonl" if chain.endswith("ACCUMULATE-FILTER") else "synthetic.jsonl")
        if f.exists():
            out.append((chain, g, f))
    return out


def not_in_sorted(c: np.ndarray, table: np.ndarray) -> int:
    """How many entries of c are absent from the sorted unique table (binary search, no re-sorting of the table)."""
    if not len(c):
        return 0
    i = np.searchsorted(table, c)
    found = (i < len(table)) & (table[np.minimum(i, len(table) - 1)] == c)
    return int((~found).sum())


def one(job) -> dict:
    chain, g, path = job
    lang = chain[:2]
    st = state(lang)
    codes = {n: [] for n in (1, 2, 3, 4)}
    n_docs = n_words = near = exact = 0
    for d in read_jsonl(Path(path)):
        ws_raw = words(d["text"])
        ws = [w.lower() for w in ws_raw]
        n_docs += 1
        n_words += len(ws)
        for n in (1, 2, 3, 4):
            codes[n].append(ngram_codes(ws, n))
        near += st["index"].is_dup(minhash(ws_raw[:400], 64))
        exact += " ".join(ws[:400]) in st["exact"]
    occ, new = {}, {}
    for n in (1, 2, 3, 4):
        c = np.concatenate(codes[n]) if codes[n] else np.zeros(0, dtype=np.uint64)
        occ[n], new[n] = len(c), not_in_sorted(c, st["ngrams"][n])
    return {"chain_id": chain, "generation": g, "corpus_file": Path(path).name, "docs": n_docs, "words": n_words,
            **{f"novelty_{n}": new[n] / max(1, occ[n]) for n in (1, 2, 3, 4)}, **{f"ngram_occurrences_{n}": occ[n] for n in (1, 2, 3, 4)},
            "near_dup_docs": near, "near_dup_rate": near / max(1, n_docs), "exact_dup_docs": exact, "exact_dup_rate": exact / max(1, n_docs),
            "corpus_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(), "computed_at": now_iso(), "language": lang}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default=None, help="test: a chain id, e.g. EN-REPLACE")
    ap.add_argument("--max-gen", type=int, default=99)
    ap.add_argument("--out", default=str(RESULTS / "novelty_duplicates.jsonl"))
    a = ap.parse_args()
    checks = [check_seed_signatures(L) for L in ("EN", "BN")]
    for c in checks:
        print(c, flush=True)
    for L in ("EN", "BN"):
        seed_tables(L)
    jobs = [(c, g, str(p)) for c, g, p in corpora() if (a.only is None or c == a.only) and g <= a.max_gen]
    print(f"{len(jobs)} corpora", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex, open(a.out, "w", encoding="utf-8") as f:
        for r in ex.map(one, jobs):
            f.write(json.dumps(r) + "\n")
            f.flush()
            rows.append(r)
            print(f"{r['chain_id']} gen {r['generation']}: docs {r['docs']}, novelty_2 {r['novelty_2']:.4f}, near-dup {r['near_dup_rate']:.4f}, "
                  f"exact {r['exact_dup_rate']:.4f} ({len(rows)}/{len(jobs)})", flush=True)
    if a.only is None and a.max_gen == 99:
        log_decision(f"robustness (viii) and the exploratory n-gram novelty computed (REQ-027): {len(rows)} synthetic training corpora -> "
                     f"results/novelty_duplicates.jsonl; seed signature check: {'; '.join(checks)}.")


if __name__ == "__main__":
    main()
