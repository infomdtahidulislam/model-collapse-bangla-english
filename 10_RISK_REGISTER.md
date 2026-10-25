# 10 — Risk register (revised 2026-10-12)

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Measured step costs exceed the pre-pilot estimates and the cap | medium | high | pre-registered priority order of robustness chains and a stopping rule (reported as not run); then scale rules (10M → 5M tokens; 6 → 5 generations) with a deviation note | both |
| Base model has poor Bangla to begin with, so BN starts closer to collapse | high | medium | base-model and gen-0 metrics reported (generation −1 and 0); bits per byte and log-ratio-to-gen-0 slopes as the cross-language scale; the claim is scoped to the model–corpus–language tuple | both |
| Token-matched budgets give Bangla less text than English | high | high | words/bytes per corpus reported; document lengths matched in words; EN-REPLACE-WM word-matched control chain (priority 2) | agent |
| One chain per cell | high | high | re-seeded REPLACE pairs (priorities 1 and 5); measurement vs run-to-run uncertainty reported separately; decision rule requires sign agreement across seeds | both |
| Recipe drift (continual fine-tuning) mimics collapse | medium | high | REAL-REPEAT control chains (priority 3); REPLACE slopes also reported net of the control | agent |
| Numerical instability of Gemma-3 in float16 | — | — | bfloat16 everywhere (training, generation, scoring); float16 only in the Kaggle fallback with a deviation note | agent |
| Duplicated or empty generations enter training | low (fixed) | high | per-request seeds; duplicate and empty rates in every generation record; bug threshold 5% in `test_sanity.py --results` and at Gates 2–3 | agent |
| A metric change is really a length change | medium | high | fixed-window metrics with document-subsampling CIs; length in words reported; shortcut check in every gate | agent |
| Probe sets contain errors or floor effects | medium | medium | paired pool, true-object exclusion, bare object slot, 60-probe spot-check including distractor sentences; gen-0 above-chance floor rule | authors |
| Held-out text memorised by the base model | medium | medium | fresh slice scored separately; MinHash dedup seed ↔ held-out | agent |
| Interruptible instance lost mid-run | medium | medium | every stage cached and resumable; interim pulls of metrics, samples and latest checkpoints | agent |
| Another group publishes low-resource collapse first | medium | high | re-run gap checks at G0; arXiv preprint at G6; the pre-registered regime × language design with controls is the differentiator | authors |
| Licence restricts redistribution of corpora | medium | low | release manifests and ids, not text; record licences | authors |
| Synthetic text contains toxic or false content | high | low | kept in `results/`; only screened 50-sample files released | both |
| Reviewer requests after the run | medium | medium | every checkpoint, corpus, sample and per-item score archived; the pre-registered scope statements list what is out of scope | both |
