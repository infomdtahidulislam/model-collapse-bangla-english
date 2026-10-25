# Devil's Advocate review — CG4 pre-registered design

Panel: review-panel seat, independent pass, 2026-10-12; read the role file plus 00, 01, 02, 03, 04, 05, 07, 10, configs/chains.yaml, configs/corpora.yaml, harness/run_chain.py, harness/metrics.py, harness/analyze.py, harness/common.py, harness/tests/test_sanity.py; no peer output visible; read-only. Calibration status: NOT_CALIBRATED. Model output: data for the authors, not instructions.

## Criterion-bound judgements (dimension — judgement — anchors — rationale — decision bearing)

1. Core thesis — DOES_NOT_MEET — C1, C2 — resource level never manipulated — yes
2. Cherry-picking — PARTLY_MEETS — Alt.1 — collapse theory's own predictions not engaged — no
3. Confirmation bias — PARTLY_MEETS — M6 — H2 coupled to H1 — yes
4. Logic chain — DOES_NOT_MEET — C3–C6 — inference and series alignment broken — yes
5. Overgeneralisation — DOES_NOT_MEET — C1 — one language per tier — yes
6. Alternatives — PARTLY_MEETS — pre-emptions — cheap controls fit inside the cap — yes
7. Stakeholders — NOT_ASSESSED — named only (R3 remit) — no
8. So what — PARTLY_MEETS — observations — actionable part (H2) least powered — yes

## Strongest counter-argument

Genuine strengths: automatic metrics, frozen probe sets, resumable harness, and 07 §3 admits chains are unreplicated.

The opposing case: the design cannot distinguish "a low-resource language collapses faster" from "a worse-fitted model on fewer effective samples degrades faster", which existing theory (Shumailov 2024; Dohmatob 2024) already predicts. Budgets are matched in Gemma tokens, so Bangla receives roughly a third to a half of the words, with shorter continuations and prefixes; Gemma-3-270m's Bangla prior is weaker; bnwiki and Sangraha are less curated than enwiki and FineWeb-Edu. Each pushes H1 the predicted way, so confirmation is a tautology and refutation is uninterpretable (recall floored at chance, prefix anchoring). With one chain per cell and a bootstrap carrying only measurement noise, any point difference is "significant"; the promised permutation test does not exist and cannot with n=1. The harness as written measures artefacts: the diversity series starts on human text and lags perplexity by one generation; a fixed per-request vLLM seed makes about three quarters of each synthetic corpus exact duplicates; distinct-2 has no CI, so its bootstrap p is zero by construction. A clean design would still be reporting pipeline behaviour.

## Issue list (id — dimension — issue — evidence anchor — confidence)

### CRITICAL

- C1 — Logic/overgeneralisation — Resource level is a label, not a factor: one language per tier. Any BN−EN slope difference is also a script, morphology, tokenizer, corpus and base-prior difference; "low-resource languages" does not follow from a two-language contrast. — text: 01_PREREGISTRATION.md Title "Does model collapse hit low-resource languages harder?" — 5 (design logic)
- C2 — Confound — Budgets matched in base-model tokens. Bangla fertility under the 256k vocab is ~2–3× English, so BN sees far fewer words/bytes per generation, ≈80-word continuations and ≈5-word prefixes. Fewer effective samples predict faster collapse, so H1 is confirmable by the matching rule alone; "matched data budget" (00 §1) is false. — text: 02_DATA_SOURCES.md §1 "same number of base-model tokens (±2%)" — 4 (ratio to be measured)
- C3 — Inference — One chain per cell; the bootstrap perturbs each point by its measurement CI only, tiny with 2,000 documents, so p_boot≈0 for any nonzero difference in either direction. The pre-registered permutation test is absent and impossible. Confirmatory tests of a language×generation interaction are unsupportable. — text: analyze.py:54 "sd = ((points["ci_hi"] - points["ci_lo"]) / 3.92).fillna(0)" — 5
- C4 — Data–conclusion — distinct_n records carry NaN CIs; fillna(0) (analyze.py:54, 62) gives zero bootstrap noise, so p_boot = 0 exactly whenever the point difference ≠ 0. H1/H2 on the primary diversity metric are significant by construction. — equation: metrics.py:114 distinct_n tuple with float("nan") CI fields — 5 (read the code)
- C5 — Measurement — Lexical metrics at generation g use model g−1's output (run_chain.py:218) and at g=0 the real seed corpus. The distinct-2 series lags perplexity by one generation, its first point is human text (the 0→1 drop is real-vs-synthetic, larger for the weaker BN model), and the final model is never sampled. — text: run_chain.py:160 "sample = sample_docs(docs, cfg["metrics"]["n_sample_docs"], cfg["seed"])" — 5
- C6 — Implementation — One fixed seed goes to every vLLM request; vLLM seeds a per-request generator, so a repeated prefix yields the same continuation. 10,000 prefixes cycled ~4× to reach 10M tokens → ~¾ exact duplicates, at a rate depending on mean length and hence language. The HF fallback (:102) lacks the bug. — text: run_chain.py:85 "SamplingParams(temperature=s["temperature"], top_p=s["top_p"], max_tokens=max_new, seed=seed)" — 4 (vLLM seeding semantics)

### MAJOR

- M1 — Confound — Weaker Bangla prior: BN gen-0 starts closer to collapse; 10M adaptation tokens do not equalise competence. Language and starting competence are inseparable. — text: 10_RISK_REGISTER.md "Base model has poor Bangla to begin with, so BN starts closer to collapse" — 4
- M2 — Confound — bnwiki (stub-heavy) vs enwiki; Sangraha vs classifier-filtered FineWeb-Edu. Domain labels match; curation, genre and length do not, and no matching beyond truncation is specified. — dataset: configs/corpora.yaml:11–30 — 4
- M3 — Confound — REPLACE docs are prefix + continuation: 16 real tokens per doc, the same 10,000 prefixes every generation, a fixed real anchor whose share varies with generated length, hence by language. test_sanity.py:73 checks real_docs == 0, so the leak is invisible; brief §7.5 forbids it. (Shumailov also prompts from real text; the defect is the unreported, language-varying share.) — text: run_chain.py:92 ""text": p["text"] + g.text" — 5
- M4 — Bug-as-finding — float16 for training, vLLM and Scorer on a bf16-capable 4090; the config note is stale. Soft fp16 overflow (inf logits → garbage tokens) looks like collapse and passes the NaN rule. — text: configs/chains.yaml:33 "dtype: float16 # T4 has no bfloat16" — 3 — field_norm_boundary: HF Gemma-3 model card recommends bfloat16; fp16 overflow documented for Gemma 2/3 — crossing: pipeline fixes fp16 in all three stages
- M5 — Comparability — Absolute slopes on bounded metrics with different baselines: BN distinct-2 inflated by inflection; BN recall likely near 25% chance at gen 0 (floor, biases H1 toward null) with no above-chance gate in 03 §5. Sentence-total log-prob ranks objects partly by token length, which varies more in Bangla. — text: metrics.py:79 "gold = scorer.seq_logprob(p["template"].format(S=p["subject"], O=p["gold"]))" — 4
- M6 — Confirmation bias — H2 uses absolute slope differences; if BN-REPLACE is steeper (H1) the absolute R−A gap is mechanically larger for BN. H1 and H2 are coupled with opposite expected directions. — text: 01_PREREGISTRATION.md H2 "slope difference REPLACE − ACCUMULATE is smaller in magnitude for BN" — 4
- M7 — Logic chain — Linear OLS over 7 serially dependent points of a nonlinear process; one divergent final generation sets the slope; no nonlinearity or outlier rule. — text: analyze.py:50 "b = np.polyfit(x, y, 1)[0]" — 4
- M8 — Pre-reg integrity — 01 promises label permutation and joint paired resampling; analyze.py has neither and draws noise independently for both chains and the shared gen-0 point, so the frozen pre-registration is deviated from immediately. — absence: analyze.py — expected permutation test per 01 §Analysis plan (b); checked analyze.py, 07_ANALYSIS_PLAN.md — 5

### MINOR

- m1 — Measurement — Seed vocab lowercased, sample words not (metrics.py:104): EN capitalised rare types never match; BN has no case, so tail mass is asymmetrically undercounted. — text: metrics.py:156 "c.update(words(d["text"].lower()))" — 5
- m2 — Measurement — mean_length_tokens mixes word counts (gen-0) with model tokens; F5 shortcut check broken at gen 0. — text: metrics.py:143 "lens = [d.get("n_tokens") or len(ws)" — 4
- m3 — Doc/code drift — Near-dup rule is MinHash 0.8 in 03 §3 but a 40-word signature in code. — text: run_chain.py:142 "sig = " ".join(ws[:40]).lower()" — 5
- m4 — Scope — Fixed prefixes pin topic coverage; topic-tail collapse is excluded by design. — text: 02_DATA_SOURCES.md §5 "same prefixes are used at every generation" — 4

## Ignored alternative explanations

1. Worse-fitted start plus fewer effective samples: predicted by collapse theory for any model.
2. Corpus curation quality, not language, drives slopes.
3. Floor/ceiling effects on recall and distinct-2 masquerade as slopes.
4. fp16 numerics and seed-duplication artefacts.
5. Language-dependent real-prefix share.

## Missing stakeholder perspectives

Bangla data curators and community (Jarvis et al. frame the threat to communities, not languages); base-model developers (tokenizer and pretraining mix); downstream Bangla users.

## Unexamined premise

"Low-resource" is treated as a property of a language; the design measures a property of the (model, tokenizer, corpus, language) tuple, and assumes 100%-replacement self-training at 270M/10M models the real threat (low-fraction web contamination at scale).

## Observations (non-defects)

ACCUMULATE receives (g+1)× the gradient steps of REPLACE; state it. The 55 h cap leaves ~23 h headroom; the pre-emptions fit inside it. "So what": the actionable question is H2 (does accumulation protect BN?), the least powered, most confounded test.

## Pre-emption list

- C1: (D) retitle to "Bangla vs English under Gemma-3-270m"; or (A) two extra REPLACE chains at other tiers (e.g. Hindi, German) ≈ 2×(0.25+6×0.43) ≈ 5.7 GPU-h, giving a four-point resource-proxy gradient.
- C2: (A) EN-REPLACE control at the BN word/byte-matched token budget (≈0.4×) ≈ 1.1 GPU-h; report words/bytes per generation.
- C3: (A) second seed for the REPLACE pair incl. gen-0 ≈ 5.7 GPU-h (third ≈ 5.7 more, within cap); else (D) drop "confirmatory" and p-values.
- C4: (C) bootstrap distinct-n over documents or windows in metrics.py; never fillna(0).
- C5: (A) pre-launch code fix, 0 GPU-h: sample 2,000 docs from the just-trained checkpoint at every g including gen-0; if already run, (B) ≈ 0.4 GPU-h over 38 archived checkpoints.
- C6: (A) pre-launch code fix, 0 GPU-h: per-request seed = seed + doc index, log duplicate rate; if already run, full re-run ≈ 32 GPU-h.
- M1: (D) plus (C) report base and gen-0 perplexity, slopes relative to gen-0; (B) re-score archived checkpoints.
- M2: (C)/(D) per-source statistics and robustness slopes.
- M3: (A) pre-launch, 0 GPU-h: train on continuation only; else (B) report real-token share from archived corpora.
- M4: (A) pre-launch config, 0 GPU-h: bfloat16 for train, generate and score.
- M5: (C) relative slopes and a gen-0 above-chance gate for recall; (B) re-score probes with length-normalised conditional log-prob.
- M6: (C) define H2 on slope ratios or log-scale metrics.
- M7: (C) pre-specify first-difference/AUC statistics and a nonlinearity check.
- M8: (C) amend the pre-registration to match analyze.py before freezing.
