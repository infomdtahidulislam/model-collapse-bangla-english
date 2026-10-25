#!/usr/bin/env python
"""Robustness (vii), as fixed by the authors in REQ-027 (2026-10-18; 07_ANALYSIS_PLAN.md §5): distinct-1 to distinct-4 and the
type-token ratio on the base tokenizer's token ids (Gemma-3; no special tokens) of each continuation, instead of word splits.

Same seeded document order as the word version (random.Random(config seed + generation)); fertility-adjusted window = the number
of tokens that carries the registered 50,000 words in the language, from the seed corpora's words per token in
data/corpora/manifest.json (EN 68,362, BN 88,889); CI from 300 document permutations (numpy default_rng(config seed +
generation)), as harness/metrics.py does for the word version. Every checkpoint's tokenizer.json is the same file (checked against
the pack manifest), so one copy is used.

Writes results/tokenizer_metrics.jsonl (schema as results/metrics.jsonl; metrics distinct_{1..4}_tok, ttr_window_tok,
window_tokens_tok). usage: python harness/tools/token_metrics.py [--workers 4]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import CORPORA, RESULTS, load_chains_cfg, log_decision, now_iso, read_jsonl, utf8_stdout  # noqa: E402

utf8_stdout()
ROOT = RESULTS / "g6_extract" / "results" / "chains"
TOKENIZER_DIR = RESULTS / "chains" / "GEN0-EN" / "checkpoint"
B = 300
_TOK = None


def step_of(p: Path) -> tuple[str, int]:
    parts = p.parts
    i = parts.index("chains")
    c = parts[i + 1]
    return (c, -1) if c.startswith("BASE-") else (c, 0) if c.startswith("GEN0-") else (c, int(parts[i + 2].split("_")[1]))


def n_distinct(win: np.ndarray, n: int) -> float:
    if len(win) < n:
        return float("nan")
    g = np.stack([win[i:len(win) - n + 1 + i] for i in range(n)], axis=1).astype(np.int64)
    if n <= 3:                                    # ids < 2^18: exact packing into one int64
        code = np.zeros(len(g), dtype=np.int64)
        for j in range(n):
            code = (code << 18) | g[:, j]
        return len(np.unique(code)) / len(g)
    v = np.ascontiguousarray(g).view(np.dtype((np.void, 8 * n))).ravel()
    return len(np.unique(v)) / len(g)


def window_stats(toks: list[np.ndarray], order: list[int], window: int) -> dict:
    parts, n = [], 0
    for i in order:
        parts.append(toks[i])
        n += len(toks[i])
        if n >= window:
            break
    win = np.concatenate(parts)[:window] if parts else np.zeros(0, dtype=np.int64)
    out = {f"distinct_{k}_tok": n_distinct(win, k) for k in (1, 2, 3, 4)}
    out["ttr_window_tok"] = len(np.unique(win)) / max(1, len(win))
    out["window_tokens_tok"] = float(len(win))
    return out


def one(args) -> list[dict]:
    path, seed0, window = args
    global _TOK
    if _TOK is None:
        from transformers import AutoTokenizer
        _TOK = AutoTokenizer.from_pretrained(str(TOKENIZER_DIR))
    p = Path(path)
    chain, g = step_of(p)
    texts = [d["text"] for d in read_jsonl(p)]
    toks = [np.array(ids, dtype=np.int64) for ids in _TOK(texts, add_special_tokens=False)["input_ids"]]
    seed = seed0 + g
    order = list(range(len(texts)))
    random.Random(seed).shuffle(order)
    point = window_stats(toks, order, window)
    rng = np.random.default_rng(seed)
    boots = {k: [] for k in point}
    for _ in range(B):
        bo = [order[i] for i in rng.permutation(len(order))]
        for k, v in window_stats(toks, bo, window).items():
            boots[k].append(v)
    recs = []
    for k, v in point.items():
        lo, hi = (float("nan"), float("nan")) if k == "window_tokens_tok" else (float(np.nanpercentile(boots[k], 2.5)), float(np.nanpercentile(boots[k], 97.5)))
        recs.append({"chain_id": chain, "generation": g, "metric": k, "value": float(v), "ci_lo": lo, "ci_hi": hi, "n": len(texts),
                     "checkpoint": "base tokenizer (gemma-3-270m tokenizer.json)", "computed_at": now_iso(),
                     "language": chain.split("-")[1] if chain.startswith(("BASE-", "GEN0-")) else chain[:2], "window": window})
    return recs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default="**/sample.jsonl")
    ap.add_argument("--out", default=str(RESULTS / "tokenizer_metrics.jsonl"))
    a = ap.parse_args()
    cfg = load_chains_cfg()
    man = json.load(open(CORPORA / "manifest.json", encoding="utf-8"))
    wpt = {L: float(man["languages"][L]["words_per_token"]) for L in ("EN", "BN")}      # seed corpora, Gate 1 manifest
    window = {L: int(round(int(cfg["metrics"]["ttr_window_tokens"]) / wpt[L])) for L in ("EN", "BN")}
    pm = json.load(open(RESULTS / "packs" / "pack_manifest_20261016-232223.json", encoding="utf-8"))["files"]
    toks_sha = {v["sha256"] for k, v in pm.items() if k.endswith("/tokenizer.json")}
    files = sorted(ROOT.glob(a.only), key=lambda p: step_of(p))
    print(f"{len(files)} samples; windows {window} (words per token {wpt}); distinct tokenizer.json files in the pack: {len(toks_sha)}", flush=True)
    if len(toks_sha) != 1:
        raise SystemExit("the checkpoints' tokenizer.json files differ; stop")
    jobs = []
    for p in files:
        c, _ = step_of(p)
        L = c.split("-")[1] if c.startswith(("BASE-", "GEN0-")) else c[:2]
        jobs.append((str(p), int(cfg["seed"]), window[L]))
    out = Path(a.out)
    n = 0
    with ProcessPoolExecutor(max_workers=a.workers) as ex, open(out, "w", encoding="utf-8") as f:
        for recs in ex.map(one, jobs):
            for r in recs:
                f.write(json.dumps(r) + "\n")
            n += 1
            print(f"{recs[0]['chain_id']} gen {recs[0]['generation']}: distinct_2_tok {recs[1]['value']:.4f} ({n}/{len(jobs)})", flush=True)
    if a.only == "**/sample.jsonl":
        log_decision(f"robustness (vii) computed (REQ-027): distinct-1..4 and TTR on base-tokenizer ids for {n} steps, windows {window} "
                     f"tokens (50,000 words at the seed corpora's words per token), 300 permutations -> results/tokenizer_metrics.jsonl.")


if __name__ == "__main__":
    main()
