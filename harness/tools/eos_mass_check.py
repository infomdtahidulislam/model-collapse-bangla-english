"""Diagnostic, G3 follow-up (2026-10-14): which vocabulary entries carry the probability mass that REPLACE generation 1
puts on tokens unseen in the seed corpus? Run on the host:

  python harness/tools/eos_mass_check.py EN 50

Over the first N held-out documents: the mean softmax mass on <eos>, <bos>, <pad>, <end_of_turn> and the 8 entries with the
largest mean mass, for the base model, generation 0 and generation 1; and that mass split by position (before and after the
synthetic documents' length, prefix + continuation cap). Prints JSON lines; writes nothing. Diagnostic only."""
import json
import sys
from pathlib import Path

import torch

PKG = Path("/workspace/CG4_model_collapse_lowresource_experiment")
sys.path.insert(0, str(PKG / "harness"))
from common import CHAINS, HELDOUT, load_chains_cfg, read_jsonl  # noqa: E402
from run_chain import lang_lengths  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

lang, n_docs = sys.argv[1], int(sys.argv[2])
cfg = load_chains_cfg()
pre_toks, max_new = lang_lengths(cfg, lang)
cut = 1 + pre_toks + max_new          # <bos> + prefix + continuation cap: where a capped synthetic document ends
models = {"base": cfg["base_model"]["hf"], "gen0": str(CHAINS / f"GEN0-{lang}" / "checkpoint"),
          "gen1": str(CHAINS / f"{lang}-REPLACE" / "gen_1" / "checkpoint")}
tok = AutoTokenizer.from_pretrained(models["base"])
special = {"eos": tok.eos_token_id, "bos": tok.bos_token_id, "pad": tok.pad_token_id, "end_of_turn": tok.convert_tokens_to_ids("<end_of_turn>")}
held = [d["text"] for d in read_jsonl(HELDOUT / f"{lang}_heldout.jsonl") if not d.get("fresh")][:n_docs]
for name, ck in models.items():
    model = AutoModelForCausalLM.from_pretrained(ck, dtype=torch.bfloat16, device_map="cuda").eval()
    tot = None; npos = 0; eos_before = eos_after = 0.0; n_before = n_after = 0
    with torch.no_grad():
        for t in held:
            ids = tok(t, return_tensors="pt", truncation=True, max_length=1024).to("cuda")
            p = torch.softmax(model(**ids).logits[0, :-1].float(), dim=-1)
            tot = p.sum(0) if tot is None else tot + p.sum(0)
            npos += p.shape[0]
            e = p[:, special["eos"]]
            k = min(cut - 1, e.shape[0])           # position i predicts token i+1; positions >= cut-1 predict beyond the cap
            eos_before += float(e[:k].sum()); n_before += k
            eos_after += float(e[k:].sum()); n_after += e.shape[0] - k
    mean = tot / npos
    top = torch.topk(mean, 8)
    print(json.dumps({"lang": lang, "model": name, "positions": npos,
                      "mass": {k: round(float(mean[v]), 6) for k, v in special.items() if v is not None},
                      "eos_mass_before_cap": round(eos_before / max(1, n_before), 6), "eos_mass_after_cap": round(eos_after / max(1, n_after), 6),
                      "cap_position": cut,
                      "top8": [(int(i), tok.convert_ids_to_tokens(int(i)), round(float(m), 6)) for m, i in zip(top.values, top.indices)]},
                     ensure_ascii=False), flush=True)
    del model
    torch.cuda.empty_cache()
