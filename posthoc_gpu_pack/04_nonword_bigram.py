#!/usr/bin/env python3
"""CG4 post-hoc, full #18: nonword composition of the synthetic training corpora.

For the confirmatory REPLACE chains (EN and BN, generations 1-6), stream the
archived synthetic training corpora and compute, against the language's seed
vocabulary (registered word split, lower-cased):
  - token- and type-level out-of-vocabulary (OOV) shares per corpus,
  - the share of OOV types (and OOV tokens) containing a character bigram that
    never occurs inside any seed vocabulary type ("novel-bigram" nonwords, the
    recombined-junk signature) vs OOV types built only from seen bigrams
    (plausible real-but-unseen words),
  - the 40 most frequent OOV types per corpus, flagged, for manual inspection.

The training corpus of generation g is results/chains/<chain>/gen_<g>/synthetic.jsonl. harness/run_chain.py step()
writes it: generation g-1's model generates it, and generation g is trained on it. These are the corpora that robustness
(viii) measured.

Post-hoc diagnostic (2026-10-20). Not pre-registered; changes no registered number.
Run after 01_fetch.sh:  python3 04_nonword_bigram.py
On the VPS:             python 04_nonword_bigram.py --root ../results/g6_extract

VPS-route fixes, 2026-10-20 (PATCH_NOTES.md):
 - The corpus is gen_<g>/synthetic.jsonl. The old search accepted only file names containing "corpus" or "train", so it
   never found a corpus. It then fell back to whichever of sample.jsonl or sample_scores.jsonl the directory walk met
   first, and labelled that a "50-sample file". There is no fallback now: a missing corpus is an error.
 - Files are read at the archive's own paths. New --root and --out options.
"""
import argparse, csv, json, os, sys
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="extracted", help="folder holding the archive's results/ and data/ paths")
ap.add_argument("--out", default="out")
a = ap.parse_args()
ROOT, OUT = a.root, a.out
os.makedirs(OUT, exist_ok=True)
import regex as uregex
WORD_RE = uregex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")
CHAINS = ("EN-REPLACE", "BN-REPLACE")


def seed_path(lang):
    p = os.path.join(ROOT, "data", "corpora", f"{lang}_seed.jsonl")
    if not os.path.exists(p):
        sys.exit(f"ERROR: no {lang} seed corpus at {p}")
    return p


def corpus_path(chain, g):
    p = os.path.join(ROOT, "results", "chains", chain, f"gen_{g}", "synthetic.jsonl")
    if not os.path.exists(p):
        sys.exit(f"ERROR: no training corpus at {p}; check the extraction")
    return p


def bigrams(word):
    w = f"^{word}$"
    return {w[i:i+2] for i in range(len(w) - 1)}


rows, toprows = [], []
for lang in ("EN", "BN"):
    vocab, seed_bi = set(), set()
    print(f"building {lang} seed vocabulary and bigram inventory", flush=True)
    with open(seed_path(lang), encoding="utf-8") as f:
        for line in f:
            for w in WORD_RE.findall(json.loads(line)["text"]):
                vocab.add(w.lower())
    for w in vocab:
        seed_bi |= bigrams(w)
    print(f"  {len(vocab)} types, {len(seed_bi)} character bigrams", flush=True)
    chain = f"{lang}-REPLACE"
    for g in range(1, 7):
        path, src = corpus_path(chain, g), f"training corpus (gen_{g}/synthetic.jsonl)"
        ndocs = ntok = noov = 0
        types, oov_counts = set(), Counter()
        with open(path, encoding="utf-8") as f:
            for line in f:
                text = json.loads(line).get("text") or ""
                ndocs += 1
                for w in WORD_RE.findall(text):
                    w = w.lower(); ntok += 1; types.add(w)
                    if w not in vocab:
                        noov += 1; oov_counts[w] += 1
        novel_types = {w for w in oov_counts if bigrams(w) - seed_bi}
        novel_tok = sum(oov_counts[w] for w in novel_types)
        row = dict(chain=chain, gen=g, source=src, n_tokens=ntok,
                   token_oov_share=round(noov / ntok, 5) if ntok else "",
                   type_oov_share=round(len(oov_counts) / len(types), 5) if types else "",
                   oov_types=len(oov_counts),
                   novel_bigram_type_share=round(len(novel_types) / len(oov_counts), 4) if oov_counts else "",
                   novel_bigram_token_share=round(novel_tok / noov, 4) if noov else "",
                   n_docs=ndocs)
        rows.append(row); print(row, flush=True)
        for w, c in oov_counts.most_common(40):
            toprows.append(dict(chain=chain, gen=g, type=w, count=c,
                                novel_bigram="yes" if w in novel_types else "no"))

with open(f"{OUT}/nonword_corpus_shares.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
with open(f"{OUT}/nonword_top_types.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["chain", "gen", "type", "count", "novel_bigram"])
    w.writeheader(); w.writerows(toprows)
print(f"\nwrote {OUT}/nonword_corpus_shares.csv and nonword_top_types.csv")
