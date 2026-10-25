# CG4 post-hoc results #17, #18, #19: the take-home folder (VPS, 2026-10-20)

These are the results of `posthoc_gpu_pack/`, the pack the authors' PC agent wrote. The VPS agent ran it on 2026-10-20 at the authors' request (REQ-032):

- **#17**: cross-decoder evaluation of the REPLACE-family checkpoints.
- **#18 (full)**: nonword and novel-bigram composition of the synthetic training corpora.
- **#19**: sensitivity of the LaBSE dispersion measure.

All three are post-hoc and descriptive: not pre-registered, and no registered number changes. This folder holds numbers only. Interpreting them is the authors' job.

## Taking it to the PC

- Copy this whole folder, or the zip beside it: `results\cg4_posthoc_gpu_results_2026-10-20.zip`, with its SHA-256 in `...zip.sha256`.
- On the PC, put it in `CG4_model_collapse_lowresource_experiment\results\`.
- `SHA256SUMS.txt` checks every file.
- Tell the PC agent to start with this README, then read `code_as_run\PATCH_NOTES.md`.
- The scripts were fixed on the VPS before running, but the PC's own copy of `posthoc_gpu_pack\` still has the old ones. The fixed versions are in `code_as_run\`. Whether to replace the PC copies with them is the PC agent's call.
- `VPS_RECORDS_2026-10-20.md` holds today's records from the VPS, which the PC copy lacks: REQ-032 (BUDGET), REQ-033 (TEARDOWN, done), the decision-log lines, and the final CG4 spend (US$38.84). The PC agent should add them to its own `signoffs\REQUESTS.md` and `logs\decisions.md`.

**Private material:**

- `cross_decoder_samples.jsonl.gz` holds 2,600 newly generated continuations that have not been screened.
- `nonword_top_types.csv` lists word types taken from the synthetic corpora.

Keep both on private storage only: your PC or your private Google Drive. Never put them anywhere public. The same rule applies to `results\samples\`.

## Files

| File | Item | Ran on | Content |
|---|---|---|---|
| `cross_decoder_summary.csv` | #17 | rented RTX 4090 | 52 cells: 26 checkpoints × 2 decoders (top-p 1.00 and 0.95). For each: mean and SD per-token NLL under the language's gen-0 model, mean length, out-of-seed-vocabulary share, `n_empty`, `cap_hit_share`, `max_new_tokens`, `seed` |
| `cross_decoder_samples.jsonl.gz` | #17 | RTX 4090 | the 2,600 continuations (26 × 2 × 50) with their NLL (**unscreened**) |
| `cross_decoder_scorer_check.csv` | #17 check | RTX 4090 | per step, the registered `sample_scores.jsonl` NLL recomputed for the 50 archived documents |
| `scorer_numerics_probe.csv` | #17 check | RTX 4090 | GEN0-EN and GEN0-BN: the registered NLL recomputed with the harness's own batching (2,000 documents), and bf16 against fp32 |
| `cross_decoder_checks.json` | #17 check | RTX 4090 | decoder check, software versions, times |
| `host_pip_freeze.txt`, `host_nvidia_smi.txt` | #17 | RTX 4090 | the GPU host's environment |
| `labse_corruption.csv` | #19 (a), (b) | VPS CPU | dispersion of the 50 gen-0 samples under nonword substitution (0–40%), a repetition loop and (BN) Latin script mixing; REPLACE gen-6 reference |
| `labse_fluent_subset.csv` | #19 (c) | VPS CPU | the 12 human-read files: dispersion of all 50; fluent-only subset (see caveat 1) |
| `labse_info.json` | #19 | VPS CPU | LaBSE revision, versions, empty texts per set (none) |
| `nonword_corpus_shares.csv` | #18 | VPS CPU | EN and BN REPLACE training corpora, gen 1–6: token and type OOV shares against the seed vocabulary, novel-bigram shares, word and document counts |
| `nonword_top_types.csv` | #18 | VPS CPU | the 40 most frequent OOV types per corpus, flagged novel-bigram yes or no |
| `nonword_crosscheck_viii.csv` | #18 check | VPS CPU | #18 against the registered robustness (viii) |
| `INFO.md` | | | provenance in one page |
| `logs\` | | | `host_run_02.log` (the GPU job, complete), `host_scorer_numerics_probe.log`, `03_labse_sensitivity_vps.log`, `04_nonword_bigram_vps.log` |
| `code_as_run\` | | | the three scripts as run, `PATCH_NOTES.md`, `patches.diff`, the VPS-route tools, and the inputs' SHA-256 list (`inputs_17.sha256`) |
| `SHA256SUMS.txt` | | | every file in this folder |

## How it was run (not the pack's `run_from_pc.py` route)

The VPS holds the verified archive (`results\packs\cg4_pack_20261016-232223.tar.gz`) and its G6 extraction (`results\g6_extract\`, every file SHA-256 checked). That let the run be smaller and cheaper:

- **#17 ran on a rented RTX 4090** (Vast.ai instance 56846008, Ireland, US$0.546/h).
  - It received only the 26 steps it needs: 15.08 GB, every file equal to the archive manifest, and checked again on the host.
  - The pack's route would have downloaded the whole 55.7 GB from Google Drive, billed per GB.
  - The host used the experiment's transformers stack (5.17.0) and the image's torch 2.8.0.
- **#18 and #19 ran on the VPS CPU.** They need no GPU.
- **The Google Drive file was not used.** If you set `cg4_pack_20261016-232223.tar.gz` to "anyone with the link" for this pack, set it back to **Restricted**.

## Fixed before running (details in `code_as_run\PATCH_NOTES.md`)

1. **#17 would have sampled with top-k 64.** Every checkpoint's `generation_config.json` holds Gemma's default `top_k: 64`, and HF `generate()` applies it unless top-k is passed. So "top-p 1.00" would have kept only 64–67 tokens per step instead of all 262,144 (shown on the VPS). Now `top_k=0` is passed, as in the registered vLLM sampling, and a start-up check confirms it.
2. **#17's length cap** is now the registered one: 260 new tokens for EN, 338 for BN. Before it was max(n_tokens) + 8.
3. **#17's seeds** are now fixed (crc32). Before, Python's `hash()` changed them on every run.
4. **#18 now reads the real training corpora** (`gen_<g>/synthetic.jsonl`). Its old file search could not find them and would have fallen back to the sample files.
5. **#19 now reads exactly the human-read set** (the first 50 documents of each step's sample), with LaBSE at the revision robustness (ix) used and the (ix) formula.

## Checks

- **#18 equals the registered robustness (viii)** (`results\novelty_duplicates.jsonl`). For all 12 corpora the word and document counts are identical. The OOV share equals (viii)'s `novelty_1` within #18's 5-decimal rounding: largest difference 4.96e-06 (`nonword_crosscheck_viii.csv`).
- **#19:** the two reference rows equal the matching part-(c) rows (same 50 documents). None of the 14 sets contains an empty continuation (`labse_info.json`).
- **#17 inputs:** all 210 files (26 steps) matched the archive manifest on the host as well as on the VPS.
- **#17 decoder check: OK.** Top-p 1.00 keeps all 262,144 tokens at every step. Top-p 0.95 keeps 1 to 2,450 tokens, and 24 of 24 steps match the top-p rule computed from the raw logits.
- **#17 completeness:** 52 of 52 cells, each with 50 continuations. No empty continuation and no NaN. Caps 260 (EN) and 338 (BN). 52 distinct fixed seeds. 883 s on the GPU.
- **#17 scorer check:** the registered gen-0 sample NLL (`sample_scores.jsonl`) was recomputed for 26 steps × 50 documents.
  - Token counts are equal in all 1,300 documents.
  - Per-token NLL differs by mean 0.002–0.003 nats (EN) and 0.010–0.016 (BN), max 0.091.
  - `scorer_numerics_probe.csv` shows this is bf16 rounding, not a scorer difference.
    - Even the harness's own batching over all 2,000 documents differs from the archived values by mean |Δ| 0.0022 (EN) and 0.0121 (BN), with signed means of −0.00002 and +0.00016 (no bias).
    - bf16 against fp32 on the same documents differs by 0.0020 (EN) and 0.0174 (BN).
    - The host has torch 2.8.0; the run had 2.13.0.
  - #17 scores all its cells on one host in one way, so its comparisons are not affected.

## Caveats for the write-up (facts, not interpretation)

1. **#19 (c) gives no fluent-only dispersion.** Only the first 20 of the 50 samples in each human-read file carry fluency ratings. Of those, 0–4 per file have a mean of 4 or more, and the script needs at least 8. So `dispersion_fluent` is empty in all 12 rows and `n_fluent` shows the count. This follows from the data and the PC agent's threshold; the threshold was not changed.
2. **#17's statistic is not the registered `sample_nll_ref`.** #17 scores the continuation tokens given the prefix. The registered statistic scores prefix plus continuation as re-tokenised text. So #17's numbers compare within this diagnostic only, as the script's own docstring says. `cross_decoder_scorer_check.csv` shows the host reproduces the registered statistic itself.
3. **#17 samples with HF `generate`, not vLLM.** The decoders are the same by construction, and the start-up check confirms it: top-p 1.00 keeps the whole vocabulary, and top-p 0.95 keeps exactly the top-p set. Fresh seeds: the continuations are new draws, not the archived ones.
4. **#19 ran on the CPU, (ix) on a GPU.** The (ix) CPU and GPU values agreed within 1.5e-7 (REQ-028).

## Cost

- **Instance 56846008:** created 05:55Z, GPU running 05:57–06:28Z, then stopped. The authors deleted it, confirmed at 07:18:25Z (REQ-033); no instance exists now.
- **Invoiced:** US$0.29 for this instance (GPU, disk and bandwidth). The cap was US$2.50 (REQ-032).
- **CG4 total:** **US$38.84** invoiced of the US$50 ceiling (US$38.54 before this run).
- **#18 and #19** ran on the VPS CPU at no cost.
