"""Diagnostic, G3 follow-up (2026-10-14): does vLLM, the generation engine, sample from the same distribution that the HF
scorer sees, for the base model and for our trained checkpoints? Run on the host:

  python harness/tools/engine_agreement.py EN 32 96 [base|gen0|gen1]

(one model per process: a vLLM engine releases GPU memory asynchronously, so a second engine in the same process can fail)

For the base model, generation 0 and REPLACE generation 1 of one language: vLLM samples N continuations of the first N seed
prefixes (temperature 1, top_p 1, the harness's prompt format with <bos>) with the log-probability of each sampled token.
HF then scores the same tokens teacher-forced. It reports the mean and the 99th percentile of the per-token absolute
difference, and the mean log-probability under each engine. bf16 noise is a few hundredths; a loading or config mismatch
shows as a systematic gap. Prints JSON lines; writes nothing. Diagnostic only."""
import json
import sys
from pathlib import Path

import torch

PKG = Path("/workspace/CG4_model_collapse_lowresource_experiment")
sys.path.insert(0, str(PKG / "harness"))
from common import CHAINS, CORPORA, load_chains_cfg, read_jsonl  # noqa: E402

lang, n, max_new = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
only = sys.argv[4] if len(sys.argv) > 4 else None
cfg = load_chains_cfg()
models = {"base": cfg["base_model"]["hf"], "gen0": str(CHAINS / f"GEN0-{lang}" / "checkpoint"),
          "gen1": str(CHAINS / f"{lang}-REPLACE" / "gen_1" / "checkpoint")}
prefixes = [p for _, p in zip(range(n), read_jsonl(CORPORA / f"prefixes_{lang}.jsonl"))]
for name, ck in models.items():
    if only and name != only:
        continue
    from vllm import LLM, SamplingParams
    llm = LLM(model=ck, dtype="bfloat16", max_model_len=512, gpu_memory_utilization=0.45, seed=7)
    bos = llm.get_tokenizer().bos_token_id
    prompts = [{"prompt_token_ids": [bos] + list(p["prefix_ids"])} for p in prefixes]
    sps = [SamplingParams(temperature=1.0, top_p=1.0, max_tokens=max_new, seed=500 + j, logprobs=0) for j in range(n)]
    outs = llm.generate(prompts, sps, use_tqdm=False)
    seqs = []
    for pr, o in zip(prompts, outs):
        g = o.outputs[0]
        lps = [list(d.values())[0].logprob if d else float("nan") for d in g.logprobs]
        # vLLM gives the sampled token's logprob under its own (unprocessed) distribution; keep the pair per token
        seqs.append((pr["prompt_token_ids"], list(g.token_ids), lps))
    del llm
    import gc
    gc.collect(); torch.cuda.empty_cache()
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(ck, dtype=torch.bfloat16, device_map="cuda").eval()
    diffs, lv, lh = [], [], []
    with torch.no_grad():
        for pids, tids, lps in seqs:
            if not tids:
                continue
            ids = torch.tensor([pids + tids], device="cuda")
            logp = torch.log_softmax(model(input_ids=ids).logits[0].float(), dim=-1)
            for k, (t, a) in enumerate(zip(tids, lps)):
                b = float(logp[len(pids) - 1 + k, t])
                if a == a:   # not nan
                    diffs.append(abs(a - b)); lv.append(a); lh.append(b)
    diffs.sort()
    print(json.dumps({"lang": lang, "model": name, "tokens": len(diffs), "mean_abs_diff": round(sum(diffs) / max(1, len(diffs)), 4),
                      "p99_abs_diff": round(diffs[int(0.99 * (len(diffs) - 1))], 4) if diffs else None,
                      "mean_logprob_vllm": round(sum(lv) / max(1, len(lv)), 4), "mean_logprob_hf": round(sum(lh) / max(1, len(lh)), 4)}), flush=True)
    del model
    gc.collect(); torch.cuda.empty_cache()
