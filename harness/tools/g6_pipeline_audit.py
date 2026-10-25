#!/usr/bin/env python
"""G6 pipeline audit after the anchor (H0) failed: by the registered rule the pipeline is suspect, so the agent checks it for a
fault before the analysis is reported. Read-only on the files extracted from the G4b archive (results/g6_extract/).

1. Sampling settings of every step (step.json, generate.json, sample_meta.json) against the registration (03 §: temperature 1.0,
   top-p 1.0; the -topp95 pair top-p 0.95), plus the registered bug limits (exact-duplicate and empty rate <= 0.05) and NaN loss.
2. distinct-2 recomputed for every step from its archived 2,000-document sample with an independent implementation of the
   registered window (05 §2: lower-cased word split, documents in the seeded order random.Random(seed + generation), first
   50,000 tokens), compared with results/metrics.jsonl.
3. Gemma reserved placeholder tokens written as text (<unusedNNNN>) in every synthetic training corpus and every sample.

Writes results/analysis/audit/*.csv and results/analysis/audit/pipeline_audit.md (numbers only).

usage: python harness/tools/g6_pipeline_audit.py
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, chain_meta, load_chains_cfg, log_decision, now_iso, read_jsonl, utf8_stdout, words  # noqa: E402

utf8_stdout()
ROOT = RESULTS / "g6_extract" / "results" / "chains"
OUT = RESULTS / "analysis" / "audit"
UNUSED = re.compile(r"<unused\d+>")


def step_dirs() -> list[tuple[str, int, Path]]:
    """One entry per step (chain, generation): the step.json folders, plus base-model sample folders that have no step.json."""
    out: dict[tuple[str, int], Path] = {}
    for p in sorted(ROOT.glob("*/**/step.json")):
        d = json.load(open(p, encoding="utf-8"))
        out[(d["chain_id"], int(d["generation"]))] = p.parent
    for p in sorted(ROOT.glob("BASE-*/*/sample.jsonl")):
        out.setdefault((p.parts[-3], -1), p.parent)
    return [(c, g, d) for (c, g), d in sorted(out.items())]


def distinct2(sample: Path, seed: int, window: int) -> tuple[float, int]:
    docs = [d["text"] for d in read_jsonl(sample)]
    toks = [[w.lower() for w in words(t)] for t in docs]
    order = list(range(len(docs)))
    random.Random(seed).shuffle(order)
    win: list[str] = []
    for i in order:
        win += toks[i]
        if len(win) >= window:
            break
    win = win[:window]
    bigrams = list(zip(win, win[1:]))
    return len(set(bigrams)) / max(1, len(bigrams)), len(win)


def main() -> None:
    cfg = load_chains_cfg()
    meta = chain_meta(cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    recorded = {(r["chain_id"], r["generation"]): r["value"] for r in read_jsonl(RESULTS / "metrics.jsonl") if r["metric"] == "distinct_2"}
    steps = step_dirs()
    samp_rows, d2_rows, un_rows = [], [], []
    for cid, g, d in steps:
        m = meta.get(cid, {})
        want_tp = float(((m.get("sampling") or {}).get("top_p")) or cfg["sampling"]["top_p"]) if m else float(cfg["sampling"]["top_p"])
        st = json.load(open(d / "step.json", encoding="utf-8")) if (d / "step.json").exists() else {}
        for kind, f in (("generate", d / "generate.json"), ("sample", d / "sample_meta.json")):
            if not f.exists():
                continue
            j = json.load(open(f, encoding="utf-8"))
            s = j.get("sampling") or {}
            exp_tp = want_tp if not cid.startswith(("GEN0-", "BASE-")) else float(cfg["sampling"]["top_p"])
            flags = []
            if s.get("temperature") != 1.0:
                flags.append(f"temperature {s.get('temperature')}")
            if s.get("top_p") != exp_tp:
                flags.append(f"top_p {s.get('top_p')} (expected {exp_tp})")
            for k in ("exact_duplicate_rate", "empty_rate"):
                if (j.get(k) or 0) > 0.05:
                    flags.append(f"{k} {j.get(k)} > 0.05")
            samp_rows.append({"chain_id": cid, "generation": g, "record": kind, "engine": j.get("engine"), "temperature": s.get("temperature"),
                              "top_p": s.get("top_p"), "expected_top_p": exp_tp, "prefix_tokens": j.get("prefix_tokens"),
                              "max_new_tokens": j.get("max_new_tokens"), "docs": j.get("docs"), "exact_duplicate_rate": j.get("exact_duplicate_rate"),
                              "empty_rate": j.get("empty_rate"), "cap_hit_rate": j.get("cap_hit_rate"), "mean_words": j.get("mean_words"),
                              "flags": "; ".join(flags) or "ok"})
        tr = st.get("train") or {}
        if tr:
            samp_rows.append({"chain_id": cid, "generation": g, "record": "train", "flags": "NaN loss" if tr.get("nan") else "ok",
                              "docs": tr.get("real_docs", 0) + tr.get("synthetic_docs", 0)})
        sp = d / "sample.jsonl"
        if sp.exists():
            v, n = distinct2(sp, int(cfg["seed"]) + g, int(cfg["metrics"]["ttr_window_tokens"]))
            rec = recorded.get((cid, g))
            d2_rows.append({"chain_id": cid, "generation": g, "recomputed": v, "recorded": rec, "abs_diff": abs(v - rec) if rec is not None else None,
                            "window_tokens": n})
        for f in sorted(d.glob("synthetic*.jsonl")) + ([sp] if sp.exists() else []):
            n_docs = n_with = n_occ = 0
            for r in read_jsonl(f):
                n_docs += 1
                k = len(UNUSED.findall(r.get("text") or ""))
                n_occ += k
                n_with += k > 0
            un_rows.append({"chain_id": cid, "generation": g, "file": f.name, "docs": n_docs, "docs_with_unused": n_with,
                            "share_docs": n_with / max(1, n_docs), "occurrences": n_occ})
        print(f"{cid} gen {g}: checked", flush=True)

    import pandas as pd
    S, D, U = pd.DataFrame(samp_rows), pd.DataFrame(d2_rows), pd.DataFrame(un_rows)
    S.to_csv(OUT / "sampling_settings.csv", index=False)
    D.to_csv(OUT / "distinct2_reproduction.csv", index=False)
    U.to_csv(OUT / "unused_tokens.csv", index=False)
    bad = S[S["flags"] != "ok"]
    dmax = float(D["abs_diff"].max()) if len(D) else float("nan")
    syn = U[U["file"].str.startswith("synthetic")]
    rep = ["# G6 pipeline audit (numbers only; the interpretation is written by the authors)", "",
           f"Made by `harness/tools/g6_pipeline_audit.py` at {now_iso()} from `results/g6_extract/` (the G4b archive, SHA-256 checked).", "",
           "## 1. Sampling settings and bug limits",
           f"- {len(S)} records over {len(steps)} steps (generation, sample, training). Expected: temperature 1.0; top-p 1.0, 0.95 for the "
           f"-topp95 pair; exact-duplicate and empty rate <= 0.05; no NaN loss. Records that differ: {len(bad)}. File: `audit/sampling_settings.csv`."]
    rep += [f"  - {r.chain_id} gen {r.generation} {r.record}: {r.flags}" for r in bad.itertuples()][:40]
    rep += ["", "## 2. distinct-2 recomputed from the archived samples",
            f"- {len(D)} steps; largest absolute difference from `results/metrics.jsonl`: {dmax:.2e}. File: `audit/distinct2_reproduction.csv`.", "",
            "## 3. Reserved placeholder tokens written as text (`<unusedNNNN>`)",
            f"- Synthetic training corpora: {int((syn['docs_with_unused'] > 0).sum())} of {len(syn)} files contain at least one; "
            f"{int(syn['docs_with_unused'].sum())} of {int(syn['docs'].sum())} documents ({100 * syn['docs_with_unused'].sum() / max(1, syn['docs'].sum()):.3f}%), "
            f"{int(syn['occurrences'].sum())} occurrences. Per chain and generation: `audit/unused_tokens.csv`.",
            "- Decoding and training keep them exactly: the Gemma-3 tokenizer lists the 6,242 `<unusedN>` tokens as added tokens that are not "
            "special, so `decode(..., skip_special_tokens=True)` writes them out and re-encoding for training returns the same single token "
            "ids (checked 2026-10-18 with transformers 5.20.1: `The river<unused42> flows` -> [818, 8858, 48, 17752], identical to the ids decoded).", ""]
    gen1 = syn[syn["generation"] == 1].groupby("chain_id")[["docs_with_unused", "docs"]].sum()
    rep.append("- Generation 1 (text written by the generation-0 models): " + "; ".join(
        f"{c} {int(r.docs_with_unused)} of {int(r.docs)} documents" for c, r in gen1.iterrows()))
    (OUT / "pipeline_audit.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))
    log_decision(f"G6 pipeline audit (harness/tools/g6_pipeline_audit.py -> results/analysis/audit/): {len(S)} sampling/training records "
                 f"over {len(steps)} steps, {len(bad)} differing from the registration or bug limits; distinct-2 recomputed for {len(D)} steps, "
                 f"largest difference from metrics.jsonl {dmax:.2e}; <unusedNNNN> in {int(syn['docs_with_unused'].sum())} of "
                 f"{int(syn['docs'].sum())} synthetic training documents. Numbers only.")


if __name__ == "__main__":
    main()
