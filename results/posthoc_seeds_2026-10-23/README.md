# Post-hoc seed replicates and three-seed cross-decoder evaluation (REQ-035; run 24 October 2026)

The records of the eight post-hoc chains (seeds 2 and 3 of REAL-REPEAT and REPLACE-topp95 in both languages; 48 checkpoints)
and of the cross-decoder evaluation over three seeds, as pulled from the GPU host and checked (`SHA256SUMS.txt` lists all 504
files of the take-home bundle, including the withheld ones). Decided by the authors on 22 October 2026, after the registered
results had been read; post-hoc and descriptive, no registered record changes. The analysis is in
`../posthoc_seeds_analysis_2026-10-24/` (scripts and numbers-only outputs); the 23 October scripts it copied are in
`../analysis/posthoc_seeds_2026-10-23/`.

| Path | Content |
|---|---|
| `host/results/chains/<chain>/gen_k/` | per step: `step.json`, `train.json`, `generate.json`, `sample_meta.json` (settings, hashes, counts, loss curve) and the per-item sidecars `heldout_nll.jsonl`, `probe_scores.jsonl`, `bias_scores.jsonl`, `sample_scores.jsonl` (ids and numbers only); `state.json` per chain |
| `host/results/metrics_posthoc_2026-10-23.jsonl` | the metric records of the 48 new steps, in the registered record schema, kept separate from `results/metrics.jsonl` |
| `host/results/posthoc2_cross_decoder/` | `cross_decoder2_summary.csv` (per-cell means), `cross_decoder2_checks.json` (settings and checks), `cross_decoder2_scorer_check.csv` |
| `full_sample_check/`, `full_sample_check_validation/` | the equal-length distinct-2 check on the full 2,000-document samples and its validation on the 50-document files (numbers only) |
| `host/configs/`, `host/harness/` | the post-hoc chain configuration and the one patched harness file as run (`common.py`, which reads `CG4_CHAINS_CFG` when that variable is set; the patch and the run scripts are in `../../posthoc_gpu_pack2/`) |
| `host/logs/`, `host/STATUS_posthoc2` | run logs and status (training and generation, cross-decoder job, environment, plan, status) |
| `vps/` | the VPS-side records: decisions of 24 October, GPU-rental records, the request records REQ-035 and REQ-036, the SHA-256 lists of the host files and packs, and the member manifest of the archived checkpoints and corpora |

Withheld (unscreened model text; available under `../../ACCESS.md`): the 48 `sample.jsonl` files (2,000 continuations each), the 48
50-document files of `host/results/samples/`, `cross_decoder2_samples.jsonl.gz` (31,200 continuations; their per-continuation NLLs
are public in `../posthoc_seeds_analysis_2026-10-24/out/cross_decoder2_per_continuation_nll.csv`), and two host logs
(`posthoc2_host.log`, `posthoc2_setup.log`) that echo short sample snippets from the smoke test. Their SHA-256 sums are in `SHA256SUMS.txt` here.
The 48 checkpoints and the 24 synthetic training corpora are in the archive `posthoc2_checkpoints_corpora.tar`
(29.5 GB; SHA-256 `057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f`); its member manifest is
`vps/archive/pack_manifest_posthoc2_checkpoints_corpora.json`.
