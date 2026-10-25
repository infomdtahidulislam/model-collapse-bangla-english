#!/usr/bin/env python3
"""
No-GPU sanity checks. Run before every gate.
  python harness/tests/test_sanity.py            # config, schemas, data files if present
  python harness/tests/test_sanity.py --results  # also: step composition (REPLACE trains on generated tokens only; accumulation
                                                 #       components), generation quality (duplicate rate, empty rate), sample files,
                                                 #       leakage (no held-out doc ids in any synthetic corpus), FILTER shortfall, schemas
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import (CHAINS, CORPORA, HELDOUT, PROBES, RESULTS, SCHEMAS, all_chains, confirmatory_chains, load_chains_cfg,  # noqa: E402
                    load_corpora_cfg, read_json, read_jsonl, robustness_chains, utf8_stdout)

utf8_stdout()
FAIL = []


def check(cond: bool, msg: str) -> None:
    print(("[ok]   " if cond else "[FAIL] ") + msg)
    if not cond:
        FAIL.append(msg)


def note(msg: str) -> None:
    print("[note] " + msg)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--results", action="store_true"); a = ap.parse_args()
    cfg = load_chains_cfg(); ccfg = load_corpora_cfg()
    check(set(cfg["languages"]) == {"EN", "BN"}, "two languages EN and BN")
    check(set(cfg["regimes"]) == {"REPLACE", "ACCUMULATE", "ACCUMULATE-FILTER"}, "three confirmatory regimes")
    check(cfg["base_model"]["params_m"] <= 300, f"base model within the 300M cap ({cfg['base_model']['params_m']}M)")
    dt = cfg["training"]["dtype"]
    check(dt in ("bfloat16", "float16"), f"training dtype {dt}")
    if dt == "float16":
        note("float16 is the Kaggle T4 fallback only; gemma-3 is unstable in fp16 and vLLM refuses it: on the rented 4090 use bfloat16 (deviation if changed after Gate 0)")
    check(cfg["training"].get("prefix_mode", "masked") in ("masked", "dropped") and not cfg["training"].get("train_on_prefix", False),
          f"prefix tokens excluded from the loss (prefix_mode={cfg['training'].get('prefix_mode', 'masked')}): REPLACE trains on generated tokens only")
    if str(cfg.get("length_unit", "tokens")) == "words":
        check(cfg.get("prefix_words", 0) > 0 and cfg.get("max_new_words", 0) > 0, f"lengths matched in words (prefix {cfg.get('prefix_words')} / continuation {cfg.get('max_new_words')} words)")
    check(cfg["sampling"]["temperature"] == 1.0 and cfg["sampling"]["top_p"] == 1.0, "pure ancestral sampling for the confirmatory chains")
    check(abs(sum(ccfg["domain_mix"].values()) - 1.0) < 1e-6, "domain mix sums to 1")
    chains = all_chains(cfg); ids = [c["id"] for c in chains]
    check(len(confirmatory_chains(cfg)) == 6, "six confirmatory chains")
    check(len(ids) == len(set(ids)), f"chain ids unique ({len(ids)} chains, {len(robustness_chains(cfg))} robustness)")
    check(all(c["regime"] in ("REPLACE", "ACCUMULATE", "ACCUMULATE-FILTER", "ACCUMULATE-SUBSAMPLE", "REAL-REPEAT") for c in chains), "every chain has a known regime")
    check(all((c.get("seed_offset", 0) == 0) == (c.get("gen0") is None or not str(c.get("gen0")).endswith(("-s2", "-s3"))) for c in chains), "re-seeded chains name a re-seeded gen-0")
    check(int(cfg.get("replace_extension_generations", 0) or 0) >= cfg["generations"], "REPLACE extension not below the confirmatory generation count")
    check(cfg["filter"].get("top_up", True) is True and cfg["filter"].get("max_generation_multiple", 2.0) >= 1.0, "FILTER regime quantity-matched by top-up")
    # <eos> is a training target only where a document really ended (bug fixed 2026-10-14, G3 pilot): a continuation cut
    # at the length cap, or a real document cut by the corpus builder, must not teach the model to stop there
    from run_chain import pack
    blocks = pack([([2, 10, 11], [-100, 10, 11], True), ([2, 20, 21], [-100, 20, 21], False), ([2, 30], [-100, 30], True)], 11, 1)
    check(blocks == [([2, 10, 11, 1, 2, 20, 21, 1, 2, 30, 1], [-100, 10, 11, 1, -100, 20, 21, -100, -100, 30, 1])],
          "pack: <eos> is a target after complete documents and context only after cut ones")
    blocks = pack([([2, 10, 11], [-100, 10, 11], True), ([2, 20, 21], [-100, 20, 21], False)], 8, 1)
    check(blocks == [([2, 10, 11, 1, 2, 20, 21, 1], [-100, 10, 11, 1, -100, 20, 21, -100])], "pack: labels of a cut document end in -100, not <eos>")
    try:
        import jsonschema  # noqa
        have_js = True
    except Exception:
        have_js = False; note("jsonschema not installed; schema validation skipped")
    schemas = {}
    for s in ("step", "metric", "document"):
        p = SCHEMAS / f"{s}.schema.json"; check(p.exists(), f"schema present: {p.name}")
        if p.exists():
            schemas[s] = json.load(open(p, encoding="utf-8"))
    for lang in cfg["languages"]:
        seed_p, ho_p = CORPORA / f"{lang}_seed.jsonl", HELDOUT / f"{lang}_heldout.jsonl"
        if seed_p.exists() and ho_p.exists():
            seed_ids = {d["doc_id"] for d in read_jsonl(seed_p)}; ho = list(read_jsonl(ho_p)); ho_ids = {d["doc_id"] for d in ho}
            check(not (seed_ids & ho_ids), f"{lang}: held-out disjoint from seed ({len(seed_ids)} seed, {len(ho_ids)} held-out)")
            n_fresh = sum(1 for d in ho if d.get("fresh"))
            check(n_fresh > 0, f"{lang}: fresh held-out slice present ({n_fresh} docs)")
            if 0 < n_fresh < 300:
                note(f"{lang}: fresh slice has only {n_fresh} docs; state it (02 §2)")
            pre = list(read_jsonl(CORPORA / f"prefixes_{lang}.jsonl"))
            if pre:
                man_tok = (read_json(CORPORA / "manifest.json") or {}).get("tokenizer", "")
                if str(man_tok).startswith("hf:"):
                    check(all(p.get("prefix_ids") for p in pre), f"{lang}: prefixes carry token ids ({len(pre)} prefixes)")
                else:
                    note(f"{lang}: corpora were built without the HF tokenizer ({man_tok}); on the host prefixes must carry token ids")
                check(len(pre) >= cfg["metrics"]["n_sample_docs"], f"{lang}: at least n_sample_docs prefixes for the fixed sample")
        else:
            note(f"{lang}: corpora not yet built")
        pp = PROBES / f"{lang}_tail_facts.jsonl"
        if pp.exists():
            probes = list(read_jsonl(pp)); strata = Counter(p["stratum"] for p in probes)
            check(all(len(p["distractors"]) == 3 for p in probes), f"{lang}: every probe has 3 distractors ({len(probes)} probes, strata {dict(strata)})")
            check(all(p["gold"] not in p["distractors"] for p in probes), f"{lang}: gold never among the distractors")
            subs = Counter(p["subject"] for p in probes)
            check(max(subs.values(), default=0) <= 1, f"{lang}: one probe per subject")
    man = read_json(CORPORA / "manifest.json")
    if man and len(man.get("languages", {})) == 2:
        t = [v["seed_tokens"] for v in man["languages"].values()]
        check(abs(t[0] - t[1]) / max(t) <= 0.02, f"seed token counts matched within 2%: {t}")
        w = {k: v.get("seed_words") for k, v in man["languages"].items()}
        note(f"seed words per language (token-matched budgets carry different word counts; reported, and the EN-REPLACE-WM chain controls it): {w}")
        if str(cfg.get("length_unit", "tokens")) == "words":
            check(all(v.get("prefix_tokens") and v.get("max_new_tokens") for v in man["languages"].values()),
                  "manifest carries per-language prefix/continuation token lengths: " + str({k: (v.get("prefix_tokens"), v.get("max_new_tokens")) for k, v in man["languages"].items()}))
    if a.results:
        ho_ids = {d["doc_id"] for lang in cfg["languages"] for d in read_jsonl(HELDOUT / f"{lang}_heldout.jsonl")}
        n_sample = cfg["metrics"]["n_sample_docs"]
        for c in chains:
            for gdir in sorted((CHAINS / c["id"]).glob("gen_*")):
                st = read_json(gdir / "step.json")
                if not st:
                    continue
                g = st["generation"]; comp = st["training_set"]; tag = f"{c['id']} gen {g}"
                if c["regime"] == "REPLACE":
                    check(comp["real_docs"] == 0 and comp.get("real_target_tokens", 0) == 0 and comp["components"] == [f"synthetic_gen{g}"], f"{tag}: REPLACE trained on generated tokens only")
                elif c["regime"] == "REAL-REPEAT":
                    check(comp["synthetic_docs"] == 0 and comp["components"] == ["seed"], f"{tag}: REAL-REPEAT trained on the seed only")
                else:
                    exp = ["seed"] + [f"synthetic_gen{gg}" for gg in range(1, g + 1)] + (["subsampled_to_budget"] if c["regime"] == "ACCUMULATE-SUBSAMPLE" else [])
                    check(comp["components"] == exp, f"{tag}: accumulation components {comp['components']}")
                gen = st.get("generate") or {}
                if gen:
                    check(gen.get("exact_duplicate_rate", 1.0) <= 0.05, f"{tag}: exact-duplicate rate of generated continuations {gen.get('exact_duplicate_rate')} <= 0.05")
                    check(gen.get("empty_rate", 1.0) <= 0.05, f"{tag}: empty-generation rate {gen.get('empty_rate')} <= 0.05")
                    check(gen.get("tokens", 0) >= 0.95 * st.get("budget_tokens", cfg["tokens_per_generation"]), f"{tag}: generated tokens within 5% of the budget")
                sm = st.get("sample") or {}
                check(sm.get("docs", 0) >= 0.98 * n_sample, f"{tag}: sample from the trained checkpoint has {sm.get('docs')} docs (expected {n_sample})")
                if c["regime"] == "ACCUMULATE-FILTER" and st.get("filter"):
                    f = st["filter"]
                    if f.get("shortfall_tokens", 0) > 0:
                        note(f"{tag}: FILTER shortfall {f['shortfall_tokens']:,} tokens after {f.get('topup_rounds')} top-up rounds (reported, not a failure)")
                for fn in ("synthetic.jsonl",) + tuple(p.name for p in gdir.glob("synthetic_topup_*.jsonl")):
                    syn = gdir / fn
                    if syn.exists():
                        ids = {d["doc_id"] for d in read_jsonl(syn)}
                        check(not (ids & ho_ids), f"{tag}: no held-out ids in {fn}")
                for side in ("heldout_nll.jsonl", "probe_scores.jsonl", "sample_scores.jsonl"):
                    check((gdir / side).exists(), f"{tag}: sidecar {side} present")
                if have_js and "step" in schemas:
                    try:
                        jsonschema.validate(st, schemas["step"]); ok = True
                    except Exception as e:  # noqa
                        ok = False; print("   ", e)
                    check(ok, f"{tag}: step.json schema")
        mp = RESULTS / "metrics.jsonl"
        if mp.exists() and have_js and "metric" in schemas:
            bad = 0; n = 0
            for r in read_jsonl(mp):
                n += 1
                try:
                    jsonschema.validate(r, schemas["metric"])
                except Exception:
                    bad += 1
            check(bad == 0, f"metrics.jsonl: {bad} schema violations in {n} records")
    print("\nRESULT:", "PASS" if not FAIL else f"FAIL ({len(FAIL)} problems)")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
