"""Diagnostic, G3 pilot read follow-up (2026-10-14): how much probability does each model put on tokens of other writing
systems while reading real text? Run on the host:

  python harness/tools/tail_mass_check.py EN 200

For the base model, generation 0 and REPLACE generation 1 of one language, over the first N held-out documents: the mean
(over predicted positions) of the softmax mass on "foreign" vocabulary entries, i.e. tokens whose text contains a letter
outside the target script (EN: not Latin; BN: neither Bengali nor Latin). Also the mass on tokens that never occur in the
language's seed corpus, and the generation_config.json sampling fields of each checkpoint. Prints JSON lines; writes
nothing. Diagnostic only, not a reported metric."""
import json
import sys
from pathlib import Path

import regex
import torch

PKG = Path("/workspace/CG4_model_collapse_lowresource_experiment")
sys.path.insert(0, str(PKG / "harness"))
from common import CHAINS, CORPORA, HELDOUT, load_chains_cfg, read_jsonl  # noqa: E402

lang, n_docs = sys.argv[1], int(sys.argv[2])
cfg = load_chains_cfg()
models = {"base": cfg["base_model"]["hf"], "gen0": str(CHAINS / f"GEN0-{lang}" / "checkpoint"),
          "gen1": str(CHAINS / f"{lang}-REPLACE" / "gen_1" / "checkpoint")}
FOREIGN = {"EN": regex.compile(r"(?V1)[\p{L}--\p{Script=Latin}]"), "BN": regex.compile(r"(?V1)[\p{L}--[\p{Script=Bengali}\p{Script=Latin}]]")}[lang]

from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, GenerationConfig  # noqa: E402

tok = AutoTokenizer.from_pretrained(models["base"])
mc = AutoConfig.from_pretrained(models["base"])
V = getattr(mc, "vocab_size", None) or getattr(getattr(mc, "text_config", None), "vocab_size")   # logits width (262,144); len(tok) is 262,145
foreign = torch.zeros(V, dtype=torch.bool)
for i in range(V):
    if FOREIGN.search(tok.decode([i])):
        foreign[i] = True
seen = torch.zeros(V, dtype=torch.bool)
for d in read_jsonl(CORPORA / f"{lang}_seed.jsonl"):
    ids_ = torch.tensor(tok(d["text"], add_special_tokens=False)["input_ids"], dtype=torch.long)
    seen[ids_[ids_ < V]] = True
print(json.dumps({"lang": lang, "vocab": V, "foreign_tokens": int(foreign.sum()), "tokens_seen_in_seed": int(seen.sum())}), flush=True)

held = [d["text"] for d in read_jsonl(HELDOUT / f"{lang}_heldout.jsonl") if not d.get("fresh")][:n_docs]
for name, ck in models.items():
    try:
        gc_ = GenerationConfig.from_pretrained(ck)
        gen_cfg = {k: getattr(gc_, k, None) for k in ("do_sample", "top_k", "top_p", "temperature")}
    except Exception as e:  # noqa
        gen_cfg = {"error": type(e).__name__}
    model = AutoModelForCausalLM.from_pretrained(ck, dtype=torch.bfloat16, device_map="cuda").eval()
    fm, um, npos = 0.0, 0.0, 0
    fmask, umask = foreign.to("cuda"), (~seen).to("cuda")
    with torch.no_grad():
        for t in held:
            ids = tok(t, return_tensors="pt", truncation=True, max_length=1024).to("cuda")
            logits = model(**ids).logits[0, :-1].float()
            p = torch.softmax(logits, dim=-1)
            fm += float(p[:, fmask].sum()); um += float(p[:, umask].sum()); npos += p.shape[0]
    print(json.dumps({"lang": lang, "model": name, "positions": npos, "mean_mass_foreign_script_tokens": round(fm / npos, 6),
                      "mean_mass_tokens_unseen_in_seed": round(um / npos, 6), "generation_config": gen_cfg}), flush=True)
    del model
    torch.cuda.empty_cache()
