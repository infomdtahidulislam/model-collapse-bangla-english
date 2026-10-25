# posthoc_gpu_pack2 (2026-10-23): seed replicates of the two controls, cross-decoder over three seeds, full-sample check

**For the VPS agent (Claude Code on the authors' VPS), which runs this pack from the VPS.** Nothing in it runs from the PC.
Everything here is post-hoc: it was decided after the registered results had been read, it is not pre-registered, and it
changes no registered file, number, test or verdict. The results feed a dated post-hoc section of the paper.

**Authors' decision (chat, 2026-10-22T22:36Z; confirmed 2026-10-24):** run two more seeds per language of REAL-REPEAT
and of the top-p 0.95 chain, a larger cross-decoder sample, and the equal-length diversity check on the full
2,000-document samples. File it as **REQ-035** (BUDGET and DECISION) in `signoffs/REQUESTS.md`, quoting this decision,
before any GPU time. Cap for this pack: **US$15**.

## 1. What runs, and why

| Part | Where | What | Why |
|---|---|---|---|
| A. eight chains | rented RTX 4090 | `EN/BN-REAL-REPEAT-s2/-s3`, `EN/BN-REPLACE-topp95-s2/-s3`, six generations each, with the registered recipe | The paper's two headline controls (REAL-REPEAT and the top-p 0.95 decoding arm) are single chains. Each new chain starts from the same re-seeded generation-0 model as the registered REPLACE seed of the same number (`GEN0-EN-s2`, ...), so REPLACE-sK minus REAL-REPEAT-sK and REPLACE-sK against REPLACE-topp95-sK are paired comparisons, exactly as for seed 0. |
| B. cross-decoder over three seeds | same host, after A | `host/02b_cross_decoder.py`: the 12 REPLACE-family chains (seeds 0, 2, 3 under each training decoder) at generations 1 to 6, plus their six generation-0 models, each sampled under both decoders, 200 prefixes per cell (was 50), each chain scored under its own generation-0 model | The paper's main extension (the direction of sample NLL and distinct-2 follows the training-text decoder) currently rests on one chain per training decoder and 50 draws per cell. |
| C. full-sample equal-length check | VPS CPU | `cpu/full_sample_equal_length.py` on the archived 2,000-document samples of all 17 registered chains and the eight new ones | Supplementary Section S14 (Table S12) ran this check on the released 50-document files only. |

Expected GPU time, from the archived step records (EN/BN-REAL-REPEAT: about 14.5 min per step; REPLACE-topp95: about 23.5 min
per step): A = 24 x 14.5 min + 24 x 23.5 min, about 15.2 h; B about 3 h (31,200 draws at the 2026-10-20 rate of about 0.34 s per draw, scoring included);
setup and pre-flight about 1 h. **About 19 to 20 GPU-hours, roughly US$9 at US$0.45/h.** If the cap gets close, the plan
stops starting new steps (`--max-hours`): the order is priority 8 (REAL-REPEAT-s2), 9 (topp95-s2), 10 (REAL-REPEAT-s3),
11 (topp95-s3), so a partial run still yields complete second seeds. Part B needs only the topp95 seeds that finished.

## 2. Files in this pack

| File | Role |
|---|---|
| `configs/chains_posthoc_2026-10-23.yaml` | a copy of the registered `configs/chains.yaml` (SHA-256 c911895e...) with four comment lines on top and the eight chains (`posthoc: true`, priorities 8 to 11) appended to `robustness_chains`; every other setting is identical (checked by parsing both files) |
| `harness_patch/apply_patch.py` | the only code change to the harness, applied on the HOST copy only: `common.load_chains_cfg()` reads `CG4_CHAINS_CFG` when that variable is set. Refuses to run unless `harness/common.py` is the run's version (f7618104...); prints the patched hash |
| `vps_route/stage_inputs2.py` | stages batch A (the four re-seeded generation-0 models, harness, configs, schemas, data, this pack) and batch B (the 50 checkpoints, about 27 GB, that the cross-decoder needs besides the new chains) from `results/g6_extract/`, `results/chains/` or the archive; every archive member checked against the pack manifest, every key package file against the run's SHA-256; writes `inputs_A.sha256` and `inputs_B.sha256` |
| `vps_route/upload_inputs2.py` | uploads a staged batch to `/workspace/CG4` on the host (small files as one tarball, weights in parallel scp streams, sizes checked on the host) |
| `host/host_run2.sh` | on the host: `setup` (unpack and SHA-check batch A, post-hoc config, patch, the run's pinned stack via `harness/vast/bootstrap.sh`, `test_sanity.py`, `smoke_gpu.py`, the plan must list exactly the 8 chain jobs and no gen-0 or base job), `chains HOURS`, `xdec` (unpack and check batch B, then 02b), `pack` |
| `host/02b_cross_decoder.py` | the 2026-10-20 cross-decoder script as run (`host/02_cross_decoder_as_run_2026-10-20.py`, SHA-256 de660e6e...) with only these changes: chain list option (default the 12 chains), each chain scored under its own generation-0 model (gen0_id from its step.json, as the registered sample NLL does), a gen-0 cell for every gen-0 model used, `--n 200`, `--check-n 50` for the scorer check, outputs named `cross_decoder2_*`. Seeds unchanged, so the first 50 draws of each seed-0 cell use the 2026-10-20 seeds |
| `cpu/full_sample_equal_length.py` | the Table S12 statistic on the full samples (defaults: 2,000 prefixes, stability subsets of 1,600, 500 subsets, seed 20261024); numbers only |
| `SHA256SUMS.txt` | hashes of every file of this pack |

Tested before shipping (PC agent's cloud workspace, 2026-10-23): the post-hoc config parses to the registered settings plus the
eight chains; with the patch and `CG4_CHAINS_CFG` set, `run_rented.py --plan --skip-gen0 --chains <8>` lists exactly the eight
chain jobs in priorities 8 to 11, and with the variable unset it lists nothing; `02b_cross_decoder.py` ran end to end on tiny
random models (40 cells, per-chain gen-0 scorers, decoder check OK); `full_sample_equal_length.py` with `--n 50 --m 40 --B 2000
--seed 20261023` on a tree built from the released 50-document files reproduced every value of Supplementary Table S12 exactly.

## 3. Steps

0. **Place and check the pack.** Copy this folder to the package root (`<package>/posthoc_gpu_pack2_2026-10-23/`) and run
   `sha256sum -c SHA256SUMS.txt` inside it. File REQ-035 as above. Log each step below in `logs/decisions.md` as usual.
1. **Stage** on the VPS: `python posthoc_gpu_pack2_2026-10-23/vps_route/stage_inputs2.py --batch A` (about 2.4 GB plus the
   package files), then `--batch B` (about 27 GB; it can run while the host works on part A).
2. **Rent** one RTX 4090 as in `12_VASTAI_RUNBOOK.md`: a driver that supports CUDA 13.0 (the pinned torch 2.13.0+cu130),
   at least 120 GB disk (inputs about 30 GB, new checkpoints about 26 GB, synthetic corpora about 2 GB, working space), price
   at or below the run's (about US$0.45/h). Push `/workspace/.env` (HF token for `smoke_gpu.py`) with `vast_ops.py push-env`.
3. **Upload batch A**: `python posthoc_gpu_pack2_2026-10-23/vps_route/upload_inputs2.py --instance <ID> --batch A`.
4. **Setup on the host**: `bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh setup` (through `vast_ops.py run`). Go on only
   if `STATUS_posthoc2` reads `SETUP_OK`. Check that `logs/posthoc2_pip_freeze.txt` shows the pinned versions
   (vllm 0.31.0, torch 2.13.0, transformers 5.17.0, ...), as every rental of the run did.
5. **Chains**: `bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh chains <H>` with H = (15 - spend so far - 2 reserve) /
   hourly price. Check `vast_ops.py status` at least every 2 h. Upload batch B meanwhile.
6. **Cross-decoder**: `bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh xdec`.
7. **Pack and pull**: `bash posthoc_gpu_pack2_2026-10-23/host/host_run2.sh pack`; pull `posthoc2_results_small.tar.gz`,
   `posthoc2_checkpoints_corpora.tar`, `posthoc2_packs.sha256`, `posthoc2_files.sha256` and `logs/posthoc2_*`; check the
   SHA-256 of both packs on the VPS; stop the instance; file the TEARDOWN request for the authors (they destroy it).
8. **Archive** the big tar beside the G4b archive, with a member manifest and SHA-256 (as `pack_results.py` does), and ask
   the authors for the second copy (their Google Drive folder `CG4_backup`), as at G4b.
9. **Full-sample check on the VPS CPU.** First the validation, which must reproduce Table S12 exactly (the first 50 rows of
   each archived `sample.jsonl` are the released 50-document file):
   `python posthoc_gpu_pack2_2026-10-23/cpu/full_sample_equal_length.py --roots results/g6_extract --out results/posthoc_seeds_2026-10-23/full_sample_check_validation --n 50 --m 40 --B 2000 --seed 20261023 --chains EN-REPLACE EN-REPLACE-s2 EN-REPLACE-s3 EN-ACCUMULATE EN-ACCUMULATE-FILTER EN-ACCUMULATE-SUBSAMPLE EN-REAL-REPEAT EN-REPLACE-WM EN-REPLACE-topp95 BN-REPLACE BN-REPLACE-s2 BN-REPLACE-s3 BN-ACCUMULATE BN-ACCUMULATE-FILTER BN-ACCUMULATE-SUBSAMPLE BN-REAL-REPEAT BN-REPLACE-topp95`
   Expected, for example: EN-REPLACE +0.00381 [+0.00200, +0.00557], 3,282 words per step; EN-REPLACE-topp95 -0.02720
   [-0.02974, -0.02322], 3,197; BN-ACCUMULATE-SUBSAMPLE +0.00147 [+0.00072, +0.00186], 2,624. If any value differs, stop and
   report. Then the real run over all 25 chains (unpack the small pack first, see step 10):
   `python posthoc_gpu_pack2_2026-10-23/cpu/full_sample_equal_length.py --roots results/g6_extract results/posthoc_seeds_2026-10-23/host --out results/posthoc_seeds_2026-10-23/full_sample_check`
   (defaults: 2,000 prefixes, subsets of 1,600, 500 subsets, seed 20261024; a few minutes per chain).
10. **Assemble the take-home folder** `results/posthoc_seeds_2026-10-23/`: `host/` (the small pack unpacked at its own paths:
    the eight chains' records and sidecars without weights or synthetic corpora, `results/metrics.jsonl` renamed
    `metrics_posthoc_2026-10-23.jsonl`, the 50-document files, `results/posthoc2_cross_decoder/`, the host logs), the two
    full-sample-check folders, the VPS logs of this pack, and `SHA256SUMS.txt` over everything. Zip it as
    `results/posthoc_seeds_2026-10-23.zip` with its SHA-256 beside it, and tell the authors it is ready to copy to the PC
    folder `results/`.

## 4. Checks to report

- Every staged input matched (batch A and B), the patched `common.py` hash, and the plan file (8 jobs, no gen-0 or base job).
- For each of the eight chains: the generations completed (all six expected), the final training loss of each step, and the
  `step.json` seed, seed offset, gen0_id and sampling (top_p 1.0 for REAL-REPEAT's evaluation samples, 0.95 for topp95).
- `cross_decoder2_checks.json`: `decoder_check_ok` true; scorer check token-count mismatches 0 and mean |diff| of the order
  of the 2026-10-20 run (0.002 to 0.016 nats/token); 156 cells with 200 draws each (fewer usable draws only for empty
  continuations, which the summary counts).
- The validation run of step 9 reproduced Table S12.
- Spend: GPU-hours, price, total for this pack and the new study total.

## 5. Do not

- Edit `configs/chains.yaml`, `results/metrics.jsonl`, `results/analysis/` or anything registered on the VPS or PC copies.
  The patch and the post-hoc config live only on the host and in this pack.
- Run `analyze.py` with `CG4_CHAINS_CFG` set, or merge the new metric records into `results/metrics.jsonl`.
- Release, print or paste model-written text. The new `sample.jsonl` files, the 50-document files, the synthetic corpora and
  `cross_decoder2_samples.jsonl.gz` hold unscreened model output: private storage only, as for the registered run.
- Interpret results. Report numbers and checks; the PC agent writes the analysis for the authors.
