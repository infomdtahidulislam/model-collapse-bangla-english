"""Diagnostic, G3 pilot (2026-10-14): is the generation-1 held-out NLL change a pipeline artefact? Run on the host:

  python harness/tools/drift_check.py EN 200 300

Uses the harness's own scorer (metrics.Scorer) on the base model, the generation-0 checkpoint and the REPLACE generation-1
checkpoint of one language:
  1. every tokenizer adds <bos> as the first token;
  2. re-scoring the first N held-out documents reproduces the per-document NLL stored in each step's heldout_nll.jsonl;
  3. mean per-token NLL of M synthetic training documents (prefix + continuation) under each model;
  4. parameter drift gen-0 -> gen-1 (relative L2 norm of the difference, all weights).
Prints one JSON line per check; writes nothing. Diagnostic only, not a reported metric."""
import json
import sys
from pathlib import Path

PKG = Path("/workspace/CG4_model_collapse_lowresource_experiment")
sys.path.insert(0, str(PKG / "harness"))
from common import CHAINS, HELDOUT, load_chains_cfg, read_jsonl  # noqa: E402
from metrics import Scorer  # noqa: E402

lang, n_held, n_syn = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
cfg = load_chains_cfg()
models = {"base": cfg["base_model"]["hf"],
          "gen0": str(CHAINS / f"GEN0-{lang}" / "checkpoint"),
          "gen1": str(CHAINS / f"{lang}-REPLACE" / "gen_1" / "checkpoint")}
stored = {"gen0": CHAINS / f"GEN0-{lang}" / "heldout_nll.jsonl",
          "gen1": CHAINS / f"{lang}-REPLACE" / "gen_1" / "heldout_nll.jsonl"}
held = [d for d in read_jsonl(HELDOUT / f"{lang}_heldout.jsonl") if not d.get("fresh")][:n_held]
syn = [d for _, d in zip(range(n_syn), read_jsonl(CHAINS / f"{lang}-REPLACE" / "gen_1" / "synthetic.jsonl"))]
syn_texts = [d["prefix"] + d["text"] for d in syn]

params = {}
for name, ck in models.items():
    sc = Scorer(ck)
    ids = sc.tok("test")["input_ids"]
    print(json.dumps({"lang": lang, "model": name, "bos_first": ids[0] == sc.tok.bos_token_id, "bos_id": sc.tok.bos_token_id}), flush=True)
    res = sc.nll_batch([d["text"] for d in held])
    per_doc = [a / n for a, n in res if n > 0]
    rec = {"lang": lang, "model": name, "heldout_docs": len(per_doc), "heldout_macro_nll": round(sum(per_doc) / len(per_doc), 4)}
    if name in stored:
        ref = {r["doc_id"]: r for r in read_jsonl(stored[name]) if r.get("set") == "heldout"}
        diffs = [abs(a / n - ref[d["doc_id"]]["nll_total"] / ref[d["doc_id"]]["n_tokens"]) for d, (a, n) in zip(held, res) if n > 0 and d["doc_id"] in ref]
        rec.update({"matched_docs": len(diffs), "max_abs_diff_vs_sidecar": round(max(diffs), 6) if diffs else None})
    sres = sc.nll_batch(syn_texts)
    tot, ntok = sum(a for a, n in sres), sum(n for a, n in sres)
    rec["synthetic_micro_nll"] = round(tot / max(1, ntok), 4)
    print(json.dumps(rec), flush=True)
    if name in ("gen0", "gen1"):
        params[name] = {k: v.detach().float().cpu() for k, v in sc.model.state_dict().items()}
    del sc

num = sum(float(((params["gen1"][k] - params["gen0"][k]) ** 2).sum()) for k in params["gen0"])
den = sum(float((params["gen0"][k] ** 2).sum()) for k in params["gen0"])
print(json.dumps({"lang": lang, "relative_l2_drift_gen0_to_gen1": round((num / den) ** 0.5, 6), "tensors": len(params["gen0"])}), flush=True)
