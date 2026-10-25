"""A/B test on the host: base gemma-3-270m, the same 64 prefixes per language and the same request seeds, prompt token ids with
and without the <bos> token. Prints the harness's own repetition / degeneration / script / empty measures. Diagnostic only."""
import json
import sys

sys.path.insert(0, "/workspace/CG4_model_collapse_lowresource_experiment/harness")
from common import CORPORA, read_jsonl, repeat_4gram_rate, script_ratio, words  # noqa: E402
from run_chain import lang_lengths, load_chains_cfg  # noqa: E402
from vllm import LLM, SamplingParams  # noqa: E402

cfg = load_chains_cfg()
llm = LLM(model=cfg["base_model"]["hf"], dtype="bfloat16", max_model_len=400, gpu_memory_utilization=0.6, seed=1)
bos = llm.get_tokenizer().bos_token_id
for lang in ("EN", "BN"):
    pre = [p for _, p in zip(range(64), read_jsonl(CORPORA / f"prefixes_{lang}.jsonl"))]
    _, max_new = lang_lengths(cfg, lang)
    for tag, add in (("without BOS", False), ("with BOS   ", True)):
        prompts = [{"prompt_token_ids": ([bos] if add else []) + list(p["prefix_ids"])} for p in pre]
        sps = [SamplingParams(temperature=1.0, top_p=1.0, max_tokens=max_new, seed=1000 + j) for j in range(len(pre))]
        outs = llm.generate(prompts, sps, use_tqdm=False)
        texts = [o.outputs[0].text for o in outs]
        ws = [[w.lower() for w in words(t)] for t in texts]
        rep = [repeat_4gram_rate(w) for w in ws]
        print(json.dumps({"lang": lang, "prompt": tag, "mean_repeat_4gram": round(sum(rep) / len(rep), 3), "degenerate_docs(>=0.5)": round(sum(r >= 0.5 for r in rep) / len(rep), 3),
                          "script_docs_ge95": round(sum(script_ratio(t, lang) >= 0.95 for t in texts) / len(texts), 3), "empty": sum(1 for w in ws if not w),
                          "mean_words": round(sum(len(w) for w in ws) / len(ws), 1)}, ensure_ascii=False), flush=True)
        print("   e.g.:", repr(texts[1][:150]), flush=True)
