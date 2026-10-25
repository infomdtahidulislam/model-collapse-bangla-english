# Sign-off: G2 gen0

**Status:** PASSED
**Date:** 2026-10-14 (an earlier "G2 passed" the same day was withdrawn by the authors; this verdict is on the final re-run, REQ-015)
**Author 1:** Md Tahidul Islam   **Author 2:** Maksuda Akter

## Evidence reviewed
Final run: the REQ-004 re-run on the final G1 probe files, job gen0d on instance 55878879, 2026-10-14 06:40–07:22Z (REQ-015). Two earlier runs were discarded after the probe changes (`invalid_runs/`).

**Update 2026-10-14, 11:05Z:** generation 0 was retrained after the `<eos>`-target bug fix (job eosfix, 09:31–09:58Z). The numbers below are from gen0d (passed) and barely change:
- Held-out log-perplexity: EN 2.693 → 2.693; BN 2.998 → 3.003.
- Recall: EN 0.500 / 0.570 / 0.580; BN 0.530 / 0.360 / 0.405. Every lower bound is above 0.25 (lowest 0.297, BN MID).
- Samples: script 98.4% / 98.3%; duplicates 0 / 0; empty 0.05% / 0%.
- The authors confirmed in chat (2026-10-14T11:10:50Z, REQ-018): "G2 still passed". gen0d is in `invalid_runs/2026-10-14_eos_targets/`.
- [x] Held-out log-perplexity (document-macro, primary), `results/metrics.jsonl`:
  - Base → gen-0: EN 2.776 → 2.693, BN 3.562 → 2.998.
  - Secondary measures: BN improves on all. EN gets slightly worse on token-micro 2.749 → 2.767, bits per byte 0.879 → 0.885, and fresh slice 2.614 → 2.698 (REQ-008 note).
  - Improved? [x] Both authors, "G2 passed" (chat, 2026-10-14). The primary measure improves in both languages.
- [x] 1,000-token generation per language in the right script; repetition < 0.2:
  - Agent, 2,000-document samples: documents ≥ 95% in the right script EN 98.1%, BN 98.6%.
  - 4-gram repetition 0.004 / 0.003; exact duplicates 0 / 0; empty 0.05% / 0.10%.
- [x] Base model id, revision and licence recorded in results/chains/manifest.json: [agent: written on 55878879 at 07:23Z: google/gemma-3-270m, revision 9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1, Gemma Terms of Use, file hashes and library versions (torch 2.13.0+cu130, transformers 5.17.0, vllm 0.31.0)]
- [x] Tail-fact recall above chance per stratum (criterion 2):
  - Agent, gen-0, Wilson 95% CI: EN HEAD 0.495 [0.427, 0.564], MID 0.580 [0.511, 0.646], TAIL 0.595 [0.526, 0.661].
  - BN HEAD 0.515 [0.446, 0.583], MID 0.380 [0.316, 0.449], TAIL 0.425 [0.359, 0.494].
  - Every lower bound is above 0.25.

## Failure-mode checklist (tick all)
- [x] Implementation bug checked (tokenizer, truncation, packing, seeds): [agent: `<bos>` on every document and prompt; micro-batch 4 via `configs/runtime.yaml` (OOM at 8); test_sanity and smoke_gpu PASS on 55878879; seeds 20261010 (train) and 20261017 (sample); the base metrics reproduce exactly across three hosts]
- [x] Every number traceable to results/ or logs/: [agent: `results/metrics.jsonl`, `results/chains/*/step.json` and `sample_meta.json`, `logs/host_55878879/`]
- [x] Shortcut: diversity change vs length change compared: [agent: gen-0 distinct-2 EN 0.722 → 0.775, BN 0.865 → 0.893; mean length EN 169.6 → 165.7 words, BN 174.7 → 150.1 words; cap-hit EN 0.71 → 0.71, BN 0.68 → 0.56]
- [x] Surprising drops checked against NaN loss, empty generations, script collapse: [agent: no NaN; empty 0.05% / 0.10%; documents in the right script 98.1% / 98.6% (base BN 48.5%: the base model drifts out of Bangla, generation 0 does not)]
- [x] No leakage between training, held-out and probe sets; no cross-chain contamination: [agent: test_sanity: held-out disjoint from seed; generation 0 trains on the seed corpora only]
- [x] Run matches chains.yaml and the pre-registration, or deviations.md is updated: [agent: chains.yaml untouched; deviations recorded for the probe changes (REQ-009, REQ-012)]
- [x] Design still answers the RQ (frame-lock check): [agent: yes; the generation-0 floor rule holds in every stratum, so no stratum is excluded from H1(iii)]
- [x] New citations resolved: [agent: none added at G2]

## Notes / conditions

English secondary measures (token-micro log-perplexity, bits per byte, fresh slice) get slightly worse from base to generation 0, while the primary measure improves; see the REQ-008 note (FineWeb-Edu documents worse, Wikipedia documents better). The authors passed G2 on the final numbers (REQ-015). Two earlier generation-0 runs were discarded under REQ-004 after probe changes (`invalid_runs/`). Recorded by the agent.
