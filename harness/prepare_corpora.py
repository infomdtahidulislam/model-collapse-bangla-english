#!/usr/bin/env python3
"""
Prepare matched seed corpora, held-out sets and generation prefixes (02_DATA_SOURCES.md).

  python harness/prepare_corpora.py --dry-run          # counts per source, no writes
  python harness/prepare_corpora.py --build            # clean, filter, dedup, match, split, write manifest
Steps: NFC normalisation -> length filter (base tokenizer if available, else word count) -> script filter ->
exact + MinHash near-duplicate removal -> domain-mix sampling to tokens_per_generation per language ->
held-out split disjoint by document id (+ fresh slice) -> prefixes (first N tokens of seed docs) -> manifest.
"""
from __future__ import annotations

import argparse
import random
import sys
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CORPORA, HELDOUT, ROOT, NearDupIndex, ensure_dirs, load_chains_cfg, load_corpora_cfg, minhash, now_iso,  # noqa: E402
                    read_jsonl, script_ratio, sha256_file, sha256_text, utf8_stdout, words, write_json, write_jsonl, log_decision)

utf8_stdout()


class Tok:
    """Base-model tokenizer if available, else a word-count proxy (recorded in the manifest)."""
    def __init__(self, hf: str):
        self.kind = "words"
        try:
            from transformers import AutoTokenizer
            self.t = AutoTokenizer.from_pretrained(hf)
            self.kind = f"hf:{hf}"
        except Exception:
            self.t = None

    def count(self, text: str) -> int:
        if self.t is not None:
            return len(self.t(text, add_special_tokens=False)["input_ids"])
        return len(words(text))

    def prefix(self, text: str, n: int) -> str:
        if self.t is not None:
            ids = self.t(text, add_special_tokens=False)["input_ids"][:n]
            return self.t.decode(ids)
        return " ".join(words(text)[:n])

    def prefix_ids(self, text: str, n: int) -> list[int] | None:
        """Exact token ids of the prefix (fed to the generator as ids so re-tokenisation cannot change the prefix length
        or cut inside a Bengali grapheme cluster; reviewer fix 2026-10-12). None without the HF tokenizer."""
        if self.t is None:
            return None
        return [int(i) for i in self.t(text, add_special_tokens=False)["input_ids"][:n]]


def near_dup_filter(docs: list[dict], perms: int, threshold: float, index: NearDupIndex | None = None) -> tuple[list[dict], NearDupIndex]:
    """Keep the first of every near-duplicate group (MinHash over word 3-grams, banded LSH, estimated Jaccard >= threshold).
    Shares one index across calls so that duplicates are removed across domains and the held-out/fresh docs can be tested
    against the seed pool (reviewer fix 2026-10-12: previously per-domain only)."""
    index = index or NearDupIndex(perms=perms, threshold=threshold)
    keep = [d for d in docs if index.add_if_new(minhash(d["_words"], perms))]
    return keep, index


def load_clean(path: Path, language: str, tok: Tok, cfg: dict) -> list[dict]:
    out = []
    seen = set()
    for i, r in enumerate(read_jsonl(path)):
        text = unicodedata.normalize("NFC", (r.get("text") or "")).strip()
        if not text:
            continue
        h = sha256_text(text)
        if h in seen:
            continue
        seen.add(h)
        ws = words(text)
        if script_ratio(text, language) < cfg["cleaning"]["min_script_ratio"]:
            continue
        n = tok.count(text)
        if n < cfg["cleaning"]["min_tokens"]:
            continue
        if n > cfg["cleaning"]["max_tokens"]:
            text = tok.prefix(text, cfg["cleaning"]["max_tokens"]); n = cfg["cleaning"]["max_tokens"]; ws = words(text)
        out.append({"doc_id": f"{language}-{path.stem}-{r.get('id', i)}", "language": language, "source": path.stem, "created": r.get("created"), "text": text, "n_tokens": n, "_words": ws[:400]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    ensure_dirs()
    ccfg = load_corpora_cfg(); chains = load_chains_cfg()
    budget = chains["tokens_per_generation"]; rnd = random.Random(ccfg["seed"])
    tok = Tok(chains["base_model"]["hf"])
    print(f"tokenizer: {tok.kind}; budget per language: {budget:,} tokens")
    manifest = {"created_at": now_iso(), "tokenizer": tok.kind, "budget_tokens": budget, "languages": {}}
    for lang, lcfg in ccfg["languages"].items():
        by_domain: dict[str, list[dict]] = {}
        for src in lcfg["sources"]:
            p = ROOT / src["file"]
            docs = load_clean(p, lang, tok, ccfg) if p.exists() else []
            print(f"[{lang}] {src['name']}: {len(docs)} cleaned docs, {sum(d['n_tokens'] for d in docs):,} tokens ({'missing' if not p.exists() else 'ok'})")
            by_domain.setdefault(src["domain"], []).extend(docs)
        if a.dry_run:
            continue
        # near-dup across the language's whole pool: one MinHash index shared by all domains (deterministic order), so a
        # held-out article cannot survive in the seed through another domain (e.g. Wikipedia text inside a web source)
        index: NearDupIndex | None = None; removed = {}
        for dom in sorted(by_domain):
            rnd.shuffle(by_domain[dom]); before = len(by_domain[dom])
            by_domain[dom], index = near_dup_filter(by_domain[dom], ccfg["cleaning"]["minhash_perms"], ccfg["cleaning"]["near_dup_jaccard"], index)
            removed[dom] = before - len(by_domain[dom])
            print(f"[{lang}] {dom}: near-dup removed {removed[dom]} (index shared across domains)")
        # held-out first (disjoint by doc), then seed sampling by domain mix
        heldout, seed_docs = [], []
        n_ho = ccfg["heldout"]["n_docs"]
        for dom, share in ccfg["domain_mix"].items():
            pool = by_domain.get(dom, [])
            k = int(round(n_ho * share))
            heldout.extend(pool[:k]); pool = pool[k:]
            target = budget * share; acc = 0
            for d in pool:
                if acc >= target:
                    break
                seed_docs.append(d); acc += d["n_tokens"]
            print(f"[{lang}] {dom}: seed {acc:,} tokens from {len(seed_docs)} docs so far")
        fresh, fresh_dropped = [], 0
        fp = lcfg.get("heldout_fresh", {}).get("file")
        if fp and (ROOT / fp).exists():
            # fresh pages are tested against the whole deduplicated pool (seed + held-out) so a new page that copies an
            # old article cannot leak into the "fresh" perplexity set
            for d in load_clean(ROOT / fp, lang, tok, ccfg):
                if index is not None and index.is_dup(minhash(d["_words"], ccfg["cleaning"]["minhash_perms"])):
                    fresh_dropped += 1; continue
                d["fresh"] = True; fresh.append(d)
                if len(fresh) >= ccfg["heldout"]["fresh_n_docs"]:
                    break
        ids_seed = {d["doc_id"] for d in seed_docs}
        n_regular = len(heldout)
        heldout = [d for d in heldout + fresh if d["doc_id"] not in ids_seed]
        strip = lambda d: {k: v for k, v in d.items() if not k.startswith("_")}  # noqa: E731
        write_jsonl(CORPORA / f"{lang}_seed.jsonl", (strip(d) for d in seed_docs))
        write_jsonl(HELDOUT / f"{lang}_heldout.jsonl", (strip(d) for d in heldout))
        total = sum(d["n_tokens"] for d in seed_docs)
        n_words = [len(words(d["text"])) for d in seed_docs]; n_bytes = [len(d["text"].encode()) for d in seed_docs]
        n_chars = [len(d["text"]) for d in seed_docs]; n_toks = [d["n_tokens"] for d in seed_docs]
        wpt = sum(n_words) / max(1, total)
        # per-language prefix and continuation lengths: in words (converted with the measured words-per-token of this seed
        # corpus) when length_unit is 'words', so both languages get the same amount of TEXT per document; else global tokens
        if str(chains.get("length_unit", "tokens")) == "words" and wpt > 0:
            prefix_tokens = max(4, int(round(chains["prefix_words"] / wpt))); max_new_tokens = max(32, int(round(chains["max_new_words"] / wpt)))
        else:
            prefix_tokens, max_new_tokens = int(chains["prefix_tokens"]), int(chains["max_new_tokens"])
        prefixes = [{"prefix_id": f"{lang}-P{i:05d}", "doc_id": d["doc_id"], "text": tok.prefix(d["text"], prefix_tokens),
                     "prefix_ids": tok.prefix_ids(d["text"], prefix_tokens)}
                    for i, d in enumerate(rnd.sample(seed_docs, min(chains["n_prefixes"], len(seed_docs))))]
        write_jsonl(CORPORA / f"prefixes_{lang}.jsonl", prefixes)
        pct = lambda xs: {str(q): float(np.percentile(xs, q)) for q in (5, 25, 50, 75, 95)} if xs else {}  # noqa: E731
        manifest["languages"][lang] = {"seed_docs": len(seed_docs), "seed_tokens": total, "seed_bytes": sum(n_bytes), "seed_words": sum(n_words), "seed_chars": sum(n_chars),
                                       "words_per_token": round(wpt, 4), "bytes_per_token": round(sum(n_bytes) / max(1, total), 4),
                                       "chars_per_token": round(sum(n_chars) / max(1, total), 4),
                                       "prefix_tokens": prefix_tokens, "max_new_tokens": max_new_tokens, "length_unit": str(chains.get("length_unit", "tokens")),
                                       "doc_length_percentiles": {"tokens": pct(n_toks), "words": pct(n_words), "bytes": pct(n_bytes)},
                                       "near_dup_removed": removed, "heldout_docs": len(heldout), "heldout_regular_docs": n_regular, "fresh_docs": len(fresh),
                                       "fresh_dropped_as_near_dup": fresh_dropped, "prefixes": len(prefixes),
                                       "sources": [{"name": s["name"], "licence": s["licence"], "domain": s["domain"]} for s in lcfg["sources"]],
                                       "sha256": {"seed": sha256_file(CORPORA / f"{lang}_seed.jsonl"), "heldout": sha256_file(HELDOUT / f"{lang}_heldout.jsonl"), "prefixes": sha256_file(CORPORA / f"prefixes_{lang}.jsonl")}}
        print(f"[{lang}] seed {total:,} tokens = {sum(n_words):,} words = {sum(n_bytes):,} bytes; held-out {n_regular} + fresh {len(fresh)} docs; prefixes {len(prefixes)}")
    if a.build:
        toks = [v["seed_tokens"] for v in manifest["languages"].values()]
        if len(toks) == 2 and toks[0] and abs(toks[0] - toks[1]) / max(toks) > 0.02:
            print(f"[warn] token counts differ by more than 2%: {toks}; adjust sources or budget")
        write_json(CORPORA / "manifest.json", manifest)
        log_decision("built seed corpora, held-out sets and prefixes")
        print("[ok] manifest written; HUMAN: confirm licences and matching at Gate 1")


if __name__ == "__main__":
    main()
