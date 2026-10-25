# posthoc_gpu_pack2: seed replicates of the two controls, cross-decoder over three seeds, full-sample check

Analysis written 2026-10-24 on the PC from the take-home folder `results/posthoc_seeds_2026-10-23/` (zip SHA-256 `75725fb1...0b77`; all checks in `checks.md` passed). The authors decided these runs on 22 October (REQ-035), after the registered results had been read, so everything here is post-hoc: nothing is pre-registered, and no registered number, test or verdict changes. Square brackets are 95% measurement intervals from the registered bootstrap of `harness/analyze.py` (1,000 draws; p is its two-sided bootstrap p, unadjusted) unless a table says otherwise; the seeds are the run-to-run comparison. Model-written text was read only by code, in memory; this report and `out/` hold numbers only. Seed 0 is the registered chain; for REPLACE, seeds 2 and 3 are the registered replicates; for REAL-REPEAT and REPLACE-topp95, seeds 2 and 3 are the new post-hoc chains, each started from the same re-seeded generation-0 model and the same step seeds as the REPLACE chain of its seed.

## Summary

1. **The English non-specificity is not a property of one chain.** REPLACE minus REAL-REPEAT on log held-out perplexity is +0.0001 [−0.0071, +0.0068], −0.0005 [−0.0070, +0.0065] and +0.0009 [−0.0058, +0.0081] nats/generation in seeds 0, 2 and 3, and +0.0669, +0.0646 and +0.0656 in Bangla (all three intervals exclude zero). Section 5.7 of the manuscript named this test: more REAL-REPEAT seeds with a clearly nonzero English contrast would have tied the finding to one chain. They did not.
2. **The differences behind the matching summary replicate.** In all three seeds English REPLACE rises almost linearly (quadratic coefficients −0.0031, −0.0029, −0.0033) while REAL-REPEAT accelerates (+0.0145, +0.0151, +0.0145); the per-document slopes of the two arms correlate 0.47, 0.47, 0.46 (Bangla −0.10, −0.07, −0.08), while two seeds of the same arm correlate 0.90 to 0.91 (REPLACE) and 0.94 to 0.95 (REAL-REPEAT) in English and 0.92 to 0.93 and 0.94 to 0.95 in Bangla. Each arm's per-document pattern is reproducible across seeds, and the two arms' patterns differ. Bangla REAL-REPEAT first falls and then rises in every seed (lowest at generation 2 in all three, −0.090, −0.092, −0.096 nats against generation 0).
3. **The top-p 0.95 arm replicates in all three seeds**: distinct-2 falls steeply, the sample NLL under the generation-0 model falls, and repeated 4-grams rise, while the top-p 1.0 chains move the other way (Section 3). New, and also in every seed: the top-p 0.95 chains raise held-out perplexity faster than REPLACE (+0.0842, +0.0903, +0.0889 nats/generation in English, +0.0726, +0.0756, +0.0651 in Bangla; every interval excludes zero).
4. **Cross-decoder over three seeds (200 prefixes per cell):** all 24 slopes follow the training-text decoder (12 of 12 top-p 1.0-trained slopes rise, 12 of 12 top-p 0.95-trained slopes fall; 24 of 24 prefix-bootstrap intervals exclude zero). The training-decoder contrast, averaged over the three seeds, is English +0.510 [+0.492, +0.529] (evaluation top-p 1.0); English +0.412 [+0.392, +0.431] (evaluation top-p 0.95); Bangla +0.414 [+0.393, +0.435] (evaluation top-p 1.0); Bangla +0.394 [+0.374, +0.415] (evaluation top-p 0.95). Distinct-2 of the continuations falls for all 12 top-p 0.95-trained rows and does not fall for 11 of the 12 top-p 1.0-trained rows.
5. **The full-sample check changes the conclusion of Supplementary Section S14.** On all 2,000 documents per step, the equal-length slope has the registered window slope's sign in 13 of the 17 registered chains, against 9 of 17 on the 50-document files, and in 11 of the 12 chains whose registered interval excludes zero (the exception, EN-REPLACE-WM, has a registered interval that starts at +0.0001). The four chains whose registered intervals excluded zero and whose 50-document check changed sign (EN-ACCUMULATE-FILTER, EN-REAL-REPEAT, BN-REPLACE-s2, BN-REPLACE-s3) all return to the registered sign. The 50-document check was too small to resolve slopes of this size; the registered window slopes hold up.
6. **Two smaller points need care.** The English REAL-REPEAT novelty proxy falls only slightly (slopes −0.0004, −0.0010, −0.0007 per generation; in seeds 2 and 3 its generation-6 value lies above generation 0), so Section S8 should call the English fall small (Section 6). The sample-NLL spread of BN-REPLACE-topp95-s3 widens (SD slope +0.097) because of one or two documents per generation at about 40 nats/token, not because the bulk spreads (Section 3).
7. **Run and money.** All eight chains completed six generations with the registered recipe and seeds; the 156 cross-decoder cells and the full-sample check are complete; every check of README_RUN.md section 4 passed (`checks.md`). The pack used 14.4 GPU-hours and was invoiced US$9.00 (cap US$15); the CG4 total is US$47.83 of the US$55 ceiling.

## 2. The REAL-REPEAT control in three seeds

**Table A. REPLACE minus REAL-REPEAT, slope over generations 0 to 6 (the registered net contrast of Table 4, per seed).**

| Language | Metric | Seed 0 (registered) | Seed 2 | Seed 3 | Mean of 3 (range) |
|---|---|---|---|---|---|
| English | log held-out perplexity | +0.0001 [−0.0071, +0.0068], p 0.948 | −0.0005 [−0.0070, +0.0065], p 0.894 | +0.0009 [−0.0058, +0.0081], p 0.804 | +0.0002 (−0.0005 to +0.0009) |
| English | bits per byte | −0.0014 [−0.0033, +0.0007], p 0.178 | −0.0016 [−0.0035, +0.0004], p 0.120 | −0.0012 [−0.0033, +0.0008], p 0.206 | −0.0014 (−0.0016 to −0.0012) |
| English | log(distinct-2 / gen-0) | +0.0109 [+0.0090, +0.0127], p < 0.002 | +0.0115 [+0.0097, +0.0133], p < 0.002 | +0.0072 [+0.0054, +0.0090], p < 0.002 | +0.0099 (+0.0072 to +0.0115) |
| English | log(recall / gen-0) | −0.0051 [−0.0221, +0.0113], p 0.522 | +0.0006 [−0.0158, +0.0176], p 0.954 | −0.0118 [−0.0284, +0.0035], p 0.132 | −0.0054 (−0.0118 to +0.0006) |
| Bangla | log held-out perplexity | +0.0669 [+0.0561, +0.0765], p < 0.002 | +0.0646 [+0.0544, +0.0758], p < 0.002 | +0.0656 [+0.0553, +0.0756], p < 0.002 | +0.0657 (+0.0646 to +0.0669) |
| Bangla | bits per byte | +0.0090 [+0.0073, +0.0107], p < 0.002 | +0.0087 [+0.0070, +0.0104], p < 0.002 | +0.0088 [+0.0070, +0.0105], p < 0.002 | +0.0088 (+0.0087 to +0.0090) |
| Bangla | log(distinct-2 / gen-0) | +0.0034 [+0.0007, +0.0062], p 0.008 | +0.0058 [+0.0035, +0.0081], p < 0.002 | +0.0037 [+0.0014, +0.0061], p 0.002 | +0.0043 (+0.0034 to +0.0058) |
| Bangla | log(recall / gen-0) | −0.0270 [−0.0451, −0.0078], p 0.006 | −0.0248 [−0.0440, −0.0057], p 0.018 | −0.0262 [−0.0461, −0.0064], p 0.006 | −0.0260 (−0.0270 to −0.0248) |

The registered seed-0 row is reproduced exactly. English: the perplexity and bits-per-byte contrasts are near zero in every seed, with every interval including zero; REPLACE's log distinct-2 ratio rises relative to REAL-REPEAT in every seed; recall does not separate the arms. Bangla: every contrast that excluded zero in seed 0 excludes it in seeds 2 and 3, with the same sign and similar size.

**Table B. Trajectory shape of log held-out perplexity (nats/generation).**

| Language | Seed | REPLACE slope 0-3 / 3-6 | REAL-REPEAT slope 0-3 / 3-6 | REPLACE quadratic | REAL-REPEAT quadratic | Rise to gen. 6, REPLACE / REAL-REPEAT |
|---|---|---|---|---|---|---|
| English | 0 | +0.139 / +0.120 | +0.086 / +0.172 | −0.0031 [−0.0062, −0.0000] | +0.0145 [+0.0111, +0.0178] | +0.775 / +0.776 |
| English | 2 | +0.139 / +0.121 | +0.085 / +0.176 | −0.0029 [−0.0059, +0.0001] | +0.0151 [+0.0117, +0.0184] | +0.776 / +0.784 |
| English | 3 | +0.139 / +0.120 | +0.084 / +0.173 | −0.0033 [−0.0062, −0.0002] | +0.0145 [+0.0113, +0.0180] | +0.778 / +0.773 |
| Bangla | 0 | +0.088 / +0.080 | −0.026 / +0.057 | −0.0012 [−0.0064, +0.0035] | +0.0141 [+0.0087, +0.0191] | +0.500 / +0.090 |
| Bangla | 2 | +0.085 / +0.077 | −0.029 / +0.060 | −0.0013 [−0.0059, +0.0036] | +0.0146 [+0.0097, +0.0198] | +0.484 / +0.089 |
| Bangla | 3 | +0.086 / +0.077 | −0.027 / +0.057 | −0.0012 [−0.0061, +0.0034] | +0.0145 [+0.0095, +0.0196] | +0.487 / +0.090 |

Seed 0 reproduces Supplementary Table S11 (0.139 / 0.120 and 0.086 / 0.172; quadratic coefficients −0.0031 and +0.0145 in English, −0.0012 and +0.0141 in Bangla) and the main text's generation-6 rises (+0.775 and +0.776).

**Table C. Per-document held-out slopes (2,000 documents per language; document-bootstrap intervals, 2,000 draws).**

| Language | Seed | Correlation, REPLACE vs REAL-REPEAT | Share of documents rising, REPLACE / REAL-REPEAT | REPLACE mean slope, web / Wikipedia | REAL-REPEAT mean slope, web / Wikipedia |
|---|---|---|---|---|---|
| English | 0 | +0.472 [+0.419, +0.525] | 1.000 / 0.978 | 0.136 / 0.124 | 0.152 / 0.108 |
| English | 2 | +0.466 [+0.415, +0.516] | 1.000 / 0.975 | 0.136 / 0.124 | 0.154 / 0.107 |
| English | 3 | +0.463 [+0.409, +0.515] | 1.000 / 0.974 | 0.137 / 0.124 | 0.153 / 0.107 |
| Bangla | 0 | −0.097 [−0.150, −0.039] | 1.000 / 0.756 | 0.088 / 0.080 | 0.031 / 0.004 |
| Bangla | 2 | −0.071 [−0.126, −0.010] | 1.000 / 0.754 | 0.088 / 0.075 | 0.030 / 0.004 |
| Bangla | 3 | −0.082 [−0.134, −0.026] | 1.000 / 0.764 | 0.087 / 0.077 | 0.031 / 0.003 |

Between seeds of the same arm the per-document slopes correlate 0.90 to 0.91 (English REPLACE), 0.94 to 0.95 (English REAL-REPEAT), 0.92 to 0.93 (Bangla REPLACE) and 0.94 to 0.95 (Bangla REAL-REPEAT), every interval within 0.03 of its value (`out/perdoc_seeds_extra.csv`). The registered comparison was 0.910 between REPLACE seeds 0 and 2. So the gap between the arms (0.46 to 0.47 in English, about −0.1 in Bangla) is not seed noise: each training policy raises the loss on its own set of documents, and does so again in a new seed. REAL-REPEAT's larger rise on the web half of the held-out set also replicates in every seed. Seed 0's correlation intervals differ from Table S11's ([0.421, 0.523] and [−0.147, −0.038]) in the third decimal only because this script draws its own bootstrap resamples.

## 3. The top-p 0.95 arm in three seeds

**Table D. Sample diagnostics of the top-p 0.95 chain against the REPLACE chain of the same seed (top-p 0.95 / top-p 1.0).**

| Language | Seed | Distinct-2 slope, gen. 1-6 | Distinct-2, top-p 0.95, gen. 1 to 6 | Sample NLL slope, gen. 1-6 | Sample NLL slope, gen. 0-6 (registered window) | Repeated 4-grams, gen. 6 / REPLACE max | Sample-NLL SD slope, gen. 1-6 |
|---|---|---|---|---|---|---|---|
| English | 0 | −0.0476 / +0.0038 | 0.682 to 0.445 | −0.167 / +0.270 | −0.233 / +0.288 | 0.180 / 0.004 | +0.002 / +0.035 |
| English | 2 | −0.0551 / +0.0034 | 0.690 to 0.415 | −0.172 / +0.229 | −0.241 / +0.260 | 0.192 / 0.004 | +0.004 / +0.030 |
| English | 3 | −0.0519 / +0.0010 | 0.675 to 0.412 | −0.173 / +0.233 | −0.245 / +0.260 | 0.216 / 0.004 | +0.006 / +0.012 |
| Bangla | 0 | −0.0621 / +0.0002 | 0.841 to 0.531 | −0.210 / +0.156 | −0.251 / +0.179 | 0.177 / 0.011 | +0.007 / +0.021 |
| Bangla | 2 | −0.0563 / +0.0022 | 0.838 to 0.561 | −0.199 / +0.128 | −0.241 / +0.146 | 0.142 / 0.006 | +0.003 / +0.025 |
| Bangla | 3 | −0.0626 / −0.0000 | 0.852 to 0.542 | −0.211 / +0.155 | −0.253 / +0.182 | 0.175 / 0.004 | +0.097 / +0.033 |

Every distinct-2 and sample-NLL slope of the top-p 0.95 chains has an interval excluding zero (`out/seeds_controls.csv`), and so does every REPLACE minus top-p 0.95 difference. The seed-0 rows reproduce Section 4.3 (−0.0476 and −0.0621; −0.167 and −0.210 against +0.270 and +0.156; repetition 0.180 and 0.177). The spread of the sample NLL does not narrow under top-p 0.95 in five of six chains; in BN-REPLACE-topp95-s3 it widens (+0.097) because one or two of its 2,000 documents per generation score about 40 nats/token at generations 4 to 6 (without documents above 10 nats/token its SD stays at 0.90 to 0.94, as in the other seeds; the 5th and 95th percentiles are unchanged).

**Table E. Held-out log-perplexity under the two training decoders (slopes over generations 0 to 6).**

| Language | Seed | REPLACE (top-p 1.0) | REPLACE-topp95 | Difference (top-p 0.95 minus 1.0) | Difference, bits per byte |
|---|---|---|---|---|---|
| English | 0 | +0.1300 [+0.1242, +0.1350] | +0.2142 [+0.2081, +0.2200] | +0.0842 [+0.0771, +0.0914] | +0.0285 [+0.0264, +0.0305] |
| English | 2 | +0.1303 [+0.1252, +0.1355] | +0.2206 [+0.2150, +0.2266] | +0.0903 [+0.0834, +0.0971] | +0.0301 [+0.0280, +0.0321] |
| English | 3 | +0.1307 [+0.1256, +0.1355] | +0.2196 [+0.2138, +0.2255] | +0.0889 [+0.0827, +0.0962] | +0.0300 [+0.0279, +0.0321] |
| Bangla | 0 | +0.0842 [+0.0753, +0.0930] | +0.1569 [+0.1472, +0.1662] | +0.0726 [+0.0623, +0.0837] | +0.0118 [+0.0101, +0.0136] |
| Bangla | 2 | +0.0817 [+0.0736, +0.0902] | +0.1572 [+0.1478, +0.1670] | +0.0756 [+0.0649, +0.0863] | +0.0121 [+0.0104, +0.0138] |
| Bangla | 3 | +0.0821 [+0.0738, +0.0904] | +0.1472 [+0.1384, +0.1572] | +0.0651 [+0.0547, +0.0754] | +0.0104 [+0.0088, +0.0120] |

This comparison is not in the manuscript. Training on top-p 0.95 text raised held-out perplexity 1.65 to 1.69 times as fast as training on top-p 1.0 text in English and 1.79 to 1.93 times as fast in Bangla, in every seed, while its own samples became more predictable to the generation-0 model (Table D).

## 4. Cross-decoder evaluation over three seeds

Each checkpoint drew 200 continuations (the first 200 evaluation prefixes) under each decoder; each continuation is scored as its mean per-token NLL under the chain's own generation-0 model. Slopes are OLS over generations 1 to 6 with prefix-paired bootstrap intervals (5,000 draws, one resample of the prefixes shared by all cells of a language). Three of the 31,200 continuations are empty (no NLL); each such cell is averaged over its 199 usable draws, as the run's summary does (dropping the two affected prefixes from every Bangla cell instead moves no Bangla slope or contrast by more than 0.0039).

**Table F. Cross-decoder slopes (nats/generation) by training-text decoder and evaluation decoder.**

| Language | Training text | Evaluation | Seed 0 | Seed 2 | Seed 3 | Gen. 1 level (3 seeds) | Gen. 6 level (3 seeds) |
|---|---|---|---|---|---|---|---|
| English | top-p 1.0 | top-p 1.0 | +0.309 [+0.280, +0.338] | +0.247 [+0.217, +0.276] | +0.277 [+0.249, +0.305] | 3.75 to 3.79 | 5.04 to 5.29 |
| English | top-p 1.0 | top-p 0.95 | +0.259 [+0.237, +0.280] | +0.216 [+0.193, +0.239] | +0.231 [+0.212, +0.250] | 2.94 to 3.00 | 4.12 to 4.24 |
| English | top-p 0.95 | top-p 1.0 | −0.235 [−0.255, −0.216] | −0.242 [−0.261, −0.223] | −0.222 [−0.243, −0.202] | 2.99 to 3.15 | 1.92 to 1.93 |
| English | top-p 0.95 | top-p 0.95 | −0.174 [−0.194, −0.153] | −0.184 [−0.203, −0.167] | −0.171 [−0.195, −0.145] | 2.48 to 2.58 | 1.63 to 1.64 |
| Bangla | top-p 1.0 | top-p 1.0 | +0.176 [+0.154, +0.199] | +0.132 [+0.109, +0.155] | +0.181 [+0.156, +0.207] | 4.09 to 4.13 | 4.75 to 5.06 |
| Bangla | top-p 1.0 | top-p 0.95 | +0.182 [+0.157, +0.206] | +0.150 [+0.128, +0.172] | +0.161 [+0.141, +0.182] | 3.49 to 3.52 | 4.16 to 4.43 |
| Bangla | top-p 0.95 | top-p 1.0 | −0.242 [−0.268, −0.213] | −0.248 [−0.274, −0.221] | −0.264 [−0.285, −0.242] | 3.54 to 3.59 | 2.26 to 2.32 |
| Bangla | top-p 0.95 | top-p 0.95 | −0.237 [−0.260, −0.213] | −0.226 [−0.249, −0.204] | −0.227 [−0.250, −0.203] | 3.06 to 3.13 | 1.94 to 1.97 |

**Table G. Training-decoder contrast (top-p 1.0-trained slope minus top-p 0.95-trained slope, same seed and evaluation decoder).**

| Language | Evaluation | Seed 0 | Seed 2 | Seed 3 | Mean of the three seeds |
|---|---|---|---|---|---|
| English | top-p 1.0 | +0.544 [+0.510, +0.578] | +0.488 [+0.455, +0.522] | +0.499 [+0.469, +0.529] | +0.510 [+0.492, +0.529] |
| English | top-p 0.95 | +0.433 [+0.403, +0.461] | +0.401 [+0.372, +0.431] | +0.402 [+0.370, +0.432] | +0.412 [+0.392, +0.431] |
| Bangla | top-p 1.0 | +0.418 [+0.383, +0.450] | +0.380 [+0.341, +0.418] | +0.445 [+0.412, +0.478] | +0.414 [+0.393, +0.435] |
| Bangla | top-p 0.95 | +0.418 [+0.386, +0.450] | +0.376 [+0.345, +0.407] | +0.388 [+0.357, +0.420] | +0.394 [+0.374, +0.415] |

The evaluation decoder shifts the level (top-p 0.95 scores 0.22 to 1.08 nats lower on the same checkpoint; median 0.59) and reverses no direction. The three generation-0 models score English 3.35 to 3.44 (top-p 1.0) and 2.65 to 2.69 (top-p 0.95), Bangla 3.72 to 3.77 and 3.14 to 3.21. Seed 0's numbers differ from Table 5 because these are new draws (the host's torch changed from 2.8.0 to 2.13.0, so the same seeds gave identical continuations in only 7.8% of cases) and 200 rather than 50 prefixes: on the same first 50 prefixes, all eight seed-0 slopes fall inside the 2026-10-20 intervals (8 of 8; `out/cross_decoder2_first50.csv`).

**Table H. Distinct-2 of the continuations, equal length per prefix (raw slope over generations 1 to 6; brackets: stability range over 2,000 subsets of 160 of the 200 prefixes, not a confidence interval).**

| Language | Training text | Evaluation | Seed 0 | Seed 2 | Seed 3 | Words per generation |
|---|---|---|---|---|---|---|
| English | top-p 1.0 | top-p 1.0 | +0.0043 [+0.0032, +0.0052] | +0.0024 [+0.0014, +0.0038] | +0.0024 [+0.0014, +0.0033] | 13,196 to 14,577 |
| English | top-p 1.0 | top-p 0.95 | +0.0023 [+0.0011, +0.0037] | +0.0019 [+0.0009, +0.0031] | +0.0023 [+0.0011, +0.0036] | 12,680 to 13,927 |
| English | top-p 0.95 | top-p 1.0 | −0.0324 [−0.0334, −0.0298] | −0.0373 [−0.0381, −0.0345] | −0.0355 [−0.0366, −0.0328] | 13,950 to 14,701 |
| English | top-p 0.95 | top-p 0.95 | −0.0353 [−0.0369, −0.0331] | −0.0385 [−0.0398, −0.0359] | −0.0371 [−0.0385, −0.0346] | 14,372 to 15,218 |
| Bangla | top-p 1.0 | top-p 1.0 | +0.0045 [+0.0028, +0.0055] | +0.0007 [−0.0005, +0.0019] | +0.0012 [−0.0006, +0.0024] | 10,728 to 11,684 |
| Bangla | top-p 1.0 | top-p 0.95 | +0.0015 [−0.0002, +0.0033] | +0.0025 [+0.0008, +0.0037] | −0.0010 [−0.0022, −0.0000] | 10,090 to 11,544 |
| Bangla | top-p 0.95 | top-p 1.0 | −0.0297 [−0.0310, −0.0260] | −0.0256 [−0.0275, −0.0220] | −0.0254 [−0.0265, −0.0222] | 10,991 to 12,387 |
| Bangla | top-p 0.95 | top-p 0.95 | −0.0367 [−0.0386, −0.0332] | −0.0265 [−0.0284, −0.0235] | −0.0278 [−0.0301, −0.0241] | 10,400 to 11,917 |

All 12 top-p 0.95-trained rows fall (−0.0254 to −0.0385), every stability range excluding zero. Of the 12 top-p 1.0-trained rows, 11 rise and one falls slightly (BN-REPLACE-s3 under top-p 0.95 evaluation, −0.0010, 0.04 times the smallest top-p 0.95 fall). The statement of Section 4.3 ("did not fall for the chains trained on top-p 1.0 text") holds for 11 of 12 rows and in sign for every English row.

## 5. Full-sample equal-length check

Same statistic as Supplementary Table S12 (each prefix contributes the same number of words, at most 100, at every step; bigrams within documents), now on all 2,000 documents per step of all 25 chains. Brackets after the full-sample value: stability range over 500 subsets of 1,600 prefixes. Window: the registered distinct-2 slope with its registered 95% interval (for the eight post-hoc chains, the same computation on their records).

**Table I. Distinct-2 slopes: registered window, 50-document check (Table S12) and full-sample check.**

| Chain | Generations | Window [95% CI] | 50 documents (S12) | 2,000 documents [range] | Words per step | Sign vs window |
|---|---|---|---|---|---|---|
| EN-REPLACE | 0 to 6, log ratio | +0.0062 [+0.0046, +0.0077] | +0.0038 | +0.0069 [+0.0060, +0.0071] | 134,721 | same |
| EN-REPLACE-s2 | 0 to 6, log ratio | +0.0060 [+0.0045, +0.0076] | +0.0052 | +0.0055 [+0.0047, +0.0059] | 132,312 | same |
| EN-REPLACE-s3 | 0 to 6, log ratio | +0.0029 [+0.0013, +0.0045] | +0.0013 | +0.0035 [+0.0030, +0.0041] | 127,068 | same |
| EN-ACCUMULATE | 0 to 6, log ratio | +0.0006 [−0.0010, +0.0023] | −0.0016 | −0.0010 [−0.0013, −0.0004] | 135,931 | **changed** |
| EN-ACCUMULATE-FILTER | 0 to 6, log ratio | −0.0060 [−0.0077, −0.0044] | +0.0002 | −0.0052 [−0.0054, −0.0044] | 133,385 | same |
| EN-ACCUMULATE-SUBSAMPLE | 0 to 6, log ratio | +0.0027 [+0.0011, +0.0044] | +0.0026 | +0.0027 [+0.0020, +0.0030] | 134,823 | same |
| EN-REAL-REPEAT | 0 to 6, log ratio | −0.0047 [−0.0065, −0.0029] | +0.0011 | −0.0045 [−0.0047, −0.0037] | 147,547 | same |
| EN-REPLACE-WM | 0 to 6, log ratio | +0.0018 [+0.0001, +0.0035] | +0.0039 | −0.0002 [−0.0007, +0.0005] | 128,453 | **changed** |
| EN-REPLACE-topp95 | 1 to 6, raw | −0.0476 [−0.0501, −0.0448] | −0.0272 | −0.0365 [−0.0371, −0.0360] | 142,837 | same |
| BN-REPLACE | 0 to 6, log ratio | +0.0023 [−0.0000, +0.0047] | −0.0002 | +0.0033 [+0.0025, +0.0035] | 110,627 | same |
| BN-REPLACE-s2 | 0 to 6, log ratio | +0.0046 [+0.0027, +0.0066] | −0.0014 | +0.0049 [+0.0040, +0.0049] | 97,030 | same |
| BN-REPLACE-s3 | 0 to 6, log ratio | +0.0022 [+0.0003, +0.0041] | −0.0006 | +0.0022 [+0.0015, +0.0025] | 106,613 | same |
| BN-ACCUMULATE | 0 to 6, log ratio | +0.0015 [−0.0002, +0.0033] | −0.0007 | −0.0006 [−0.0009, −0.0002] | 118,213 | **changed** |
| BN-ACCUMULATE-FILTER | 0 to 6, log ratio | +0.0009 [−0.0008, +0.0026] | −0.0011 | −0.0005 [−0.0009, −0.0001] | 118,477 | **changed** |
| BN-ACCUMULATE-SUBSAMPLE | 0 to 6, log ratio | +0.0033 [+0.0016, +0.0051] | +0.0015 | +0.0021 [+0.0016, +0.0024] | 115,616 | same |
| BN-REAL-REPEAT | 0 to 6, log ratio | −0.0011 [−0.0029, +0.0009] | −0.0000 | −0.0037 [−0.0039, −0.0030] | 128,825 | same |
| BN-REPLACE-topp95 | 1 to 6, raw | −0.0621 [−0.0666, −0.0580] | −0.0351 | −0.0423 [−0.0425, −0.0409] | 119,406 | same |
| EN-REAL-REPEAT-s2 (post-hoc) | 0 to 6, log ratio | −0.0055 [−0.0072, −0.0039] | n/a | −0.0067 [−0.0068, −0.0057] | 145,538 | same |
| EN-REAL-REPEAT-s3 (post-hoc) | 0 to 6, log ratio | −0.0043 [−0.0058, −0.0027] | n/a | −0.0053 [−0.0054, −0.0044] | 148,353 | same |
| EN-REPLACE-topp95-s2 (post-hoc) | 1 to 6, raw | −0.0551 [−0.0578, −0.0527] | n/a | −0.0412 [−0.0419, −0.0409] | 147,360 | same |
| EN-REPLACE-topp95-s3 (post-hoc) | 1 to 6, raw | −0.0519 [−0.0546, −0.0492] | n/a | −0.0384 [−0.0392, −0.0381] | 142,654 | same |
| BN-REAL-REPEAT-s2 (post-hoc) | 0 to 6, log ratio | −0.0012 [−0.0031, +0.0007] | n/a | −0.0044 [−0.0045, −0.0036] | 125,259 | same |
| BN-REAL-REPEAT-s3 (post-hoc) | 0 to 6, log ratio | −0.0015 [−0.0033, +0.0005] | n/a | −0.0056 [−0.0057, −0.0047] | 129,260 | same |
| BN-REPLACE-topp95-s2 (post-hoc) | 1 to 6, raw | −0.0563 [−0.0600, −0.0523] | n/a | −0.0364 [−0.0366, −0.0348] | 100,495 | same |
| BN-REPLACE-topp95-s3 (post-hoc) | 1 to 6, raw | −0.0626 [−0.0670, −0.0588] | n/a | −0.0401 [−0.0404, −0.0386] | 103,288 | same |

On the full samples the equal-length slope keeps the window's sign in 13 of the 17 registered chains (9 of 17 at 50 documents) and in 11 of the 12 with registered intervals excluding zero; 12 of 17 full-sample values lie inside the registered interval. The sign changes left are EN-ACCUMULATE, BN-ACCUMULATE, BN-ACCUMULATE-FILTER, whose registered intervals include zero, and EN-REPLACE-WM (+0.0018 [+0.0001, +0.0035] against −0.0002). The three Bangla REPLACE seeds, which all changed sign at 50 documents, keep the registered sign, and so do EN-ACCUMULATE-FILTER and EN-REAL-REPEAT. English REPLACE rises in all three seeds and both REPLACE-topp95 chains fall, as at 50 documents. The 50-document stability ranges were taken over subsets of the same 50 prefixes, so they could not show how far a different set of 50 prefixes would move the slope; the full samples show that it moved by up to 0.0063 on the log-ratio chains, the size of the slopes in question. For the eight post-hoc chains the full-sample sign agrees with the window in 8 of 8. The raw slopes of the top-p 0.95 chains are smaller in magnitude on the equal-length statistic than in the window (for example −0.0365 against −0.0476), as at 50 documents: the window counts bigrams across document boundaries and over unequal lengths.

## 6. Lexical-novelty proxy for the new chains (rows for Supplementary Table S6)

Share of continuation word tokens absent from the language's seed vocabulary, per 50-sample file (the statistic of Table S6; recomputing it on the registered files reproduces every published share within 0.000005, `out/validation/oov_share_recomputed_vs_published.csv`). Generation 0 is the chain's own generation-0 model; the top-p 0.95 chains have no generation-0 file under their decoder.

| Chain | Gen. 0 | 1 | 2 | 3 | 4 | 5 | 6 | OLS slope, gen. 1-6 |
|---|---|---|---|---|---|---|---|---|
| EN-REAL-REPEAT | 0.0343 | 0.0349 | 0.0189 | 0.0267 | 0.0245 | 0.0255 | 0.0284 | −0.0004 |
| EN-REAL-REPEAT-s2 (post-hoc) | 0.0303 | 0.0368 | 0.0271 | 0.0310 | 0.0246 | 0.0262 | 0.0318 | −0.0010 |
| EN-REAL-REPEAT-s3 (post-hoc) | 0.0271 | 0.0251 | 0.0391 | 0.0286 | 0.0278 | 0.0241 | 0.0290 | −0.0007 |
| EN-REPLACE-topp95 | n/a | 0.0191 | 0.0155 | 0.0117 | 0.0106 | 0.0195 | 0.0111 | −0.0008 |
| EN-REPLACE-topp95-s2 (post-hoc) | n/a | 0.0141 | 0.0135 | 0.0149 | 0.0135 | 0.0134 | 0.0092 | −0.0007 |
| EN-REPLACE-topp95-s3 (post-hoc) | n/a | 0.0159 | 0.0136 | 0.0099 | 0.0105 | 0.0205 | 0.0106 | −0.0001 |
| BN-REAL-REPEAT | 0.1002 | 0.1185 | 0.0950 | 0.0928 | 0.0880 | 0.0837 | 0.0689 | −0.0082 |
| BN-REAL-REPEAT-s2 (post-hoc) | 0.1146 | 0.1013 | 0.0882 | 0.0870 | 0.0789 | 0.0756 | 0.0740 | −0.0052 |
| BN-REAL-REPEAT-s3 (post-hoc) | 0.0988 | 0.0962 | 0.0957 | 0.0891 | 0.0787 | 0.0731 | 0.0742 | −0.0054 |
| BN-REPLACE-topp95 | n/a | 0.0649 | 0.0519 | 0.0429 | 0.0373 | 0.0275 | 0.0239 | −0.0081 |
| BN-REPLACE-topp95-s2 (post-hoc) | n/a | 0.0763 | 0.0744 | 0.0582 | 0.0407 | 0.0554 | 0.0356 | −0.0079 |
| BN-REPLACE-topp95-s3 (post-hoc) | n/a | 0.0809 | 0.0577 | 0.0547 | 0.0455 | 0.0398 | 0.0436 | −0.0071 |

Bangla REAL-REPEAT falls in all three seeds (slopes −0.0082, −0.0052, −0.0054). The top-p 0.95 chains stay far below the confirmatory chains in both languages and fall clearly in Bangla (slopes −0.0081, −0.0079, −0.0071) and slightly in English (−0.0008, −0.0007, −0.0001). English REAL-REPEAT drifts down only slightly (slopes −0.0004, −0.0010, −0.0007 per generation) against file-to-file swings of about 0.01, and its generation-6 value lies above its generation-0 value in seeds 2 and 3, unlike seed 0. Section S8's "the REAL-REPEAT controls fall in both languages" holds as a trend over generations 1 to 6 in every seed, but the English fall is small and should be described as such.

## 7. What this changes in the manuscript (proposal for rev 20; nothing has been edited yet)

- **Abstract and Section 3.1:** the real-data and decoding controls now have three seeds each (seeds 2 and 3 post-hoc, run 24 October); SUBSAMPLE and the word-matched chain remain single chains. The English net contrast can be stated as near zero in all three seeds.
- **Table 2:** add a post-hoc row for 24 October (seed replicates of REAL-REPEAT and REPLACE-topp95, cross-decoder over three seeds, full-sample equal-length check).
- **Section 4.2 and Table 4:** keep the registered seed-0 rows; add the seed-2 and seed-3 contrasts (Table A) or their mean and range; replace "This is one REAL-REPEAT chain and a failure to detect a difference" by the three-seed result (still a failure to detect a difference, now in three seeds); add the shape and per-document replication (Tables B and C), including the within-arm correlations that show the arms' per-document patterns are reproducible.
- **Section 4.3, Table 5 and Supplementary Section S9 (Tables S8 and S9):** report the three-seed cross-decoder results with 200 prefixes (Tables F, G and H); the seed-0 values change because the draws are new; the third limit ("each decoder arm is a single chain") goes; add the top-p 0.95 sample diagnostics of seeds 2 and 3 (Table D).
- **Section 4.3 or 5.3, new:** the top-p 0.95 chains also raise held-out perplexity faster than REPLACE, in every seed (Table E).
- **Section 4.4, Supplementary Section S14 and Table S12:** add the full-sample column (Table I) and replace the conclusion that registered window slopes "depend on how the window is built": on the full samples, 11 of the 12 registered slopes with intervals excluding zero keep their sign; the 50-document check was too small. Remove "The same check on the full 2,000-document samples needs the restricted files and was not run".
- **Section 5.2:** "with one REAL-REPEAT chain per language neither result is an estimate of run-to-run variance" becomes the three-seed statement. **Section 5.6:** only SUBSAMPLE and the word-matched chain remain single; the attenuation ratio is still a seed-0 comparison (ACCUMULATE was not re-seeded); revise the sentence on the 50-document recomputation. **Section 5.7:** the REAL-REPEAT test it names has now been run.
- **Supplementary Sections S8 (Table S6) and S13 (Table S11):** add the new rows (Section 6; Table C); limit the English REAL-REPEAT novelty claim.
- **Two rounding slips found while checking seed 0:** Section 4.3 gives the Bangla REPLACE sample-NLL SD slope over generations 1 to 6 as +0.022; it is +0.0215 (+0.021 at three decimals). Table S11 gives the Bangla REPLACE web-half slope as 0.089; `perdoc_slopes_by_domain.csv` has 0.0884884 (0.088). Both look like a value rounded twice; a rounding pass over rev 20 would catch any others.
- **Section 3.7 and Data availability:** add the 24 October rental (14.4 GPU-hours, US$9.00; CG4 total US$47.83) and the new released outputs (numbers only: `metrics_posthoc_2026-10-23.jsonl`, the per-document held-out records, the scorer check, the cross-decoder summary and per-continuation NLLs, the full-sample tables and the files in `out/`). The new sample files, 50-document files and `cross_decoder2_samples.jsonl.gz` hold unscreened model text and stay private.

## 8. Files and re-running

Scripts are in `scripts/`; outputs in `out/` (validation runs in `out/validation/`). From the package root:

```
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/checks_posthoc2.py . results/posthoc_seeds_analysis_2026-10-24
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/seeds_controls.py . results/posthoc_seeds_2026-10-23/host/results/metrics_posthoc_2026-10-23.jsonl results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/perdoc_seeds.py results/cg4_sidecars_from_G4b_2026-10-20.zip results/posthoc_seeds_2026-10-23/host/results/chains results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/cross_decoder2_slope_ci.py results/posthoc_seeds_2026-10-23/host/results/posthoc2_cross_decoder/cross_decoder2_samples.jsonl.gz results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/cross_decoder2_distinct2.py results/posthoc_seeds_2026-10-23/host/results/posthoc2_cross_decoder/cross_decoder2_samples.jsonl.gz results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/seeds_extra.py . results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/oov_new_chains.py . results/posthoc_seeds_analysis_2026-10-24/out
python -B results/posthoc_seeds_analysis_2026-10-24/scripts/make_analysis_md.py . results/posthoc_seeds_analysis_2026-10-24
```

Validation (all in `out/validation/`): `seeds_controls.py` without the new records reproduces the registered seed-0 control of Table 4 and Section 4.2 exactly; `cross_decoder2_slope_ci.py` on the 2026-10-20 file reproduces `posthoc_review_2026-10-22/cross_decoder_slope_ci.csv` exactly; both engines of `cross_decoder2_distinct2.py` reproduce Supplementary Table S9 exactly and give identical files on the new data; `seeds_extra.py` reproduces the registered window slopes of `T2_slopes.csv` (largest difference 1e-16); `oov_new_chains.py` reproduces the published Table S6 shares. `verify_independent.py` recomputes 168 point estimates of this report by a separate route (plain NumPy on the raw records and the samples file, no bootstrap code): the largest difference is below 1e-10 (`out/validation/independent_check.csv`), and its four full-sample sign counts agree exactly. See `README.md` for what each script is and what changed from the copies prepared on 23 October.
