# Testing Model-Collapse Diagnostics in Small-Scale Bangla–English Self-Training: released materials

Release package for the pre-registered study "Testing Model-Collapse Diagnostics in Small-Scale Bangla–English Self-Training" (Md Tahidul Islam and Maksuda Akter, CCN University of Science & Technology). Earlier working titles: "Diagnosing Model Collapse at Small Scale: A Pre-Registered Self-Training Study in Bangla and English" and "Model Collapse in Bangla and English: A Pre-Registered Study of Iterative Self-Training with Gemma-3-270m". This is version 1.0.0 (25 October 2026). An earlier deposit of the package, made on 20 October 2026, was withdrawn by the authors before this release; its records remain in `logs/decisions.md`. Pre-registration: OSF, 13 October 2026, DOI [10.17605/OSF.IO/SRA28](https://doi.org/10.17605/OSF.IO/SRA28).

## What is here

| Path | Content |
|---|---|
| `01_PREREGISTRATION.md` ... `12_VASTAI_RUNBOOK.md`, `00_PACKAGE_README.md` | The frozen study protocol and the execution-package documents it shipped with |
| `harness/` | The complete experiment and analysis code (training, generation, filtering, metrics, `analyze.py`) |
| `configs/`, `schemas/` | The registered chain and corpus configuration and the frozen record schemas |
| `data/corpora/manifest.json` | Corpus manifest: document ids and source pointers (corpus text is not redistributed; see licences below) |
| `data/probes/` | The frozen tail-fact probe sets with Wikidata ids, plus the build cache and verification records |
| `results/metrics.jsonl` and companions | Every registered metric record (plus screening, tokenizer, dispersion and novelty records) |
| `results/samples/` | The 50-sample evaluation files per chain and generation (the human-read inputs), with model-written e-mail addresses and phone numbers replaced by placeholders |
| `results/samples_redaction/` | The redaction script, per-file counts, and the SHA-256 of every original and redacted sample file |
| `results/human_read/` | The two authors' complete reading and fluency records |
| `results/analysis/` | All tables, figures and reports of the registered analysis, plus the post-hoc folders `posthoc_review_2026-10-19/`, `posthoc_paired_bootstrap_2026-10-20/` and `posthoc_review_2026-10-22/` |
| `results/cg4_posthoc_gpu_results/` | The post-hoc checkpoint-level diagnostics of 2026-10-20 (see its README; two restricted files withheld, below) |
| `results/posthoc_seeds_2026-10-23/` | The records of the eight post-hoc chains run on 2026-10-24 (seeds 2 and 3 of REAL-REPEAT and REPLACE-topp95; 48 steps with their per-item sidecars and step records) and of the three-seed cross-decoder evaluation (see its README; restricted files withheld, below) |
| `results/posthoc_seeds_analysis_2026-10-24/`, `results/analysis/posthoc_seeds_2026-10-23/` | The post-hoc analysis of those runs: scripts, numbers-only outputs, checks and validation runs |
| `posthoc_gpu_pack/` | The diagnostic scripts as run, with patch notes |
| `posthoc_gpu_pack2/` | The scripts of the 2026-10-24 post-hoc runs as run (chain configuration, harness patch, cross-decoder and full-sample scripts, `README_RUN.md`) |
| `signoffs/` | The gate and request log (`REQUESTS.md`), the SHA-256 freeze record, and the OSF bundle |
| `logs/` | The decision log, the pre-registration design review, and the GPU-rental records |
| `SHA256SUMS.txt` | SHA-256 of every file in this release |

## How to verify the registration

From `01_PREREGISTRATION.md` and `signoffs/prereg_freeze_2026-10-13.json`:
`sha256sum 01_PREREGISTRATION.md configs/chains.yaml configs/corpora.yaml schemas/document.schema.json schemas/metric.schema.json schemas/step.schema.json` and compare with the freeze record (the OSF registration archives the same hashes). `configs/corpora.yaml` intentionally differs from the first freeze per the approved, logged deviation REQ-009 (`results/deviations.md`).

## Not included, and why

- **Full synthetic training corpora and the unscreened 2,000-document evaluation samples** (size; possible offensive or personal content). Available on request under the terms in `ACCESS.md`.
- **From the 2026-10-24 post-hoc runs**: the 48 `sample.jsonl` files and 48 50-document files of the new steps, and `cross_decoder2_samples.jsonl.gz` (31,200 continuations), all unscreened model text, and two host logs that echo short sample snippets (`ACCESS.md`). The numbers derived from them are public in `results/posthoc_seeds_2026-10-23/` and `results/posthoc_seeds_analysis_2026-10-24/`; their hashes remain listed in `results/posthoc_seeds_2026-10-23/SHA256SUMS.txt`. The 48 new checkpoints and the 24 synthetic corpora of the top-p 0.95 chains are in a second archive (29.5 GB), whose member manifest is public in `results/posthoc_seeds_2026-10-23/vps/archive/`.
- **`cross_decoder_samples.jsonl.gz` and `nonword_top_types.csv`** from the 2026-10-20 diagnostics: newly generated, unscreened text and word types; same restriction (`ACCESS.md`). Their numeric content (one NLL per continuation) is public in `results/analysis/posthoc_review_2026-10-22/cross_decoder_per_continuation_nll.csv`. Their hashes remain listed in `results/cg4_posthoc_gpu_results/SHA256SUMS.txt`.
- **Corpus text** (`EN_seed.jsonl`, `BN_seed.jsonl`, generation prefixes): rebuildable from `manifest.json` with `harness/` from the upstream sources (FineWeb-Edu; Sangraha), whose licences govern redistribution.
- **Model checkpoints** (all generations, including generation 0): not released publicly, by the authors' choice; as Gemma model derivatives they carry the Gemma Terms of Use. They live in the authors' verified 55.7 GB run archive and are available on request under the terms in `ACCESS.md`, including to the journal's editors and reviewers.
- **Per-item sidecar records / per-step training records** (`heldout_nll.jsonl`, `probe_scores.jsonl`, `bias_scores.jsonl`, `sample_scores.jsonl`, `step.json` for all 119 scored steps): attached to this release as the asset `cg4_sidecars_from_G4b_2026-10-20.zip` (28.2 MB; SHA-256 `cd2e94082639dadb01e6acb1b56443af755356409ce64b6b88f1a7755cdc87dc`; per-file checksums, counts, provenance and the archive's member manifest inside), kept out of the working tree for size. The sidecars carry ids and numbers only; the single text field (`candidate` in `probe_scores.jsonl`) holds answer-option strings that already appear verbatim in the released probe files under `data/probes/`.
- **Bias-probe pair files** (`EN_bias.jsonl`, `BN_bias.jsonl`, their spot-check sheets and the exclusion record): BanStereoSet carries no explicit licence and is used for evaluation only, as the paper states, and CrowS-Pairs is CC BY-SA 4.0; both sets are rebuilt from their sources by `harness/build_probes.py`, and the per-pair NLL records remain available on request with the sidecars.
- Vast.ai host log mirrors (bulk); summarized in `logs/decisions.md` and `logs/vast_instances.jsonl`.

## Licence

Code (`harness/`, `posthoc_gpu_pack/`, `posthoc_gpu_pack2/`, scripts): **MIT**, see `LICENSE`. Data, records and documents: **CC BY 4.0**, see `LICENSE-DATA`. Upstream terms still govern what they cover: FineWeb-Edu (ODC-By) and Sangraha for corpus text (not included), Wikidata (CC0) for probe facts, and the Gemma licence for model weights (not hosted here).

## Notes on this release

- `results/posthoc_seeds_2026-10-23/` and `results/posthoc_seeds_analysis_2026-10-24/` hold the post-hoc seed replicates of the two controls (REAL-REPEAT and REPLACE-topp95, seeds 2 and 3, both languages), the three-seed cross-decoder evaluation and the full-sample equal-length distinct-2 check, run on 24 October 2026 under REQ-035 (`signoffs/REQUESTS.md`), with their records, sidecars, scripts and numbers-only outputs; the 23 October scripts in `results/analysis/posthoc_seeds_2026-10-23/`; the run pack in `posthoc_gpu_pack2/`.
- `results/analysis/posthoc_review_2026-10-22/`: post-hoc analyses, each with its script and output: per-document held-out loss slopes and their correlations between arms; trajectory shape (slopes over generations 0 to 3 and 3 to 6, quadratic term) with document-bootstrap intervals; training exposure per step from the step records; prefix-paired bootstrap intervals for the cross-decoder slopes and training-decoder contrasts, with the numbers-only per-continuation NLL file they use; length-normalized and within-file checks of the out-of-vocabulary proxy; a prefix-paired, length-controlled distinct-2 check on the 50-sample files, and its equal-length version with subset ranges (`prefix_paired_diversity_equal.py`); distinct-2 of the cross-decoder continuations (`cross_decoder_distinct2.py`, which reads the restricted continuations and writes numbers only); the effect of the sample redaction on the out-of-vocabulary proxy (`redaction_effect_oov.py`); the window document counts; and the paper's Figure 1 (`F9_controls_decoder`).
- `results/samples/`: e-mail addresses (12) and phone-number-formatted strings (11) written by the models, in 16 of the 119 files, replaced by `[EMAIL]` and `[PHONE]`. The analyses used the originals; `results/samples_redaction/redaction_log.csv` lists the SHA-256 of both versions.
- `ACCESS.md`: who can request the restricted files (the model checkpoints included), how, and on which terms, including the duty to delete or replace files after a correction.
- The logs and planning documents hold the study record only. Manuscript drafting, reviews of drafts and journal choice are not part of it, so their entries were taken out of `logs/decisions.md`, `signoffs/REQUESTS.md`, `09_WRITING_AND_DISCLOSURE.md` and other planning documents of 12 to 13 October, and the design review's journal-fit seat report is not included. The design review's wording is updated. Pointers to the article follow its current sections. Study decisions, dates and numbers are unchanged, and the registered files are byte-identical to the OSF registration.
- No registered record, table or figure changed after the registered analysis.
