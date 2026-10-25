#!/usr/bin/env python
"""Cross-check of #18 (04_nonword_bigram.py) against the registered robustness (viii) (results/novelty_duplicates.jsonl,
REQ-027, harness/tools/novelty_duplicates.py). Both read the same corpora (gen_<g>/synthetic.jsonl) with the same word split,
lower-cased, against the same seed corpus. So #18's token_oov_share must equal (viii)'s novelty_1, the share of word
occurrences whose unigram never occurs in the seed. #18's n_tokens must equal (viii)'s words, and n_docs must equal docs.
(viii) compares 64-bit word hashes, so a difference would need a hash collision.

usage: python posthoc_gpu_pack/vps_route/crosscheck_18_vs_viii.py   (writes nonword_crosscheck_viii.csv into the results folder)
"""
import csv
import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
RES = PKG / "results" / "cg4_posthoc_gpu_results"
nov = {}
for line in open(PKG / "results" / "novelty_duplicates.jsonl", encoding="utf-8"):
    r = json.loads(line)
    nov[(r["chain_id"], int(r["generation"]))] = r
out, worst, bad = [], 0.0, 0
for row in csv.DictReader(open(RES / "nonword_corpus_shares.csv", encoding="utf-8")):
    key = (row["chain"], int(row["gen"]))
    v = nov[key]
    d = abs(float(row["token_oov_share"]) - float(v["novelty_1"]))
    same_counts = int(row["n_tokens"]) == int(v["words"]) and int(row["n_docs"]) == int(v["docs"])
    worst = max(worst, d)
    bad += int(not same_counts or d > 5e-6)
    out.append(dict(chain=key[0], gen=key[1], token_oov_share_18=row["token_oov_share"], novelty_1_viii=round(float(v["novelty_1"]), 7),
                    abs_diff=f"{d:.2e}", n_tokens_18=row["n_tokens"], words_viii=v["words"], n_docs_18=row["n_docs"], docs_viii=v["docs"],
                    counts_equal="yes" if same_counts else "NO", viii_corpus_sha256=v["corpus_sha256"][:16]))
with open(RES / "nonword_crosscheck_viii.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"{len(out)} corpora: largest |token_oov_share - novelty_1| = {worst:.2e} (#18 rounds to 5 decimals); "
      f"{len(out) - bad} of {len(out)} with equal word and document counts and agreement within rounding")
