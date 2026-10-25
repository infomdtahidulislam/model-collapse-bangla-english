# Checks of the posthoc_gpu_pack2 results (README_RUN.md section 4)

Written by `scripts/checks_posthoc2.py` (2026-10-24T17:51Z) from the take-home folder `results/posthoc_seeds_2026-10-23/` and the registered records named below. Numbers, hashes and log lines only; no model-written text is shown. A failed check is marked **NO** and listed at the end.

## 0. Take-home folder

- `results/posthoc_seeds_2026-10-23.zip`: SHA-256 `75725fb11785aa128f50548c580a2e3111bf6290ba2d4d5eac30d34d57c80b77`. Same as given by the authors: yes; same as the `.sha256` file beside it: yes.
- `SHA256SUMS.txt` lists 504 files; 504 are present with matching SHA-256: yes. Files in the folder but not listed: 0; listed but missing: 0.

## 1. Inputs, patch, plan, software

- Batch A: setup log `batch A: all 110 files match (pack manifest for archive members, run hashes for package files)`; `inputs_A.sha256` lists 110 files: yes. Batch B: cross-decoder log `batch B: all 450 files match (pack manifest for archive members, run hashes for package files)`; `inputs_B.sha256` lists 450 files: yes. VPS staging log: batch A done: 110 files listed in inputs_A.sha256; batch B done: 450 files listed in inputs_B.sha256.
- Configs on the host (setup log): `chains.yaml` c911895ecc1f6b00..., the registered file on the PC c911895ecc1f6b00...: yes; `chains_posthoc_2026-10-23.yaml` 8bf3f19db5703771..., same as the pack copy and the take-home copy: yes.
- Patched `harness/common.py`: before `f7618104c625fd389a097e4434365b0138601d9f39ed7f394e8e6d258d942ca5` (the PC's registered `harness/common.py` is `f7618104c625fd389a097e4434365b0138601d9f39ed7f394e8e6d258d942ca5`: yes); after `de72a8f9d91d0b7f8f10ef6b8fa03632456f0af4bab4d0f4d54be322adf353c9` (the take-home `host/harness/common.py` is `de72a8f9d91d0b7f8f10ef6b8fa03632456f0af4bab4d0f4d54be322adf353c9`: yes). The patch only adds `import os` and lets `load_chains_cfg()` read `CG4_CHAINS_CFG` when it is set (8 changed lines): yes:

```diff
--- harness/common.py (as run)
+++ host/harness/common.py (patched)
@@ -6,0 +7 @@
+import os
@@ -45,2 +46,5 @@
-    """configs/chains.yaml (frozen, registered) with the whitelisted operational overrides of configs/runtime.yaml on top."""
-    with open(path or CONFIGS / "chains.yaml", encoding="utf-8") as f:
+    """configs/chains.yaml (frozen, registered) with the whitelisted operational overrides of configs/runtime.yaml on top.
+    Post-hoc runs (posthoc_gpu_pack2, 2026-10-23) may set CG4_CHAINS_CFG to a copy with added chains; the registered
+    file is never edited, and with the variable unset nothing changes."""
+    env_cfg = os.environ.get("CG4_CHAINS_CFG")
+    with open(path or (Path(env_cfg) if env_cfg else CONFIGS / "chains.yaml"), encoding="utf-8") as f:
```

- Plan (`posthoc2_plan.txt`): 8 jobs, priorities [8, 9, 10, 11], chains BN-REAL-REPEAT-s2, EN-REAL-REPEAT-s2, BN-REPLACE-topp95-s2, EN-REPLACE-topp95-s2, BN-REAL-REPEAT-s3, EN-REAL-REPEAT-s3, BN-REPLACE-topp95-s3, EN-REPLACE-topp95-s3. Exactly the eight post-hoc chains, each once: yes; no generation-0 or base job: yes. Setup ended `== setup OK`: yes. `STATUS_posthoc2` reads `XDEC_DONE`.
- Software (`posthoc2_pip_freeze.txt`): vllm 0.31.0, torch 2.13.0, transformers 5.17.0, tokenizers 0.23.3, accelerate 1.15.0: the README's pins (vllm 0.31.0, torch 2.13.0, transformers 5.17.0): yes. All 13 pins of `harness/vast/pins_gen0.txt` (the generation-0 stack) match the freeze: yes. GPU: RTX 4090.

## 2. The eight chains

Per step: `host/results/chains/<chain>/gen_<g>/step.json`; the registered step records come from `results/cg4_sidecars_from_G4b_2026-10-20.zip`. All values per step are in `out/checks_steps.csv`.

| chain | generations done | final training loss, generations 1 to 6 | seeds (step) | offset | gen0_id | top-p: evaluation sample / training text |
|---|---|---|---|---|---|---|
| EN-REAL-REPEAT-s2 | [1, 2, 3, 4, 5, 6] | 2.6459 2.4952 2.2904 2.1369 1.9507 1.7872 | 20262011 to 20262016 | 1000 | GEN0-EN-s2 | 1.0 / real text only |
| BN-REAL-REPEAT-s2 | [1, 2, 3, 4, 5, 6] | 3.1630 3.0045 2.8537 2.6800 2.5470 2.4104 | 20262011 to 20262016 | 1000 | GEN0-BN-s2 | 1.0 / real text only |
| EN-REPLACE-topp95-s2 | [1, 2, 3, 4, 5, 6] | 2.8941 2.5866 2.2609 1.9537 1.6994 1.4227 | 20262011 to 20262016 | 1000 | GEN0-EN-s2 | 0.95 / 0.95 |
| BN-REPLACE-topp95-s2 | [1, 2, 3, 4, 5, 6] | 3.4938 3.1622 2.8760 2.5277 2.1533 1.7751 | 20262011 to 20262016 | 1000 | GEN0-BN-s2 | 0.95 / 0.95 |
| EN-REAL-REPEAT-s3 | [1, 2, 3, 4, 5, 6] | 2.6585 2.4677 2.2928 2.1279 1.9554 1.7705 | 20263011 to 20263016 | 2000 | GEN0-EN-s3 | 1.0 / real text only |
| BN-REAL-REPEAT-s3 | [1, 2, 3, 4, 5, 6] | 3.1511 2.9873 2.8702 2.7048 2.5684 2.4157 | 20263011 to 20263016 | 2000 | GEN0-BN-s3 | 1.0 / real text only |
| EN-REPLACE-topp95-s3 | [1, 2, 3, 4, 5, 6] | 2.9073 2.5704 2.2175 1.9118 1.6431 1.3798 | 20263011 to 20263016 | 2000 | GEN0-EN-s3 | 0.95 / 0.95 |
| BN-REPLACE-topp95-s3 | [1, 2, 3, 4, 5, 6] | 3.5180 3.2122 2.8763 2.4821 2.1220 1.7557 | 20263011 to 20263016 | 2000 | GEN0-BN-s3 | 0.95 / 0.95 |

- All six generations done for each chain (`state.json` and a `step.json` per generation): yes; no NaN loss: yes; 2,000-document evaluation sample at every step: yes (empty-continuation rate 0.0000 to 0.0040).
- Top-p as specified (evaluation samples 1.0 for REAL-REPEAT, 0.95 for topp95; topp95 training text 0.95): yes.
- Paired with the registered REPLACE chain of the same seed: same step seed and sample seed at every generation: yes; same generation-0 model: yes (seed offset 1000 for s2, 2000 for s3); each step starts from the chain's previous checkpoint (generation 1 from its generation-0 model): yes.
- Registered recipe: every `step.json` setting equals that of the registered seed-0 chain of the same arm at the same generation (EN/BN-REAL-REPEAT, EN/BN-REPLACE-topp95), apart from run-specific fields (ids, seeds, times, losses, sample statistics and, for topp95, the sizes that follow from the generated text): yes. The REAL-REPEAT training sets have the same sizes as the registered REAL-REPEAT at every generation (real documents, tokens, blocks, optimizer steps): yes.
- Final training loss beside the registered seed-0 chain of the same arm (mean over generations 1 to 6): EN-REAL-REPEAT-s2 2.2177 vs 2.2190; BN-REAL-REPEAT-s2 2.7765 vs 2.7744; EN-REPLACE-topp95-s2 2.1362 vs 2.1718; BN-REPLACE-topp95-s2 2.6647 vs 2.6911; EN-REAL-REPEAT-s3 2.2121 vs 2.2190; BN-REAL-REPEAT-s3 2.7829 vs 2.7744; EN-REPLACE-topp95-s3 2.1050 vs 2.1718; BN-REPLACE-topp95-s3 2.6611 vs 2.6911.
- `metrics_posthoc_2026-10-23.jsonl`: 2,112 records = 8 chains x 6 generations x 44 metrics: yes; duplicates 0; the same metrics per step as the registered seed-0 chains: yes; each record names its own step's checkpoint: yes; empty values 0 (registered seed-0 counterparts: 0). The generation-0 points of the new chains (GEN0-BN-s2, GEN0-BN-s3, GEN0-EN-s2, GEN0-EN-s3) are registered records in `results/metrics.jsonl`: yes.

## 3. Cross-decoder over three seeds

- `cross_decoder2_checks.json`: `decoder_check_ok` True: yes (top-p 1.0: 24 of 24 steps follow the rule, 262144 to 262144 of 262144 tokens kept; top-p 0.95: 24 of 24 steps follow the rule, 1 to 2243 of 262144 tokens kept). 200 prefixes per cell, scorer check on 50 documents per step; torch 2.13.0+cu130, transformers 5.17.0. Each chain scored under its own generation-0 model (the step's gen0_id): yes.
- Scorer check (`cross_decoder2_scorer_check.csv`, the registered sample-NLL statistic recomputed on the host for the first 50 archived documents of each step): 78 rows (72 chain steps and 6 generation-0 models): yes; token-count mismatches 0: yes. Mean |diff| 0.001962 to 0.017337 nats/token (EN 0.001962 to 0.003334, BN 0.008954 to 0.017337); max |diff| per row 0.006017 to 0.093761. On 2026-10-20 (26 rows): mean |diff| 0.002055 to 0.016073 (EN 0.002055 to 0.003292, BN 0.010347 to 0.016073). Rows above 0.016: 2, BN-REPLACE-topp95-s3 generation 2 (0.017337, max 0.073122), BN-REPLACE-s2 generation 6 (0.016008, max 0.067997); both are BN rows, where every row is between 0.0090 and 0.0173. The 26 steps checked in both runs differ by 0.000006 to 0.003291 in mean |diff|.
- Cells (`cross_decoder2_summary.csv`): 156 = 78 steps x 2 decoders: yes; 200 draws in every cell, n + n_empty = 200: yes; usable draws per cell: 153 cells with 200, 3 cells with 199. The cells with 199: BN-REPLACE-topp95-s2 generation 5, evaluation top-p 1.0 (n_empty 1); BN-REPLACE-topp95-s2 generation 6, evaluation top-p 1.0 (n_empty 1); BN-REPLACE-topp95-s3 generation 4, evaluation top-p 0.95 (n_empty 1). In the samples file these are 3 records with 0 tokens and no NLL: yes. The generation-0 model named in each cell is the chain's own: yes. Every cell has the same 200 prefix ids within a language: yes; cell means recomputed from the samples file equal the summary (max |diff| 0.00005 at its 4 decimals; n equal: yes). Generation cap: EN 260, BN 338 tokens; share of draws at the cap EN 0.65 to 0.86, BN 0.42 to 0.66.
- Against the 2026-10-20 run (same seeds for the first 50 draws of the seed-0 cells): its prefix ids are the first 50 of each language here: yes. Of the 2600 draws in both runs, 204 continuations are identical (7.8%; the host's torch changed from 2.8.0+cu129 to 2.13.0+cu130, so identical seeds need not give identical samples); identical ones also have the same token count: yes. Their NLL differs by a median 0.0065 nats/token (95th percentile 0.0697; the largest, 0.7512, is for a continuation of 1 tokens, where the per-token mean rests on few tokens).

## 4. Full-sample equal-length check

- Validation (`full_sample_check_validation/`, 50 prefixes, subsets of 40, 2,000 subsets, seed 20261023): 17 chains, 17 matched to Supplementary Table S12 (`results/analysis/posthoc_review_2026-10-22/prefix_paired_diversity_equal_K100.csv`). Point and stability range, as the run printed them at 5 decimals from full precision (`vps/logs/posthoc2_full_sample_validation.log`), equal every Table S12 value: yes. The 6-decimal CSV agrees within its precision (largest difference 0.000005; re-rounding it to 5 decimals splits three ties that end in 5 at the sixth decimal). Words per step, prefixes at full K and median words per prefix identical: yes. README examples: EN-REPLACE +0.00381 [+0.00200, +0.00557], 3,282 words; EN-REPLACE-topp95 -0.02720 [-0.02974, -0.02321], 3,197 words; BN-ACCUMULATE-SUBSAMPLE +0.00147 [+0.00072, +0.00186], 2,624 words.
- Run (`full_sample_check/`, 2,000 prefixes, subsets of 1,600, 500 subsets, seed 20261024): 25 chains (17 registered + 8 post-hoc): yes; 2,000 prefixes each; generation-0 model as configured (none for the topp95 chains, whose statistic is the raw slope over generations 1 to 6): yes. Results: see the analysis.

## 5. Spend

- Instance 57450903 (RTX 4090, offer US$0.616/h): created 2026-10-24T01:50:14+00:00, stopped 2026-10-24T16:13:38+00:00 = 14.39 h (US$8.86 at the offer price, before disk and bandwidth); last status line before the stop: 14.1 GPU-h, US$8.71. Deleted by the authors; the VPS agent confirmed 0 instances and 0 volumes at 2026-10-24T17:05:49Z (REQ-036).
- Invoiced for this pack: US$9.00 for 14.4 GPU-h, cap US$15 (pre-run estimate 19 to 20 GPU-h, about US$9 at US$0.45/h). CG4 total US$47.83 of the US$55 ceiling (invoice query US$47.54 plus US$0.29 for 56846008); 125 GPU-h ceiling.
- The big archive `posthoc2_checkpoints_corpora.tar` (29,495,818,240 bytes, SHA-256 `057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f`; the `.sha256` file agrees: yes; manifest 264 members) stays on the VPS in `results/packs/`; the authors are making the second copy in Google Drive `CG4_backup`. Not needed for the analysis.

## Result

All checks passed.
