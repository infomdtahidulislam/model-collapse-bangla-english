# Post-hoc analyses for posthoc_gpu_pack2 (written 2026-10-23; run when the VPS results are back)

Scripts only, so far. They read the take-home folder `results/posthoc_seeds_2026-10-23/` that the VPS agent assembles
(`host/results/...` at the host's own paths) together with the registered records, and write numbers only. Everything here
is post-hoc and descriptive; no registered quantity, test or verdict changes.

| Script | What | Validated on the existing seed-0 data (2026-10-23) |
|---|---|---|
| `seeds_controls.py <package root> <posthoc metrics jsonl or none> <out>` | REPLACE-sK minus REAL-REPEAT-sK slopes (log held-out perplexity, bits per byte, log distinct-2 and recall ratios) with the registered measurement bootstrap (harness/analyze.py Boot), endpoints, slopes over 0..3 and 3..6, and the top-p 0.95 seeds' raw distinct-2 and sample-NLL slopes over 1..6 and repetition at generation 6 | reproduces the registered control exactly: EN +0.0001 [-0.0071, +0.0068], p 0.948; bits/byte -0.0014 [-0.0033, +0.0007]; BN +0.0669 [+0.0561, +0.0765]; and the Section 4.2/4.3 values (rises 0.775/0.776; 0..3 and 3..6 slopes 0.139/0.120 and 0.086/0.172; top-p distinct-2 -0.0476/-0.0621; sample NLL -0.167/-0.210 and +0.270/+0.156; repetition 0.180/0.177) |
| `cross_decoder2_slope_ci.py <cross_decoder2_samples.jsonl.gz> <out>` | prefix-paired bootstrap CIs of every cross-decoder slope (generations 1..6), the per-seed training-decoder contrast and its mean over seeds | reproduces `../posthoc_review_2026-10-22/cross_decoder_slope_ci.csv` exactly (max difference 0) |
| `cross_decoder2_distinct2.py <cross_decoder2_samples.jsonl.gz> <out> [--n 200 --m 160 --B 2000 --seed 20261024]` | equal-length distinct-2 of the cross-decoder continuations for every chain and seed | with `--n 50 --m 40 --B 2000 --seed 20261023` reproduces `cross_decoder_distinct2_K100.csv` (Table S9) exactly |
| `perdoc_seeds.py <sidecar zip> <posthoc chains root> <out>` | per-document held-out slope correlation REPLACE-sK vs REAL-REPEAT-sK, shares of documents rising | reproduces seed 0: EN 0.472, BN -0.097; shares 1.000/0.978 and 1.000/0.756 (its bootstrap CI, 0.419 to 0.525, uses its own draw sequence; the published seed-0 interval is 0.42 to 0.52) |

The full-sample equal-length check runs on the VPS (`posthoc_gpu_pack2_2026-10-23/cpu/full_sample_equal_length.py`), because
the 2,000-document samples stay in private storage there; it reproduces Table S12 exactly in its 50-document validation mode.
