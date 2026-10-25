"""Print selected metric rows (and step samples) from a CG4 results folder. usage: python show_metrics.py <package_dir> [chain ...]"""
import json
import sys
from pathlib import Path

pkg = Path(sys.argv[1]); chains = set(sys.argv[2:])
KEEP = ["log_ppl_heldout", "log_ppl_fresh", "log_ppl_micro_heldout", "bpb_heldout", "bpb_fresh", "tail_fact_recall_ALL", "tail_fact_recall_HEAD",
        "tail_fact_recall_MID", "tail_fact_recall_TAIL", "tail_fact_recall_norm_ALL", "stereotype_preference", "distinct_2", "script_ratio_mean",
        "script_docs_ge95", "repeat_4gram_rate", "degenerate_docs", "mean_length_words", "cap_hit_rate", "empty_docs", "fertility_tokens_per_word",
        "sample_nll_ref_mean"]
rows = [json.loads(line) for line in open(pkg / "results" / "metrics.jsonl", encoding="utf-8") if line.strip()]
for r in rows:
    if r["metric"] in KEEP and (not chains or r["chain_id"] in chains):
        cid, g, m = r["chain_id"], r["generation"], r["metric"]
        print(f"{cid:9s} g{g:>2} {m:28s} {r['value']:9.4f}  [{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  n={r['n']}")
for sj in sorted((pkg / "results" / "chains").glob("*/*/step.json")) + sorted((pkg / "results" / "chains").glob("GEN0-*/step.json")):
    st = json.load(open(sj, encoding="utf-8"))
    if chains and st.get("chain_id") not in chains:
        continue
    s = st.get("sample") or {}
    t = st.get("train") or {}
    print(sj.relative_to(pkg), "| sample:", {k: s.get(k) for k in ("engine", "docs", "tokens", "exact_duplicate_rate", "empty_rate", "cap_hit_rate", "mean_words", "generate_seconds", "gpu_memory_utilization")},
          "| train:", {k: t.get(k) for k in ("train_tokens", "optimizer_steps", "loss_first", "final_loss", "nan", "train_seconds", "micro_batch_seqs", "grad_accum_steps")} if t else "")
