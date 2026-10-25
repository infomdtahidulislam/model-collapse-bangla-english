# PATCH_NOTES: posthoc_gpu_pack, run on the VPS on 2026-10-20

The VPS agent (Claude Code on the authors' Windows Server VPS) ran this pack for the authors on 2026-10-20 (REQ-032 in `signoffs/REQUESTS.md`). Before any GPU time it checked every script against the archive's own file list (`results/packs/pack_manifest_20261016-232223.json`) and the harness code, and fixed the defects below.

The PC originals are kept byte-identical in `_original_from_pc/` (`SHA256SUMS.txt`); `patches.diff` beside this file is the unified diff. The statistics, outputs and file names are the PC agent's. Nothing registered changes.

## Route used (instead of `run_from_pc.py` → `RUN_ALL.sh` → `01_fetch.sh`)

The VPS holds the verified archive (`results/packs/cg4_pack_20261016-232223.tar.gz`, G4b) and its G6 extraction (`results/g6_extract/`, every file SHA-256 checked). So:

- **#17 (02) ran on a rented RTX 4090** (instance 56846008, Ireland).
  - Only the 26 steps it needs went to the host: 15.08 GB, every file's SHA-256 equal to the pack manifest. The pack's route would have downloaded the whole 55.7 GB from Google Drive, billed per GB on the host, with the Drive file shared by link.
  - Staging: `vps_route/stage_inputs.py`. Upload: `vps_route/upload_inputs.py`.
  - On the host, `vps_route/host_run_02.sh` checked the SHA-256 of every input again and installed the run's transformers stack (transformers 5.17.0, tokenizers 0.23.3, safetensors 0.8.0, huggingface_hub 1.33.0, regex 2026.9.29; torch 2.8.0 from the image).
- **#18 (04) and #19 (03) ran on the VPS CPU** with `--root results/g6_extract`. Neither needs a GPU.
- `RUN_ALL.sh`, `01_fetch.sh`, `05_pack_results.sh` and `run_from_pc.py` are unchanged and were not used. The patched scripts still default to `extracted/` with the archive's own paths, so the Drive route would also work with them.

## Fixes

### 02_cross_decoder.py (#17)

1. **Top-k 64 removed.** Every checkpoint's `generation_config.json` (one SHA-256 for all 117) holds Gemma's defaults `top_k: 64, top_p: 0.95`. HF `generate()` starts from that config and only overrides what is passed. The old call passed `top_p` but not `top_k`, so both decoders were top-k 64 samplers.
   - Shown on the VPS with GEN0-EN: the old call kept 64–67 tokens per step at "top-p 1.0"; the fixed call keeps all 262,144.
   - The registered sampling (vLLM `SamplingParams`) has no top-k. The fix passes `top_k=0`, `temperature=1.0` and `top_p` as `generate()` keyword arguments.
   - Do not pass a separate `GenerationConfig` instead: transformers then fills fields left at their global default from the model's file, which would turn `top_p=1.0` into 0.95.
   - A start-up decoder check, recorded in `cross_decoder_checks.json`, confirms this on the host from the processed scores. Top-p 1.0 must keep the whole vocabulary. Top-p 0.95 must keep exactly the top-p set of the raw logits.
2. **Length cap = the registered one.** `max_new_tokens` comes from the step's `sample_meta.json` (EN 260, BN 338), as in the run. The old code used max(n_tokens of the 50 rows) + 8, capped at 384, which gave 268 and 346.
3. **Fixed seeds.** `seed = zlib.crc32("<chain>|<gen>|<top_p>")`. The old `abs(hash((name, gen, top_p)))` changes with every Python process (hash randomisation), so a rerun would sample differently. Batches use seed + batch offset, as before.
4. **Files at the archive's paths** (`results/chains/<chain>[/gen_<g>]/...`) instead of the regex walk, which was fragile. The confirmatory REPLACE chains have generations 1–10; generations 1–6 are used, as the PC agent designed.
5. **No pad stripping.** A `<pad>` token the model actually samples stays in the continuation, as in the registered vLLM sampling. Only the first `<eos>` ends a continuation. HF pads only after `<eos>`, so nothing else changes.
6. **Missing `prefix_ids` is an error.** A step with fewer than 50 rows carrying `prefix_ids` now stops the run (the old code went on with fewer rows).
7. **Added, all backward compatible:**
   - A per-step **scorer check** (`cross_decoder_scorer_check.csv`): the registered `sample_scores.jsonl` statistic is recomputed for the first 50 archived documents of every step. It shows that the host reproduces the registered gen-0 scorer.
   - Extra summary columns `n_empty`, `cap_hit_share`, `max_new_tokens` and `seed`, and a `finish` field per sample.
   - A gzip header with mtime 0, so the file's bytes are reproducible.
   - Options `--root --out --steps --n --max-new --batch --device`. The defaults reproduce the original behaviour.

### 03_labse_sensitivity.py (#19)

1. **Sets = the first 50 documents of each step's `sample.jsonl`.** Those are exactly `results/samples/<step>_50.jsonl`, the human-read files. The old regex walk took whichever of the two files it met first. It also missed GEN0's `_50` file, because its lookahead rejects `GEN0-EN_`.
   - Empty continuations are counted (`labse_info.json`), not replaced by the 51st document, so the set stays the human-read set.
2. **Registered (ix) statistic.**
   - LaBSE is pinned to the revision robustness (ix) used (`836121a0533e5664b21c7aacc5d22951f2b8b25b`).
   - Dispersion uses the (ix) formula in float64: 1 − (|Σe|² − n) / (n(n − 1)) on unit-normalised embeddings.
   - The archive holds no harness, so the old code always took its fallback, which is the same quantity in float32.
3. The human-read folder is found next to the script, not the working directory. New options `--root --out --device`.

### 04_nonword_bigram.py (#18)

1. **The real training corpora.** A generation's corpus is `gen_<g>/synthetic.jsonl`: `harness/run_chain.py step()` writes it from generation g − 1's model, and generation g is trained on it.
   - The old search accepted only file names containing "corpus" or "train", so it found none.
   - It would then have fallen back to `sample.jsonl` or `sample_scores.jsonl`, whichever the directory walk met first, and labelled it "50-sample file".
   - Now a missing corpus is an error, with no fallback.
2. A malformed JSON line now raises instead of being skipped. The corpora are SHA-256 checked, so none is expected. New column `n_docs`, and options `--root --out`.

## Checks done on the VPS

- **#18 equals robustness (viii).** For all 12 corpora, #18's word and document counts are identical to `results/novelty_duplicates.jsonl`. Its `token_oov_share` equals (viii)'s `novelty_1` within its 5-decimal rounding (largest difference 4.96e-06). See `vps_route/crosscheck_18_vs_viii.py` and `nonword_crosscheck_viii.csv`.
- **#17 smoke test on the VPS CPU** (GEN0-EN, 4 prefixes, 12 new tokens): decoder check OK, and registered sample NLLs reproduced within 0.004 nats/token with every token count equal.
- **#17 on the GPU** (transformers 5.17.0, torch 2.8.0):
  - All 210 inputs match the manifest on the host.
  - Decoder check OK: top-p 1.00 keeps all 262,144 tokens; top-p 0.95 keeps 1 to 2,450, matching the top-p rule at 24 of 24 steps.
  - Scorer check over 26 steps × 50 documents: token counts all equal. Per-token NLL differs by mean 0.002–0.003 (EN) and 0.010–0.016 (BN).
  - `vps_route/scorer_numerics_probe.py` (output `scorer_numerics_probe.csv`) traces that to bf16 rounding:
    - The harness's own batching over 2,000 documents gives mean |Δ| 0.0022 (EN) and 0.0121 (BN), with a signed mean of about 0.
    - bf16 against fp32 differs by 0.0020 (EN) and 0.0174 (BN).
- **#19's human-read join works** (20 of 50 sample ids per file). Only the first 20 prompts of each file carry fluency ratings, and 0–4 of them per file have a mean ≥ 4. That is below the script's minimum of 8, so `labse_fluent_subset.csv` has no fluent-only dispersion values. This follows from the data and the PC agent's threshold. It was not changed.
