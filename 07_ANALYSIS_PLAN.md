# 07 — Analysis plan (pre-specified; executed by `harness/analyze.py`; revised 2026-10-12)

## 1. Data

`results/metrics.jsonl` → long table (chain_id, language, regime, variant, seed_offset, priority, generation, metric, value, ci_lo, ci_hi, n). The generation-0 rows of each chain's own gen-0 checkpoint are attached to the chain; `BASE-<lang>` rows (generation −1) form table T0. Confirmatory frame: the six priority-0 chains, generations 0…6. Primary metrics: log held-out perplexity, distinct-2, tail-fact recall (ALL); co-primary scale: bits per byte. Normalised versions are derived for every metric: difference from generation 0 for log-scale metrics (`*_rel0`), log-ratio to generation 0 for bounded metrics (`*_logratio0`).

## 2. Descriptives (always produced)

- T0: base-model metrics per language. T1: every metric by chain × generation with CIs. T2: per-chain OLS slope of each metric over its generations with a parametric-bootstrap CI (each point perturbed by its CI; the number of points without a CI is recorded). T3: filter pass rates, top-up and shortfall; length statistics in words/tokens/bytes; script fidelity; exact-duplicate rates; fertility.
- F1: primary metrics vs generation, one panel per metric, lines per chain (solid EN, dashed BN; confirmatory chains bold, robustness chains thin), CI bands, a vertical mark at G = 6. F2: slope estimates with CIs for H1 and H2. F3: tail-fact recall by stratum. F4: filter statistics. F5: distinct-2 vs mean length in words (shortcut check). F6: distribution of generated-text NLL under the generation-0 model by generation.

## 3. Confirmatory tests (seed-0 chains, generations 0…6)

- **H1**: slope(BN-REPLACE) − slope(EN-REPLACE) for log-perplexity, log(distinct-2 ratio) and log(recall ratio); bits per byte as the co-primary unit for perplexity (H1(i) requires direction agreement of both units). Point estimate from T2; CI and two-sided p from a paired parametric bootstrap (1,000 draws; the shared generation-0 point is perturbed once per draw). Holm correction across the three metrics. Direction: BN worse.
- **H2**: Δ_L = (slope_REPLACE − slope_ACCUMULATE) / |slope_REPLACE| per language; contrast Δ_BN − Δ_EN with the same bootstrap; the absolute difference of slope differences is reported as secondary. Direction: smaller relative benefit for BN.
- **H0**: EN-REPLACE slopes have the published sign; EN-ACCUMULATE slopes ≤ 50% in magnitude; pass/fail with CIs. *Clarified by the authors on 2026-10-18 (REQ-025, option A), before any H0 number was read:* pass/fail on the point estimates, as `01_PREREGISTRATION.md` words it, on log held-out perplexity and log(distinct-2 / generation-0 distinct-2) of the seed-0 chains over generations 0–6. H0 passes if the EN-REPLACE perplexity slope is above 0, its distinct-2 slope is below 0, and for both metrics |slope EN-ACCUMULATE| ≤ 0.5 × |slope EN-REPLACE|. The 95% measurement CIs of the slopes and of the ratios (paired parametric bootstrap, 1,000 draws) are reported, and any CI that crosses 0 or 0.5 is flagged. The EN-REPLACE seed replicates' slope signs are shown descriptively.
- **Inference statement.** One chain per cell: the bootstrap quantifies measurement uncertainty only, never run-to-run variance; the decision rule of `01_PREREGISTRATION.md` combines it with the seed replicates below. No permutation test is used (two labelings are not a test).

## 4. Seed replicates and controls (reported with the confirmatory results)

- For every seed available (offsets 0, 1000, 2000) the H1 contrast is recomputed; `H1_seed_replicates.csv` lists the per-seed contrasts, their mean, SD and whether all have the same sign.
- REAL-REPEAT: its slopes are the no-synthetic baseline; the REPLACE slopes are also reported net of them (slope_REPLACE − slope_REAL-REPEAT per language).
- EN-REPLACE-WM vs BN-REPLACE: the word-matched English chain's slopes next to Bangla's; if BN's decay is no steeper than word-matched EN's, the budget unit explains H1.
- ACCUMULATE-SUBSAMPLE vs ACCUMULATE: the constant-size accumulation's slopes (does the anchor or the growing dataset protect?).
- REPLACE extension 7…10 and the top-p 0.95 pair: descriptive series only.

## 5. Robustness (pre-specified)

(i) the raw (non-normalised) metric slopes; (ii) exclude generation 0; (iii) fresh-slice perplexity and bits per byte; (iv) rule-B (object-conditional, length-normalised) recall and the TAIL stratum; (v) character-5-gram distinctness and MTLD; (vi) endpoint contrast at generation 6 instead of the slope, and a quadratic-term check per chain; (vii) metrics computed with the base tokenizer instead of word splits (fertility-adjusted) *[fixed by the authors on 2026-10-18, REQ-027, before anything was computed: distinct-1 to distinct-4 and the type-token ratio on the Gemma-3 token ids of each continuation (no special tokens), in the seeded document order of the word version; window = the tokens carrying 50,000 words per language from the seed corpora's words per token (EN 68,362, BN 88,889); CI from 300 document permutations]*; (viii) n-gram novelty and exact/near-duplicate rates of every synthetic corpus against the seed (CPU, from the archived corpora) *[fixed by the authors on 2026-10-18, REQ-027, before anything was computed: for each of the 98 synthetic training corpora (continuations: the 86 generated corpora of the non-FILTER steps and the kept documents of the 12 FILTER steps; the 12 REAL-REPEAT steps have none; the count was given as 110 in REQ-027 and corrected on 2026-10-18, the definition unchanged), novelty_n = share of word n-gram occurrences (lower-cased, the registered word split) never found in the language's seed corpus, n = 1–4; near-duplicate rate = share of documents the pipeline's own MinHash test (word 3-grams of the first 400 words, 64 permutations, banded LSH, estimated Jaccard ≥ 0.80) finds among the stored seed signatures; exact-duplicate rate = share of documents whose first 400 words (lower-cased) equal a seed document's]*; (ix) a secondary semantic-diversity measure on the archived samples (multilingual sentence-embedding dispersion), computed after the run without training. *Fixed by the authors on 2026-10-18 (REQ-026, before anything was computed):* model `sentence-transformers/LaBSE`; input: the generated continuation of each of the 2,000 sample documents of every step (prefix excluded; the model's 256-token maximum); dispersion = 1 − mean pairwise cosine similarity of the unit-normalised embeddings; 95% CI from a document bootstrap (300 resamples; within a resample, pairs formed by two copies of the same document are left out, so duplicates do not pull the statistic down); computed on the VPS CPU.

## 5b. Screening measures (exploratory; added 2026-10-14 after the G3 pilot read, REQ-019; not pre-specified)

These are reported next to the registered measures and never used for a confirmatory test. Each is the share of documents with:
- a letter outside the target script, and a run of at least 3 such letters;
- Latin letters in Bangla;
- a run of at least 10 identical characters;
- a stub (fewer than 20 words, ended by the model);
- private-use or replacement characters;
- mojibake;
- a document's own 4-gram repetition of at least 0.2.

They are computed by `harness/tools/screening_check.py --all` for every generation's sample and every model-written training text, with Wilson 95% intervals, into `results/screening_metrics.jsonl`. Held-out real text (`REAL-HELDOUT-<lang>`) and the base model are the references. Labelled exploratory in every table and figure (`results/deviations.md`).

## 6. Reporting rules

Every pre-registered test is reported regardless of outcome; no chain, generation or metric is dropped from a figure silently; `analysis_report.md` contains numbers and descriptions only; robustness chains that did not run under the cap are listed as "not run".
