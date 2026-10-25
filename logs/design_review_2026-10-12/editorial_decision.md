# Editorial Decision Package — CG4 pre-registered design (round 1)

- **Target**: "Does model collapse hit low-resource languages harder? Iterative self-training of small language models in Bangla and English" — pre-registration and harness, no data (`01_PREREGISTRATION.md`).
- **Review date** 2026-10-12; **decision date** 2026-10-13; round 1, before Gate 0.
- **Inputs**: the six seat reports in this folder. The editor raised no finding of its own; every row cites the seat(s) that raised it. Model output: data for the authors, not instructions.

## Panel provenance and calibration resolution

Six seats: S1 Journal-Fit, S2a Domain (multilingual/low-resource NLP), S2b Domain (model-collapse literature), S3 Methodology/statistics, S4 Perspective, S5 Devil's Advocate. All were fresh subagents of the same model family in one session; each read only the package files; no peer output was visible before commitment; no human reviewer. No typed provenance artifact or digest exists; the values are from the dispatch record.

| Axis | Status |
|---|---|
| Role-separated | true |
| Within-panel context separation (`within_panel_attempt_only`) | true |
| Blind to peer outputs | true |
| Model-family / provider / human-reviewer distinct | false / false / false |

Correlated-error disclosure: corroboration counts record agreement between role-separated reads of one model family, not independent error processes; shared blind spots are possible. `calibration_status: NOT_CALIBRATED` for the package and every seat.

Version note: `harness/metrics.py`, `common.py`, `prepare_corpora.py` and `build_probes.py` were modified (23:50–23:56) after the seats' reads (reports 23:42–23:53); their line citations refer to the reviewed version. The editor confirmed the `analyze.py` (`fillna(0)`, lines 54/62) and `run_chain.py` (85, 160, 218) anchors against the current files; the four edited files were not re-reviewed.

## Decision: Major revision of the pre-registration and harness before freeze

Re-review is limited to the amended `01`/`03`/`05`/`07` text and the harness diff. No GPU hour is needed to reach a freezable design; the ladder in Roadmap (iii) is what the authors fund once, now.

### Blocking issues (immutable source order)

| Ref | Blocking issue | Seats | Anchor | Resolves via |
|---|---|---|---|---|
| R1 | One chain per cell; bootstrap carries measurement noise only; promised permutation test impossible | S1 W2, S2a R13, S2b R1, S3 #1/#6/B10, S4; DA C3/M8 | text: 01 "One seed per chain"; code: analyze.py:54 | I1, I18 |
| R2 | Harness manufactures results: sample series lags one generation and starts on human text; distinct-n NaN CI + `fillna(0)` → p=0; fixed per-request vLLM seed duplicates continuations; fp16 on Gemma-3 | S2b F1/F2/F7, S3 B1/B6/B8, S2a F10; DA C4–C6, M4 | code: run_chain.py:85/160/218; analyze.py:54; chains.yaml:33 | I2, I3, I5, I17 |
| R3 | Cross-language units and budget not comparable (per-token perplexity, token-matched 10M, 16-token prefix, 256-token cap); starting competence unadjusted | S1 W4, S2a R1–R4, S2b R5/R6, S3 #4/#5, S4 W1/W2; DA C2, M1, M5 | text: 02 §1 "same number of base-model tokens (±2%)" | I8–I11 |

### Reviewer summary

| Seat | Role | Recommendation | Confidence |
|---|---|---|---|
| S1 | Journal-Fit | Minor revision before Gate 0 | 4 |
| S2a | Domain, multilingual NLP | none stated; "defensible once … F1–F8 fixed before Gate 1" | — |
| S2b | Domain, model collapse | none stated; two CRITICAL recipe departures | — |
| S3 | Methodology/statistics | none stated; bugs "unpublishable as written" | — |
| S4 | Perspective (Bangla computational linguist) | Major revision before freeze | 4 |
| S5 | Devil's Advocate | N/A; six CRITICAL findings | 4–5 per finding |

## Consensus analysis

Denominator: the five non-DA seats; "+DA" marks Devil's Advocate corroboration (tracked separately). Severity is the raising seat's own tag ("flaw" where S2a/S2b/S3 gave file:line findings without a tag). Class: A new GPU hours; B needs archived checkpoints/corpora; C analysis-only; D scope/text.

| ID | Issue | Seats | n/5 | Severity | Class, cost |
|---|---|---|---|---|---|
| I1 | One chain per cell; ≥2 (ideally 3) seeds for the REPLACE pair, re-seeding gen-0 | S1 W2, S2a R13, S2b R1, S3 #1, S4; +DA C3 | 5 CONSENSUS-5 | Major (S1), critical (DA) | A 5.7 h/pair + D |
| I2 | Sample at g is model g−1's output; gen-0 sample is real text; model G never sampled | S2b F1, S3 B1; +DA C5 | 2 | critical (S2b) | code, ≈0.02 h/step |
| I3 | Fixed per-request vLLM seed → identical continuations for repeated prefixes | S2b F2; +DA C6 | 1 | critical, verify in pilot | code 0 h + Gate-3 check |
| I4 | Real 16-token prefixes in REPLACE training text (~6%, language-varying), contra 00 §7.5 | S2b F3, S3 #12; +DA M3 | 2 | flaw; Major (DA) | code 0 h |
| I5 | float16 for Gemma-3 on a bf16 GPU; overflow mimics collapse | S2b F7, S3 B8; +DA M4 | 2 | flaw; Major (DA) | config 0 h |
| I6 | `--checkpoints final` discards per-generation checkpoints | S1 W3, S2b F10/R4, S3 #7, S4 | 4 CONSENSUS-4 (S2a silent) | Major (S1) | B-enabler, ~21 GB bf16 |
| I7 | Per-document NLL/tokens/bytes, per-option probe scores, per-doc filter reason, gen-0 NLL for all chains | S2a R1/R5/R6, S2b F9/R4/R11, S3 #4/#5/B7; +DA M5 | 3 CONSENSUS-3 (S1, S4 silent) | flaw | code 0 h; turns B into C |
| I8 | Bits-per-byte/character and gen-0-normalised log-ratio slopes as cross-language scale; log/logit transforms | S2a R1/R7, S2b R5, S3 #4, S4 W2; +DA M5/M6 | 4 CONSENSUS-4 (S1 silent) | Major (S4) | C + text |
| I9 | Starting-competence confound; measure the untouched base; state init rule; recall chance-floor gate | S1 W4, S2a R2, S2b R5, S3 #5, S4 W1; +DA M1 | 5 CONSENSUS-5 | Major (S1, S4) | C/D + ≈0.2 h |
| I10 | Token-matched 10M gives BN ⅓–½ the words/bytes | S2a R3, S2b R6, S3 #4, S4 W2; +DA C2 | 4 CONSENSUS-4 (S1 silent) | Major (S4), critical (DA) | A 1.1 h EN-down arm (S2b/S3/DA) or 5–7 h BN byte-matched (S2a/S4); C words/bytes |
| I11 | Prefix/cap asymmetry (≈5 vs 12 words; ≈80 vs 190); prefixes stored as text and re-tokenised | S2a R4/F9/F12, S4 W2; +DA C2 | 2 | Major (S4) | config/text 0 h |
| I12 | Probe validity: distractors among subject's true objects, duplicate subjects, unstemmed BN strata, length bias, allomorphy, spot-check skips distractors, paired triples | S2a R5/F4–F7, S3 #5, S4 W3; +DA M5 | 3 CONSENSUS-3 (S1, S2b silent) | Major (S4) | Gate-1 build 0 h |
| I13 | Fresh slice never scored (first 2,000 docs read; fresh appended after) | S2a F1, S3 B3 | 2 | flaw | code 0 h |
| I14 | Seed↔held-out cross-domain near-dups; contamination; fresh slice co-primary | S2a R6/R9/F8, S3 #8 | 2 | flaw | CPU at Gate 1 + text |
| I15 | Tail-mass case mismatch; EN undercounted | S2a F2, S3 B2; +DA m1 | 2 | flaw | code 0 h |
| I16 | "Rarest 10%" order-dependent; BN tail inflectional; threshold + lemma/char-n-gram variant | S2a F3/R8, S4 W5 | 2 | Minor (S4) | code + C |
| I17 | distinct-n NaN CI from one random window; `fillna(0)` makes p_boot = 0 | S2a F10/R7, S3 B6; +DA C4 | 2 | flaw; critical (DA) | code 0 h |
| I18 | Permutation absent/impossible; no unit of inference, effect size, decision rule; linear OLS on 7 points; H2 absolute difference coupled to H1 | S3 #6/B10; +DA C3/M6/M7/M8 | 1 | flaw; critical/Major (DA) | text + C |
| I19 | Filter: 40-word exact dedup vs MinHash 0.8; silent `except`; band calibration; shortfall vs top-up; pass rates; cross-language asymmetry | S2a R10/F14, S2b F5/F6/R9, S3 #9/B4; +DA m3 | 3 CONSENSUS-3 (S1, S4 silent) | flaw | code 0 h (+≈1 h top-up) |
| I20 | ACCUMULATE is continual warm-start, (g+1)× gradient steps; anchors re-initialise; unstated | S2a R2, S2b F4/R10, S3 #3; +DA | 3 CONSENSUS-3 (S1, S4 silent) | flaw | D + cumulative tokens; optional A 5.2 h |
| I21 | REAL-REPEAT no-synthetic control | S3 #2 | 1 | request | A 3.1 h |
| I22 | Fixed-fraction / subsampled / realistic mixing regime | S2b R2/R3, S4 LR5; +DA premise | 2 | request | A 5.2 h or D |
| I23 | REPLACE to G=8 (or 10), declared before the first chain | S1 LR6, S2b R8, S3 #10 | 3 CONSENSUS-3 | request | A 1.7 h |
| I24 | Decoding sensitivity (top-p 0.95) | S1 LR7, S2b R7, S3 #13 | 3 CONSENSUS-3 (S3: scope out) | request | A 5.2 h or D |
| I25 | BYTE/H3 sold but disabled; no character budget; 15–25 h | S1 W5, S2a R11, S3 #13, S4 W7 | 4 CONSENSUS-4 | Major (S1), Minor (S4) | D + C fertility analysis |
| I26 | "Low-resource" a label, one language per tier; co-variates; title overclaims | S1 title/W4, S4 W1; +DA C1 | 2 | Major (S4), critical (DA) | D retitle/reframe |
| I27 | Seed curation mismatch (FineWeb-Edu vs Sangraha; bnwiki stubs) | S3 #11; +DA M2 | 1 | Major (DA) | D or CPU swap |
| I28 | Assamese in the Bengali block; fastText optional; ZWJ/ZWNJ regex; `isascii`; NFC | S2a F11, S4 W4 | 2 | Major (S4) | code 0 h |
| I29 | Diversity lexical-only; add char-5-gram/stemmed/syntactic | S1 W6, S2a R7 | 2 | Minor (S1) | C |
| I30 | Bias probes not comparable across languages; within-language only; freeze one EN probe | S1, S2a R12, S4 W8 | 3 CONSENSUS-3 | Minor | D |
| I31 | Publication venue (not part of the study record; not kept here) | S1 W1 | 1 | Major (S1) | D |
| I32 | No rubric for the 50-sample qualitative read | S1 W7 | 1 | Minor | D |
| I33 | `min_lr_ratio` unimplemented; `doc_id.split` fragile; gen-0 length units; 05 Wilson vs percentile | S3 B5/B9, S2a F13; +DA m2 | 1 each | minor | code/text 0 h |
| I34 | Stale "Kaggle T4"; "collapse" undefined; MIX chain = romanised Bangla; practitioner table; second base model; model size | S1, S4 W6/W8, S2b R12 | 1–2 | Minor | D |

## Devil's Advocate CRITICAL adjudication

- **C1 (resource level is a label)** — **Partly validated.** Corroborated by S4 W1 and S1's title note. Validated as a claim-scope defect: the design tests one (model, tokenizer, corpus, language) tuple. Rejected as grounds for new tier chains: S4 W1 shows other languages still co-vary script and morphology, and each would be another n=1 cell (C3). Remedy D (I26).
- **C2 (token-matched budget)** — **Validated.** Corroborated by S2a R3, S2b R6, S3 #4, S4 W2. Remedy: 1.1 h EN arm, BPB, words/bytes per corpus, per-language prefix/cap (I8, I10, I11).
- **C3 (n=1; bootstrap carries measurement noise only)** — **Validated.** Corroborated by S3 #1/#6/B10, S2b R1, S1 W2. Remedy: second seed pair confirmatory (I1), rewritten inference (I18); a third pair is the only route to a valid permutation test (S3: 20 labelings, min p = 0.05).
- **C4 (`fillna(0)` → p=0)** — **Validated.** NaN CIs corroborated by S2a F10, S3 B6; `fillna(0)` confirmed at `analyze.py:54/62`. Remedy C (I17).
- **C5 (one-generation lag; human-text gen-0 sample)** — **Validated.** Corroborated by S2b F1 (critical), S3 B1; `run_chain.py:160/218` confirmed. Remedy: sample from the just-trained checkpoint at every g including gen-0 (I2).
- **C6 (per-request vLLM seed)** — **Validated as must-fix-and-verify.** Corroborated by S2b F2, which, like the DA (confidence 4), asks for pilot verification of vLLM seeding semantics. The fix is costless either way, so it is required; the Gate-3 pilot and `test_sanity` must report the exact-duplicate rate (I3).

## Points of disagreement and resolution

1. **Prefix handling (I4).** S2b, S3 and DA each offer: train and measure on continuations only, or keep the prefix and pre-register/report its share (DA: Shumailov also prompts from real text). No seat proposed loss-masking; the editor adds nothing. **Resolution**: continuation-only training and sample metrics, prefixes stored separately as token ids (S2a F12); the leak is forbidden by 00 §7.5 and its share varies by language.
2. **Budget-matching arm (I10).** S2a (7 h) and S4 (5–7 h) scale BN up; S2b, S3 and DA scale EN down (≈1.1 h). **Resolution**: EN-down arm now, BN-up as the first conditional arm; same confound, three seats, six times cheaper. S2a's point that BN-up is the stronger test is recorded as unresolved.
3. **Highest-priority GPU addition.** S2a ranks its byte-matched chain first and the second seed last; S1, S2b, S3, S4 and DA put the seed pair first. **Resolution**: seed pair first (CONSENSUS-5 + DA C3); S2a's own R13 asks that the order of optional runs be pre-registered, which (iii) does. S3 costs the pair at 5.2 h reusing gen-0, S2b/S4/DA at 5.7 h re-seeding it; the editor budgets 5.7 h.
4. **Retitle (I26).** S1: "in Bangla"; S4: Bangla case study bounding the risk for smaller languages; DA: "Bangla vs English under Gemma-3-270m" or tier chains (5.7 h); S4 also lists an Assamese control (2.8 h). **Resolution**: single-language, single-model title with "low-resource" defined operationally (S4 W1); no extra-language chains inside the current cap (C1).
5. **FILTER reallocation.** S3 proposes cutting ACCUMULATE-FILTER to G=3 (saves 8.3 h; FILTER is in no confirmatory hypothesis) to fund a third seed; S4 says practitioners need the FILTER numbers most; S2b R9 studies FILTER itself. **Resolution**: keep FILTER at G=6 and fund seeds from headroom. If the cap is set below 48 h, the FILTER cut is the DECISION to file, not dropping the second seed.
6. **Decision level.** S1 Minor vs S4 Major. **Resolution**: Major; S1's remit excluded the harness, where S2b, S3 and DA found corroborated critical defects (R2).
7. **ACCUMULATE recipe (I20).** S3: compute-matched arm (13 h, unaffordable) or REAL-REPEAT; S2b: re-init REPLACE (5.2 h, "lowest priority") or a statement. **Resolution**: statement in 01/03 plus cumulative-token reporting; REAL-REPEAT as the affordable control (ladder 5); re-init scoped out.

## Decision rationale

The panel agrees on the merits: judge-free metrics with length controls, a falsifiable pre-registration with an English anchor, sound governance of synthetic Bangla (S1 S1–S5, S4 S1–S4, DA "genuine strengths"). Every seat that read the harness also agrees the design as written would yield unsupportable or artefactual results: one chain per cell with a bootstrap carrying no run variance (CONSENSUS-5, DA C3), a sample series shifted one generation and anchored on human text (S2b, S3, DA C5), a diversity test significant by construction (S2a, S3, DA C4), and a generation seed that can quarter the effective corpus (S2b, DA C6). All are repairable at zero GPU cost before Gate 0, so the decision is Major revision rather than rejection: the fixes change the inference section and the harness, not the question, factors or metrics; the comparability block (R3) is a text change plus one 1.1 h arm. S1's Minor is the lone outlier and rests on not having read the code. DA C1 is accepted only as a framing limit, since no affordable addition removes the script and morphology co-variates. With (i)–(ii) done and ladder items 1–3 funded, the design is publishable at ACL/EMNLP Findings whichever way H1/H2 fall (S1).

## Revision roadmap

### (i) Code fixes, zero GPU, before Gate 0 (source order; re-verify in the four files edited after the review)

1. `configs/chains.yaml`: `dtype: bfloat16` for train, generate, score (I5); declare the REPLACE generation count (I23).
2. `configs/corpora.yaml`: BN templates with a final-sound suffix rule or suffix-free frames; P106 tense (I12).
3. `harness/prepare_corpora.py`: select fresh docs separately (I13); cross-domain MinHash seed↔held-out (I14); prefixes as token ids, per-language prefix/cap from measured fertility (I11); words/bytes/docs per corpus (I10).
4. `harness/build_probes.py`: exclude all of a subject's golds from distractors, dedupe subjects, prefix-match BN counting, absolute counts per stratum, spot-check distractors, intersect triples across languages (I12).
5. `harness/common.py`: letter+mark regex keeping ZWJ/ZWNJ, drop `isascii`, Assamese-marker check, NFC, mandatory fastText LID (I28).
6. `harness/run_chain.py`: per-request seed = seed + index with duplicate-rate log (I3); sample 2,000 docs from the new checkpoint at every g incl. gen-0 (I2); store prefix and continuation separately, train and measure on continuations (I4); MinHash 0.8 per config, fatal perplexity criterion, top-up to budget, per-document filter reason and gen-0 NLL for all chains (I19, I7); `min_lr_ratio`, `doc_id` guard (I33); base-model `compute_all` (I9); bf16 checkpoints (I6).
7. `harness/metrics.py`: per-document sidecar (I7); case-consistent and threshold-defined tail (I15, I16); document-level bootstrap and fixed window for distinct-n (I17); per-option, length-normalised probe scores (I12); BPB/BPC (I8); gen-0 length units (I33).
8. `harness/analyze.py`: remove `fillna(0)`; joint paired resampling; log-ratio-to-gen-0 estimand; nonlinearity check; permutation only with ≥3 seeds (I17, I18).
9. `harness/tests/test_sanity.py`: exact-duplicate rate; `real_docs` on continuations (I3, I4).
10. `pack_results.py` / `04 §4b`: `--checkpoints all` in bf16, all corpora, `sample.jsonl`, prefixes, sidecars (I6).

### (ii) Pre-registration text changes (01, 02, 03, 05, 07, 09)

Title and claim: single language, single model, "low-resource" defined operationally, co-variates listed as inseparable (I26). Co-primary cross-language scale: BPB/BPC and log-ratio slopes; log/logit transforms; H2 on ratios (I8, I18). Inference: unit of inference, smallest effect, decision rule, functional form; drop "permutation" unless three seeds; seed pair confirmatory with a pre-registered order of conditional arms (I1, I18). Initialisation rule and "accumulation as practised (continual)" estimand (I20). Prefix handling and per-language caps (I4, I11). Budget unit with fertility reported (I10). Base-model row and recall floor rule (I9). Fresh-slice co-primary (I14). Shared filter thresholds, asymmetry reported (I19). Bias drift within language; freeze one EN probe (I30). Qualitative rubric (I32). Remove "Kaggle T4"; define "collapse"; CI wording (I33, I34).

### (iii) GPU ladder by consensus priority, cumulative hours

Base: default design 32.2 h. Overheads of (i): post-training sampling ≈0.8 h (38 × 0.02), base-model pass 0.2 h, filter top-up ≈1 h → **34.2 h**.

| Rank | Addition | Seats | Hours | Cumulative |
|---|---|---|---|---|
| 1 | Second seed, EN/BN REPLACE incl. gen-0 (I1) | S1, S2a, S2b, S3, S4; DA | 5.7 | **39.9** |
| 2 | EN-REPLACE at BN word-matched budget, ~4M tokens (I10) | S2b, S3; DA (S2a/S4 variant) | 1.1 | **41.0** |
| 3 | REPLACE primary pair to G=8 (I23); +1.7 per further seed pair | S1, S2b, S3 | 1.7 | **42.7** |
| 4 | Third seed pair → valid permutation test (I1, I18) | S2b, S3; DA | 5.7 | **48.4** |
| 5 | REAL-REPEAT control, both languages (I21; serves I20) | S3 | 3.1 | **51.5** |
| 6 | Fixed-fraction mixing pair (I22) | S2b, S4; DA | 5.2 | 56.7 (above the 55 h cap) |
| 7 | Decoding ablation, top-p pair (I24) | S1, S2b | 5.2 | 61.9 |
| 8 | BN byte-matched REPLACE chain (I10 variant) | S2a, S4 | 7.0 | 68.9 |
| 9 | Assamese REPLACE, same-script control (I26) | S4 | 2.8 | 71.7 |
| 10 | Second base model, REPLACE pair (I34) | S1 | 5.7 | 77.4 |
| 11 | Re-initialised REPLACE pair (I20) | S2b | 5.2 | 82.6 |

Cap line: 42.7 h (items 1–3) is the minimum at which the blocking issues are answered; 51.5 h (items 1–5) exhausts the affordable methodology requests and fits the existing 55 h cap with ≈3.5 h for the pre-registered re-run rule, provided the Gate-3 pilot confirms the per-step costs (S3). Items below the chosen line are declared conditional arms in this order (S2a R13) or scoped out in (iv).

### (iv) Limitations to scope out explicitly

BYTE/H3 and any tokenizer attribution (I25; replaced by the within-language fertility analysis); decoding sensitivity if item 7 is unfunded (I24); model size and second base model (I34); other languages and resource tiers (I26); re-initialisation versus warm-start (I20); seed-corpus curation (I27); one standard register, translationese (S4); the code-mixed chain's construct (I34); 100 % replacement as a model of the real threat (DA premise); cross-language bias comparison (I30).

## Reviewer report summaries

**S1 Journal-Fit** (Minor revision, confidence 4). A timely answer to Jarvis et al.'s call; three cheap fixes (confirmatory second-seed REPLACE pair, archive all checkpoints, gen-0-conditioned analysis of starting competence) make it publishable whichever way H1 falls. Also flags the disabled tokenizer differentiator, lexical-only diversity, no qualitative rubric, overclaiming title.

**S2a Domain, multilingual** (no verdict). Thirteen ranked requests and fifteen file:line flaws: perplexity units, base-model row and initialisation rule, token- versus text-matched budget (its 7 h byte-matched BN chain is "the only new-training request a reviewer would insist on"), prefix/cap asymmetry, probe validity, fresh-slice and tail-mass bugs, no distinct-2 CI, held-out leakage, filter asymmetry, script regex and Assamese; most pre-emptable by per-document storage and scope statements.

**S2b Domain, model collapse** (no verdict). Two critical recipe departures (sample metrics off by one generation; fixed per-request vLLM seed), plus real prefixes in training text, fp16, filter code diverging from the pre-registration, final-only archiving. Requests: seed variance (5.7 h), mixing regimes, collapse signatures from archived corpora, gen-0 normalisation, a 1.1 h EN arm, decoding, G=10, warm-start statement. Cheapest package ≈39 h.

**S3 Methodology** (no verdict). H1/H2 compare single trajectories, so every CI is anti-conservative and the permutation test has two labelings; run ≥2 seeds, add REAL-REPEAT (3.1 h), state the continual estimand, report BPB with sidecars, gate probes above chance, archive everything, rewrite the inference section. Ten bugs (B1–B10) make results unpublishable as written; additions ≈43.5 h.

**S4 Perspective** (Major revision, confidence 4). "Low-resource" is undefined and the contrast bundles script, morphology, fertility, register and base-model exposure; token-matched units are not cross-script comparable; cloze templates ignore allomorphy; the script filter cannot see Assamese. Recommends a Bangla case-study framing, bits-per-character and log-ratio slopes, probe repair at Gate 1, a practitioner table, checkpoint archiving.

**S5 Devil's Advocate** (findings only). The design cannot separate "a low-resource language collapses faster" from "a worse-fitted model on fewer effective samples degrades faster", and the harness measures artefacts. Six CRITICAL (C1–C6), eight Major, four Minor; pre-emptions fit the 23 h headroom. Adjudicated above: five validated, C1 partly.

## Response instructions

Respond item by item (`templates/revision_response_template.md`): each entry in (i)–(iv) with the change made or the reason for declining; the chosen cap line in (iii) with the pre-registered order of conditional arms; a `results/deviations.md` line for any pre-registered element changed. The amended text and harness diff go to verification re-review before the `prereg-v1` tag.
