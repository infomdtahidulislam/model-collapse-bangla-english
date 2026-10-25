# 06 — Human tasks (the authors as researchers; revised 2026-10-12)

CG4 has no judges and no raters. The human work is design, verification and reading, about one to two days in total plus the writing. No ethics review is implied; the Gate 0 department notice covers the activity. Both authors are native Bangla readers (confirmed 2026-10-12), so the BN tasks can be split between them, and the EN tasks likewise. The agent asks for each task through `signoffs/REQUESTS.md`; while a request is pending the rented host keeps billing (≈ US$0.40/h), so answer Gate 1–3 requests within a day or tell the agent to stop the instance (`12_VASTAI_RUNBOOK.md` §3). Done already (2026-10-12): `.env` filled, Gemma licence accepted, SSH key registered. Still human-only: loading the Vast.ai balance, approving the cap, and deleting the instance after the teardown checklist.

| Task | Gate | Who | Time | Why it cannot be delegated to the agent |
|---|---|---|---|---|
| Read the design-review decision (`logs/design_review_2026-10-12/editorial_decision.md`) and confirm or veto the pre-Gate-0 changes listed in the DECISION request (claim scope and title, prefix masking, word-matched lengths, robustness order, scoped-out items); freeze `01_PREREGISTRATION.md`; agree authorship (department notice waived by the authors 2026-10-13: independent study, institution has no ethics committee) | G0 | both | half a day | authorship and design ownership |
| Choose the cap option (BUDGET request: A US$25/55 h, B US$30/70 h, C US$34/84 h — **B chosen 2026-10-13, REQ-002**) and load the Vast.ai balance to at least US$30 | G0 | one | 20 min | money |
| Confirm corpus licences; inspect the manifest (domain mix, cleaning, words/bytes per token, length percentiles, fresh-slice size, near-duplicates removed) | G1 | both | 2 h | legal responsibility |
| Spot-check tail-fact probes: 60 BN and 60 EN probes, each with its gold sentence and three distractor sentences (`data/probes/spotcheck_*.csv`); reject per the rule in `02_DATA_SOURCES.md` §3 | G1 | both, split | 1.5 h each | native reading |
| Spot-check bias pairs: 30 per language (the BanStereoSet licence question was decided 2026-10-13, REQ-005: use for evaluation only, cite, disclose the missing licence) | G1 | each | 30 min | |
| Email the BanStereoSet authors for permission to use the dataset (evaluation only; cite arXiv 2409.11638); record the reply, if any, in the data statement | G7 | one | 15 min | the authors' promise of 2026-10-13; legal responsibility |
| Judge the Gate 2 validation: base vs generation-0 perplexity and bits per byte per language; generation-0 recall above chance per stratum; generation-0 sample in the right script, duplicate rate ≤ 5% | G2 | one | 30 min | |
| Pilot review: read 50 generation-1 samples per language; confirm metrics match the text; confirm the duplicate-rate and empty-rate checks; approve the measured projection and how many robustness phases the cap allows | G3 | both | 2 h | bug-as-insight check; money |
| Verify the downloaded archive is complete and delete the rented instance (`11_TEARDOWN_CHECKLIST.md` step 7) | G4b | one | 20 min | irreversible deletion |
| Qualitative read at generations 3 and 6 for every confirmatory chain (12 files of 50; split by chain): code each sample with the rubric below; notes to `results/human_read/<chain>_gen<g>.csv` | G5 | both, split | 2–3 h each | metric sanity; the paper's qualitative section |
| Optional fluency rating: 20 samples per chain × generation {0, 3, 6}, both authors, 1–5 scale, report agreement | G5 | both | ~3 h each | strengthens the "contested metrics" defence |
| Review `analysis_report.md`; decide deviations; write interpretation | G6 | both | 1 day | interpretation |
| Screen the 50-sample files before release (toxic or false content) | G7 | both | 2 h | release responsibility |
| Writing, revision, reviewer responses, disclosure | G7 | both | 2–3 weeks | |

## Qualitative-read rubric (pre-specified; one row per sample)

Columns: `sample_id`, `script_error` (foreign-script or garbage characters: 0/1), `english_intrusion` (BN only: 0/1), `nonwords` (morphologically broken or invented words: count), `repetition_loop` (0/1), `topic_drift` (continuation unrelated to the prefix: 0/1), `fluency_1to5` (optional), `note`. The agent aggregates the counts per chain × generation and places them next to the automatic metrics in the analysis report; disagreements between readers are reported, not resolved.

**Operational rules agreed at G5 (both authors, 2026-10-17T23:38Z; `signoffs/G5_human_read.md`).** They settle borderline cases and do not change the rubric's columns:
- *script_error* = a letter of a third script (Bangla: neither Bengali nor Latin; English: not Latin), or a broken character: a stray or doubled vowel or consonant sign, a digit glued into a word, a broken symbol or a run of repeated punctuation, or a tokenizer placeholder such as `<unusedNNNN>`. An ordinary emoji is not a script error.
- *repetition_loop* = the same word, phrase or symbol three or more times, in a row or within about 10 words. A list whose lines share a short frame but name different items is not a loop; near-identical lines repeated three or more times are.

Sign-offs: `signoffs/G*.md`. The qualitative read and the optional fluency rating are recorded in `results/human_read/` with the sample file hashes.
