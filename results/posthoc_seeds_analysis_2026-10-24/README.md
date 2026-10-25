# Post-hoc analysis of posthoc_gpu_pack2 (2026-10-24)

The analysis of the seed replicates of REAL-REPEAT and REPLACE-topp95, the cross-decoder evaluation over three seeds and the
full-sample equal-length check (REQ-035; decided by the authors on 22 October, after the registered results had been read).
Post-hoc and descriptive: no registered number, test or verdict changes.

- `ANALYSIS.md`: the analysis for the authors, with the proposed manuscript changes (section 7).
- `checks.md`: the checks listed in `posthoc_gpu_pack2_2026-10-23/README_RUN.md` section 4; all passed.
- `scripts/`: the code; `out/`: its outputs (numbers only); `out/validation/`: the validation runs.

**Inputs.** The take-home folder `results/posthoc_seeds_2026-10-23/` (unzipped from `results/posthoc_seeds_2026-10-23.zip`,
SHA-256 75725fb11785aa128f50548c580a2e3111bf6290ba2d4d5eac30d34d57c80b77; 504 files checked against its `SHA256SUMS.txt`),
the registered records (`results/metrics.jsonl`, `results/cg4_sidecars_from_G4b_2026-10-20.zip`, `results/analysis/`) and
the 2026-10-20 cross-decoder files in `results/cg4_posthoc_gpu_results/`.

**What is left untouched.** `configs/chains.yaml`, `results/metrics.jsonl` and `results/analysis/` are only read. The new
metric records (`metrics_posthoc_2026-10-23.jsonl`) are read beside the registered ones and never merged into them.
`harness/analyze.py` is imported for its functions with the post-hoc chain list passed in; it is not run, and
`CG4_CHAINS_CFG` is never set.

**Restricted files.** The new `sample.jsonl` files, the 50-document files in `host/results/samples/` and
`cross_decoder2_samples.jsonl.gz` hold unscreened model text. The scripts read them in memory and write numbers only; they
stay in private storage and are not released.

## Scripts

| Script | What it computes | Origin |
|---|---|---|
| `checks_posthoc2.py` | `checks.md` and `out/checks_steps.csv` | new |
| `seeds_controls.py` | REPLACE minus REAL-REPEAT per seed, trajectory shape, top-p 0.95 diagnostics (registered bootstrap) | copy of the 23 October script (SHA-256 b28f976b...); writes 10 decimals instead of 6 |
| `perdoc_seeds.py` | per-document held-out slopes per seed | copy (032276825...); writes 10 decimals instead of 5 |
| `cross_decoder2_slope_ci.py` | cross-decoder slopes and training-decoder contrasts with prefix-paired bootstrap CIs | copy (c996aceb...); averages each cell over its usable draws when a continuation is empty (`--empty drop` drops those prefixes instead); 10 decimals |
| `cross_decoder2_distinct2.py` | equal-length distinct-2 of the cross-decoder continuations | copy (b7452cb1...); adds an exact counting engine (default) because the PC shell stops jobs after three minutes; `--engine python` runs the original loop; 10 decimals |
| `seeds_extra.py` | window against equal-length slopes for 25 chains, per-seed arms, decoder extras, per-document extras, cross-decoder levels | new |
| `oov_new_chains.py` | the Table S6 novelty proxy for the 48 new 50-document files | new |
| `verify_independent.py` | independent recomputation of 168 point estimates and the full-sample sign counts | new |
| `make_analysis_md.py` | writes `ANALYSIS.md` from the files in `out/` | new |

The four copies come from `results/analysis/posthoc_seeds_2026-10-23/`, written on 23 October when the pack was built and
left there unchanged. Every change is described in the script's own header.

## Validation

- `seeds_controls.py` without the new records reproduces the registered seed-0 control (Table 4) exactly, and its seed-0
  rows are identical with and without the new records.
- `cross_decoder2_slope_ci.py` on the 2026-10-20 file reproduces `results/analysis/posthoc_review_2026-10-22/cross_decoder_slope_ci.csv`.
- `cross_decoder2_distinct2.py`: both engines reproduce Supplementary Table S9 and give byte-identical files on the 2026-10-20
  file and on the new file (2,000 and 50 subsets).
- `seeds_extra.py` reproduces the registered window slopes of `results/analysis/T2_slopes.csv` (largest difference 1e-16).
- `oov_new_chains.py` reproduces the published Table S6 shares within 0.000005.
- `verify_independent.py`: largest difference below 1e-10 (`out/validation/independent_check.csv`).

Re-running: see `ANALYSIS.md` section 8. Python 3.10 with numpy, pandas, regex and PyYAML; run from the package root with
`python -B`.
