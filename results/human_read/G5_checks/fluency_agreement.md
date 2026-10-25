# Optional G5 fluency: agreement between the two authors

Made by `harness/tools/g5_fluency_agreement.py`. Quadratic-weighted Cohen's kappa (qwk) with a bootstrap 95% interval over samples; exact and within-one agreement; Spearman's rho. Independence check: identical ratings and the content-word overlap (Jaccard) of the two notes on the same sample against notes on different samples.

## all files

| Set | n | exact | within 1 | qwk [95% CI] | Spearman |
|---|---|---|---|---|---|
| pooled | 279 | 0.74 | 1.00 | 0.833 [0.786, 0.870] | 0.836 |
| EN | 139 | 0.85 | 1.00 | 0.900 [0.847, 0.940] | 0.896 |
| BN | 140 | 0.64 | 1.00 | 0.672 [0.517, 0.770] | 0.643 |

## without GEN0-EN gen 0

| Set | n | exact | within 1 | qwk [95% CI] | Spearman |
|---|---|---|---|---|---|
| pooled | 259 | 0.72 | 1.00 | 0.813 [0.761, 0.854] | 0.819 |
| EN | 119 | 0.82 | 1.00 | 0.881 [0.820, 0.928] | 0.880 |
| BN | 140 | 0.64 | 1.00 | 0.672 [0.517, 0.770] | 0.643 |

## Per file

| File | raters (first / second) | n | exact | within 1 | qwk | identical | note overlap (baseline) |
|---|---|---|---|---|---|---|---|
| EN-REPLACE gen 3 | Maksuda Akter / Md Tahidul Islam | 20 | 0.85 | 1.00 | 0.910 | 17 of 20 | 0.06 (0.01) |
| EN-REPLACE gen 6 | Maksuda Akter / Md Tahidul Islam | 20 | 0.75 | 1.00 | 0.667 | 15 of 20 | 0.04 (0.02) |
| EN-ACCUMULATE gen 3 | Maksuda Akter / Md Tahidul Islam | 20 | 0.80 | 1.00 | 0.868 | 16 of 20 | 0.06 (0.02) |
| EN-ACCUMULATE gen 6 | Maksuda Akter / Md Tahidul Islam | 19 | 0.84 | 1.00 | 0.909 | 16 of 19 | 0.06 (0.02) |
| EN-ACCUMULATE-FILTER gen 3 | Md Tahidul Islam / Maksuda Akter | 20 | 0.90 | 1.00 | 0.794 | 18 of 20 | 0.04 (0.01) |
| EN-ACCUMULATE-FILTER gen 6 | Md Tahidul Islam / Maksuda Akter | 20 | 0.80 | 1.00 | 0.474 | 16 of 20 | 0.05 (0.02) |
| BN-REPLACE gen 3 | Md Tahidul Islam / Maksuda Akter | 20 | 0.55 | 1.00 | 0.400 | 11 of 20 | 0.03 (0.01) |
| BN-REPLACE gen 6 | Md Tahidul Islam / Maksuda Akter | 20 | 0.20 | 1.00 | 0.018 | 4 of 20 | 0.02 (0.01) |
| BN-ACCUMULATE gen 3 | Md Tahidul Islam / Maksuda Akter | 20 | 0.70 | 1.00 | 0.595 | 14 of 20 | 0.03 (0.02) |
| BN-ACCUMULATE gen 6 | Md Tahidul Islam / Maksuda Akter | 20 | 0.70 | 1.00 | 0.810 | 14 of 20 | 0.05 (0.01) |
| BN-ACCUMULATE-FILTER gen 3 | Maksuda Akter / Md Tahidul Islam | 20 | 0.85 | 1.00 | 0.821 | 17 of 20 | 0.03 (0.01) |
| BN-ACCUMULATE-FILTER gen 6 | Maksuda Akter / Md Tahidul Islam | 20 | 0.70 | 1.00 | 0.812 | 14 of 20 | 0.03 (0.01) |
| GEN0-EN gen 0 | Maksuda Akter / Md Tahidul Islam | 20 | 1.00 | 1.00 | 1.000 | 20 of 20 | 0.27 (0.04) |
| GEN0-BN gen 0 | Md Tahidul Islam / Maksuda Akter | 20 | 0.75 | 1.00 | 0.688 | 15 of 20 | 0.07 (0.03) |
