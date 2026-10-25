# 01 — Pre-registration (freeze before Gate 0)

Revised 2026-10-12 after a six-seat simulated design review (`logs/design_review_2026-10-12/editorial_decision.md`); every change below was made before any run and is therefore not a deviation. Items marked **HUMAN** are the authors' decisions at Gate 0.

**Title (chosen by the authors 2026-10-13, before Gate 0; replaces the question-form title confirmed in REQ-001 item 1).** Model Collapse in Bangla and English: A Pre-Registered Study of Iterative Self-Training with Gemma-3-270m.
**Authors.** Md Tahidul Islam (ORCID 0009-0004-6798-892X; corresponding) and Maksuda Akter (ORCID 0009-0004-5808-518X), Department of Computer Science and Engineering, CCN University of Science & Technology, Cumilla, Bangladesh. Both are undergraduate (bachelor's) students; no supervising faculty member is an author.
**Date frozen.** 2026-10-13 — freeze record: `signoffs/prereg_freeze_2026-10-13.json` (SHA-256 of this file, `configs/chains.yaml`, `configs/corpora.yaml` and the three schemas). An OSF registration DOI, if the authors obtain one, is recorded in `signoffs/G0_preregistration.md`, not here, so that this file's hash stays valid.
**Ethics statement (authors, 2026-10-13).** No human participants were studied; the study uses public text corpora and model outputs only. The authors' institution has no research ethics committee, so no ethics review was sought. The study is conducted independently by the authors; their department is not involved in it, and no departmental notice was required or sent.
**Funding and competing interests.** No external funding; the rented GPU time is paid by the authors personally. The authors declare no competing interests.

## Scope of the claim

The study contrasts one language pair under one base model. "Low-resource" is used operationally, not as a property of Bangla as such: relative to English, Bangla has (a) a smaller share of the base model's pretraining data (not disclosed by the model card; approximated by the base model's bits-per-character gap between the two held-out sets, reported as generation −1), (b) a higher tokenizer fertility (tokens per word, measured on the seed corpora and reported), and (c) a smaller curated web presence. Script, morphology, tokenizer fertility, corpus curation and the base model's prior are co-varying with language in this design and cannot be separated by it; the conclusions are about the (model, tokenizer, corpus, language) tuple that current Bangla practitioners actually face, and any generalisation to other languages is stated as a hypothesis for future work, not a result.

## Hypotheses (confirmatory)

Metrics are defined in `05_METRICS.md`; "slope" is the ordinary-least-squares slope over generations 0…6 of the seed-0 chain of a cell.

- **H0 (anchor).** EN-REPLACE shows rising held-out perplexity and falling distinct-2 across generations, and EN-ACCUMULATE's slopes are at least 50% smaller in magnitude. If the anchor fails, the pipeline is suspect and no other hypothesis is interpreted.
- **H1 (faster degradation in Bangla).** Under REPLACE, the slope of (i) held-out log-perplexity, (ii) log(distinct-2 / distinct-2 at generation 0), and (iii) log(tail-fact recall / recall at generation 0) is steeper (worse) for BN than for EN. For (i) the contrast must agree in direction on both the token scale (log-perplexity) and the tokenizer-independent scale (bits per byte); the byte scale is the co-primary cross-language unit.
- **H2 (weaker anchoring).** The relative benefit of accumulation, Δ_L = (slope_REPLACE − slope_ACCUMULATE) / |slope_REPLACE| computed per language on the same three metrics, is smaller for BN than for EN. (Defined as a ratio so that H2 is not mechanically implied by H1; the absolute difference is reported as secondary.)

## Exploratory (reported, not tested)

Per-stratum tail-fact recall (HEAD/MID/TAIL); bias-probe drift within each language (the two bias sets are not comparable across languages); fertility of generated text; "fairness before perplexity" ordering (Proskurina et al. 2026) within BN; the REPLACE extension to generation 10 (plateau check); the robustness chains listed below; distribution of generated-text perplexity under the generation-0 model (the classic collapse signature); n-gram novelty of each synthetic corpus against the seed.

## Design

- **Factors.** Language L ∈ {EN, BN} × regime R ∈ {REPLACE, ACCUMULATE, ACCUMULATE-FILTER} = 6 confirmatory chains, one seed each (seed offset 0), G = 6 generations after generation 0.
- **Data budget.** 10M generated base-model tokens per generation per chain; seed corpora of 10M base-model tokens per language (±2%), matched in domain mix and cleaning (`02_DATA_SOURCES.md`). Because 10M Gemma tokens carry fewer words in Bangla than in English (fertility), the number of words, characters and bytes of every corpus is reported, and the robustness chain EN-REPLACE-WM runs the English REPLACE condition at the token budget that carries the same number of words as the Bangla seed.
- **Document lengths** are matched in words, not tokens: a 12-word real prefix and up to 190 generated words per document, converted to per-language token counts from the measured words-per-token of each seed corpus at Gate 1 (English ≈ 16 / 256 tokens; Bangla more tokens for the same text).
- **Model and recipe.** One pretrained multilingual base ≤ 300M parameters (`google/gemma-3-270m`), full fine-tuning in bfloat16 mixed precision, identical recipe across chains (`03_MODELS_AND_TRAINING.md`). Generation g initialises from the generation g−1 checkpoint (warm-start chaining; generation 0 from the base model). Synthetic documents are generated by pure ancestral sampling (temperature 1, top-p 1) from the fixed real prefixes; the prefix tokens are context only and are excluded from the training loss, so a REPLACE step trains on generated tokens only.
- **Pre-registered robustness chains**, run after the six confirmatory chains in this fixed order until the post-pilot projection (`harness/vast/plan_budget.py --measured`) reaches the approved cap; whatever is not reached is reported as "not run" (no deviation):
  1. EN-REPLACE-s2, BN-REPLACE-s2: the REPLACE pair with a second seed for generation-0 training, generation and training (run-to-run variance);
  2. EN-REPLACE-WM: English REPLACE at the word-matched budget (is faster Bangla decay just less text?);
  3. EN-REAL-REPEAT, BN-REAL-REPEAT: the identical recipe re-trained on the real seed corpus at every generation, no synthetic text (separates continual-fine-tuning drift from collapse);
  4. EN-REPLACE and BN-REPLACE continued to generation 10 (plateau check; the confirmatory slopes use 0…6 only);
  5. EN-REPLACE-s3, BN-REPLACE-s3: a third seed;
  6. EN/BN-ACCUMULATE-SUBSAMPLE: accumulate, then subsample the union to 10M tokens (constant dataset size; compute-matched control for H2);
  7. EN/BN-REPLACE-topp95: REPLACE with top-p 0.95 (decoding sensitivity).
- **Scoped out** (no result will be claimed): a byte-level tokenizer condition (H3 of the earlier draft), the code-mixed chain, other languages or resource tiers, larger models, re-initialisation from the base model at every generation, temperatures other than 1.

## Metrics and sampling

Defined in `05_METRICS.md`. Model-based metrics are computed on frozen held-out and probe sets created at Gate 1 and never modified; a separate fresh slice (Wikipedia pages created after the base model's release) is scored on its own. Sample-based metrics are computed on a fixed-prefix sample of 2,000 documents generated by the checkpoint being evaluated (including generation 0 and the untouched base model), on the generated continuation only. Every metric carries a confidence interval over its items (documents, probes, pairs, or document subsamples for the window metrics).

## Analysis plan and inference

Detailed in `07_ANALYSIS_PLAN.md`. The unit is a chain trajectory; with one chain per cell no population claim is made. Uncertainty is reported at two levels and never mixed: (a) measurement uncertainty, a paired parametric bootstrap from the per-point item CIs (1,000 draws), giving a bootstrap p-value for the slope contrasts with Holm correction across the three primary metrics within each hypothesis; (b) run-to-run variance from the re-seeded REPLACE chains, reported as the per-seed contrast and its spread (descriptive). **Decision rule.** H1 is "supported" if all three primary contrasts have the predicted sign with Holm-adjusted bootstrap p < 0.05 and, where seed replicates exist, every per-seed contrast has the same sign; "not supported" if no contrast has the predicted sign; "inconclusive" otherwise. The same rule applies to H2. The OLS slope over 0…6 is the pre-registered summary; the endpoint contrast at generation 6 (log-ratio to generation 0) and a quadratic-term check are reported as robustness because collapse trajectories need not be linear. A tail-fact stratum (or a language) whose generation-0 recall CI includes the chance level (0.25) is excluded from H1(iii) and reported.

## Stopping, exclusion and bug rules

A generation is re-run (max 3 attempts) if training diverges (NaN loss) or the generated corpus is < 95% of budget; persistent failure is reported as missing. A generation whose exact-duplicate rate of generated continuations exceeds 5%, or whose empty-generation rate exceeds 5%, is a pipeline bug: it is regenerated, never analysed. No chain is dropped for giving unexpected results. Scale rules, in order, with a `results/deviations.md` entry: drop robustness chains from the lowest priority upward (reported, no deviation); 10M → 5M tokens per generation; 6 → 5 generations; never drop a language or a confirmatory regime without author sign-off.

## Deviations

Recorded in `results/deviations.md` with date, reason and effect on inference.
