# 08 — Gates, pass criteria and checklists (revised 2026-10-12)

A gate passes only when its `signoffs/` file is filled and dated by a human author. The agent prepares the evidence, appends a `GATE` request to `signoffs/REQUESTS.md` (format and the other request types LICENCE / BUDGET / TEARDOWN / DECISION in `..\AGENT_PIPELINE.md` §6), and stops; `python ..\scripts\pipeline_status.py` shows which gate is open and which requests are pending.

| Gate | Evidence prepared by the agent | Pass criteria | Sign-off |
|---|---|---|---|
| **G0 Pre-registration** | Gap checks G11/G28 re-run (`..\scripts\gap_check.py`), saved to `logs/gap_recheck_<date>.txt`; `01_PREREGISTRATION.md` complete; the six-seat design review and editorial decision (`logs/design_review_2026-10-12/`); `plan_budget.py` ladder; offline tests (`test_sanity.py` PASS, scratch integration test) | No new empirical low-resource collapse study (or sub-gap restated); the DECISION items confirmed or vetoed; pre-registration frozen (SHA-256 record in `signoffs/prereg_freeze_<date>.json`; OSF optional); cap option chosen; ethics statement fixed (department notice waived by the authors 2026-10-13: independent study, no ethics committee at the institution); authorship order agreed (CRediT roles deferred to G7 by the authors) | `signoffs/G0_preregistration.md` |
| **G1 Corpora and probes** | `data/corpora/manifest.json` (tokens, words, bytes, per-language prefix/continuation lengths, near-duplicates removed, fresh-slice size); `data/sources/SOURCES_MANIFEST.json`; held-out disjointness and near-duplicate check; probe sets (paired pool, strata counts) and bias pairs; spot-check CSVs with distractor sentences | Licences recorded; token counts matched ±2%; no document id or near-duplicate shared between seed and held-out; 60+60 probes spot-checked, ≤ 5% rejected (rejected ones replaced); fresh slice present | `signoffs/G1_corpora.md` |
| **G2 Base model and gen-0** | `BASE-EN/BN` and `GEN0-EN/BN` metric rows (log-perplexity, bits per byte, recall per stratum); gen-0 samples; `generate.json` of the samples (duplicate and empty rates); `logs/environment.json` | Generation 0 improves on the base model in both languages; recall above chance per stratum (floor rule); samples in the right script, repetition < 0.2, duplicate rate ≤ 5%, empty rate ≤ 5% | `signoffs/G2_gen0.md` |
| **G3 Pilot** | one REPLACE step per language; 50 samples each; `step.json` of both steps (generation, filter n/a, train, sample records); `plan_budget.py --measured` output and `logs/throughput.csv`; the number of robustness phases the approved cap allows | Authors read the samples; metrics match the text; duplicate and empty rates ≤ 5%; schedule fits the cap or a scale rule is applied with a deviation note | `signoffs/G3_pilot.md` |
| **G4 Chains complete** | `run_chain.py --status`; `test_sanity.py --results`; step records; list of robustness phases run / not run | All confirmatory steps complete or documented; composition, duplicate, leakage and schema checks pass | `signoffs/G4_chains.md` |
| **G4b Teardown** (rented GPU only) | `pack_results.py` archive (all checkpoints, all synthetic corpora, sidecars, seed corpora) + manifest; local `--verify` output; analysis regenerated from the downloaded copy; second-copy location | VERIFY: OK locally; analysis reproduces; two copies exist; only then may the instance be deleted (`11_TEARDOWN_CHECKLIST.md`) | `signoffs/G4b_teardown.md` |
| **G5 Human read** | sample files for generations 3 and 6 per confirmatory chain; rubric CSVs | Both authors have read and recorded the rubric; any metric–text mismatch investigated | `signoffs/G5_human_read.md` |
| **G6 Analysis** | `analysis_report.md`, tables and figures regenerated from a clean run; `deviations.md`; seed-replicate and control tables | Reproducible; robustness present; authors have read it | `signoffs/G6_analysis.md` |
| **G7 Writing** | manuscript inputs; screened sample files; disclosure statements | Disclosure present; release policy followed; co-author approval | `signoffs/G7_manuscript.md` |

## 2. Agent stop conditions

Licence forbids use; gen-0 fails validation twice; pilot metrics contradict the text; NaN loss persists after 3 attempts; duplicate or empty rate above 5% after regeneration; any result that would require a design change.

## 3. Failure-mode checklist (copy into every sign-off)

- [ ] Implementation bug: tokenizer, truncation, packing, prefix masking and seeds verified by test or human read
- [ ] Every number traceable to a file in `results/` or `logs/`
- [ ] Shortcut: is a diversity change a length change? (length in words and fixed-window metrics compared)
- [ ] Bug-as-insight: surprising drops checked against NaN losses, empty or duplicated generations, script collapse, precision issues
- [ ] Leakage: no held-out or probe text in any training set; no cross-chain contamination; REPLACE has zero real target tokens
- [ ] Methodology drift: run matches `configs/chains.yaml` and the pre-registration, or `deviations.md` updated
- [ ] Frame-lock: does the design still answer the RQ after the pilot?
- [ ] Citations resolved to identifiers
