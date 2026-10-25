# G6 reproducibility check (numbers only)

Made by `harness/tools/g6_clean_run.py` at 2026-10-18T08:58:09+00:00: a clean copy of `harness/` and `configs/` in `results/g6_clean_run_20261018T085748Z/`, with `metrics.jsonl` and `screening_metrics.jsonl` taken from the G4b archive copies and the G6 robustness inputs from `results/`; `analyze.py --robustness --no-log` run there and compared with `results/analysis/`.

**17 of 17 tables and reports are byte-identical.**

| File | Clean run vs main run |
|---|---|
| `H0_anchor.csv` | identical |
| `H1_seed_replicates.csv` | identical |
| `H_decision.csv` | identical |
| `H_tests.csv` | identical |
| `S1_screening.csv` | identical |
| `T0_base_model.csv` | identical |
| `T1_metrics.csv` | identical |
| `T2_slopes.csv` | identical |
| `T3_filter.csv` | identical |
| `T3_generation.csv` | identical |
| `analysis_report.md` | identical |
| `controls.csv` | identical |
| `exploratory_fairness_before_perplexity_BN.csv` | identical |
| `exploratory_slopes.csv` | identical |
| `robustness.csv` | identical |
| `robustness_quadratic.csv` | identical |
| `robustness_viii_novelty_duplicates.csv` | identical |
