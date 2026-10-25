#!/usr/bin/env python3
"""
Run one chain (language x regime [x variant]) generation by generation with resume (04_RUN_PLAN.md).

  python harness/run_chain.py --base EN                        # metrics of the untouched base model (chain BASE-EN, generation -1)
  python harness/run_chain.py --gen0 EN                        # generation-0 training on the real seed corpus (GEN0-EN; shared per language)
  python harness/run_chain.py --gen0 GEN0-EN-s2                # a re-seeded or budget-reduced gen-0 named by a robustness chain
  python harness/run_chain.py --chain EN-REPLACE --until 6 --session-id rented-01
  python harness/run_chain.py --status

Each generation step g (regimes REPLACE / ACCUMULATE / ACCUMULATE-FILTER / ACCUMULATE-SUBSAMPLE; REAL-REPEAT has no generation):
  1. generate the synthetic corpus for g with the g-1 checkpoint (per-request seeds; real prefix and generated continuation stored
     separately), 2. filter (FILTER regime: script, repetition, gen-0 perplexity band, MinHash near-dup vs seed + kept; topped up to
     the budget), 3. assemble the training set per regime, 4. train one epoch from the g-1 checkpoint (loss on generated tokens only:
     prefix tokens are masked), 5. generate the fixed-prefix 2,000-document SAMPLE from the NEW checkpoint, 6. metrics + sidecars,
  7. step.json. Every stage is cached (generate.json, filter.json, train.json, sample_meta.json), so a crash costs one stage, not a step.
State lives in results/chains/<chain>/state.json; a step is complete only when step.json exists.
Reviewer fixes 2026-10-12 (logs/design_review_2026-10-12/): sample from the trained model (not from its training data), per-request
generation seeds, prefix masking, MinHash filter, quantity-matched FILTER, bf16, min-lr cosine, resumable stages.
"""
from __future__ import annotations

import argparse
import math
import random
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CHAINS, CORPORA, HELDOUT, RESULTS, NearDupIndex, all_chains, ensure_dirs, load_chains_cfg, minhash, now_iso,  # noqa: E402
                    read_json, read_jsonl, repeat_4gram_rate, script_ratio, sha256_dir, utf8_stdout, words, write_json, write_jsonl, log_decision)

utf8_stdout()


# ---------------- chain and gen-0 specifications ----------------
def gen0_specs(cfg: dict) -> dict[str, dict]:
    """GEN0-<lang> for every language plus every custom gen-0 named by an enabled chain (re-seeded or budget-reduced)."""
    specs = {f"GEN0-{lang}": {"id": f"GEN0-{lang}", "language": lang, "seed_offset": 0, "tokens": None} for lang in cfg["languages"]}
    for c in all_chains(cfg):
        gid = c.get("gen0")
        if gid and gid not in specs:
            specs[gid] = {"id": gid, "language": c["language"], "seed_offset": int(c.get("seed_offset", 0)), "tokens": c.get("tokens")}
    return specs


def gen0_id(chain: dict) -> str:
    return chain.get("gen0") or f"GEN0-{chain['language']}"


def chain_seed(cfg: dict, chain: dict, g: int) -> int:
    return int(cfg["seed"]) + int(chain.get("seed_offset", 0)) + g


def resolve_tokens(cfg: dict, spec_tokens, language: str) -> int:
    """Token budget of a chain or gen-0: an integer, None (= tokens_per_generation) or 'match_words_of_<LANG>' (the number of
    THIS language's base-model tokens that carries as many words as the other language's seed corpus; resolved from
    data/corpora/manifest.json, so it needs Gate 1 corpora)."""
    if spec_tokens is None:
        return int(cfg["tokens_per_generation"])
    if isinstance(spec_tokens, int):
        return spec_tokens
    s = str(spec_tokens)
    if s.startswith("match_words_of_"):
        other = s.rsplit("_", 1)[-1]
        man = read_json(CORPORA / "manifest.json")
        if not man or other not in man.get("languages", {}) or language not in man.get("languages", {}):
            raise SystemExit(f"cannot resolve {s}: data/corpora/manifest.json with both languages is needed (Gate 1)")
        L = man["languages"]
        words_other = L[other].get("seed_words") or L[other]["seed_tokens"] * L[other]["words_per_token"]
        return int(round(words_other / L[language]["words_per_token"]))
    raise SystemExit(f"unknown tokens spec {spec_tokens!r}")


# ---------------- training ----------------
def pack(seqs: list[tuple], seq_len: int, eos: int) -> list[tuple[list[int], list[int]]]:
    """Concatenate documents into seq_len blocks, each followed by <eos>. The <eos> is a training target only when the
    document really ended there (third tuple element True): a real document the corpus builder did not cut, or a synthetic
    continuation the model stopped itself. After a cut (the generation length cap, the corpus builder's max_tokens, the
    seq_len truncation) it is context only (label -100). Bug fixed 2026-10-14 (G3 pilot): <eos> was always a target, so
    REPLACE generation 1 learned to end documents at the cap (72% of English continuations hit it) and put 73% of its
    probability on <eos> beyond that length in real text (harness/tools/eos_mass_check.py). Two-element tuples (no flag)
    keep the old behaviour, for callers that know every document is complete."""
    buf_i: list[int] = []; buf_l: list[int] = []; out = []
    for s in seqs:
        ids, labels = s[0], s[1]
        ends = s[2] if len(s) > 2 else True
        buf_i.extend(ids + [eos]); buf_l.extend(labels + [eos if ends else -100])
        while len(buf_i) >= seq_len:
            out.append((buf_i[:seq_len], buf_l[:seq_len])); buf_i, buf_l = buf_i[seq_len:], buf_l[seq_len:]
    return out


def lang_lengths(cfg: dict, language: str) -> tuple[int, int]:
    """(prefix_tokens, max_new_tokens) for a language. With generation.length_unit == 'words' the per-language token values
    come from data/corpora/manifest.json (set by prepare_corpora.py from the measured words-per-token of the seed corpus), so
    prefixes and continuations carry the same number of WORDS in both languages; otherwise the global token values apply."""
    unit = str(cfg.get("length_unit", "tokens"))
    if unit == "words":
        man = read_json(CORPORA / "manifest.json")
        L = (man or {}).get("languages", {}).get(language, {})
        if L.get("prefix_tokens") and L.get("max_new_tokens"):
            return int(L["prefix_tokens"]), int(L["max_new_tokens"])
        raise SystemExit(f"length_unit is 'words' but manifest.json has no per-language lengths for {language}: re-run prepare_corpora.py --build")
    return int(cfg["prefix_tokens"]), int(cfg["max_new_tokens"])


def tokenise_docs(tok, docs: list[dict], cfg: dict) -> tuple[list[tuple[list[int], list[int]]], dict]:
    """Synthetic documents (those with a prefix_id) are prefix + continuation. training.prefix_mode decides what the model
    trains on: 'masked' (default) feeds the real prefix as context but excludes it from the loss (label -100), 'dropped'
    trains on the continuation alone, 'trained' includes the prefix in the loss (real tokens enter a REPLACE step; not the
    pre-registered setting). Real documents are trained on in full."""
    seq_len = int(cfg["seq_len"]); mode = str(cfg["training"].get("prefix_mode", "masked"))
    if cfg["training"].get("train_on_prefix"):
        mode = "trained"
    # every document starts with <bos>, as in Gemma's pretraining format and in generate() and the scorer: without it
    # gemma-3 degenerates (base-model A/B 2026-10-13: 73% degenerate EN samples without <bos>, 0% with it). The <bos> is
    # context, never a target (label -100), and is not counted in the target tokens.
    bos = [tok.bos_token_id] if tok.bos_token_id is not None else []
    # the corpus builder cut documents longer than cleaning.max_tokens to their first max_tokens tokens and stored
    # n_tokens = max_tokens for them (prepare_corpora.py), so such a document did not end where its text stops
    try:
        from common import load_corpora_cfg
        corpus_max = int(load_corpora_cfg()["cleaning"]["max_tokens"])
    except Exception:  # noqa
        corpus_max = None
    seqs = []; st = {"real_target_tokens": 0, "synthetic_target_tokens": 0, "masked_prefix_tokens": 0, "real_docs": 0, "synthetic_docs": 0, "prefix_mode": mode,
                     "bos_per_document": bool(bos), "eos_target_docs": 0, "eos_context_only_docs": 0}
    for d in docs:
        if "prefix_id" in d:
            pre = d.get("prefix_ids") or tok(d.get("prefix") or "", add_special_tokens=False)["input_ids"]
            pre = list(pre)[: max(0, seq_len - 8)]
            if mode == "dropped":
                pre = []
            room = seq_len - len(bos) - len(pre)
            full = tok(d["text"], add_special_tokens=False)["input_ids"]
            cont = full[:room]
            ids = bos + pre + cont
            labels = [-100] * len(bos) + (pre if mode == "trained" else [-100] * len(pre)) + cont
            ends = d.get("finish") == "stop" and len(full) <= room     # the model stopped itself; "length" = cut at the cap
            st["synthetic_target_tokens"] += len(cont); st["synthetic_docs"] += 1
            if mode == "trained":
                st["real_target_tokens"] += len(pre)
            else:
                st["masked_prefix_tokens"] += len(pre)
        else:
            room = seq_len - len(bos)
            full = tok(d["text"], add_special_tokens=False)["input_ids"]
            body = full[:room]
            ids = bos + body; labels = [-100] * len(bos) + list(body)
            cut_by_builder = corpus_max is not None and int(d.get("n_tokens") or 0) >= corpus_max
            ends = len(full) <= room and not cut_by_builder
            st["real_target_tokens"] += len(body); st["real_docs"] += 1
        if len(ids) > len(bos):
            seqs.append((ids, labels, ends))
            st["eos_target_docs" if ends else "eos_context_only_docs"] += 1
    return seqs, st


def train(train_docs: list[dict], init_checkpoint: str, out_dir: Path, cfg: dict, seed: int) -> dict:
    import torch
    from torch.utils.data import Dataset
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments
    t = cfg["training"]; dtype = t["dtype"]
    tok = AutoTokenizer.from_pretrained(init_checkpoint)
    eos = tok.eos_token_id if tok.eos_token_id is not None else 0
    seqs, st = tokenise_docs(tok, train_docs, cfg)
    blocks = pack(seqs, cfg["seq_len"], eos)
    rnd = random.Random(seed); rnd.shuffle(blocks)

    class DS(Dataset):
        def __len__(self): return len(blocks)
        def __getitem__(self, i):
            ids, labels = blocks[i]
            return {"input_ids": torch.tensor(ids), "labels": torch.tensor(labels)}

    model = AutoModelForCausalLM.from_pretrained(init_checkpoint, dtype=torch.float32)   # fp32 master weights (`dtype`: transformers >= 4.56)
    if t["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
    # transformers 5.x removed warmup_ratio; a float warmup_steps in [0, 1) is the ratio with the same rule, ceil(ratio x steps)
    import inspect
    warm = ({"warmup_ratio": float(t["warmup_ratio"])} if "warmup_ratio" in inspect.signature(TrainingArguments.__init__).parameters
            else {"warmup_steps": float(t["warmup_ratio"])})
    args = TrainingArguments(output_dir=str(out_dir / "trainer"), per_device_train_batch_size=t["micro_batch_seqs"],
                             gradient_accumulation_steps=max(1, t["effective_batch_seqs"] // t["micro_batch_seqs"]), num_train_epochs=t["epochs"],
                             learning_rate=t["lr"], **warm, lr_scheduler_type="cosine_with_min_lr",
                             lr_scheduler_kwargs={"min_lr_rate": float(t["min_lr_ratio"])}, weight_decay=t["weight_decay"],
                             adam_beta1=t["betas"][0], adam_beta2=t["betas"][1], max_grad_norm=t["grad_clip"],
                             fp16=(dtype == "float16"), bf16=(dtype == "bfloat16"),
                             logging_steps=20, save_strategy="no", report_to=[], seed=seed, dataloader_num_workers=2)
    trainer = Trainer(model=model, args=args, train_dataset=DS())
    t0 = time.time(); result = trainer.train(); dt = time.time() - t0
    ckpt = out_dir / "checkpoint"
    if ckpt.exists():
        shutil.rmtree(ckpt)
    save_dtype = getattr(torch, t.get("save_dtype", dtype))
    model.to(save_dtype).save_pretrained(str(ckpt), safe_serialization=True); tok.save_pretrained(str(ckpt))
    losses = [l["loss"] for l in trainer.state.log_history if "loss" in l]
    global_step = int(trainer.state.global_step)
    # release the GPU before the next stage: vLLM (the sample right after training) refuses to start unless
    # gpu_memory_utilization x total is free, and the caching allocator still held ~20 GB here (smoke test 2026-10-13)
    del trainer, model
    import gc
    gc.collect(); torch.cuda.empty_cache()
    return {"train_blocks": len(blocks), "train_tokens": len(blocks) * cfg["seq_len"], "target_tokens": st["real_target_tokens"] + st["synthetic_target_tokens"], **st,
            "final_loss": losses[-1] if losses else None, "loss_first": losses[0] if losses else None, "loss_curve": losses,
            "nan": any(math.isnan(l) for l in losses), "train_seconds": round(dt, 1), "optimizer_steps": global_step,
            "micro_batch_seqs": int(t["micro_batch_seqs"]), "grad_accum_steps": max(1, t["effective_batch_seqs"] // t["micro_batch_seqs"]),
            "effective_batch_seqs": int(t["effective_batch_seqs"]), "warmup": warm,
            "dtype": dtype, "save_dtype": t.get("save_dtype", dtype), "trainer_metrics": result.metrics}


# ---------------- generation ----------------
def generate(checkpoint: str, language: str, budget_tokens: int, cfg: dict, sampling: dict, seed: int, out_path: Path,
             max_docs: int | None = None, prefix_subset: int | None = None, start_index: int = 0) -> dict:
    """Generate continuations of the fixed prefixes until budget_tokens generated tokens (prefix tokens are not counted) or
    max_docs documents. prefix_subset=N uses the first N prefixes in file order (the fixed SAMPLE prefixes); otherwise the
    prefixes are cycled in a seeded shuffle. Every request gets its own seed (seed*1000003 + document index), so a prefix
    reused in the same corpus gets a fresh continuation while the whole corpus stays reproducible."""
    prefixes = list(read_jsonl(CORPORA / f"prefixes_{language}.jsonl"))
    if not prefixes:
        raise SystemExit(f"no prefixes for {language}: run prepare_corpora.py --build")
    if prefix_subset is not None:
        prefixes = prefixes[:prefix_subset]
    else:
        random.Random(seed).shuffle(prefixes)
    prefix_tokens, max_new = lang_lengths(cfg, language); dtype = cfg["training"]["dtype"]
    docs: list[dict] = []; total = 0; t0 = time.time(); k = start_index

    def mk_doc(p: dict, text: str, n: int, finish: str) -> dict:
        nonlocal k
        d = {"doc_id": f"{language}-G-{k:07d}", "prefix_id": p["prefix_id"], "prefix": p["text"], "prefix_ids": p.get("prefix_ids"),
             "text": text, "n_tokens": int(n), "hit_cap": n >= max_new, "finish": finish, "request_seed": seed * 1_000_003 + k}
        k += 1
        return d

    def remaining() -> int:
        if max_docs is not None:
            return max(0, max_docs - len(docs))
        return 1 << 30

    util = 0.85
    free_before = None
    try:
        from vllm import LLM, SamplingParams
        # vLLM refuses to start unless util x total GPU memory is free; size it from what is free now (an earlier stage of
        # this process, e.g. the FILTER scorer, may still hold memory). Affects throughput only, not what is sampled.
        try:
            import gc
            import torch
            gc.collect(); torch.cuda.empty_cache()
            free_b, total_b = torch.cuda.mem_get_info()
            free_before = free_b
            util = round(max(0.25, min(0.85, (free_b - 1.5 * 2**30) / total_b)), 3)
        except Exception:  # noqa
            util = 0.85
        llm = LLM(model=checkpoint, dtype=dtype, max_model_len=prefix_tokens + max_new + 16, gpu_memory_utilization=util, seed=seed)
        bos_id = llm.get_tokenizer().bos_token_id
        bos = [bos_id] if bos_id is not None else []    # token-id prompts get <bos> (text prompts get it from the tokenizer)
        i = 0
        while total < budget_tokens and remaining() > 0:
            n_req = min(512, remaining())
            batch = [prefixes[(i + j) % len(prefixes)] for j in range(n_req)]; i += n_req
            prompts = [{"prompt_token_ids": (bos if list(p["prefix_ids"][:1]) != bos else []) + list(p["prefix_ids"])} if p.get("prefix_ids") else p["text"] for p in batch]
            sps = [SamplingParams(temperature=float(sampling["temperature"]), top_p=float(sampling["top_p"]), max_tokens=max_new, seed=seed * 1_000_003 + k + j) for j in range(n_req)]
            outs = llm.generate(prompts, sps)
            for p, o in zip(batch, outs):
                g = o.outputs[0]; n = len(g.token_ids)
                docs.append(mk_doc(p, g.text, n, str(g.finish_reason))); total += n
        engine = "vllm"
        del llm
        # the engine process tears down asynchronously: wait until its memory is back before the next stage allocates
        # (gen-0 log 2026-10-13: the scorer met < 1 GB free 9 s after the shutdown and only survived on allocator retries)
        try:
            import gc
            import torch
            gc.collect()
            t_w = time.time()
            while free_before is not None and time.time() - t_w < 120 and torch.cuda.mem_get_info()[0] < free_before - 1.5 * 2**30:
                time.sleep(1)
            if free_before is not None and torch.cuda.mem_get_info()[0] < free_before - 1.5 * 2**30:
                print(f"[generate] note: GPU memory not fully back {time.time() - t_w:.0f}s after the vLLM shutdown", flush=True)
        except Exception:  # noqa
            pass
    except ImportError:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(checkpoint); tok.padding_side = "left"
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(checkpoint, dtype=getattr(torch, dtype), device_map="auto").eval()
        i = 0
        while total < budget_tokens and remaining() > 0:
            n_req = min(64, remaining())
            batch = [prefixes[(i + j) % len(prefixes)] for j in range(n_req)]; i += n_req
            if all(p.get("prefix_ids") for p in batch):
                hb = [tok.bos_token_id] if tok.bos_token_id is not None else []   # <bos> as in the vLLM path
                enc = tok.pad({"input_ids": [(hb if list(p["prefix_ids"][:1]) != hb else []) + list(p["prefix_ids"]) for p in batch]}, return_tensors="pt").to(model.device)
            else:
                enc = tok([p["text"] for p in batch], return_tensors="pt", padding=True).to(model.device)
            torch.manual_seed(seed * 1_000_003 + k)
            with torch.no_grad():
                out = model.generate(**enc, do_sample=True, temperature=float(sampling["temperature"]), top_p=float(sampling["top_p"]), max_new_tokens=max_new, pad_token_id=tok.pad_token_id)
            for p, row in zip(batch, out):
                ids = [int(x) for x in row[enc["input_ids"].shape[1]:].tolist()]
                if tok.eos_token_id in ids:
                    ids = ids[: ids.index(tok.eos_token_id)]
                ids = [x for x in ids if x != tok.pad_token_id]
                n = len(ids)
                docs.append(mk_doc(p, tok.decode(ids, skip_special_tokens=True), n, "length" if n >= max_new else "stop")); total += n
        engine = "hf_generate"
        del model
    try:
        import gc
        import torch; gc.collect(); torch.cuda.empty_cache()   # the vLLM engine process exits once `llm` is collected
    except Exception:
        pass
    conts = [d["text"] for d in docs]
    n_words = [len(words(t)) for t in conts]
    info = {"engine": engine, "docs": len(docs), "tokens": total, "generate_seconds": round(time.time() - t0, 1), "seed": seed, "start_index": start_index,
            "gpu_memory_utilization": util if engine == "vllm" else None,
            "sampling": dict(sampling), "max_docs": max_docs, "prefix_subset": prefix_subset, "prefix_tokens": prefix_tokens, "max_new_tokens": max_new,
            "exact_duplicate_rate": round(1 - len(set(conts)) / max(1, len(conts)), 4),
            "mean_tokens": round(total / max(1, len(docs)), 2), "mean_words": round(sum(n_words) / max(1, len(docs)), 2),
            "mean_chars": round(sum(len(t) for t in conts) / max(1, len(docs)), 2), "mean_bytes": round(sum(len(t.encode()) for t in conts) / max(1, len(docs)), 2),
            "cap_hit_rate": round(sum(1 for d in docs if d["hit_cap"]) / max(1, len(docs)), 4), "empty_rate": round(sum(1 for w in n_words if w == 0) / max(1, len(docs)), 4)}
    write_jsonl(out_path, docs)
    return info


# ---------------- filter (ACCUMULATE-FILTER) ----------------
def ppl_band(gen0_checkpoint: str, language: str, cfg: dict):
    """Per-token NLL band of the gen-0 model on the regular held-out docs, truncated to the synthetic document length
    (prefix + max_new tokens), so the band is length-matched to what it is applied to. Failure is fatal (never skipped)."""
    import numpy as np
    from metrics import Scorer
    sc = Scorer(gen0_checkpoint, cfg["training"]["dtype"])
    L = sum(lang_lengths(cfg, language))
    held = [d["text"] for d in read_jsonl(HELDOUT / f"{language}_heldout.jsonl") if not d.get("fresh")][: int(cfg["metrics"]["heldout_docs"])]
    if not held:
        raise SystemExit(f"no held-out docs for {language}")
    res = sc.nll_batch(held, max_len=L); per_tok = [a / b for a, b in res if b > 0]
    lo, hi = cfg["filter"]["ppl_percentile_band"]
    return float(np.percentile(per_tok, lo)), float(np.percentile(per_tok, hi)), sc, L


def signatures_for(path_jsonl: Path, cache_npy: Path, perms: int, text_key: str = "text"):
    """MinHash signatures of every document in a JSONL file, cached as .npy next to it."""
    import numpy as np
    if cache_npy.exists():
        return np.load(cache_npy)
    sigs = [minhash(words(d[text_key])[:400], perms) for d in read_jsonl(path_jsonl)]
    arr = np.stack(sigs) if sigs else np.zeros((0, perms), dtype=np.uint64)
    np.save(cache_npy, arr)
    return arr


def build_filter_index(chain: dict, g: int, cfg: dict, language: str) -> NearDupIndex:
    f = cfg["filter"]; perms = int(f.get("minhash_perms", 64))
    index = NearDupIndex(perms=perms, threshold=float(f["near_dup_jaccard"]))
    for sig in signatures_for(CORPORA / f"{language}_seed.jsonl", CORPORA / f"{language}_seed_minhash.npy", perms):
        index.add(sig)
    cdir = CHAINS / chain["id"]
    for gg in range(1, g):
        kp = cdir / f"gen_{gg}" / "synthetic_kept.jsonl"
        if kp.exists():
            for sig in signatures_for(kp, cdir / f"gen_{gg}" / "synthetic_kept_minhash.npy", perms):
                index.add(sig)
    return index


def filter_docs(docs: list[dict], language: str, cfg: dict, scorer, band: tuple[float, float], max_len: int, index: NearDupIndex) -> tuple[list[dict], dict, list[dict]]:
    f = cfg["filter"]; perms = int(f.get("minhash_perms", 64)); lo, hi = band
    stats: Counter = Counter({"input": len(docs), "fail_script": 0, "fail_repeat": 0, "fail_ppl": 0, "fail_dup": 0, "kept": 0})
    res = scorer.nll_batch([(d.get("prefix") or "") + d["text"] for d in docs], max_len=max_len)
    kept, log_rows = [], []
    for d, (nll, n) in zip(docs, res):
        ws = words(d["text"]); sr = script_ratio(d["text"], language); rr = repeat_4gram_rate([w.lower() for w in ws]); lp = nll / n if n > 0 else float("inf")
        reason = None
        if sr < f["min_script_ratio"]:
            reason = "script"
        elif rr > f["max_repeat_4gram"]:
            reason = "repeat"
        elif not (lo <= lp <= hi):
            reason = "ppl"
        elif not index.add_if_new(minhash(ws[:400], perms)):
            reason = "dup"
        log_rows.append({"doc_id": d["doc_id"], "reason": reason or "kept", "script_ratio": round(sr, 4), "repeat_rate": round(rr, 4), "nll_per_token": round(lp, 4), "n_tokens": d["n_tokens"]})
        if reason:
            stats[f"fail_{reason}"] += 1
        else:
            stats["kept"] += 1; kept.append(d)
    st = dict(stats); st["pass_rate"] = round(st["kept"] / max(1, st["input"]), 4)
    return kept, st, log_rows


# ---------------- orchestration ----------------
def sample_from(checkpoint: str, language: str, cfg: dict, sampling: dict, seed: int, gdir: Path) -> list[dict]:
    """The fixed-prefix sample of n_sample_docs documents generated by `checkpoint` (one continuation per sample prefix)."""
    sample_path = gdir / "sample.jsonl"
    if not sample_path.exists() or read_json(gdir / "sample_meta.json") is None:
        n = int(cfg["metrics"]["n_sample_docs"])
        meta = generate(checkpoint, language, n * sum(lang_lengths(cfg, language)), cfg, sampling,
                        seed + int(cfg["metrics"].get("sample_seed_offset", 7)), sample_path, max_docs=n, prefix_subset=n)
        write_json(gdir / "sample_meta.json", meta)
    return list(read_jsonl(sample_path))


def base_metrics(language: str, cfg: dict, session_id: str) -> None:
    """Metrics of the untouched base model ('generation -1'), so the gen-0 adaptation and the starting level of each
    language are on record (chain id BASE-<lang>)."""
    cid = f"BASE-{language}"; gdir = CHAINS / cid / "base"
    if (gdir / "step.json").exists():
        print(f"[base] {language} already done"); return
    gdir.mkdir(parents=True, exist_ok=True)
    base = cfg["base_model"]["hf"]
    sample = sample_from(base, language, cfg, cfg["sampling"], int(cfg["seed"]) - 1, gdir)
    write_jsonl(RESULTS / "samples" / f"{cid}_base_50.jsonl", sample[:50])
    from metrics import compute_all
    compute_all(cid, -1, base, language, sample, cfg, sidecar_dir=gdir, reference_checkpoint=None)
    write_json(gdir / "step.json", {"chain_id": cid, "generation": -1, "language": language, "regime": "BASE", "session_id": session_id,
                                    "base_model": cfg["base_model"], "sample": read_json(gdir / "sample_meta.json"), "created_at": now_iso()})
    log_decision(f"base-model metrics computed for {language}")


def gen0(spec: dict, cfg: dict, session_id: str) -> None:
    gid, lang = spec["id"], spec["language"]
    out = CHAINS / gid
    if (out / "step.json").exists():
        print(f"[gen0] {gid} already done"); return
    out.mkdir(parents=True, exist_ok=True)
    budget = resolve_tokens(cfg, spec.get("tokens"), lang)
    docs, acc = [], 0
    for d in read_jsonl(CORPORA / f"{lang}_seed.jsonl"):
        if acc >= budget:
            break
        docs.append(d); acc += int(d.get("n_tokens") or len(words(d["text"])))
    seed = int(cfg["seed"]) + int(spec.get("seed_offset", 0))
    ck = out / "checkpoint"
    if not (out / "train.json").exists() or not ck.exists():
        info = train(docs, cfg["base_model"]["hf"], out, cfg, seed)
        if info["nan"]:
            raise SystemExit(f"[gen0] NaN loss for {gid}; fix and re-run (max 3 attempts, log it)")
        write_json(out / "train.json", info)
    info = read_json(out / "train.json")
    sample = sample_from(str(ck), lang, cfg, cfg["sampling"], seed, out)
    write_jsonl(RESULTS / "samples" / f"{gid}_gen0_50.jsonl", sample[:50])
    from metrics import compute_all
    compute_all(gid, 0, str(ck), lang, sample, cfg, sidecar_dir=out, reference_checkpoint=str(ck))
    write_json(out / "step.json", {"chain_id": gid, "generation": 0, "language": lang, "regime": "GEN0", "session_id": session_id, "seed": seed,
                                   "seed_offset": int(spec.get("seed_offset", 0)), "budget_tokens": budget,
                                   "training_set": {"real_docs": len(docs), "synthetic_docs": 0, "components": ["seed"], "tokens": info["train_tokens"],
                                                    "target_tokens": info["target_tokens"], "real_target_tokens": info["real_target_tokens"], "synthetic_target_tokens": 0, "masked_prefix_tokens": 0},
                                   "train": info, "sample": read_json(out / "sample_meta.json"), "checkpoint_sha256": sha256_dir(ck), "base_model": cfg["base_model"], "created_at": now_iso()})
    shutil.rmtree(out / "trainer", ignore_errors=True)
    log_decision(f"gen-0 trained: {gid} ({acc:,} seed tokens, seed {seed})")


def assemble(chain: dict, g: int, cfg: dict, synthetic_for_training: list[dict], budget: int, seed: int) -> tuple[list[dict], list[str]]:
    cid, lang, regime = chain["id"], chain["language"], chain["regime"]; cdir = CHAINS / cid
    if regime == "REPLACE":
        return list(synthetic_for_training), [f"synthetic_gen{g}"]
    real = list(read_jsonl(CORPORA / f"{lang}_seed.jsonl"))
    if regime == "REAL-REPEAT":
        return real, ["seed"]
    if regime in ("ACCUMULATE", "ACCUMULATE-FILTER", "ACCUMULATE-SUBSAMPLE"):
        train_docs = list(real); components = ["seed"]
        for gg in range(1, g):
            fn = "synthetic_kept.jsonl" if regime == "ACCUMULATE-FILTER" else "synthetic.jsonl"
            train_docs += list(read_jsonl(cdir / f"gen_{gg}" / fn)); components.append(f"synthetic_gen{gg}")
        train_docs += list(synthetic_for_training); components.append(f"synthetic_gen{g}")
        if regime == "ACCUMULATE-SUBSAMPLE":
            rnd = random.Random(seed); rnd.shuffle(train_docs)
            sub, acc = [], 0
            for d in train_docs:
                if acc >= budget:
                    break
                sub.append(d); acc += int(d.get("n_tokens") or len(words(d["text"])))
            train_docs = sub; components.append("subsampled_to_budget")
        return train_docs, components
    raise SystemExit(f"unknown regime {regime}")


def step(chain: dict, g: int, cfg: dict, session_id: str) -> None:
    cid = chain["id"]; lang = chain["language"]; regime = chain["regime"]
    cdir = CHAINS / cid; gdir = cdir / f"gen_{g}"; gdir.mkdir(parents=True, exist_ok=True)
    if (gdir / "step.json").exists():
        print(f"[{cid}] gen {g} already complete"); return
    g0 = gen0_id(chain)
    prev_ck = (CHAINS / g0 / "checkpoint") if g == 1 else (cdir / f"gen_{g - 1}" / "checkpoint")
    if not prev_ck.exists():
        raise SystemExit(f"[{cid}] missing previous checkpoint {prev_ck}")
    seed = chain_seed(cfg, chain, g); budget = resolve_tokens(cfg, chain.get("tokens"), lang)
    sampling = chain.get("sampling") or cfg["sampling"]
    # 1. generate the synthetic corpus with the previous model
    gen_info, synthetic = None, []
    if regime != "REAL-REPEAT":
        syn_path = gdir / "synthetic.jsonl"; gen_info = read_json(gdir / "generate.json")
        if gen_info is None or not syn_path.exists():
            gen_info = generate(str(prev_ck), lang, budget, cfg, sampling, seed, syn_path)
            write_json(gdir / "generate.json", gen_info)
        synthetic = list(read_jsonl(syn_path))
    # 2. filter (FILTER regime only), topped up to the budget
    filter_stats = None; synthetic_for_training = synthetic
    if regime == "ACCUMULATE-FILTER":
        kept_path = gdir / "synthetic_kept.jsonl"
        if read_json(gdir / "filter.json") is None or not kept_path.exists():
            lo, hi, sc, L = ppl_band(str(CHAINS / g0 / "checkpoint"), lang, cfg)
            index = build_filter_index(chain, g, cfg, lang)
            kept, stats, log_rows = filter_docs(synthetic, lang, cfg, sc, (lo, hi), L, index)
            kept_tokens = sum(d["n_tokens"] for d in kept); generated_total = gen_info["tokens"]; rounds = 0
            fcfg = cfg["filter"]; max_total = float(fcfg.get("max_generation_multiple", 2.0)) * budget
            while fcfg.get("top_up", True) and kept_tokens < budget and generated_total < max_total:
                rounds += 1
                need = min(int((budget - kept_tokens) / max(0.2, stats["pass_rate"]) * 1.1) + 1000, int(max_total - generated_total))
                tp = gdir / f"synthetic_topup_{rounds}.jsonl"
                extra_info = generate(str(prev_ck), lang, need, cfg, sampling, seed + 100_000 * rounds, tp, start_index=len(synthetic))
                extra = list(read_jsonl(tp)); synthetic += extra; generated_total += extra_info["tokens"]
                k2, s2, l2 = filter_docs(extra, lang, cfg, sc, (lo, hi), L, index)
                kept += k2; log_rows += l2
                for key in ("input", "fail_script", "fail_repeat", "fail_ppl", "fail_dup", "kept"):
                    stats[key] += s2[key]
                stats["pass_rate"] = round(stats["kept"] / max(1, stats["input"]), 4); kept_tokens += sum(d["n_tokens"] for d in k2)
            used, acc = [], 0
            for d in kept:
                if acc >= budget:
                    break
                used.append(d); acc += d["n_tokens"]
            write_jsonl(kept_path, used); write_jsonl(gdir / "filter_log.jsonl", log_rows)
            write_json(gdir / "filter.json", {**stats, "kept_tokens_available": kept_tokens, "kept_tokens_used": acc, "kept_docs_used": len(used), "budget_tokens": budget,
                                              "topup_rounds": rounds, "generated_tokens_total": generated_total, "shortfall_tokens": max(0, budget - acc),
                                              "ppl_band_nll_per_token": [lo, hi], "ppl_band_percentiles": cfg["filter"]["ppl_percentile_band"], "band_max_len": L})
            del sc
        filter_stats = read_json(gdir / "filter.json"); synthetic_for_training = list(read_jsonl(kept_path))
    # 3. assemble the training set
    train_docs, components = assemble(chain, g, cfg, synthetic_for_training, budget, seed)
    n_real = sum(1 for d in train_docs if "prefix_id" not in d)
    # 4. train from the previous checkpoint (cached)
    ck = gdir / "checkpoint"
    if read_json(gdir / "train.json") is None or not ck.exists():
        info = train(train_docs, str(prev_ck), gdir, cfg, seed)
        if info["nan"]:
            raise SystemExit(f"[{cid}] NaN loss at gen {g}; fix and re-run (max 3 attempts, log it)")
        write_json(gdir / "train.json", info)
    info = read_json(gdir / "train.json")
    # 5. the fixed-prefix sample generated by the NEW checkpoint (+ the 50-document human-read file)
    sample = sample_from(str(ck), lang, cfg, sampling, seed, gdir)
    write_jsonl(RESULTS / "samples" / f"{cid}_gen{g}_50.jsonl", sample[:50])
    # 6. metrics and sidecars (held-out, probes, bias, lexical on continuations, sample NLL under the gen-0 model)
    from metrics import compute_all
    compute_all(cid, g, str(ck), lang, sample, cfg, sidecar_dir=gdir, reference_checkpoint=str(CHAINS / g0 / "checkpoint"))
    # 7. step record, state, cleanup
    write_json(gdir / "step.json", {"chain_id": cid, "generation": g, "language": lang, "regime": regime, "variant": chain.get("variant"), "session_id": session_id,
                                    "seed": seed, "seed_offset": int(chain.get("seed_offset", 0)), "gen0_id": g0, "budget_tokens": budget, "sampling": dict(sampling),
                                    "training_set": {"real_docs": n_real, "synthetic_docs": len(train_docs) - n_real, "components": components, "tokens": info["train_tokens"],
                                                     "target_tokens": info["target_tokens"], "real_target_tokens": info["real_target_tokens"],
                                                     "synthetic_target_tokens": info["synthetic_target_tokens"], "masked_prefix_tokens": info["masked_prefix_tokens"]},
                                    "generate": gen_info, "filter": filter_stats, "train": info, "sample": read_json(gdir / "sample_meta.json"),
                                    "checkpoint_sha256": sha256_dir(ck), "previous_checkpoint": str(prev_ck), "created_at": now_iso()})
    st = read_json(cdir / "state.json", {"chain_id": cid, "completed": []})
    st["completed"] = sorted(set(st["completed"] + [g])); st["updated_at"] = now_iso(); write_json(cdir / "state.json", st)
    shutil.rmtree(gdir / "trainer", ignore_errors=True)
    print(f"[{cid}] gen {g} complete: {info['target_tokens']:,} target tokens ({info['real_target_tokens']:,} real), loss {info['final_loss']}")


def status(cfg: dict) -> None:
    for lang in cfg["languages"]:
        print(f"BASE-{lang}: {'done' if (CHAINS / f'BASE-{lang}' / 'base' / 'step.json').exists() else 'missing'}")
    for gid in gen0_specs(cfg):
        print(f"{gid}: {'done' if (CHAINS / gid / 'step.json').exists() else 'missing'}")
    for c in all_chains(cfg):
        st = read_json(CHAINS / c["id"] / "state.json", {"completed": []})
        until = c.get("until") or cfg["generations"]
        print(f"{c['id']:28s} [{c['regime']:20s} prio {c.get('priority', 0)}] completed generations: {st['completed']} / planned 1..{until}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain"); ap.add_argument("--until", type=int); ap.add_argument("--gen0", help="language (EN/BN) or a gen-0 id such as GEN0-EN-s2")
    ap.add_argument("--base", help="language: metrics of the untouched base model"); ap.add_argument("--status", action="store_true")
    ap.add_argument("--session-id", default="local"); ap.add_argument("--max-hours", type=float, default=1e9, help="stop starting new steps after this many hours")
    ap.add_argument("--deadline", type=float, default=None, help="unix time; stop starting new steps after it (run_rented.py passes the cap)")
    a = ap.parse_args(); cfg = load_chains_cfg(); ensure_dirs()
    if a.status:
        status(cfg); return
    if a.base:
        base_metrics(a.base, cfg, a.session_id); return
    if a.gen0:
        specs = gen0_specs(cfg)
        gid = a.gen0 if a.gen0 in specs else f"GEN0-{a.gen0}"
        if gid not in specs:
            raise SystemExit(f"unknown gen-0 {a.gen0}; known: {list(specs)}")
        gen0(specs[gid], cfg, a.session_id); return
    if not a.chain:
        ap.error("use --chain, --gen0, --base or --status")
    chain = next((c for c in all_chains(cfg) if c["id"] == a.chain), None)
    if chain is None:
        raise SystemExit(f"unknown chain {a.chain}; known: {[c['id'] for c in all_chains(cfg)]}")
    until = a.until or chain.get("until") or cfg["generations"]
    t0 = time.time()
    for g in range(1, until + 1):
        if (time.time() - t0) / 3600 > a.max_hours or (a.deadline and time.time() > a.deadline):
            print(f"[{chain['id']}] time budget reached before gen {g}; resume later"); break
        step(chain, g, cfg, a.session_id)


if __name__ == "__main__":
    main()
