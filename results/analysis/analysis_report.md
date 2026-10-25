# Analysis report (numbers only; the interpretation is written by the authors)

Pre-registration: prereg-v1 (`01_PREREGISTRATION.md`); analysis plan `07_ANALYSIS_PLAN.md`; confirmatory generations 0..6; bootstrap: 1000 draws, seed 20261010. Inference statement (07 §3): one chain per cell; the bootstrap quantifies measurement uncertainty only, never run-to-run variance; the seed replicates give the run-to-run spread (descriptive).
Inputs: `metrics.jsonl`, `tokenizer_metrics.jsonl`, `semantic_dispersion.jsonl`.

## Descriptives (07 §2)
- T0 base-model metrics (generation -1): `T0_base_model.csv`; T1 every metric by chain x generation with CI (incl. normalised versions): `T1_metrics.csv` (12725 rows); T2 per-chain OLS slopes over 0..6 with bootstrap CIs, plus the REPLACE extension over 0..10 and 6..10: `T2_slopes.csv` (1719 rows; 290 with points lacking a CI).
- T3: `T3_generation.csv` (98 generating steps: documents, tokens, exact-duplicate, empty and cap-hit rates, mean lengths; largest exact-duplicate rate 0.0042, largest empty rate 0.0027) and `T3_filter.csv` (12 ACCUMULATE-FILTER steps: rejections by criterion, applied in the order script, repetition, perplexity band, near-duplicate; top-up rounds; kept tokens; shortfall). Sample length, script fidelity and fertility per step are in `T1_metrics.csv`.
- Filter: pass rate 0.604 to 0.862; top-up rounds up to 1; shortfall tokens 0 in total. Figure `F4_filter`.

## H0, the anchor (01 Hypotheses; decided as REQ-025 option A, 2026-10-18)
Rule: on log held-out perplexity and log(distinct-2 / gen 0), seed-0 chains, generations 0..6: the EN-REPLACE slope has the published sign (+ for perplexity, - for distinct-2) and |slope EN-ACCUMULATE| <= 0.5 x |slope EN-REPLACE| for both. Point estimates decide; 95% measurement CIs are reported and flagged. File: `H0_anchor.csv`.
- (i) log held-out perplexity: EN-REPLACE slope +0.1300 [+0.1242, +0.1350] (published sign +: yes); EN-ACCUMULATE slope +0.0786 [+0.0728, +0.0845]; ratio |ACC|/|REP| 0.605 [0.563, 0.649] (<= 0.5: NO); flags: none; seed replicates (descriptive): EN-REPLACE-s2 +0.1303 (published sign); EN-REPLACE-s3 +0.1307 (published sign)
- (ii) log(distinct-2 / gen 0): EN-REPLACE slope +0.0062 [+0.0046, +0.0077] (published sign -: NO); EN-ACCUMULATE slope +0.0006 [-0.0010, +0.0023]; ratio |ACC|/|REP| 0.104 [0.007, 0.355] (<= 0.5: yes); flags: none; seed replicates (descriptive): EN-REPLACE-s2 +0.0060 (NOT the published sign); EN-REPLACE-s3 +0.0029 (NOT the published sign)
- **H0 rule output: FAIL**. By the registered rule, if the anchor fails, no other hypothesis is interpreted (the numbers are still reported).

## H1 and H2 (07 §3; decision rule of 01, 'Analysis plan and inference')
Floor rule (05 §4): generation-0 recall (ALL) and 95% CI: EN 0.550 [0.510, 0.589] (includes 0.25: False); BN 0.432 [0.393, 0.472] (includes 0.25: False) -> H1(iii) included.
- H1 (i) log held-out perplexity: estimate -0.0458 [-0.0560, -0.0358], p_boot 0.0000, p_holm 0.0000, predicted sign + (no); slope BN +0.0842 [+0.0753, +0.0930], slope EN +0.1300 [+0.1242, +0.1350]
- H1 (ii) log(distinct-2 / gen 0): estimate -0.0039 [-0.0067, -0.0011], p_boot 0.0040, p_holm 0.0080, predicted sign - (yes); slope BN +0.0023 [-0.0000, +0.0047], slope EN +0.0062 [+0.0046, +0.0077]
- H1 (iii) log(tail-fact recall / gen 0): estimate +0.0041 [-0.0178, +0.0285], p_boot 0.7060, p_holm 0.7060, predicted sign - (no); slope BN -0.0108 [-0.0280, +0.0080], slope EN -0.0149 [-0.0290, +0.0004]
- H1 (i) bits per byte (co-primary unit) [co-primary unit for H1(i) (direction only)]: estimate -0.0303 [-0.0323, -0.0281], p_boot 0.0000, p_holm n/a, predicted sign + (no); slope BN +0.0121 [+0.0108, +0.0136], slope EN +0.0423 [+0.0409, +0.0440]
- H2 (i) log held-out perplexity: estimate +0.6517 [+0.5355, +0.7668], p_boot 0.0000, p_holm 0.0000, predicted sign - (no); Delta_BN +1.0472, Delta_EN +0.3954; secondary absolute difference +0.0368 [+0.0254, +0.0481]; flags: none
- H2 (ii) log(distinct-2 / gen 0): estimate -0.5650 [-4.9134, +0.2482], p_boot 0.1740, p_holm 0.1740, predicted sign + (no); Delta_BN +0.3313, Delta_EN +0.8963; secondary absolute difference -0.0048 [-0.0078, -0.0015]; flags: BN-REPLACE slope CI includes 0 (ratio unstable)
- H2 (iii) log(tail-fact recall / gen 0): estimate -2.4161 [-34.6038, -0.4074], p_boot 0.0320, p_holm 0.0640, predicted sign + (no); Delta_BN -1.7881, Delta_EN +0.6280; secondary absolute difference -0.0286 [-0.0532, -0.0026]; flags: BN-REPLACE slope CI includes 0 (ratio unstable); EN-REPLACE slope CI includes 0 (ratio unstable)
- H2 (i) bits per byte (co-primary unit) [bits per byte, reported (not in the Holm family)]: estimate +0.6515 [+0.5303, +0.7779], p_boot 0.0000, p_holm n/a, predicted sign - (no); Delta_BN +0.9995, Delta_EN +0.3480; secondary absolute difference -0.0027 [-0.0052, -0.0003]; flags: none
- H1 seed replicates log_ppl_heldout: per seed offset [0, 1000, 2000]: ['-0.0458', '-0.0486', '-0.0485'], mean -0.0476, SD 0.0016, same sign True, all with the predicted sign False
- H1 seed replicates distinct_2_logratio0: per seed offset [0, 1000, 2000]: ['-0.0039', '-0.0014', '-0.0007'], mean -0.0020, SD 0.0017, same sign True, all with the predicted sign True
- H1 seed replicates tail_fact_recall_ALL_logratio0: per seed offset [0, 1000, 2000]: ['+0.0041', '+0.0030', '+0.0068'], mean +0.0046, SD 0.0020, same sign True, all with the predicted sign False
- H1 seed replicates bpb_heldout: per seed offset [0, 1000, 2000]: ['-0.0303', '-0.0306', '-0.0307'], mean -0.0306, SD 0.0002, same sign True, all with the predicted sign False
- **H1 rule output: inconclusive**; **H2 rule output: not supported** (conditions per contrast: `H_decision.csv`; tests: `H_tests.csv`; seed replicates: `H1_seed_replicates.csv`). Mechanical output of the registered rule; the authors write the interpretation.

## Seed replicates and controls (07 §4)
- Seed replicates: `H1_seed_replicates.csv` (above). Controls: `controls.csv`:
  - REPLACE net of REAL-REPEAT | EN | log_ppl_heldout: +0.0001 [-0.0071, +0.0068], p_boot 0.9480
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | EN | log_ppl_heldout: -0.0258 [-0.0326, -0.0196], p_boot 0.0000
  - REPLACE net of REAL-REPEAT | EN | distinct_2_logratio0: +0.0109 [+0.0090, +0.0127], p_boot 0.0000
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | EN | distinct_2_logratio0: +0.0021 [+0.0003, +0.0038], p_boot 0.0200
  - REPLACE net of REAL-REPEAT | EN | tail_fact_recall_ALL_logratio0: -0.0051 [-0.0221, +0.0113], p_boot 0.5220
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | EN | tail_fact_recall_ALL_logratio0: +0.0255 [+0.0087, +0.0427], p_boot 0.0020
  - REPLACE net of REAL-REPEAT | EN | bpb_heldout: -0.0014 [-0.0033, +0.0007], p_boot 0.1780
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | EN | bpb_heldout: -0.0098 [-0.0116, -0.0079], p_boot 0.0000
  - REPLACE net of REAL-REPEAT | BN | log_ppl_heldout: +0.0669 [+0.0561, +0.0765], p_boot 0.0000
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | BN | log_ppl_heldout: +0.0043 [-0.0057, +0.0138], p_boot 0.4120
  - REPLACE net of REAL-REPEAT | BN | distinct_2_logratio0: +0.0034 [+0.0007, +0.0062], p_boot 0.0080
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | BN | distinct_2_logratio0: +0.0018 [-0.0004, +0.0039], p_boot 0.1020
  - REPLACE net of REAL-REPEAT | BN | tail_fact_recall_ALL_logratio0: -0.0270 [-0.0451, -0.0078], p_boot 0.0060
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | BN | tail_fact_recall_ALL_logratio0: +0.0025 [-0.0164, +0.0223], p_boot 0.7940
  - REPLACE net of REAL-REPEAT | BN | bpb_heldout: +0.0090 [+0.0073, +0.0107], p_boot 0.0000
  - ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes) | BN | bpb_heldout: +0.0002 [-0.0014, +0.0018], p_boot 0.8020
  - slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English) | BN vs EN-WM | log_ppl_heldout: -0.0455 [-0.0553, -0.0349], p_boot 0.0000
  - H2 contrast with ACCUMULATE-SUBSAMPLE as the accumulation arm (compute-matched) | BN vs EN | log_ppl_heldout: +0.4018 [+0.2939, +0.5175], p_boot 0.0000
  - slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English) | BN vs EN-WM | distinct_2_logratio0: +0.0005 [-0.0025, +0.0033], p_boot 0.7520
  - H2 contrast with ACCUMULATE-SUBSAMPLE as the accumulation arm (compute-matched) | BN vs EN | distinct_2_logratio0: -1.0070 [-12.4161, -0.0108], p_boot 0.0420
  - slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English) | BN vs EN-WM | tail_fact_recall_ALL_logratio0: +0.0034 [-0.0181, +0.0256], p_boot 0.7720
  - H2 contrast with ACCUMULATE-SUBSAMPLE as the accumulation arm (compute-matched) | BN vs EN | tail_fact_recall_ALL_logratio0: -0.9261 [-17.9771, +3.0729], p_boot 0.4500
  - slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English) | BN vs EN-WM | bpb_heldout: -0.0301 [-0.0322, -0.0279], p_boot 0.0000
  - H2 contrast with ACCUMULATE-SUBSAMPLE as the accumulation arm (compute-matched) | BN vs EN | bpb_heldout: +0.4017 [+0.2850, +0.5226], p_boot 0.0000
- REPLACE extension 7..10 and the top-p 0.95 pair: descriptive series in `T1_metrics.csv`, slopes in `T2_slopes.csv`, figure `F1_all_chains`.

## Robustness (07 §5; reported, no decision rule)
File: `robustness.csv`; quadratic-term check per chain: `robustness_quadratic.csv`.
- (i) raw (non-normalised) metrics | H1 log_ppl_heldout: -0.0458 [-0.0560, -0.0358], p_boot 0.0000, predicted sign + (no)
- (i) raw (non-normalised) metrics | H2 log_ppl_heldout: +0.6517 [+0.5355, +0.7668], p_boot 0.0000, predicted sign - (no)
- (i) raw (non-normalised) metrics | H1 distinct_2: -0.0028 [-0.0053, -0.0004], p_boot 0.0280, predicted sign - (yes)
- (i) raw (non-normalised) metrics | H2 distinct_2: -0.5637 [-5.0777, +0.3520], p_boot 0.1840, predicted sign + (no); BN-REPLACE slope CI includes 0 (ratio unstable)
- (i) raw (non-normalised) metrics | H1 tail_fact_recall_ALL: +0.0032 [-0.0070, +0.0133], p_boot 0.5220, predicted sign - (no)
- (i) raw (non-normalised) metrics | H2 tail_fact_recall_ALL: -2.4342 [-31.5435, -0.3746], p_boot 0.0320, predicted sign + (no); BN-REPLACE slope CI includes 0 (ratio unstable); EN-REPLACE slope CI includes 0 (ratio unstable)
- (i) raw metrics: H0 | H0 log_ppl_heldout: +0.1300 [+0.1242, +0.1350], predicted sign + (yes); ratio 0.605 [0.563, 0.649]; none
- (i) raw metrics: H0 | H0 distinct_2: +0.0049 [+0.0035, +0.0061], predicted sign - (no); ratio 0.102 [0.005, 0.332]; none
- (ii) generation 0 excluded (1..6) | H1 log_ppl_heldout: -0.0438 [-0.0559, -0.0315], p_boot 0.0000, predicted sign + (no)
- (ii) generation 0 excluded (1..6) | H2 log_ppl_heldout: +0.5079 [+0.3599, +0.6417], p_boot 0.0000, predicted sign - (no)
- (ii) generation 0 excluded (1..6) | H1 distinct_2_logratio0: -0.0046 [-0.0080, -0.0010], p_boot 0.0140, predicted sign - (yes)
- (ii) generation 0 excluded (1..6) | H2 distinct_2_logratio0: +5.3499 [-3.8049, +20.3752], p_boot 0.8860, predicted sign + (yes); BN-REPLACE slope CI includes 0 (ratio unstable)
- (ii) generation 0 excluded (1..6) | H1 tail_fact_recall_ALL_logratio0: -0.0037 [-0.0312, +0.0261], p_boot 0.8080, predicted sign - (yes)
- (ii) generation 0 excluded (1..6) | H2 tail_fact_recall_ALL_logratio0: -2.5988 [-44.7799, +1.3983], p_boot 0.1060, predicted sign + (no); BN-REPLACE slope CI includes 0 (ratio unstable); EN-REPLACE slope CI includes 0 (ratio unstable)
- (ii) generation 0 excluded: H0 | H0 log_ppl_heldout: +0.1275 [+0.1206, +0.1336], predicted sign + (yes); ratio 0.611 [0.552, 0.677]; none
- (ii) generation 0 excluded: H0 | H0 distinct_2_logratio0: +0.0048 [+0.0029, +0.0068], predicted sign - (no); ratio 0.060 [0.008, 0.513]; ratio CI crosses 0.5
- (iii) fresh slice | H1 log_ppl_fresh: -0.0510 [-0.0625, -0.0398], p_boot 0.0000, predicted sign + (no)
- (iii) fresh slice | H2 log_ppl_fresh: +0.4954 [+0.4014, +0.6036], p_boot 0.0000, predicted sign - (no)
- (iii) fresh slice | H1 bpb_fresh: -0.0336 [-0.0368, -0.0301], p_boot 0.0000, predicted sign + (no)
- (iii) fresh slice | H2 bpb_fresh: +0.4846 [+0.3703, +0.5959], p_boot 0.0000, predicted sign - (no)
- (iv) rule-B recall and the TAIL stratum (TAIL at chance in: none) | H1 tail_fact_recall_norm_ALL_logratio0: -0.0044 [-0.0287, +0.0198], p_boot 0.7020, predicted sign - (yes)
- (iv) rule-B recall and the TAIL stratum (TAIL at chance in: none) | H2 tail_fact_recall_norm_ALL_logratio0: -1.1031 [-13.6148, +0.5393], p_boot 0.1260, predicted sign + (no); EN-REPLACE slope CI includes 0 (ratio unstable)
- (iv) rule-B recall and the TAIL stratum (TAIL at chance in: none) | H1 tail_fact_recall_TAIL_logratio0: +0.0013 [-0.0374, +0.0438], p_boot 0.9640, predicted sign - (no)
- (iv) rule-B recall and the TAIL stratum (TAIL at chance in: none) | H2 tail_fact_recall_TAIL_logratio0: -1.2325 [-13.6133, +0.3558], p_boot 0.0800, predicted sign + (no); BN-REPLACE slope CI includes 0 (ratio unstable)
- (v) character-5-gram distinctness and MTLD | H1 distinct_char5_logratio0: +0.0047 [-0.0011, +0.0108], p_boot 0.1340, predicted sign - (no)
- (v) character-5-gram distinctness and MTLD | H2 distinct_char5_logratio0: -0.5005 [-11.8256, +1.0483], p_boot 0.5020, predicted sign + (no); EN-REPLACE slope CI includes 0 (ratio unstable)
- (v) character-5-gram distinctness and MTLD | H1 mtld_logratio0: -0.4095 [-0.5592, -0.2659], p_boot 0.0000, predicted sign - (yes)
- (v) character-5-gram distinctness and MTLD | H2 mtld_logratio0: -1.9390 [-2.1461, -1.7477], p_boot 0.0000, predicted sign + (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H1 log_ppl_heldout: -0.2749 [-0.3528, -0.2003], p_boot 0.0000, predicted sign + (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H2 log_ppl_heldout: +0.7025 [+0.5624, +0.8555], p_boot 0.0000, predicted sign - (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H1 distinct_2_logratio0: -0.0280 [-0.0510, -0.0043], p_boot 0.0180, predicted sign - (yes)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H2 distinct_2_logratio0: -0.8353 [-8.5171, +0.0609], p_boot 0.0660, predicted sign + (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H1 tail_fact_recall_ALL_logratio0: +0.0175 [-0.1527, +0.1925], p_boot 0.8220, predicted sign - (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H2 tail_fact_recall_ALL_logratio0: -3.1976 [-48.1206, -0.1204], p_boot 0.0440, predicted sign + (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H1 bpb_heldout: -0.1812 [-0.1967, -0.1654], p_boot 0.0000, predicted sign + (no)
- (vi) endpoint contrast at generation 6 (change from generation 0) | H2 bpb_heldout: +0.7056 [+0.5486, +0.8789], p_boot 0.0000, predicted sign - (no)
- (vii) base-tokenizer metrics (REQ-027): log(token distinct-2 / gen 0) | H1 distinct_2_tok_logratio0: -0.0084 [-0.0117, -0.0051], p_boot 0.0000, predicted sign - (yes)
- (vii) base-tokenizer metrics (REQ-027): log(token distinct-2 / gen 0) | H2 distinct_2_tok_logratio0: -0.1686 [-0.7373, +0.3641], p_boot 0.4300, predicted sign + (no)
- (ix) semantic dispersion under LaBSE (REQ-026): log(dispersion / gen 0) | H1 semantic_dispersion_labse_logratio0: +0.0131 [+0.0104, +0.0158], p_boot 0.0000, predicted sign - (no)
- (ix) semantic dispersion under LaBSE (REQ-026): log(dispersion / gen 0) | H2 semantic_dispersion_labse_logratio0: -0.5349 [-1.0844, -0.1538], p_boot 0.0000, predicted sign + (no)
- (vi) quadratic term: 8 of 24 chain x metric fits have a 95% CI excluding 0 (`robustness_quadratic.csv`).
- (vii) base-tokenizer metrics (REQ-027): contrasts above; distinct-1..4 and TTR on token ids for every step in `T1_metrics.csv` / `T2_slopes.csv` (`*_tok`); input `results/tokenizer_metrics.jsonl`.
- (viii) n-gram novelty and duplicates against the seed (REQ-027; descriptive): `robustness_viii_novelty_duplicates.csv`, 98 synthetic training corpora, 4,021,761 documents. novelty_1..4 = share of word n-gram occurrences never found in the seed. Near-duplicates of seed documents by the pipeline's MinHash test against the seed signatures: 1 documents in total (largest rate in one corpus 2.44e-05); exact duplicates of seed documents (first 400 words): 0 documents in total. Figure `F8_novelty`.
- (ix) semantic dispersion (REQ-026): contrasts above; values for every step in `T1_metrics.csv` (`semantic_dispersion_labse`); input `results/semantic_dispersion.jsonl`.

## Exploratory (01: reported, not tested)
- Per-stratum recall, bias-probe drift (within language), fertility of generated text and the NLL of the sample under the generation-0 model: slopes in `exploratory_slopes.csv`, series in `T1_metrics.csv`, figures `F3_recall_strata` and `F6_nll_under_gen0`.
- Generation-0 recall per stratum and 95% CI (floor rule; at chance = CI includes 0.25): EN HEAD 0.500 [0.431, 0.569]; BN HEAD 0.530 [0.461, 0.598]; EN MID 0.570 [0.501, 0.637]; BN MID 0.360 [0.297, 0.429]; EN TAIL 0.580 [0.511, 0.646]; BN TAIL 0.405 [0.339, 0.474]
- 'Fairness before perplexity' (BN): first generation whose 95% CI no longer overlaps the generation-0 CI, per metric: `exploratory_fairness_before_perplexity_BN.csv` (descriptive operationalisation by the agent; not pre-specified).
- n-gram novelty of each synthetic corpus against the seed: with robustness (viii) (`robustness_viii_novelty_duplicates.csv`).

## Screening measures (07 §5b; EXPLORATORY, never used for a test)
- `S1_screening.csv`: 1636 rows (share of documents, Wilson 95% CI), for each generation's sample (`screen_*`) and every model-written training text (`screen_train_*`); references: held-out real text and the base model. Figure `F7_screening`.

## Figures
- F1_primary (confirmatory chains, CI bands), F1_all_chains (every chain incl. extension, seeds, controls), F2_contrasts (H1/H2 with CIs), F3_recall_strata, F4_filter (filter statistics, when the extracted step records are present), F5_length_check (shortcut check), F6_nll_under_gen0, F7_screening (exploratory), F8_novelty (robustness viii, when computed).

