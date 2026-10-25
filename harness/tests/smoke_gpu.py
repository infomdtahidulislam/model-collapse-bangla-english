#!/usr/bin/env python3
"""
GPU smoke test for a new host (added 2026-10-13, before the first generation-0 run): exercises the GPU code paths of
run_chain.py and metrics.py on a few hundred documents, in the same order and in one process as gen-0 and a chain step do
(HF training -> vLLM generation -> HF scoring -> vLLM again), so an API change in transformers / vLLM, a dtype problem or
GPU memory that is not released between stages shows up in minutes instead of inside a 25-minute stage.

  python harness/tests/smoke_gpu.py                # uses the Gate 1 corpora (data/corpora/*_seed.jsonl, prefixes_*.jsonl)
  python harness/tests/smoke_gpu.py --fake-inputs  # before the corpora exist: filler documents and prefixes (token ids
                                                   # from the base tokenizer) are written to the scratch directory

Everything is written to /workspace/smoke_gpu (outside data/ and results/); nothing it produces is a result or a finding,
and the directory can be deleted afterwards. Exit code 0 = PASS.
"""
from __future__ import annotations

import argparse
import copy
import gc
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common  # noqa: E402
from common import CORPORA, load_chains_cfg, read_jsonl, utf8_stdout, write_json, write_jsonl  # noqa: E402

utf8_stdout()
SCRATCH = Path("/workspace/smoke_gpu") if Path("/workspace").exists() else Path(__file__).resolve().parents[2] / "smoke_gpu"
FAIL: list[str] = []
EN_FILL = ["The river runs through the old town and past the market where farmers sell rice, fish and vegetables every morning.",
           "In the nineteenth century the railway reached the district, and the population of the small port grew quickly.",
           "Students in the village school learn mathematics, history and two languages before they move to the college in the city.",
           "The museum keeps a collection of coins, maps and letters that describe trade along the coast over three hundred years."]
BN_FILL = ["নদীটি পুরনো শহরের মধ্য দিয়ে বয়ে গেছে এবং বাজারের পাশ দিয়ে চলে গেছে যেখানে কৃষকেরা প্রতিদিন সকালে চাল, মাছ ও সবজি বিক্রি করেন।",
           "উনিশ শতকে রেলপথ জেলায় পৌঁছায় এবং ছোট বন্দরটির জনসংখ্যা দ্রুত বাড়তে থাকে।",
           "গ্রামের বিদ্যালয়ে শিক্ষার্থীরা শহরের কলেজে যাওয়ার আগে গণিত, ইতিহাস ও দুটি ভাষা শেখে।",
           "জাদুঘরে মুদ্রা, মানচিত্র ও চিঠির একটি সংগ্রহ আছে যা তিনশো বছর ধরে উপকূলের বাণিজ্যের কথা বলে।"]


def check(cond: bool, msg: str) -> None:
    print(("[ok]   " if cond else "[FAIL] ") + msg, flush=True)
    if not cond:
        FAIL.append(msg)


def gpu_used_mib() -> str:
    try:
        return subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:  # noqa
        return f"n/a ({e})"


def make_fake_inputs(cfg: dict, corp: Path) -> None:
    """Filler seed documents and prefixes (12 words) with token ids from the base tokenizer, plus a manifest with
    per-language lengths; for the smoke test only."""
    import random
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(cfg["base_model"]["hf"])
    rnd = random.Random(3)
    lens = {}
    for lang, fill in (("EN", EN_FILL), ("BN", BN_FILL)):
        docs = []
        for i in range(400):
            text = " ".join(rnd.choice(fill) for _ in range(12))
            docs.append({"doc_id": f"{lang}-fake-{i}", "language": lang, "source": "fake", "text": text, "n_tokens": len(tok(text, add_special_tokens=False)["input_ids"])})
        write_jsonl(corp / f"{lang}_seed.jsonl", docs)
        pre = []
        for i, d in enumerate(docs[:64]):
            words = d["text"].split()[:12]
            ids = tok(" ".join(words), add_special_tokens=False)["input_ids"]
            pre.append({"prefix_id": f"{lang}-P{i:05d}", "doc_id": d["doc_id"], "text": " ".join(words), "prefix_ids": [int(x) for x in ids]})
        write_jsonl(corp / f"prefixes_{lang}.jsonl", pre)
        lens[lang] = {"prefix_tokens": max(len(p["prefix_ids"]) for p in pre), "max_new_tokens": 96 if lang == "EN" else 160}
    write_json(corp / "manifest.json", {"tokenizer": f"hf:{cfg['base_model']['hf']}", "fake": True, "languages": lens})


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--fake-inputs", action="store_true"); a = ap.parse_args()
    import torch
    import run_chain
    from metrics import Scorer
    cfg = load_chains_cfg()
    small = copy.deepcopy(cfg)
    small["training"]["effective_batch_seqs"] = small["training"]["micro_batch_seqs"]   # >= 20 optimizer steps on a few hundred docs
    SCRATCH.mkdir(parents=True, exist_ok=True)
    corp = CORPORA
    if a.fake_inputs:
        corp = SCRATCH / "fake_corpora"; corp.mkdir(parents=True, exist_ok=True)
        make_fake_inputs(cfg, corp)
        print(f"[note] fake inputs in {corp} (smoke test only)")
    run_chain.CORPORA = corp                                # generate() and lang_lengths() read prefixes and the manifest here
    try:
        import transformers
        print(f"torch {torch.__version__} cuda {torch.version.cuda} | transformers {transformers.__version__}")
        import vllm
        print(f"vllm {vllm.__version__}")
    except Exception as e:  # noqa
        print(f"[note] version probe: {type(e).__name__}: {e}")
    print("GPU memory before:", gpu_used_mib(), flush=True)

    # 1. train (bf16, cosine_with_min_lr, gradient checkpointing, prefix masking) on 400 real-shaped + 16 synthetic-shaped docs
    #    (>= 20 optimizer steps at 8 sequences per step, so the trainer logs a loss: logging_steps is 20 in train())
    seed_docs = [d for _, d in zip(range(400), read_jsonl(corp / "EN_seed.jsonl"))]
    pre = [p for _, p in zip(range(16), read_jsonl(corp / "prefixes_EN.jsonl"))]
    synth = [{"doc_id": f"EN-G-smoke{i}", "prefix_id": p["prefix_id"], "prefix": p["text"], "prefix_ids": p["prefix_ids"], "text": " continuation text " * 20, "n_tokens": 60} for i, p in enumerate(pre)]
    check(len(seed_docs) == 400 and len(pre) == 16 and all(p.get("prefix_ids") for p in pre), f"inputs: {len(seed_docs)} seed docs, {len(pre)} prefixes with ids")
    t0 = time.time()
    info = run_chain.train(seed_docs + synth, cfg["base_model"]["hf"], SCRATCH / "train", small, 1234)
    check(not info["nan"] and info["final_loss"] is not None, f"train: {info['optimizer_steps']} steps, loss {info['loss_first']} -> {info['final_loss']}, {time.time() - t0:.0f}s, dtype {info['dtype']}")
    check(info["masked_prefix_tokens"] > 0 and info["synthetic_target_tokens"] > 0, f"prefix tokens masked ({info['masked_prefix_tokens']}), synthetic target tokens {info['synthetic_target_tokens']}")
    ck = SCRATCH / "train" / "checkpoint"
    check((ck / "config.json").exists(), f"checkpoint saved: {sorted(p.name for p in ck.iterdir())[:8]}")
    print("GPU memory right after train() returned:", gpu_used_mib(), "| torch reserved MiB:", torch.cuda.memory_reserved() // 2**20, flush=True)

    # 2. vLLM generation right after training (as in gen-0 and step()): per-request seeds, token-id prompts, both languages
    for lang in ("EN", "BN"):
        t0 = time.time()
        gi = run_chain.generate(str(ck), lang, 10_000, cfg, cfg["sampling"], 99, SCRATCH / f"gen_{lang}.jsonl", max_docs=32, prefix_subset=32)
        docs = list(read_jsonl(SCRATCH / f"gen_{lang}.jsonl"))
        check(gi["engine"] == "vllm", f"{lang} generate engine {gi['engine']} ({time.time() - t0:.0f}s incl. engine start), gpu_memory_utilization {gi.get('gpu_memory_utilization')}")
        rates = f"{lang}: {len(docs)} docs, empty {gi['empty_rate']}, dup {gi['exact_duplicate_rate']}, mean words {gi['mean_words']}, cap hit {gi['cap_hit_rate']}, max_new {gi['max_new_tokens']}"
        if a.fake_inputs:   # a model fine-tuned on four English filler sentences: rates are mechanics only, not quality
            check(len(docs) == 32, rates + " (fake inputs: rates not judged)")
        else:
            check(len(docs) == 32 and gi["empty_rate"] <= 0.05 and gi["exact_duplicate_rate"] <= 0.05, rates)
            # regression check for the missing-<bos> bug (2026-10-13): without <bos> gemma-3 output was 73% degenerate
            from common import repeat_4gram_rate, words
            rep = [repeat_4gram_rate([w.lower() for w in words(d["text"])]) for d in docs]
            check(sum(rep) / len(rep) < 0.2, f"{lang}: mean 4-gram repeat rate {sum(rep) / len(rep):.3f} < 0.2 (Gate 2 criterion; prompts carry <bos>)")
        print(f"   {lang} sample continuation: {docs[0]['text'][:160]!r}")
        print("GPU memory after generate():", gpu_used_mib(), flush=True)
    # one prefix, 16 request seeds -> 16 different continuations
    one = [next(read_jsonl(corp / "prefixes_EN.jsonl"))]
    same = SCRATCH / "same_prefix_corpora"; same.mkdir(parents=True, exist_ok=True)
    write_jsonl(same / "prefixes_EN.jsonl", one * 16)
    (same / "manifest.json").write_bytes((corp / "manifest.json").read_bytes())   # lang_lengths() reads it from CORPORA
    run_chain.CORPORA = same
    try:
        run_chain.generate(str(ck), "EN", 10_000, cfg, cfg["sampling"], 7, SCRATCH / "same_prefix.jsonl", max_docs=16, prefix_subset=16)
        run_chain.generate(str(ck), "EN", 10_000, cfg, cfg["sampling"], 7, SCRATCH / "same_prefix_again.jsonl", max_docs=16, prefix_subset=16)
    finally:
        run_chain.CORPORA = corp
    texts = [d["text"] for d in read_jsonl(SCRATCH / "same_prefix.jsonl")]
    again = [d["text"] for d in read_jsonl(SCRATCH / "same_prefix_again.jsonl")]
    # different request seeds must give different samples (identical seeds would give 1 distinct text); a near-deterministic
    # model can still repeat a continuation by chance, so the fake-input run asks for >= 2, the real run for >= 15 of 16
    need = 2 if a.fake_inputs else 15
    check(len(set(texts)) >= need, f"one prefix x 16 request seeds -> {len(set(texts))} distinct continuations (need >= {need})")
    same_n = sum(1 for x, y in zip(texts, again) if x == y)
    check(same_n == 16, f"reproducibility: the same seeds again -> {same_n}/16 identical continuations")

    # 3. HF scoring after vLLM (document-length texts and probe-style short sentences)
    t0 = time.time()
    sc = Scorer(str(ck), cfg["training"]["dtype"])
    texts = [d["text"] for d in seed_docs[:12]] + ["The capital of France is Paris.", "ঢাকা বাংলাদেশের রাজধানী।"]
    res = sc.nll_batch(texts, max_len=1024)
    ok = all(r is not None and r[1] > 0 and r[0] == r[0] and r[0] > 0 for r in res)
    check(ok, f"scorer: {len(res)} texts, per-token NLL {[round(x / n, 2) for x, n in res][:6]} ..., {time.time() - t0:.0f}s")
    del sc; gc.collect(); torch.cuda.empty_cache()
    print("GPU memory after scoring:", gpu_used_mib(), flush=True)

    # 4. vLLM once more after the scorer (a chain step starts vLLM twice: synthetic corpus, then the sample)
    gi = run_chain.generate(str(ck), "BN", 10_000, cfg, cfg["sampling"], 5, SCRATCH / "gen_again.jsonl", max_docs=8, prefix_subset=8)
    check(gi["docs"] == 8, f"second vLLM start after scoring: {gi['docs']} docs")
    print("\nRESULT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)}): {FAIL}")
    json.dump({"fail": FAIL, "at": time.time(), "fake_inputs": a.fake_inputs}, open(SCRATCH / "smoke_result.json", "w"))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
