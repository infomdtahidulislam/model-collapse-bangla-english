# Sign-off: G3 pilot

**Status:** PASSED
**Date:** 2026-10-14 ("G3 passed" in chat, 2026-10-14T11:37:32Z; corrected pilot after the `<eos>` fix, REQ-018)
**Author 1:** Md Tahidul Islam   **Author 2:** Maksuda Akter

## Evidence reviewed
- [x] One REPLACE step per language completed; measured step time: [agent, corrected pilot after the `<eos>` fix: EN 0.37 h (22.2 min), BN 0.38 h (22.7 min); instance 55878879, 2026-10-14 09:58–10:43Z; REQ-018. The first pilot (07:29–08:16Z, REQ-016) is discarded: its read found the bug]
- [x] 50 samples per language read by both authors; metrics consistent with the text: [first read (REQ-016): yes, broadly, with defects flagged; it led to the `<eos>` bug fix. Corrected read: sheet `results/human_read/G3_pilot_read_corrected_2026-10-14.html` (REQ-018). Authors: yes, broadly, in both languages; EN 8 and BN 2 rows flagged, inspected by the agent (`signoffs/G3_pilot_read_corrected_reply_2026-10-14.txt`)]
- [x] plan_budget.py re-run with measured throughput; fits the cap? [agent: everything (P0–P7) is 57.6 GPU-h, about 56 h still to run. The cap was raised to US$40 / 85 h (REQ-017). The authors set US$40 as the hard total. The projection including the final download is about US$37–38, and the run gets a dollar-based `--max-hours`. Authors: US$40 hard ceiling (chat, 2026-10-14)]

## Failure-mode checklist (tick all)
- [x] Implementation bug checked (tokenizer, truncation, packing, seeds): [agent: the authors' first read led to the `<eos>`-target packing bug, fixed and re-run (`results/deviations.md`). Checks run: `<bos>` on every input, re-scoring reproduces the stored values, vLLM agrees with the HF scorer, prefix masking (712k/796k masked tokens), test_sanity PASS with a pack() check]
- [x] Every number traceable to results/ or logs/: [agent: `results/metrics.jsonl`, step.json, `logs/host_55878879/`, the `harness/tools/` diagnostics]
- [x] Shortcut: diversity change vs length change compared: [agent: gen 0 → 1 distinct-2 EN 0.771 → 0.787, BN 0.879 → 0.897; mean words EN 167 → 169, BN 159 → 154]
- [x] Surprising drops checked against NaN loss, empty generations, script collapse: [agent: no NaN; empty ≤ 0.05%. The script and character defects are measured (`harness/tools/screening_check.py`; REQ-019)]
- [x] No leakage between training, held-out and probe sets; no cross-chain contamination: [agent: REPLACE gen 1 trains on 0 real target tokens; held-out disjoint (test_sanity)]
- [x] Run matches chains.yaml and the pre-registration, or deviations.md is updated: [agent: chains.yaml untouched; the `<eos>` fix is recorded for completeness]
- [x] Design still answers the RQ (frame-lock check): [agent: yes]
- [x] New citations resolved: [agent: none added]

## Notes / conditions

The first pilot read (REQ-016) found the `<eos>`-target bug. It was fixed, and generation 0 and the pilot were re-run. The authors confirmed G2 ("G2 still passed") and passed G3 on the corrected pilot (REQ-018).
The budget is a hard US$40 for all CG4 spending, including the final download. The full run gets a dollar-based `--max-hours`, and if anything runs slower, P7 and then P6 are reported as not run. Recorded by the agent.
