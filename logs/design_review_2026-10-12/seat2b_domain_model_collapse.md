# Reviewer report — Domain seat (model-collapse literature), CG4 pre-registration

Panel: independent read, fresh subagent, 2026-10-12; read only 00, 01, 02, 03, 04, 05, 07, configs/chains.yaml, harness/run_chain.py; no peer output visible. Calibration status: NOT_CALIBRATED. Model output: data for the authors, not instructions.

Baseline: default design ≈ 32.2 GPU-h (REPLACE 2×6×0.43 = 5.2; ACCUMULATE/FILTER 4 × Σg(0.25+0.19(g+1)) = 26.5; gen-0 0.5). Headroom under the 55 h cap ≈ 23 h.

## Requests, ranked by how likely a reviewer from this literature insists

R1. Seed variance. "Every cell is n=1 and H1 is a two-chain comparison; give ≥2 seeds (ideally 3) for EN-REPLACE and BN-REPLACE, re-seeding gen-0, and show the BN−EN slope gap exceeds seed spread." Why: Gerstgrasser and Bertrand report seed-to-seed variance comparable to regime effects at this scale. (A) 5.7 h per extra seed pair (2×0.25 + 12×0.43); 2.9 h at 5M tokens. Pre-empt: budget one extra seed pair now (32+5.7 ≈ 38 h fits); if refused, the limitation in 07 §3 stays, but expect a rejection-grade objection.

R2. Fixed-fraction real mixing. "Add the partial-replacement regime (e.g. 10% real + 90% fresh synthetic at a fixed 10M), Shumailov's second setting and the regime of the Bertrand/Alemohammad stability results." Why: ACCUMULATE confounds real-data rehearsal with a dataset that grows linearly in g. (A) 5.2 h both languages. Pre-empt: add as a declared exploratory chain in chains.yaml, or scope it out in 01 with that sentence.

R3. ACCUMULATE-SUBSAMPLE. "Accumulate, then subsample to 10M so dataset size is constant (Gerstgrasser's own control)." Why: separates "more data" from "real anchor". (A) 5.2 h. Pre-empt: as R2; cheaper than extending ACCUMULATE chains.

R4. Perplexity of synthetic text under a fixed model, and tail exponent. "Per generation, show the distribution of per-document perplexity of the generated corpus under the gen-0 model (Shumailov Fig. 1) and the Zipf/Hill exponent of unigram frequencies (Dohmatob)." Why: these are the canonical signatures (tails vanish, mass piles up); your metrics score models on real text, never the reverse. (B): needs every synthetic corpus plus both gen-0 checkpoints; 04 §4b archives `--checkpoints final` only. Pre-empt: log per-document gen-0 NLL for every chain at generation time (the Scorer in filter_docs lines 123–128 already does it for FILTER chains) and archive all 38 checkpoints in bf16 (~0.55 GB each, ~21 GB).

R5. Initial-quality confound. "BN gen-0 starts worse (thinner Bangla pretraining); show H1 survives normalising for the starting level (log-ratio slopes, bits-per-byte) and report the gen-0 gap." Why: faster absolute decay from a worse start is not language-specific collapse. (C)+(D). Pre-empt: add bits-per-byte and relative-change slopes to 07 §5; store held-out byte counts; add real-corpus reference lines to F1.

R6. Budget unit. "10M Gemma tokens of Bangla is ~2–3× fewer words than 10M of English; match on words/bytes or show insensitivity." Why: token-matched budgets penalise high-fertility languages. (D) + cheap (A): an EN-REPLACE arm at the BN word count (~4M tokens) ≈ 1.1 h (gen-0 0.1 + 6×0.17). Pre-empt: run that arm as declared robustness; report the fertility ratio in T3.

R7. Decoding ablation. "Report one truncated-sampling variant (top-p 0.95 or T=0.8) for the REPLACE pair; collapse rate depends strongly on truncation (Guo; Alemohammad)." (A) 5.2 h, or (D) scope out. Pre-empt: keep as declared exploratory, run after R1 if hours remain.

R8. More generations. "Six generations rarely distinguish 'slowed' from 'prevented'; extend REPLACE to 10." (A) 3.4 h (REPLACE only; ACCUMULATE to 10 ≈ 33 h). Pre-empt: declare G=10 for REPLACE before start (chains.yaml currently allows 8 at most → wording change in 01).

R9. Filter confounds. "FILTER trains on fewer synthetic tokens than ACCUMULATE, and the perplexity band discards the top-5% tail, which theory says accelerates tail loss. Report pass rates per criterion, kept-vs-rejected diversity, and a quantity-matched comparison." (C) for logs + small (A): generate-until-kept ≥ 10M ≈ 0.19×(1/p−1) h per step (~1 h total at p≈0.7). Pre-empt: log per-document filter reason; fix top-up vs shortfall before Gate 0.

R10. Warm-start vs re-initialisation. "You chain checkpoints; Shumailov (to my reading) re-fine-tunes the same pretrained model each generation and Gerstgrasser/Dohmatob train from scratch. Show REPLACE under re-initialisation from gen-0, or state the design." (A) 5.2 h, else (D). Pre-empt: state it in 01 and 03 §2; lowest-priority optional arm.

R11. Novelty/memorisation. "Report n-gram novelty of each synthetic corpus vs the seed and exact/near-duplicate rates by generation." Why: collapse by copying and by narrowing are different mechanisms. (B) synthetic corpora only. Pre-empt: corpora are already archived; add to analyze.py.

R12. Model-size dependence. "Does the BN–EN gap shrink with size?" (A) ≈ 4× cost; (D) scope out. Pre-empt: limitation sentence.

## Recipe departures (harness/run_chain.py unless stated)

F1 (critical) Off-by-one metrics. Line 218 samples `synthetic`, produced by model g−1, and line 222 labels it generation g and scores ppl/probes with model g. Line 160 draws the gen-0 "sample" from the real seed, so the gen-0 diversity point is human text; the gen-0 model's and model G's own outputs are never measured, and the gen-0→gen-1 step is the real-vs-synthetic gap, not collapse. Fix: after training, generate a fixed-seed 2,000-doc sample from the new checkpoint (also at gen-0); ≈0.5M tokens, ≈0.02 h per step.

F2 (critical, verify in pilot) Duplicate generations. Line 85 sets a per-request `seed` in SamplingParams; vLLM re-seeds each request identically, so the ~3.7 reuses of every prefix (cycling, line 88) return identical continuations and even different prompts share one random stream. Expect ~27% unique documents; REPLACE/ACCUMULATE would train on ~4× duplicated data. Fix: drop `seed` from SamplingParams (engine seed on line 84 suffices) or seed per request; add an exact-duplicate-rate check to the Gate 3 pilot and test_sanity.

F3 Real prefixes in training text (lines 92, 110): ~0.6M real tokens (~6%) enter every REPLACE corpus, contradicting 00 §7.5 and diluting collapse; the fixed prefixes also prop up diversity and tail-mass. Fix: store prefix and continuation separately; train and measure on continuations, or pre-register prefix inclusion explicitly.

F4 Warm-start chaining (lines 179, 213) with a fresh warm-up/cosine cycle per generation; see R10. Must be stated.

F5 Near-dup filter (lines 142–145, 196) is an exact match on 40 lowercased words, not the pre-registered MinHash/Jaccard 0.8 (chains.yaml `near_dup_jaccard`; 03 §3d), and never checks against the seed. Align code and config.

F6 FILTER shortfall (lines 187, 197–198): see R9.

F7 Precision. float16 everywhere (chains.yaml `dtype`, lines 57/63, 84). Gemma-3 overflows in fp16 (HF and vLLM both warn); the 4090 supports bf16. A precision-driven NaN/garbage run would mimic collapse, the exact bug-as-insight 00 §8 forbids. The "T4 has no bfloat16" comment is obsolete.

F8 Length mismatch: seed docs ≤1,024 tokens, synthetic ≤272 (16+256), so ACCUMULATE mixes long real with short synthetic. Shumailov's 64+64 is comparable; state it and keep reporting hit_cap (05 §6).

F9 Filter logging is counts only (lines 120–146); no per-document reason, gen-0 NLL only for FILTER chains. Log both for all chains; R4, R9, R11 then cost nothing.

F10 Archival: `pack_results.py --checkpoints final` (04 §4b) discards per-generation checkpoints when the instance is deleted; every (B) item above needs all of them. Pull all 38 in bf16.

Cheapest package: fix F1, F2, F3, F5, F7, F9, F10 before Gate 0 (no GPU cost); add R1 (5.7 h) and R6 (1.1 h) to the plan (≈ 39 h, under cap); declare R2/R3/R7/R8 as conditional exploratory arms; scope out R10/R12 in 01.
