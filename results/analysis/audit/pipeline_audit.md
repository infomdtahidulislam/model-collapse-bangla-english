# G6 pipeline audit (numbers only; the interpretation is written by the authors)

Made by `harness/tools/g6_pipeline_audit.py` at 2026-10-18T06:23:34+00:00 from `results/g6_extract/` (the G4b archive, SHA-256 checked).

## 1. Sampling settings and bug limits
- 334 records over 119 steps (generation, sample, training). Expected: temperature 1.0; top-p 1.0, 0.95 for the -topp95 pair; exact-duplicate and empty rate <= 0.05; no NaN loss. Records that differ: 0. File: `audit/sampling_settings.csv`.

## 2. distinct-2 recomputed from the archived samples
- 119 steps; largest absolute difference from `results/metrics.jsonl`: 0.00e+00. File: `audit/distinct2_reproduction.csv`.

## 3. Reserved placeholder tokens written as text (`<unusedNNNN>`)
- Synthetic training corpora: 105 of 122 files contain at least one; 27714 of 4726785 documents (0.586%), 29347 occurrences. Per chain and generation: `audit/unused_tokens.csv`.
- Decoding and training keep them exactly: the Gemma-3 tokenizer lists the 6,242 `<unusedN>` tokens as added tokens that are not special, so `decode(..., skip_special_tokens=True)` writes them out and re-encoding for training returns the same single token ids (checked 2026-10-18 with transformers 5.20.1: `The river<unused42> flows` -> [818, 8858, 48, 17752], identical to the ids decoded).

- Generation 1 (text written by the generation-0 models): BN-ACCUMULATE 0 of 36864 documents; BN-ACCUMULATE-FILTER 0 of 81859 documents; BN-ACCUMULATE-SUBSAMPLE 0 of 36864 documents; BN-REPLACE 0 of 36864 documents; BN-REPLACE-s2 0 of 36864 documents; BN-REPLACE-s3 0 of 36864 documents; BN-REPLACE-topp95 0 of 37888 documents; EN-ACCUMULATE 3 of 44544 documents; EN-ACCUMULATE-FILTER 4 of 119036 documents; EN-ACCUMULATE-SUBSAMPLE 2 of 44544 documents; EN-REPLACE 1 of 44544 documents; EN-REPLACE-WM 1 of 34816 documents; EN-REPLACE-s2 3 of 44032 documents; EN-REPLACE-s3 4 of 45056 documents; EN-REPLACE-topp95 0 of 44544 documents
