# 04 — Run plan, compute budget and the Vast.ai decision (revised 2026-10-12)

Decision (2026-10-11, confirmed 2026-10-12): the GPU phase runs on one rented Vast.ai RTX 4090 host operated by the agent (`12_VASTAI_RUNBOOK.md`). Kaggle (two T4s per session, 30 quota hours per week) stays the fallback (§5).

## 1. Units of work

A **chain** is (language, regime, variant). A **generation step** g is: generate 10M synthetic tokens with the g−1 checkpoint → (filter, topped up) → assemble the training set per regime → train one epoch → generate the fixed-prefix 2,000-document sample from the new checkpoint → metrics and sidecars → `step.json`. Generation 0 is training on the real seed corpus; the untouched base model is scored first (generation −1). REAL-REPEAT steps skip generation.

Confirmatory design: 2 base evaluations + 2 generation-0 trainings + 6 chains × 6 steps = 36 steps. Robustness chains (pre-registered order, `01_PREREGISTRATION.md`) follow.

## 2. Pre-pilot estimates per step on the RTX 4090 (270M model, 10M generated tokens; `harness/vast/plan_budget.py`)

| Part | Estimate | Basis |
|---|---|---|
| Generate 10M tokens (vLLM, 512 requests per batch) | 0.19 h + 0.01 h engine start | ≈ 15,000 tokens/s (3× a T4) |
| Train one epoch on 10M tokens | 0.19 h | 6 × 270M × 10M ≈ 1.6e16 FLOPs at ≈ 25 TFLOPs effective |
| Train on the accumulated set at generation g | 0.19 h × (g + 1) | training set grows linearly |
| FILTER: score 10M tokens with the gen-0 model + top-up generation | ≈ 0.07 h + ≈ 0.06 h | forward passes; pass rate ≈ 0.7 |
| Sample (2,000 documents from the new checkpoint) | 0.02 h | |
| Metrics (held-out 2,000 + fresh, 2,400 probe sentences, bias pairs, gen-0 scoring of the sample, lexical) | 0.06 h | batched forward passes |
| Step total | REPLACE ≈ 0.47 h; ACCUMULATE ≈ 0.47 h + 0.19 h × g; FILTER ≈ 0.6 h + 0.19 h × g; REAL-REPEAT ≈ 0.27 h | |

Measured rates replace these after the Gate 3 pilot (`plan_budget.py --measured`, written to `logs/throughput.csv`).

## 3. Phases, cumulative GPU-hours and the cap

`run_rented.py` executes the phases in this order; `plan_budget.py` prints the table from the config:

| Phase | Content | Hours | Cumulative | Cumulative × 1.25 |
|---|---|---|---|---|
| P0 | base metrics + generation 0, both languages | 0.7 | 0.7 | 0.8 |
| P1 | six confirmatory chains to G = 6 | 34.2 | 34.9 | 43.6 |
| P1′ | second-seed REPLACE pair (with re-seeded gen-0) | 6.0 | 40.9 | 51.1 |
| P2 | EN-REPLACE-WM (word-matched budget) | 1.6 | 42.5 | 53.1 |
| P3 | REAL-REPEAT pair (no-synthetic control) | 3.2 | 45.7 | 57.1 |
| P4 | REPLACE pair extended to generation 10 | 3.7 | 49.4 | 61.8 |
| P5 | third-seed REPLACE pair | 6.0 | 55.4 | 69.3 |
| P6 | ACCUMULATE-SUBSAMPLE pair | 5.5 | 60.9 | 76.1 |
| P7 | top-p 0.95 REPLACE pair | 5.5 | 66.4 | 83.0 |

Cap options for the BUDGET request (price ≈ US$0.40/GPU-h; the 25% slack is the programme rule for estimate error): **A** US$25 / 55 h covers P0–P4 if the pilot confirms the rates (≈ 5 h margin), i.e. the confirmatory design plus seed replicate, word-matched control, no-synthetic control and the plateau series; **B** US$30 / 70 h adds the third seed and the compute-matched accumulation pair; **C** US$34 / 84 h covers everything. The pre-registered stopping rule applies whichever cap is approved: run the phases in order while the measured projection stays within the cap, report the rest as not run. Wall-clock ≈ cumulative hours on one GPU (chains are sequential; a second GPU would only parallelise across chains).

## 4. Integrity rules

- Every step writes `results/chains/<chain>/gen_<g>/step.json` (schema `schemas/step.schema.json`) with the training-set composition (documents and target tokens per source: real, synthetic, masked prefix), the generation record (tokens, exact-duplicate rate, lengths), the filter record, the sample record, checkpoint SHA-256, loss curve, wall time and session id; stage caches (`generate.json`, `filter.json`, `train.json`, `sample_meta.json`) make every stage resumable.
- `harness/tests/test_sanity.py --results` checks that no REPLACE step has real target tokens, that accumulation sets contain exactly the expected components, that duplicate and empty rates are ≤ 5%, that the sample exists, that no held-out document id appears in any synthetic corpus, and that every record matches its schema.
- Samples for human reading are the first 50 of the fixed sample at every step and are written to `results/samples/`.

## 4b. Vast.ai procedure

Exact commands in `12_VASTAI_RUNBOOK.md`: `vast_ops.py search` (RTX 4090, ≥ 24 GB VRAM, ≥ 200 GB disk, reliability > 0.98, CUDA ≥ 12.8, ≤ US$0.45/h) → `create` with the approved `--budget-usd/--max-hours` → `wait` → `push`, `push-env` → `bootstrap.sh` → `fetch_sources.py --all` → `prepare_corpora.py --build` → `build_probes.py` (Gate 1) → `run_chain.py --base` and `--gen0` (Gate 2) → pilot `run_rented.py --chains EN-REPLACE BN-REPLACE --until 1` + `plan_budget.py --measured` (Gate 3) → `run_rented.py --gpus 1 --max-hours <cap − margin>` (resumable) → `status` every ≤ 2 h → `pack_results.py --with-synthetic` (all checkpoints by default) → `pull` → local `--verify` → analysis from the download → `teardown-request` (Gate 4b); a human deletes the instance. Interruptible offers are acceptable because every stage is cached; interim pulls of `metrics.jsonl`, `samples/` and the latest checkpoints limit the loss from an interruption.

## 5. Kaggle fallback

Same harness; two chains per session (`CUDA_VISIBLE_DEVICES`), ≤ 9 h sessions, resume from `state.json`; `training.dtype: float16` with a deviation note (T4 has no bfloat16; the vLLM path is then unavailable and the HF generator is used). ≈ 97 single-T4 hours for the confirmatory design ≈ 61 quota hours over three weeks; `harness/kaggle/plan_sessions.py` and `push_and_poll.py` are the tooling.
