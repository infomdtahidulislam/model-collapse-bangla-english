# Requests from the agent to the authors

The agent appends one block per request (format in ../../AGENT_PIPELINE.md section 6); an author edits `Status: PENDING` to `DONE` and fills the reply. The agent never destroys an instance.

**Times.** Every time in this file is UTC (the `Z` or `+00:00` suffix). The authors work in Bangladesh time, UTC+6: for example, 2026-10-18T00:13Z is 06:13 on 18 October in Bangladesh. The reading pages stamp each reply with the laptop's clock converted to UTC. Some early times were typed by hand and are a few minutes off (2026-10-14 before 07:30Z, and REQ-024's first header); `logs/decisions.md` lists the real times (logs/decisions.md, time correction of 2026-10-18T01:10Z). Times before 2026-10-13T16:40Z (G0, REQ-001 to REQ-005) were written on the authors' laptop and cannot be checked against a session log. File and zip-entry times that Windows shows on the VPS are UTC+2.

## REQ-001 | 2026-10-12T20:00:00+00:00 | DECISION | Status: DONE
**Ask:** Confirm or veto the pre-Gate-0 design changes made after the design review (all made before any run, so none is a deviation; the package already implements them). Reply per item (ok / change):
1. Claim scope and proposed title: a single-language-pair, single-model claim ("…degrade faster in Bangla than in English? …with Gemma-3-270m") with "low-resource" defined operationally (`01_PREREGISTRATION.md`, "Scope of the claim").
2. Prefix handling: the real 12-word prefix is context only and excluded from the training loss (`training.prefix_mode: masked`). Alternative the review also accepts: `dropped` (train on the continuation alone).
3. Document lengths matched in words (12-word prefix, 190-word continuation, converted to per-language tokens at Gate 1) instead of 16 / 256 tokens for both languages.
4. The robustness chains and their fixed order 1–7 with the stopping rule (`configs/chains.yaml`; `01_PREREGISTRATION.md`, "Design").
5. Scoped-out items: byte-level tokenizer condition (H3), code-mixed chain, other languages, larger models, re-initialisation design, other temperatures.
6. H2 defined as a relative benefit (ratio) and the three-way decision rule (supported / not supported / inconclusive) with seed-sign agreement.
7. Bangla probe templates changed to bare-object frames (`configs/corpora.yaml`): please read the four BN templates and correct any that read unnaturally.
8. Publication venue: a writing matter, not a study decision; not recorded here.
9. BanStereoSet licence is unstated in its repository: use it, ask its authors, or swap the BN bias probe (also listed in the pre-start checklist).
**Evidence:** logs/design_review_2026-10-12/editorial_decision.md (decision: major revision before freeze, zero GPU hours); the reports in the same folder; 01_PREREGISTRATION.md; configs/chains.yaml; logs/decisions.md (offline tests passed 2026-10-12).
**Human reply:** ok to all nine items (author's reply given in chat on 2026-10-12; recorded in this file by the agent on 2026-10-13). Agent's reading of the open-ended items, to be corrected by the authors if wrong: 7 = the four BN probe templates stay as written in configs/corpora.yaml; 9 = BanStereoSet stays as the BN bias probe, but because its repository states no licence the LICENCE request at Gate 1 still stands (12_VASTAI_RUNBOOK.md). No deviation entry: all items were implemented before any run.

## REQ-002 | 2026-10-12T20:00:00+00:00 | BUDGET | Status: DONE
**Ask:** Approve one cap for the CG4 instance (price assumed US$0.40/GPU-h; the ladder is in 04_RUN_PLAN.md §3): **A** `--budget-usd 25 --max-hours 55` covers the confirmatory design plus the second seed, the word-matched English control, the no-synthetic control and the REPLACE extension if the pilot confirms the estimates (about 5 h margin); **B** `--budget-usd 30 --max-hours 70` adds the third seed and the compute-matched accumulation pair; **C** `--budget-usd 34 --max-hours 84` covers every pre-registered robustness phase. Recommendation: B. The programme cap (US$125) is unchanged. Please also load the Vast.ai balance (US$0.00 on 2026-10-12) to at least the chosen cap.
**Evidence:** `python harness\vast\plan_budget.py` (pre-pilot estimates; re-planned with measured rates at Gate 3).
**Human reply:** B — `--budget-usd 30 --max-hours 70` (author's reply given in chat on 2026-10-13; recorded in this file by the agent the same day). Covers phases P0–P6 (confirmatory chains, second and third seed, word-matched EN control, no-synthetic control, REPLACE to generation 10, ACCUMULATE-SUBSAMPLE); P7 (top-p 0.95 pair) runs only if the measured projection at Gate 3 leaves room, otherwise it is reported as not run. Programme cap US$125 unchanged. Still to do by an author: load the Vast.ai balance to at least US$30 (it was US$0.00 on 2026-10-12); `scripts/preflight.py` checks for it.

## REQ-003 | 2026-10-12T20:00:00+00:00 | GATE | Status: DONE
**Ask:** G0: after REQ-001 and REQ-002, fill signoffs/G0_preregistration.md (gap re-check verdict, prereg tag or OSF DOI, department notice date, authorship and CRediT roles). The licence and secrets items are done (Gemma licence accepted, .env filled, SSH key registered, keys verified 2026-10-12).
**Evidence:** 01_PREREGISTRATION.md; logs/gap_recheck_<date>.txt (gap re-check); logs/design_review_2026-10-12/; harness/tests/test_sanity.py → RESULT: PASS; offline integration test of the rewritten harness (logs/decisions.md).
**Human reply:** G0 PASSED on 2026-10-13 (first author, in chat; recorded by the agent). signoffs/G0_preregistration.md filled: authors Md Tahidul Islam (corresponding) and Maksuda Akter; gap re-check verdict open; pre-registration frozen (SHA-256 record) and publicly registered on OSF, DOI 10.17605/OSF.IO/SRA28, with the final title "Model Collapse in Bangla and English: A Pre-Registered Study of Iterative Self-Training with Gemma-3-270m"; department notice waived (no ethics committee at the institution; ethics statement fixed); no funding, no competing interests; CRediT deferred to G7; cap B approved (REQ-002); Vast.ai credit US$30.00 on the keyed account.

## REQ-004 | 2026-10-13T16:04:13+00:00 | DECISION | Status: DONE
**Ask:** May base-model metrics and generation-0 training start on the rented host before Gate 1 is signed? They depend only on the built corpora, which the authors' probe and licence checks rarely change; waiting idles the host at about US$0.40/h, while a redo after a corpus change costs under one GPU-hour (about US$0.30).
**Evidence:** 12_VASTAI_RUNBOOK.md §3 (idle-cost options and the pre-approval option); 04_RUN_PLAN.md §3 (phase P0 = 0.7 h).
**Human reply:** Delegated to the agent by the first author in chat on 2026-10-13 ("I don't have any idea. Just make everything in the folder, so that agent can understand and start."). Agent decision: ALLOWED. After the Gate 1 evidence is filed, the agent runs the base metrics and generation 0 for both languages, then waits for the G1 reply. Conditions: (1) if the G1 spot-check or licence decision changes any corpus or probe file, generation 0 is retrained from the corrected files and the first run is discarded and logged, never kept; (2) no generation-1 step starts before G1 is PASSED; (3) operational choice, not a design change, so no deviations entry. Recorded by the agent on the laptop on 2026-10-13 with the authors' permission.

## REQ-005 | 2026-10-13T16:12:50+00:00 | LICENCE | Status: DONE
**Ask:** BanStereoSet (Bangla stereotype / anti-stereotype pairs, Findings ACL 2025, arXiv 2409.11638; repository kamruzzaman15/BanStereoSet) states no licence. Options: (1) use it for evaluation only, cite the paper, and disclose the missing licence in the data statement; (2) ask its authors for permission first; (3) drop or swap the Bangla bias probe.
**Evidence:** 02_DATA_SOURCES.md §4; 05_METRICS.md (stereotype preference score, exploratory, within-language only); configs/corpora.yaml (bias source entry; frozen and registered, so the licence note stays in the manifest and the sign-off, not in the yaml).
**Human reply:** Option 1 chosen by the first author in chat on 2026-10-13: use BanStereoSet as is for the evaluation-only bias measure, cite the paper, never redistribute the file, and state in the manuscript's data statement that the repository carries no explicit licence. The authors will email the dataset authors for permission during the writing stage (added to 06_HUMAN_TASKS.md as a G7 task); a reply, if any, is recorded in the data statement. Recorded by the agent the same day.

## REQ-006 | 2026-10-13T16:31:09+00:00 | DECISION | Status: DONE
**Ask:** Which terminal drives the CG4 run on the VPS? The Claude Desktop (Cowork) session started on the VPS on 2026-10-13 can read and write files in this folder but has no terminal on the VPS, so it cannot install software, run `scripts\preflight.py`, open SSH/SCP to a rented host, pull the G4b archive or keep the 2-hour `vast_ops.py status` loop. Its cloud workspace cannot stand in: outbound SSH ports are blocked there, and the 45-70 GB G4b archive has to land on the VPS anyway. Options: **(A, recommended)** Claude Code (terminal version) runs on the VPS as the experiment agent, as `PRE_START_CHECKLIST.md` section G2b already describes. Node.js and Git are already installed there; one author runs `npm install -g @anthropic-ai/claude-code` in PowerShell, starts `claude` in this folder, signs in once and tells it to read `START_HERE.md`; no typing after that. **(B)** The Cowork session stays the agent and an author pastes each command it gives into PowerShell on the VPS: one setup script, about 15 commands for Gate 1, more for generation 0 and the pilot, and monitoring commands during the 1.5-3.5-day chain run (a Windows scheduled task covers the 2-hour status rule). Operational choice, not a design change: no deviations entry.
**Evidence:** Cowork tool list on the VPS (folder read/write only, no shell); cloud-workspace network test 2026-10-13 (TCP 22, 2222, 8080, 40022, 51234 refused); `scripts/pipeline_status.py` run on a snapshot of this folder (CG4 G0 PASSED, G1 OPEN, no pending requests); pre-registration freeze re-verified (6/6 SHA-256 match `signoffs/prereg_freeze_2026-10-13.json`); CG4 offline checks on the snapshot (`test_sanity.py` RESULT: PASS, `fetch_sources.py --dry-run` ok, `plan_budget.py`, `run_rented.py --plan`); logs/decisions.md 2026-10-13T16:31.
**Human reply:** Option A, Claude Code on the VPS: chosen in chat on 2026-10-13 in the VPS Cowork session by its user (Claude account "Shajbo Kam", answering for the authors per START_HERE.md §1); recorded by the agent the same day. The same user added that they are signed in to Vast.ai, Hugging Face, OSF and ORCID in Chrome on the VPS for any browser step; browser use stays within START_HERE.md §6. The Cowork session hands over without having run or rented anything; START_HERE.md, CLAUDE.md, README.md and AGENT_PIPELINE.md now name Claude Code as the agent. Operational, so no deviations entry. **Confirmed 2026-10-13T16:52Z** (the user's message arrived 16:40:56Z; 16:52Z is when it was recorded) in the first Claude Code session on the VPS: its user wrote in chat "REQ-006 in signoffs/REQUESTS.md was answered: Claude Code on this VPS drives the run; mark it DONE" (answering for the authors per START_HERE.md §1); status stays DONE. PRE_START_CHECKLIST.md §G2b now records the decision as well.

## REQ-007 | 2026-10-13T18:54:22+00:00 | GATE | Status: DONE
**Ask:** G1 evidence ready (corpora, held-out sets, probes and bias pairs built on Vast.ai instance 55779705). Please (1) read the 60 BN + 60 EN tail-fact probes and the 30 BN + 30 EN bias pairs in `signoffs/G1_spotcheck_2026-10-13.html` (the same rows as `data/probes/spotcheck_{BN,EN}.csv` and `spotcheck_bias_{BN,EN}.csv`; split them between you as you like), tick every row you reject with a short reason, and paste the sheet's "Copy reply" text into the chat. Rules: reject a probe if the gold sentence is false or ungrammatical, or if a distractor sentence is true or ungrammatical in a way the gold is not (02_DATA_SOURCES.md §3); reject a bias pair if it is garbled or ungrammatical, has an unfilled BLANK, or has stereotype and anti-stereotype swapped. More than 5% rejected (3 of 60) in a language means that language is rebuilt and you look again; rejected probes are replaced. (2) Confirm the licences of the eight sources (listed in the sheet). (3) Read the two probe-construction fixes below and veto them if you disagree. I fill `signoffs/G1_corpora.md` from your reply; G1 passes when you say so in chat. Meanwhile (REQ-004) the base-model metrics and generation 0 run on the host; if your check changes a probe or corpus file, generation 0 is redone and the first run discarded.
**Evidence:** `data/corpora/manifest.json` (seed tokens EN 10,000,387 / BN 10,001,024, 0.01% apart, rule 2%; words EN 7,314,331 / BN 5,625,959; held-out 2,000 regular + 500 / 499 fresh pages; 10,000 prefixes per language of 16 / 21 tokens, continuation caps 260 / 338 tokens = 12 / 190 words); `data/sources/SOURCES_MANIFEST.json` (bnwiki, enwiki, Sangraha, FineWeb-Edu 40,000 records each; fresh pages 600 + 600; CrowS-Pairs 1,508; BanStereoSet 1,194; licence per source); `data/probes/{EN,BN}_tail_facts.jsonl` (600 each, HEAD / MID / TAIL 200 each); `data/probes/{EN,BN}_bias.jsonl`; `data/probes/wikidata_fetch_summary.json`; `logs/host_55779705/test_sanity_G1.txt` (RESULT: PASS: held-out disjoint from seed, fresh slices present, prefixes carry token ids, three distractors per probe, gold never a distractor, one probe per subject, tokens matched within 2%); `logs/decisions.md` 2026-10-13T17:09–18:52 (setup, the bugs fixed before Gate 1, sources, corpora, probes).
**Probe-construction fixes made before anyone saw a probe (implementation of the registered text; no value in `configs/corpora.yaml` changed; details in `logs/decisions.md`):** (a) The Wikidata triples are now drawn evenly over each relation's statements (50–200 index windows, round-robin up to the registered 3,000 per relation). The original `LIMIT 3000` query returned the first matches of an index grouped by object: P17 gave 3,000 triples all with the object Canada, which leaves no same-relation distractors, so P17 would have had no probes; P19 had 29 birthplaces and P106 42 occupations. Now P36 2,395, P17 46, P19 439 and P106 33 distinct objects. P17 answers are still uneven: New Zealand is the gold of 26% (EN) and 28% (BN) of the P17 probes. (b) Distractors now exclude all true objects of the subject, fetched from Wikidata, as 02_DATA_SOURCES.md §3 says; before, only the sampled triples were excluded (people carry 2.7 occupations each on average in Wikidata, so a true occupation could have been a "distractor").
**Human reply:** Answered in chat on 2026-10-14 and recorded by the agent; verbatim in `signoffs/G1_spotcheck_reply_2026-10-14_corrected.txt` (the authors' re-paste without EN-P19-0507, authoritative; first paste in `G1_spotcheck_reply_2026-10-14.txt`). Both authors read every row together.
- Confirmed: the licences of the eight sources and the corpus numbers. Fixes (a) and (b) approved.
- Spot-check round 1, English: 34 of 60 probes rejected (35 were ticked; EN-P19-0507 was a mouse slip, withdrawn by the authors the same day).
  - P106: 18 of 18. The frame "The occupation of … is …" is malformed with a bare job title.
  - P17: 16 of 17. Topics, year summaries, bilateral relations, an Olympic delegation and an organisation are not places "located in" a country; one gold sentence lacks "the" before "United States".
  - P19: 0 of 18.
- Spot-check round 1, Bangla: 13 of 60 probes rejected.
  - P17: 12 of 15, abstract topics, dates or events.
  - P19: 1 of 17, "পৃথিবী" (Earth) as a birthplace.
- Bias pairs: 1 of 30 English and 4 of 30 Bangla rejected.

The authors then wrote "G1 passed".

Agent note: the registered rule (02_DATA_SOURCES.md §3 and this request) requires a rebuild and a second look for any language with more than 3 of 60 rejected. Both languages exceed it. The rejects are systematic, and the P106 frame sits in the frozen `configs/corpora.yaml`. G1 therefore stays OPEN until the rebuild (REQ-009) and the authors' second look. The confirmed items carry over.

## REQ-008 | 2026-10-13T19:46:27+00:00 | GATE | Status: DONE
**Ask:** G2 evidence ready (base model = generation −1 and generation 0, both languages; run under REQ-004 while G1 waits). Please judge the three G2 criteria of `03_MODELS_AND_TRAINING.md` §6 from the numbers below and say in chat "G2 passed", or what should happen instead. Criterion 1 is mixed for English, see the note. G2 can only pass after G1 (REQ-007); nothing after generation 0 runs before both are PASSED.
**Evidence (all from `results/metrics.jsonl`, `results/chains/*/step.json`; pulled to the VPS and hash-checked):** (1) held-out log-perplexity, document-macro (pre-registered primary), base → gen-0: EN 2.776 → 2.693, BN 3.562 → 2.996; token-micro: EN 2.749 → 2.767, BN 3.703 → 3.257; bits per byte: EN 0.879 → 0.885, BN 0.536 → 0.471; fresh slice log-perplexity: EN 2.614 → 2.698, BN 3.444 → 3.180 (bits per byte EN 0.865 → 0.899, BN 0.496 → 0.460). (2) gen-0 tail-fact recall (Wilson 95% CI; chance 0.25): EN HEAD 0.630 [0.561, 0.694], MID 0.675 [0.607, 0.736], TAIL 0.720 [0.654, 0.778]; BN HEAD 0.600 [0.531, 0.665], MID 0.450 [0.383, 0.519], TAIL 0.450 [0.383, 0.519]: every interval above chance. (3) gen-0 sample of 2,000 documents per language (`results/chains/GEN0-*/sample_meta.json`): documents ≥ 95% in the language's script EN 98.4%, BN 98.2%; mean 4-gram repetition EN 0.005, BN 0.004 (rule < 0.2); exact duplicates 0.0% / 0.0%; empty 0.05% / 0.10% (rule ≤ 5%); cap reached 71.7% / 56.1%. Training (`train.json`): 154 optimizer steps on 10.03M (EN) / 10.04M (BN) tokens, loss 2.97 → 2.84 (EN) and 4.09 → 3.31 (BN), no NaN, 615 s / 617 s, micro-batch 4 × 16 = effective 64. Base model `google/gemma-3-270m` revision 9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1, Gemma licence, file hashes and library versions in `results/chains/manifest.json`; host environment in `logs/host_55779705/environment.json`. 50-document samples for reading: `results/samples/{BASE,GEN0}-{EN,BN}_*_50.jsonl` (synthetic text; stays in `results/`).
**Note on criterion 1 (English):** generation 0 improves the primary measure in both languages, and every measure in Bangla. In English the token-micro log-perplexity, bits per byte and the fresh slice get slightly worse. Per document (`heldout_nll.jsonl` sidecars): FineWeb-Edu held-out documents +0.085 nats per token (94% of them worse); Wikipedia documents −0.25 on average (72% better: short ones −0.62, long ones +0.03). Checked as a possible bug before reporting: a save/reload round trip of the untouched base model changes NLL by −0.0001 per token; the checkpoint config differs from the base config only in serialization (same RoPE values); re-scoring GEN0-EN reproduces its sidecar to 0.00002. So the numbers come from the trained model, not from the pipeline. Whether this meets "generation 0 improves on the base model" is the authors' call (G2 pass, or a DECISION on the recipe, which would be a deviation from the registered training settings).
**Human reply:** WITHDRAWN. The authors wrote "G2 passed" in chat on 2026-10-14, then withdrew it the same day: "I mistakenly say G2 passed. I want to close G1 first." Recorded by the agent. No G2 verdict stands.

Superseded: the G1 rebuild changes probe files, so under REQ-004 condition (1) generation 0 and its metrics are re-run from the corrected files. After G1 closes, G2 is asked again in a new GATE request with the re-run numbers.

## REQ-009 | 2026-10-14T00:46:14+00:00 | DECISION | Status: DONE
**Ask:** How should the probes be rebuilt after G1 round 1? The rejects are systematic, so a plain rebuild would repeat them. Reply "approve", or change any item:

1. **English P106 frame.** It lives in the frozen `configs/corpora.yaml`, so this is a deviation, logged in `results/deviations.md`.
   - Current: "The occupation of {S} is {O}."
   - Recommended: "The occupation of {S} is listed as {O}." It keeps the answer slot bare, as the registered rule requires, and "listed as" takes a bare job title.
   - Alternatives: "{S} had the occupation of {O}."; or "a/an" chosen per candidate, which drops the bare-slot rule.
   - The Bangla frame stays.
2. **P17 subjects.** Keep only items with a coordinate location (P625) and no event date (P585/P580), and drop labels that read as a date in either language.
   - On the current probes this drops 26 of the 28 P17 rejects. The other two are one missing "the" (item 4) and "৫ই মে", which is the Mexican town 5 de Mayo.
   - It also drops 4 P17 probes you accepted (EN-P17-0026, BN-P17-0489, BN-P17-0533, BN-P17-0450).
   - Only EN 35 of 197 and BN 30 of 163 current P17 probes pass. The rebuilt sets will therefore hold fewer P17 probes and more of the other three relations; no per-relation quota is registered.
3. **P19 objects.** Keep only places that have a country (P17). This removes "পৃথিবী" (Earth) and affects 2 EN and 6 BN current probes, one of which you accepted (EN-P19-0048).
4. **"the" in English labels.** English labels of states that take "the" get it wherever they fill a slot ("the United States", "the Netherlands", "the Russian Empire").
5. **EN-P19-0507 (Arvind Kumar).** It had no reason. If the problem is that many people share the name, subjects whose label belongs to more than one person on Wikidata are dropped as well.
6. **Bias pairs.**
   - Drop the 5 rejected pairs, plus the 8 other BanStereoSet pairs with the same detached case ending as BN-B0128 (9 of 1,194 in all).
   - BN-B0840, checked as asked: the negation reverses it. "Not as hostile as you have heard" argues against the stereotype; "not as welcoming" argues for it. It is the only negated comparison in the set.
   - The remaining defect rate is reported in the data statement.

**Then:**
- Rebuild both languages on the VPS (no GPU).
- Draw a new sample of 60 + 60 probes for the authors' second look.
- While the authors read, generation 0 re-runs under REQ-004 (about 40 GPU-minutes, about US$0.35).

**Evidence:**
- `signoffs/G1_spotcheck_reply_2026-10-14.txt`.
- The filter test against the round-1 verdicts (agent, 2026-10-14, Wikidata queries; numbers above).
- `configs/corpora.yaml` lines 52–60 (frames and the bare-slot rule).
- 02_DATA_SOURCES.md §3.

**Human reply:** "approve" (chat, 2026-10-14; recorded by the agent). Items 1-4 and 6 are approved as written. Item 5 does not apply: the authors said the same day that EN-P19-0507 was ticked by a mouse slip, not rejected, so no name filter is added. The English P106 frame is a deviation and is recorded in results/deviations.md.

## REQ-010 | 2026-10-14T01:09:58+00:00 | GATE | Status: DONE
**Ask:** G1 round 2, the second look at the rebuilt probes. Open `signoffs/G1_spotcheck_round2_2026-10-14.html`; it has 60 EN and 60 BN probes and no bias pairs. Tick every probe you reject, with a short reason, and paste the sheet's "Copy reply" text into the chat. The rule is the same as in round 1 (02_DATA_SOURCES.md §3). G1 passes when each language has at most 3 rejects out of 60; those few are then replaced. More than 3 in a language means another rebuild of that language and another look. Licences, corpus numbers and fixes (a)/(b) were confirmed in round 1 (REQ-007).
**Evidence:**
- Probes rebuilt on the VPS with the REQ-009 changes: 600 per language, 200 per stratum.
  - EN relations: P19 221, P106 220, P36 111, P17 48.
  - BN relations: P106 212, P19 192, P36 154, P17 42.
- `configs/corpora.yaml` SHA-256 129d8d7c… (English P106 frame "The occupation of {S} is listed as {O}."; `results/deviations.md`).
- `harness/tests/test_sanity.py` PASS: three distractors per probe, gold never a distractor, one probe per subject, held-out disjoint.
- The round-2 sample: EN P19 26, P106 22, P36 6, P17 6; BN P19 21, P106 20, P36 12, P17 7 (`data/probes/spotcheck_{EN,BN}.csv`).
- P17 golds are concentrated on the United Kingdom (EN 23 of 48, BN 16 of 42).
- Round-1 files: `data/probes/round1_2026-10-13/`.
**Human reply:** Round 2 answered by the authors in chat on 2026-10-14; the verbatim text is in `signoffs/G1_spotcheck_round2_reply_2026-10-14.txt`.
- **EN: 7 of 60 rejected.** P19 3 of 26: a missing "the" in "the 2nd arrondissement of Lyon" (twice) and "the 15th arrondissement of Paris". P106 2 of 22: "lawyer" is also true of Narendra Deva; "actor" is also true when "film actor" is. P17 2 of 6: a missing "The" before "Metropolitan line"; Quebec Sign Language is a language, not a place.
- **BN: 3 of 60 rejected.** P17 2 of 7: La Route du Rock is a festival; "the geography of Canada" is a topic. P106 1 of 20: "postdoctoral researcher" is also true of Rodney Robert Porter.
- All other rows ok.
- Agent's reading under the registered rule (at most 3 of 60, `08_GATES_AND_CHECKLISTS.md` G1 "≤ 5% rejected (rejected ones replaced)"): **BN meets it** (3 of 60), so its 3 rejected probes are replaced. **EN does not** (7 of 60), so EN is rebuilt and gets another look. G1 stays OPEN. How to fix the causes is asked in REQ-012. Recorded by the agent.

## REQ-011 | 2026-10-14T01:34:21+00:00 | TEARDOWN | Status: DONE
**Ask:** Delete the old Vast.ai instance 55779705 (RTX 4090, Denmark, label CG4-run1). It has been stopped since 2026-10-13T20:48Z and cannot restart, because its GPU is rented by someone else. Its disk bills about US$0.08/h (about US$2/day) until it is deleted. The authors allowed the deletion in chat on 2026-10-14 ("You can also delete current one if needed after getting the data, you have my permission"). The agent cannot run `vastai destroy` (blocked in the project settings; deletion is a human step), so an author runs the command below.
**Evidence: what is on its disk and where it is now.**
- Safe on the VPS: results of the first generation-0 run (pulled and hash-checked 2026-10-13T19:45Z; discarded under REQ-004, quarantined in `invalid_runs/2026-10-14_round1_probes/`); host logs (`logs/host_55779705/`); corpora, held-out sets, prefixes, probes, bias pairs.
- **Not recoverable after deletion:** `data/sources/`, the raw source downloads (933 MB). Their hashes are in `data/sources/SOURCES_MANIFEST.json`. Vast's instance-to-instance copy to 55843268 failed twice (status_msg: "vastai_kaalia@202.79.159.48: Permission denied (publickey)"). The experiment does not need them, because every file built from them is preserved with hashes. They could be fetched again with `harness/fetch_sources.py` and compared against the recorded hashes; current upstream versions may differ.
- Also not recoverable: `/workspace/invalid_runs/2026-10-13_no_bos`, the invalid first base-model outputs. They are documented in `logs/decisions.md` (2026-10-13T19:02Z) and never used.
**Human command:** `vastai destroy instance 55779705`. Afterwards, check in the Vast console that the instance and its storage are gone.
**Human reply:** Done. The first author deleted instance 55779705 on the Vast.ai website and wrote in chat on 2026-10-14: "I have deleted it myself from the vast ai." (Their first try, `vastai destroy instance 55779705` in the terminal, failed with "command not found", because that shell does not have the project venv on PATH.) The agent checked at 2026-10-14T04:33:40Z: `vastai show instances` lists only 55843268 (CG4-run2, stopped), and `vastai show volumes` is empty. Recorded by the agent.

## REQ-012 | 2026-10-14T05:45:00+00:00 | DECISION | Status: DONE
**Ask:** How should the probes be fixed after G1 round 2? English did not meet the rule (7 of 60); Bangla did (3 of 60). Your 10 rejects have four causes, and each also appears in probes outside the sample. Reply "approve", or change any item:

1. **P17 subjects: settlements and administrative areas only.** Checked by Wikidata class: human settlement (Q486972) or administrative territorial entity (Q56061), through P31/P279.
   - Also out: dependent territories and places in them (Bermuda, whose Wikidata country is the United Kingdom); places with more than one present-day country (Lake Erie); names that read as a Spanish date ("1ro. de Enero"). The REQ-009 conditions stay.
   - Why: your four P17 rejects (a sign language, a music festival, a rapid-transit line, "geography of Canada") all have coordinates and no date, so the REQ-009 test let them through. Physical features also need an English article that Wikidata cannot set reliably ("the River Severn", but "Lake Erie"); that caused EN-P17-0056.
   - Effect: P17 probes go from 48 to 17 (EN) and from 42 to 18 (BN). It also removes 5 P17 probes you accepted: a railway station, a lake, an archaeological site, a mountain and a road.
2. **P17 answers: present-day sovereign states only**, both the gold and the wrong options.
   - This removes Mandatory Palestine, the Inca Empire, the Almohad Caliphate, the Union of South Africa, and "China" (the region), which sat next to "the People's Republic of China".
   - A wrong option is never the country of another place with the same name. For example, there is also a Toronto in England.
3. **P19 wrong options** may not contain, or lie inside, a true birthplace. Example: "Banff" when Wikidata gives only "Canada". 2 EN probes.
4. **P106 wrong options.** A wrong option may not be:
   - a broader or narrower occupation, in Wikidata's class tree, than one of the subject's occupations ("actor" for a "film actor"; 35 EN and 27 BN options);
   - a kind of an occupation the subject already falls under ("postdoctoral researcher" for a biochemist, who is a researcher; 6 EN and 6 BN).
   - Not fixable from Wikidata: it lists Narendra Deva only as "writer", so "lawyer" could not be excluded. Such probes are replaced when you find them.
5. **English "the"** for:
   - place names that start with an ordinal ("the 2nd arrondissement of Lyon");
   - P17 subjects, with "The" at the start of the sentence ("The Northwest Territories is located in …").
   - 7 EN probes.
6. **P36: found by the agent, not among your rejects.** Only subjects with a single capital in Wikidata.
   - Historical states list every capital they had, and the sampled one can be a minor one that reads as false: "The capital of the Portuguese Empire is Rio de Janeiro."; "… of the Republic of Texas is Houston."
   - 13 EN and 13 BN probes. You accepted 2 of them (BN-P36-0097, BN-P36-0346).
7. **How it is applied.** The round-2 sets are kept and repaired, not drawn again. 499 EN and 524 BN probes stay exactly as you read them.
   - **Replaced:** your 10 rejects, and every probe whose subject or answer breaks item 1, 2 or 6 (EN 49 in all, BN 38). Each is replaced by the next eligible subject of the same stratum.
   - **Re-drawn:** only the wrong options that break items 2–4 (EN 46 probes, BN 38). The other options stay.
   - **Text only:** item 5.
   - Bangla met the rule, so it needs no new look. English gets a third look at 60 probes you have not read (REQ-013). The round-3 sheet also shows 20 changed Bangla probes for information.
   - After G1 passes, generation 0 is retrained and rescored from the final files (REQ-004, about 40 GPU-minutes), and then G2 is filed.
   - Of the 110 round-2 rows you accepted, 13 change (5 EN, 8 BN). In those cases the rules are stricter than your reading.
   - Effect on inference, for `results/deviations.md`:
     - Relation mix: EN P19 241, P106 235, P36 107, P17 17 (was 221, 220, 111, 48); BN P19 208, P106 224, P36 150, P17 18 (was 192, 212, 154, 42).
     - P106 wrong options are less related to the subject's occupations, which can make occupation probes easier.

**Evidence:**
- `signoffs/G1_spotcheck_round2_reply_2026-10-14.txt`. The Wikidata check of each reject is in `logs/decisions.md` (2026-10-14T05:05Z).
- Facts for the rules: `data/probes/wikidata_filters_r2.json` (`harness/build_probes.py --filters-r2`).
- The staged repair: `data/probes/staging_round3/`, with the probe files and `repair_round2.json` (one entry per change).
  - `build_probes.py --repair-round2` first reproduces the round-2 sets exactly, and stops if it cannot.
  - An independent check passed: 600 per language, 200 per stratum, no rule broken, all 10 rejects replaced, and every unchanged probe identical to round 2.
- The round-2 files are archived in `data/probes/round2_2026-10-14/`.
**Human reply:** "Approve" (2026-10-14T06:16:27Z, after the clean round 3).
- The authors chose "Approve" in the chat question. The question read: "Do you approve REQ-012, the probe rules these round-3 probes were built with? Approving closes G1. I then switch to the repaired probe files, record the deviation, retrain and rescore generation 0 on the GPU (about 40 minutes), and file Gate 2."
- All 7 items are approved as written. The staged repair becomes the probe set; the deviation is recorded in `results/deviations.md`. Recorded by the agent.

## REQ-013 | 2026-10-14T05:45:00+00:00 | GATE | Status: DONE
**Ask:** G1 round 3, the third look at English. It counts only if REQ-012 is approved.
- Open `signoffs/G1_spotcheck_round3_2026-10-14.html`. It has 60 English probes from the repaired set that you have not read, and 20 changed Bangla probes for information.
- Tick each reject with a short reason, press "Copy reply" and paste the text in chat.
- G1 passes when English has at most 3 rejects out of 60; those few are then replaced. Bangla rows you reject are replaced without another look.
**Evidence:**
- The English sample:
  - Relations: P106 29, P19 26, P36 5. No P17 probe was drawn; there are 17 among the 600.
  - Strata: HEAD 20, MID 19, TAIL 21.
  - 8 are new probes, 3 have a re-drawn wrong option, and 49 are unchanged since round 2 but were not in your round-2 sample.
- The Bangla rows: 10 new probes and 10 with a re-drawn option.
- Files: `data/probes/staging_round3/spotcheck_round3_{EN,BN}.csv`. Round-2 results: REQ-010.
**Human reply:** "G1 spot-check round 3: no rejections. All other rows ok." (chat, 2026-10-14T06:15:22Z; verbatim in `signoffs/G1_spotcheck_round3_reply_2026-10-14.txt`).
- English: 0 of 60 rejected. Bangla: 0 of the 20 rows shown for information.
- English meets the rule. G1 passes once REQ-012 is approved, because this round counts only with it. Recorded by the agent.

## REQ-014 | 2026-10-14T06:35:00+00:00 | TEARDOWN | Status: DONE
**Ask:** Delete the Vast.ai instance 55843268 (RTX 4090, Japan, label CG4-run2).
- It has been stopped since 2026-10-14T03:16Z. Its GPU was then rented by someone else, so the restart at 06:2xZ stayed in "scheduling" ("Your GPU is currently in use ... hours to weeks"; the authors saw the same message in the Vast console). The agent cancelled the pending start at 06:25Z.
- Its disk bills about US$0.056/h (about US$1.3/day) until it is deleted.
- The new instance 55878879 (RTX 4090, Pennsylvania, US$0.456/h, label CG4-run3, cap US$25.0 / 64 GPU-h) replaces it.
- The authors allowed deleting a replaced instance once its data is safe (chat, 2026-10-14, for 55779705). Deleting is a human step, because `vastai destroy` is blocked for the agent.
**Evidence: what is on its disk and where it is now.**
- The discarded round-2 generation-0 run (job gen0c, 01:34–02:04Z). It was pulled and hash-checked at 02:08Z and is quarantined on the VPS in `invalid_runs/2026-10-14_round2_probes/` (REQ-004 condition 1).
- Host logs, pulled to `logs/host_55843268/` at 02:09Z. At 03:16Z no file under results/, logs/ or data/ on the host was newer than that pull.
- Code, corpora and probes: copies of the VPS files.
- Nothing on it is needed.
**Human command:**
- On the Vast website: DESTROY on CG4-run2 (55843268).
- Or in this chat: `! "/c/Users/Administrator/Desktop/Terminal gaps/.venv/Scripts/vastai.exe" destroy instance 55843268 -y`.
- Check the instance number: 55878879 (CG4-run3) must stay.
**Human reply:** Done. The first author deleted instance 55843268 and wrote in chat on 2026-10-14: "I have deleted it, please check." The agent checked at 2026-10-14T06:44:40Z: `vastai show instances` lists only 55878879 (CG4-run3, running) and `vastai show volumes` is empty. Recorded by the agent.

## REQ-015 | 2026-10-14T07:27:30+00:00 | GATE | Status: DONE
**Ask:** G2, generation 0, with the final numbers. This is the REQ-004 re-run on the final G1 probe files: job gen0d on instance 55878879, 06:40–07:22Z.
- Please judge the three G2 criteria below and reply "G2 passed", or say what should happen instead.
- After G2 comes the pilot (G3): one REPLACE step per language, about 1 GPU-hour. You then read 50 samples per language.
**Evidence:** `results/metrics.jsonl` and `results/chains/*/step.json`, pulled to the VPS at 07:23Z. Both checkpoints match their recorded SHA-256, and nothing on the host is newer than the pull.
1. **Generation 0 improves on the base model.** Primary measure: held-out log-perplexity, document-macro; lower is better.
   - EN 2.776 → 2.693.
   - BN 3.562 → 2.998.
   - Secondary measures: Bangla improves on all of them. In English these get slightly worse, as in both earlier runs: token-micro 2.749 → 2.767, bits per byte 0.879 → 0.885, fresh slice 2.614 → 2.698. The REQ-008 note explains it: FineWeb-Edu held-out documents get worse and Wikipedia documents better.
2. **Recall is above chance (0.25) in every stratum.** Generation 0, with Wilson 95% intervals:

   | Language | HEAD | MID | TAIL |
   |---|---|---|---|
   | EN | 0.495 [0.427, 0.564] | 0.580 [0.511, 0.646] | 0.595 [0.526, 0.661] |
   | BN | 0.515 [0.446, 0.583] | 0.380 [0.316, 0.449] | 0.425 [0.359, 0.494] |

   - The base model's recall (HEAD / MID / TAIL): EN 0.500 / 0.560 / 0.630; BN 0.515 / 0.330 / 0.370.
   - In English, TAIL recall is not below HEAD. That has been so in all three runs.
3. **Samples:** 2,000 documents per language.

   | | EN | BN | limit |
   |---|---|---|---|
   | Documents at least 95% in the right script | 98.1% | 98.6% | — |
   | 4-gram repetition | 0.004 | 0.003 | 0.2 |
   | Exact duplicates | 0% | 0% | 5% |
   | Empty documents | 0.05% | 0.10% | 5% |

- **Training:** 154 optimizer steps on 10.0 M seed tokens per language, no NaN. Loss: EN 2.973 → 2.838; BN 4.085 → 3.305.
- **Reproducibility:** the base metrics are identical to the discarded round-2 run, and generation 0 is within 0.001 of it on a different host.
- **Environment:**
  - `logs/host_55878879/environment.json`.
  - Model manifest `results/chains/manifest.json`: google/gemma-3-270m, revision 9b0cfec…, Gemma Terms of Use; torch 2.13.0+cu130, transformers 5.17.0, vllm 0.31.0.
- **Discarded runs:** `invalid_runs/2026-10-14_round1_probes/` and `invalid_runs/2026-10-14_round2_probes/`.
**Human reply:** "G2 passed" (chat, 2026-10-14, after the agent's 07:28 UTC message with the numbers above; recorded by the agent). All three registered criteria are met on the final run, so G2 is PASSED. Next: the pilot (G3).

## REQ-016 | 2026-10-14T08:30:37+00:00 | GATE | Status: DONE
**Ask:** G3, the pilot. Please do three things, then reply in chat:
1. Read the 50 generation-1 samples per language in `results/human_read/G3_pilot_read_2026-10-14.html`. It is a local file inside `results/`; do not share it. Say whether the text matches the numbers, and paste the sheet's "Copy reply".
2. Confirm the duplicate and empty checks below.
3. Decide the budget (REQ-017). It sets how many robustness phases run.
G3 passes when you have read the samples, the metrics match the text, the duplicate and empty rates are at most 5%, and the schedule fits the approved cap.
**Evidence:** `results/metrics.jsonl`, `results/chains/{EN,BN}-REPLACE/gen_1/step.json`, `logs/host_55878879/` (pilot.log, throughput.csv). Everything was pulled to the VPS at 08:17Z, and all four checkpoints match their SHA-256.
- **Pilot:** one REPLACE step per language on instance 55878879, 07:29–08:16Z (job `pilot`). EN took 22.7 min, BN 23.3 min.
  - Each step generates 10 M tokens with generation 0, trains generation 1 on them alone (prefixes masked, no real text), and then samples and scores.
- **Training text written by generation 0:**

  | | EN | BN |
  |---|---|---|
  | Documents | 44,544 | 37,888 |
  | Tokens | 10.06 M | 10.04 M |
  | Exact duplicates | 0.02% | 0.21% |
  | Empty | 0.03% | 0.05% |
  | Cut at the length cap | 72% | 56% |

  Duplicate and empty limits are 5% each.
- **Training:** 166 optimizer steps per language, no NaN. Logged loss: EN 3.657 → 3.650, BN 4.218 → 4.083.
- **Generation 0 → generation 1** (2,000-document samples; Wilson or bootstrap 95% intervals in `metrics.jsonl`):

  | | EN | BN |
  |---|---|---|
  | Held-out log-perplexity | 2.693 → 3.542 [3.495, 3.583] | 2.998 → 3.110 [3.062, 3.154] |
  | Bits per byte | 0.885 → 1.270 | 0.471 → 0.491 |
  | Fresh slice | 2.698 → 3.467 | 3.180 → 3.292 |
  | Recall, all | 0.557 → 0.560 | 0.440 → 0.442 |
  | Recall HEAD / MID / TAIL | 0.495 / 0.580 / 0.595 → 0.530 / 0.585 / 0.565 | 0.515 / 0.380 / 0.425 → 0.540 / 0.380 / 0.405 |
  | Right script | 98.1% → 97.1% | 98.6% → 98.2% |
  | 4-gram repetition | 0.004 → 0.004 | 0.003 → 0.004 |
  | Distinct-2 | 0.774 → 0.780 | 0.893 → 0.901 |
  | Mean length (words) | 165.7 → 160.6 | 150.1 → 146.2 |
  | Cut at the cap | 0.71 → 0.54 | 0.56 → 0.24 |
  | Sample duplicates / empty | 0% / 0% | 0% / 0% |

- **Bug check of the English held-out change, before reporting it** (agent; `harness/tools/drift_check.py`, logs/drift_*.txt on the host):
  - Every tokenizer adds `<bos>` first.
  - Re-scoring 200 held-out documents through a fresh load reproduces the stored means to within 0.0002.
  - On those documents, generation 1 fits the generated training text better than generation 0 did (EN 3.525 → 3.329, BN 3.960 → 3.881 nats per token), as training on it should. It fits real text worse (EN 2.415 → 3.186, BN 2.396 → 2.503).
  - Parameter change gen 0 → gen 1: EN 0.30%, BN 0.14% (relative L2).
  - So the numbers come from the trained models, not from the pipeline. The agent does not interpret them.
- **Measured budget:** see REQ-017.
**Human reply:** The authors' pilot read was received in chat on 2026-10-14, about 09:10Z. It is verbatim in `signoffs/G3_pilot_read_reply_2026-10-14.txt`.
- English: the text matches the numbers, "yes, broadly", with 13 of 50 rows flagged.
- Bangla: "yes, broadly", with 3 of 50 rows flagged.
- Flagged defects: letters from other writing systems inside the text, runs of one character (22 emoji, 648 commas) and short unfinished stubs.
- The authors note: "Screening gaps remain. This reading does not validate the recall, corpus rates or stopping statistics."
- No G3 verdict yet. The REQ-017 budget decision is open.
- The agent is checking the flagged defect classes before G3 can pass (`logs/decisions.md`). Recorded by the agent.
- Superseded on 2026-10-14: the read led to a real bug, `<eos>` training targets after cut documents (`results/deviations.md`). Generation 0 and the pilot were re-run with the fix, and G3 is asked again in REQ-018 with a new sheet.

## REQ-017 | 2026-10-14T08:30:37+00:00 | BUDGET | Status: DONE
**Ask:** Raise the CG4 cap to cover every pre-registered phase. Recommended: **`--budget-usd 40 --max-hours 85`** for CG4 in total; cap B is US$30 / 70 GPU-h. Reply "approve", or name another cap. If you approve, please load at least US$10 more onto the Vast.ai account.
**Why:** the authors said in chat on 2026-10-14 that they will raise the budget if it makes the paper stronger, and that nothing required should be dropped for budget reasons. Cap B was set on pre-pilot estimates at US$0.40/GPU-h; the measured price is US$0.456/h.
**Evidence:** `plan_budget.py --measured --price-usd-h 0.456` on the host, using rates measured in the pilot (`logs/host_55878879/throughput.csv`): generation 0.13 h, training 0.18 h, sample 0.01 h, metrics 0.06 h per step.
- **Spent so far:** US$5.42 (Vast credit US$24.58 at 08:29Z), 7.9 GPU-h.
- **The full design (P0–P7):** 57.6 GPU-h, of which about 1.4 h is done. That leaves 56.2 GPU-h (US$25.6), or 70.3 GPU-h with the pre-registered ×1.25 margin (US$32.0).
  - CG4 in total: about **US$37.4 and 78 GPU-h**.
  - US$40 / 85 h leaves about US$2.6 for idle time between stages and price changes.
- **Cap B covers, with the margin:** the confirmatory chains (P1), the second seed, the word-matched English control (P2), the no-synthetic control (P3) and REPLACE to generation 10 (P4).
  - Not with the margin: the third seed (P5), ACCUMULATE-SUBSAMPLE (P6) and top-p 0.95 (P7). P5 and P6 fit only if no margin is used; P7 does not fit.
  - Under the pre-registered stopping rule, phases that do not fit are reported as not run.
- **Time:** about 3 days of GPU time on one GPU (the chains run one after another), plus the authors' reading at G5.
- **Programme cap:** US$125 for CG4, CG1 and CG2. CG4 at US$40 leaves US$85 for CG1 and CG2, against US$95 under cap B.
- **Vast credit:** the account holds US$24.58. The new cap needs about US$34.6 more spending room, so load at least US$10. The agent never spends past the approved cap.
**Human reply:** "I also approve your previous 10$ extra budget request." (chat, 2026-10-14). Approved: CG4 cap US$40 / 85 GPU-h in total, with every pre-registered phase P0–P7 inside it under the measured ladder. The same message said that US$1,200 was deposited on the Vast account by mistake at 08:58:59Z (US$20 was meant) and will be refunded once the current instance is deleted. The cap, not the credit, bounds spending. Recorded by the agent.

## REQ-018 | 2026-10-14T11:05:26+00:00 | GATE | Status: DONE
**Ask:** Two things, after the bug that your pilot read uncovered was fixed. Reply in chat to both:
1. **G2:** generation 0 was retrained with the fix. Its numbers barely changed (below). Reply "G2 still passed", or say what should happen instead.
2. **G3:** read the corrected pilot in `results/human_read/G3_pilot_read_corrected_2026-10-14.html`, then paste its "Copy reply". It is local only, so do not share it. The new numbers and samples come from the re-run; your earlier ticks do not carry over. If the text matches the numbers and the rest below is fine, reply "G3 passed" with the sheet text.
**The bug, in short:**
- Training put the end-of-document token as a target after every document, also where a text had only been cut at the length limit (EN 73%, BN 60% of the generation-1 training text) or by the corpus builder at 1,024 tokens.
- REPLACE generation 1 therefore learned to stop texts early. On real English text beyond 277 tokens it put 72.8% of its probability on end-of-document.
- Fixed in `harness/run_chain.py` `pack()`, with a check in `test_sanity.py`, and recorded in `results/deviations.md`. It is a bug fix: the registered loss covers generated tokens only.
- After the fix, the end-of-document mass beyond that length is 0.14% (EN) and 0.15% (BN), the same as the base model.
- The earlier results are in `invalid_runs/2026-10-14_eos_targets/`.
**Evidence for G2** (generation 0 retrained 09:31–09:58Z on instance 55878879; `results/metrics.jsonl`; the earlier value in brackets):
- **Held-out log-perplexity, base → generation 0:** EN 2.776 → 2.693 (2.693); BN 3.562 → 3.003 (2.998).
  - Secondary measures: BN improves on all of them. In English, token-micro (2.767), bits per byte (0.885) and the fresh slice (2.698) are slightly worse than the base model, as before.
- **Recall, generation 0** (Wilson 95%; chance 0.25):

  | Language | HEAD | MID | TAIL |
  |---|---|---|---|
  | EN | 0.500 [0.431, 0.569] | 0.570 [0.501, 0.637] | 0.580 [0.511, 0.646] |
  | BN | 0.530 [0.461, 0.598] | 0.360 [0.297, 0.429] | 0.405 [0.339, 0.474] |

  Every lower bound is above 0.25.
- **Samples (2,000 documents):**

  | | EN | BN |
  |---|---|---|
  | Right script | 98.4% | 98.3% |
  | 4-gram repetition | 0.006 | 0.003 |
  | Exact duplicates | 0% | 0% |
  | Empty | 0.05% | 0% |

- **Training:** 154 steps, no NaN. End-of-document targets after 13,261 of 17,509 EN and 17,719 of 20,912 BN documents; the others were cut.
**Evidence for G3** (corrected pilot, one REPLACE step per language, 09:58–10:43Z; EN 22.2 min, BN 22.7 min):
- **Training text written by generation 0:**

  | | EN | BN |
  |---|---|---|
  | Documents | 44,544 | 36,864 |
  | Tokens | 10.08 M | 10.08 M |
  | Exact duplicates | 0.02% | 0.07% |
  | Empty | 0.03% | 0.04% |
  | Cut at the length cap | 73% | 60% |

  Duplicate and empty limits are 5% each.
- **Generation 0 → generation 1:**

  | | EN | BN |
  |---|---|---|
  | Held-out log-perplexity | 2.693 → 2.831 [2.803, 2.858] | 3.003 → 3.084 [3.038, 3.128] |
  | Bits per byte | 0.885 → 0.930 | 0.472 → 0.483 |
  | Fresh slice | 2.698 → 2.844 | 3.189 → 3.241 |
  | Recall HEAD / MID / TAIL | 0.540 / 0.555 / 0.530 (all 0.542) | 0.505 / 0.375 / 0.430 (all 0.437) |
  | Right script | 98.4% → 98.1% | 98.3% → 96.9% |
  | Repetition | 0.006 → 0.004 | 0.003 → 0.003 |
  | Mean length (words) | 167 → 169 | 159 → 154 |
  | Sample duplicates / empty | 0% / 0% | 0% / 0.05% |

  Before the fix, the English held-out log-perplexity read 3.542.
- **Checks** (agent; `harness/tools/`):
  - Every tokenizer adds `<bos>`.
  - Re-scoring reproduces the stored values.
  - vLLM and the HF scorer agree on sampled tokens: EN within 0.002 in mean log-probability for base, gen 0 and gen 1. BN shows a gap of 0.035 for base and gen 0 and 0.002 for gen 1 (about 1% per token).
- **Budget:** the measured ladder is unchanged. Everything (P0–P7) is 57.6 GPU-h, about 56 h of it still to run.
  - Spent US$6.70 (invoices, 11:04Z). The projection including the final download is about US$37–38, inside the US$40 ceiling.
  - The full run gets `--max-hours` = (40 − spend − 6) / 0.456 (runbook §5). If anything runs slower, P7 and then P6 are the first to be reported as not run.
- **Screening measures** for the defects you flagged: see REQ-019.
**Human reply:**
- Part 1 (G2): "G2 still passed" (chat, 2026-10-14T11:10:50Z). G2 stays PASSED on the generation-0 numbers retrained after the fix.
- Part 2 (G3, the corrected pilot read): received in chat, about 11:15Z (arrival in the session log: 2026-10-14T11:30:11Z). It is verbatim in `signoffs/G3_pilot_read_corrected_reply_2026-10-14.txt`.
  - English: text matches the numbers, "yes, broadly" ("compatible with the modest log-perplexity rise 2.693 to 2.831"), with 8 of 50 rows flagged.
  - Bangla: "yes, broadly", with 2 of 50 rows flagged.
  - The authors wrote: "Script/character findings need inspection; this read does not verify the fix or metric calculations."
  - No "G3 passed" yet.
  - The agent's inspection of every flagged item is in the same file:
    - the repetition limit applies to the sample mean (0.006);
    - private-use characters, mojibake (inherited from the web source; the decoding is correct) and other-script fragments are measured and proposed as screening measures in REQ-019.
  - "G3 passed" (chat, 2026-10-14T11:37:32Z). So G3 is PASSED. REQ-019 (screening measures) is answered separately. Recorded by the agent.

## REQ-019 | 2026-10-14T11:05:26+00:00 | DECISION | Status: DONE
**Ask:** Add four screening measures for the defects flagged in the G3 read. They are exploratory and reported next to the registered measures; they change neither the training nor any registered measure. Reply "approve", or change any item.
1. Share of documents with a letter outside the target script (EN: not Latin; BN: neither Bengali nor Latin), and with a run of at least 3 such letters.
2. BN: share of documents with Latin letters (the rubric's "English intrusion").
3. Share of documents with a run of at least 10 identical characters (the 648 commas, the 22 emoji).
4. Share of stubs: fewer than 20 words where the model ended the text itself.
**How:** `harness/tools/screening_check.py` runs over every generation's 2,000-document sample and every training text written by a model. Held-out real text and the base model are the references. Every pull reports it, and the analysis tables include it. In `metrics.jsonl` it carries a `screen_` prefix; the frozen metric schema allows new names.
**Current values** (share of documents; corrected run):

| Set | EN other script | EN run ≥ 3 | BN other script | BN Latin | Character runs | Stubs |
|---|---|---|---|---|---|---|
| Real held-out text | 3.0% | 1.9% | 2.5% | 16.1% | 0.05% | 0% |
| Base model | 3.1% | 1.6% | 86.5% | 82.6% | 0.4% / 0.7% | 0.6% / 1.0% |
| Generation 0 | 17.9% | 10.6% | 3.1% | 9.2% | 0% / 0.05% | 1.4% / 1.2% |
| Training text for gen 1 | 17.0% | 10.4% | 3.1% | 9.3% | 0.25% / 0.15% | 1.4% / 1.5% |
| Generation 1 | 28.0% | 17.7% | 4.9% | 16.3% | 0.25% / 0.1% | 1.3% / 2.6% |

Where a cell has two values, they are EN / BN.
- In English the other-script share rises at generation 0, which was trained on real text with the registered recipe, and again at generation 1.
- The agent checked it is not a pipeline fault: same sampling settings for every model, and vLLM matches the scorer. It is a measured property of the trained models and is not interpreted here.
**Evidence:** `signoffs/G3_pilot_read_reply_2026-10-14.txt` (your flags); `harness/tools/screening_check.py` output (`logs/decisions.md`, 2026-10-14).
**Addition after the corrected read** (2026-10-14T11:35:03Z): three more measures for the items flagged there, in the same tool and on the same terms:
5. Share of documents with private-use or replacement characters (EN-S05's U+F079).
6. Share with mojibake (EN-S37's "Nigelâ€™s" for "Nigel’s").
7. Share of documents whose own 4-gram repetition is at least 0.2 (EN-S03). The registered limit stays on the sample mean.

| Set | Private-use EN / BN | Mojibake EN / BN | Doc repetition ≥ 0.2 EN / BN |
|---|---|---|---|
| Real held-out text | 0% / 0% | 0.05% / 0% | 0.45% / 1.6% |
| Base model | 0.15% / 0.3% | 0.25% / 0% | 0.65% / 3.75% |
| Generation 0 | 0.15% / 0% | 0.20% / 0% | 0.35% / 0.3% |
| Training text for gen 1 | 0.20% / 0.02% | 0.12% / 0.01% | 0.11% / 0.62% |
| Generation 1 | 0.40% / 0% | 0.25% / 0% | 0.05% / 0.5% |

- Mojibake in the real EN seed corpus is 0.11%, all from the FineWeb-Edu slice; Wikipedia has 0%. 64.9% of FineWeb-Edu documents carry correctly encoded quotes, dashes or accents, so the decoding is correct and the mojibake comes from the original pages.
**Human reply:** "approve" (chat, 2026-10-14, after the agent listed the seven measures). All seven are approved as exploratory measures.
- They are computed by `harness/tools/screening_check.py --all` into `results/screening_metrics.jsonl`, not into `metrics.jsonl`, so they never collide with the run writing that file. They use the same row schema and a `screen_` prefix, with Wilson 95% intervals.
- Recorded in `results/deviations.md` and `07_ANALYSIS_PLAN.md` §5b. Recorded by the agent.

## REQ-020 | 2026-10-14T17:29:28+00:00 | BUDGET | Status: DONE
**Ask:** (Raised by the authors in chat; recorded by the agent.) Raise the CG4 hard ceiling from US$40 to US$50, so that every pre-registered phase, P7 included, finishes with a safe margin. The ACCUMULATE steps run about 6% slower than the measured plan.
**Evidence:**
- Spend US$9.62 at 2026-10-14T17:29Z (invoices, `vast_ops.py status`).
- The measured ladder for P0–P7 is 57.6 GPU-h; at today's pace about 57–59 h are still needed against the US$40 run deadline of 59.3 h (logs/decisions.md, 17:08Z).
- Under US$40 the projection was about US$38.5–39.5 including the final download.
**Human reply:** "You can increase the celling to 50$, I want to be safe there. I did planned 50$ for this project." (chat, 2026-10-14).
- **Approved: CG4 hard ceiling US$50 in total, including the final pack and download**, and 100 GPU-h.
- The running job keeps its deadline (2026-10-16 22:56Z). If work remains at that point, the agent re-runs the same command, which resumes from cached stages, with `--max-hours = (50 − spend − 6) / price`.
- Programme cap: CG4 at US$50 leaves US$75 of the US$125 for CG1 and CG2.

## REQ-021 | 2026-10-16T23:33:20+00:00 | GATE | Status: DONE
**Ask:** G4 (chains complete): the full run has ended, and the evidence is in `signoffs/G4_chains.md`. Please read it (summary below), then reply in chat:
1. **"G4 passed"** if you agree that every step is complete and the checks pass;
2. or say what looks wrong. G4 then stays OPEN and the agent investigates.

The registered rule (`08_GATES_AND_CHECKLISTS.md`, G4): "All confirmatory steps complete or documented; composition, duplicate, leakage and schema checks pass."
**Evidence:**
- **Complete:** 110 of 110 planned generation steps (17 chains × 6 generations, plus REPLACE generations 7–10 in both languages), 7 generation-0 models and 2 base-model evaluations. Every phase P1–P7 ran; none was dropped. Job `chains` on instance 55878879 ran 2026-10-14T11:38Z – 2026-10-16T23:05Z, and all 24 jobs ended `rc=0` (`logs/host_55878879/chains.log`, `logs/host_55878879/run_chain_status_G4.txt`).
- **Checks:** `test_sanity.py --results` RESULT: PASS, 1,100 checks ok, 0 failed (`logs/host_55878879/test_sanity_results_G4.txt`). `run_qa.py`: 119 steps, 0 anomalies (`logs/host_55878879/qa_G4.txt`). Lineage check: 110 steps, 0 violations. `results/metrics.jsonl`: 5,228 records, 0 schema violations, no NaN.
- **Leakage:** no held-out id in any synthetic corpus (110 of 110 chain steps); every chain trains only from its own previous generation.
- **Pre-registration:** `01_PREREGISTRATION.md`, `configs/chains.yaml` and the three schemas match the freeze record; `configs/corpora.yaml` differs only by the recorded REQ-009 deviation. The run added no deviation.
- **For your judgement (reported, not interpreted):**
  - the distinct-2 and length table for the six confirmatory chains, in `signoffs/G4_chains.md`;
  - a flag on the top-p 0.95 pair: its share of highly repetitive sampled documents (own 4-gram repetition ≥ 0.5) rises steadily to 0.110 (EN) and 0.141 (BN) at generation 6, against at most 0.0115 in every other REPLACE chain. Both chains sampled with top-p 0.95 as registered, and no NaN, empty-output or script problem goes with it. Their 50-sample files are `results/samples/EN-REPLACE-topp95_gen6_50.jsonl` and `results/samples/BN-REPLACE-topp95_gen6_50.jsonl` (on the VPS only; unscreened text, do not share).
  - a second flag, from the exploratory screening measures (REQ-019): under REPLACE, the share of sampled documents with letters of another script rises every generation. EN-REPLACE: 0.178 at generation 0, 0.541 at generation 6, 0.653 at generation 10. BN-REPLACE, Latin letters: 0.091, 0.312, 0.397. The ACCUMULATE chains stay roughly flat and the FILTER chains are lower. The registered script measure stays at 0.897 or above, and no sample has broken characters (`results/screening_metrics.jsonl`; details in `signoffs/G4_chains.md`).
- **Spend:** US$34.32 at 2026-10-16T23:30Z (Vast invoices), against the US$50 hard ceiling (REQ-020).

**Reading sheet (asked for by the authors):** `results/human_read/G4_read_2026-10-17.html` shows the text behind both flags: 10 samples each for English and Bangla, generation 0 next to generation 6, with the counted letters highlighted. Its "Copy reply" ends with the G4 verdict. Local only (unscreened text); made by `harness/make_g4_sheet.py`.
**Not part of this request:** G4b (archive download and verification, your external-drive backup, then the teardown) is filed separately once the download is verified. The instance keeps running until then.
**Human reply:** "G4 passed" (chat, 2026-10-17T00:11Z; the reply arrived 00:09:52Z), after reading all 40 pairs of `results/human_read/G4_read_2026-10-17.html`; the full reply is in `signoffs/G4_read_reply_2026-10-17.txt`. In short:
- A (English other-script letters): mostly words or fragments of other scripts inserted into English, often fused with Latin text; recognizable script characters, not replacement-character corruption. No technical fault.
- B (Bangla Latin letters): mostly unrelated Latin fragments, invented strings or stray letters (exceptions: B06 the connector 'and'; B09's two counted Latin letters are the n of literal backslash-n; B05 one stray letter). The text is partly readable Bangla (B04, B07, B09, B10 particularly fragmented). No technical fault.
- C (English top-p 0.95): readable sentences, list items or names that loop; C08 ends in about 110 vertical bars. No technical fault.
- D (Bangla top-p 0.95): loops of intact Bangla words, place names and sentence templates; partly readable (D02, D07 almost only loops). No technical fault.
- Caveats named by the authors: B09's literal backslash-n and stray symbol, C08's delimiter loop, D05's generation-0 literal backslash-n ("source-check caveats, not proven software failures").

**Agent's source check of the caveats** (2026-10-17T00:10Z):
- Literal backslash-n (the two characters) is in the real Bangla seed text: 146 of 20,913 documents (1,421 times). 145 of them come from the source `bn_web_slice` (1.4% of its documents), 1 from `bnwiki_articles`. English seed: 3 of 17,509 documents. Generation 0 learned it from the real text; the harness does not produce it.
- The C08 loop is the ASCII bar followed by a space, 109 times, until the length cap (`finish: length`). Runs of 5 or more spaced bars occur in 3 English and 1 Bangla seed documents (table formatting). Neither repetition measure sees such a loop: `words()` drops the bar, and `screen_char_run10` needs an unbroken run. C08's own 4-gram repetition (0.455) comes from its words.
- Neither is a software fault. Both are recorded for the data statement and the limitations; no deviation.

Recorded by the agent; `signoffs/G4_chains.md` is PASSED.

## REQ-022 | 2026-10-17T02:25:30+00:00 | GATE | Status: DONE
**Ask:** G4b (teardown): the archive is downloaded to the VPS and verified. Two steps for the authors, in order:
1. **Make the second copy** on your external drive, then reply in chat with where it is (for example "copied to drive E:, folder CG4_backup"):
   - copy `CG4_model_collapse_lowresource_experiment\results\packs\cg4_pack_20261016-232223.tar.gz` (55.69 GB) and `pack_manifest_20261016-232223.json` from the same folder, as they are. Copy, do not move: the VPS copy is the first of the two copies;
   - add a zip of the rest of the folder `Terminal gaps` (about 12 GB), without `.env` (your keys) and without `CG4_model_collapse_lowresource_experiment\results\packs` (already covered above);
   - optional check: the copied archive's SHA-256 (PowerShell `Get-FileHash -Algorithm SHA256 <file>`, several minutes) must be `f51a5dcbd919ab99392c1ec4921a3e479c53081dedd746d675bfafa68d429a1d`.
2. The agent then files the TEARDOWN request with the exact command. You delete instance 55878879 and check in the Vast.ai console that no instance or volume remains; G4b then passes. After that you can ask Vast.ai to refund the mistaken US$1,200 deposit.

The registered rule (`08_GATES_AND_CHECKLISTS.md`, G4b): "VERIFY: OK locally; analysis reproduces; two copies exist; only then may the instance be deleted".
**Evidence:** `signoffs/G4b_teardown.md` items 1–5:
- archive `cg4_pack_20261016-232223.tar.gz`: 2,109 files, 78.11 GB uncompressed, 55.69 GB; every checkpoint (117) and every synthetic corpus (132 files);
- SHA-256 identical on the host and the VPS (`f51a5dcb…29a1d`); `pack_results.py --verify`: VERIFY: OK (0 missing, 0 corrupt);
- analysis regenerated from the downloaded copy alone: `analyze.py --robustness` exit 0, 44 files (results not read; that is G6).

Everything from the host is on the VPS, including the two MinHash files ("copy them"). The instance is stopped since 2026-10-17T02:23:42Z; its disk costs about US$0.056/h (US$1.34 a day) until it is deleted. Spend US$37.85 at 2026-10-17T02:24Z (Vast invoices), against the US$50 hard ceiling.
**Human reply:** "Google Drive, folder CG4_backup, all four files, sizes match, private." (chat, 2026-10-17T06:43Z), after "all done backup". The second copy is the four files of `results/packs/` in the authors' private Google Drive folder CG4_backup (11_TEARDOWN_CHECKLIST.md section 6 allows a cloud drive). Recorded in `signoffs/G4b_teardown.md` item 6. The TEARDOWN request follows as REQ-023; G4b passes once the instance is deleted (item 7).

## REQ-023 | 2026-10-17T06:43:37+00:00 | TEARDOWN | Status: DONE
**Ask:** destroy Vast.ai instance 55878879 (label CG4-run3, RTX 4090, 0.456 $/h, 68.0 h so far, about US$30.96).
**Evidence:** archive `cg4_pack_20261016-232223.tar.gz` SHA-256 `f51a5dcbd919ab99392c1ec4921a3e479c53081dedd746d675bfafa68d429a1d`; local `pack_results.py --verify` printed VERIFY: OK on 2026-10-17; second copy at `Google Drive, folder CG4_backup (the authors' private account; all four files of results/packs, sizes checked by the authors on 2026-10-17)`; analysis regenerated from the downloaded copy: yes (analyze.py --robustness from the downloaded copy, exit 0, 2026-10-17).
**Human command (only after signoffs/G4b_teardown.md is filled):**  `vastai destroy instance 55878879`  then confirm in the Vast console that no volumes remain.
**Human reply:** destroyed by the authors on 2026-10-17 with `vastai destroy instance 55878879 -y` in the Claude Code `!` shell (output: "destroying instance 55878879."). Confirmed by the agent at 2026-10-17T07:15:17Z: `vastai show instances` lists 0 instances, `vastai show volumes` lists none, and `vast_ops.py status` says "no instances". Final CG4 spend US$38.12 (Vast invoices, all three instances). Recorded in `logs/vast_instances.jsonl` and `signoffs/G4b_teardown.md` item 7.

## REQ-024 | 2026-10-17T07:16:46+00:00 | GATE | Status: DONE
**Ask:** G5 (human read): code generations 3 and 6 of the six confirmatory chains with the pre-specified rubric (`06_HUMAN_TASKS.md`), on the reading sheets in `results/human_read/` (start page `G5_index_2026-10-17.html`).
1. Split the six chain pages between you (for example three each); about 2–3 hours per page (100 samples: 50 prompts × generations 3 and 6).
2. On each page: enter your name; for each sample fill in the nonword count (this marks it coded) and tick script error, English intrusion (Bangla pages), repetition loop and topic drift where they apply. Notes are optional.
3. Press **Copy reply** and paste it into the chat, one page at a time. The agent writes `results/human_read/<chain>_gen<g>.csv` with the sample file hashes, counts the codes per chain and generation, and puts them next to the automatic measures. Any mismatch between the numbers and the text is investigated.
4. Optional: the fluency rating (1–5) by both of you on the 20 marked prompts of every page and on the two generation-0 pages, so that agreement can be reported.
5. When all six pages are in, reply **"G5 passed"**, or say what is wrong.

The registered rule (`08_GATES_AND_CHECKLISTS.md`, G5): "Both authors have read and recorded the rubric; any metric–text mismatch investigated."
**Evidence:** the 12 sample files `results/samples/<chain>_gen{3,6}_50.jsonl` (SHA-256 on the index page); sheets made by `harness/make_g5_sheets.py` (no automatic numbers or highlighting on the pages, so the coding is independent of the measures; a sample counts as coded only when its nonword count is filled in, and uncoded samples are recorded blank, never as 0).
**Human reply:** "Okay keep it in short form and G5 passed." (chat, 2026-10-18T00:13Z). G5 PASSED (`signoffs/G5_human_read.md`). Checked against the registered rule before recording: both authors read and recorded the rubric (12 files: six chains × generations 3 and 6, 50 of 50 coded each; Md Tahidul Islam BN-ACCUMULATE, BN-REPLACE, EN-ACCUMULATE-FILTER; Maksuda Akter BN-ACCUMULATE-FILTER, EN-ACCUMULATE, EN-REPLACE), and every metric–text mismatch was investigated (`results/human_read/G5_checks/*_mismatch_notes.md`). On the way: rules R1 and R2 and corrections (a)–(c) (authors, 2026-10-17T23:38Z; the three corrections recorded 2026-10-17T23:48Z and 2026-10-18T00:06Z). Optional item 4 done: all ten fluency pages. "Short form" = the paper reports the agreement without the GEN0-EN pair (quadratic-weighted kappa 0.813 [0.761, 0.854], 259 pairs; `results/human_read/G5_checks/fluency_agreement.md`), with one sentence on the exclusion. Carried to G6: where the `<unusedNNNN>` strings enter (the open checklist item in the sign-off).

## REQ-025 | 2026-10-18T00:26:48+00:00 | DECISION | Status: DONE
**Ask:** G6 (analysis): how H0, the anchor, is decided. Please decide before anyone reads the H0 numbers. Nobody has: the analysis written during the G4b check stays unread, and the corrected analysis runs only after this reply. Reply in chat with one of:
1. **"H0 option A"** (recommended): decided on the point estimates, as the registration words it. On log held-out perplexity and log(distinct-2 / generation-0 distinct-2) of the seed-0 chains over generations 0–6, H0 passes if the EN-REPLACE perplexity slope is above 0 and its distinct-2 slope below 0, and for both metrics |EN-ACCUMULATE slope| ≤ 0.5 × |EN-REPLACE slope| (magnitudes, as registered); otherwise it fails. Reported with it: each slope's 95% measurement CI, the 95% CI of each ratio (paired parametric bootstrap, 1,000 draws), a flag on any CI that crosses 0 or 0.5, and the slope signs of the EN-REPLACE seed replicates (descriptive).
2. **"H0 option B"** (strict): passes only if the CIs clear the thresholds: both EN-REPLACE slope CIs exclude 0 in the published direction, and both ratio CIs lie at or below 0.5. Fails otherwise.

Why A is recommended: it is the registered wording; the measurement CIs leave out run-to-run variance (`07_ANALYSIS_PLAN.md` §3), so they are a weak basis for a hard gate; under B, a ratio CI that straddles 0.5 would fail the anchor and, by the registered rule, stop the interpretation of every other hypothesis.
**Evidence:**
- Registered (`01_PREREGISTRATION.md`, H0): "EN-REPLACE shows rising held-out perplexity and falling distinct-2 across generations, and EN-ACCUMULATE's slopes are at least 50% smaller in magnitude. If the anchor fails, the pipeline is suspect and no other hypothesis is interpreted." The registration gives H1 and H2 an explicit decision rule (Holm-adjusted bootstrap p < 0.05 and, where seed replicates exist, the same sign in every seed) but none for H0. `07_ANALYSIS_PLAN.md` §3 says "pass/fail with CIs" without saying whether the CIs decide.
- `harness/analyze.py` lines 160–163: the H0 slopes are computed without the bootstrap (no CIs); the EN-ACCUMULATE slope is written into the `lo` column; H0 rows are produced for every analysed metric, not only the two registered ones. The agent fixes this whichever option is chosen.
- For information (no decision needed): `harness/analyze.py` does not yet carry out the registered analysis in full. The agent fixes it before anyone reads a result, and logs each fix and lists it in `results/deviations.md` as an implementation fix:
  1. the "main" analysis uses raw distinct-2 and recall; the registered H1 uses log(distinct-2 ratio) and log(recall ratio), and raw slopes are robustness item (i);
  2. H2 is computed as the absolute difference of the slope differences; the registered H2 is the ratio Δ_L = (slope_REPLACE − slope_ACCUMULATE) / |slope_REPLACE|, with the absolute difference as secondary;
  3. not yet in the code: the H1 decision table (Holm-adjusted p with the bits-per-byte direction check for H1(i) and the per-seed signs, which today come only from raw metrics in the all-chains table); the chance-level exclusion for H1(iii); the generation-6 endpoint contrast and the quadratic check; robustness (v) MTLD and character-5-gram, (vii) base-tokenizer metrics, (viii) n-gram novelty and duplicate rates of every synthetic corpus, (ix) semantic diversity; the control comparisons of §4; table T3, figures F2–F4 and F6; the screening-measure tables.
  (viii) runs on the VPS from the archive (CPU). (ix) needs a multilingual sentence-embedding model and comes as a separate request.
**Human reply:** "H0 option A" (chat, 2026-10-18T00:29Z). Decided before any H0 number was read: H0 is judged on the point estimates, as registered. On log held-out perplexity and log(distinct-2 / generation-0 distinct-2) of the seed-0 chains over generations 0–6, H0 passes if the EN-REPLACE perplexity slope is above 0 and its distinct-2 slope below 0, and for both metrics |EN-ACCUMULATE slope| ≤ 0.5 × |EN-REPLACE slope|; otherwise it fails. Reported with it: 95% measurement CIs of the slopes and the ratios (paired parametric bootstrap, 1,000 draws), a flag where a CI crosses 0 or 0.5, and the EN-REPLACE seed replicates' slope signs (descriptive). Recorded as a dated clarification of the H0 line in `07_ANALYSIS_PLAN.md` §3; it applies the registered wording, so no deviation line.

## REQ-026 | 2026-10-18T05:50:53+00:00 | DECISION | Status: DONE
**Ask:** G6, robustness item (ix). The registration names "a secondary semantic-diversity measure on the archived samples (multilingual sentence-embedding dispersion), computed after the run without training" but no model and no statistic. Please fix both before anything is computed. Reply in chat with one of:
1. **"ix as proposed"** (recommended): model `sentence-transformers/LaBSE` (language-agnostic sentence embeddings, 109 languages including Bengali; Apache-2.0). Input: the generated continuation of each of the 2,000 sample documents of every step (prefix excluded; the model's default maximum of 256 tokens). Statistic: dispersion = 1 − mean pairwise cosine similarity of the unit-normalised embeddings, with a 95% CI from a document bootstrap (300 resamples). Computed for all 119 steps on the VPS CPU (no cost; about 2–4 hours; installs PyTorch (CPU) and sentence-transformers into the project environment and downloads the model, about 2 GB). Reported as robustness (ix) next to distinct-2; never used for a test.
2. **"ix with <model>"**: the same with another model you name.
3. **"ix on a GPU"**: as 1, but on a short Vast.ai rental (about US$1 of the US$11.88 left under the US$50 ceiling; a BUDGET request would follow). `CLAUDE.md` asks for heavy work on a rented host; this job is small enough for the VPS, but it is your call.
**Evidence:** `01_PREREGISTRATION.md` (robustness list) and `07_ANALYSIS_PLAN.md` §5 (ix). The samples are in the G4b archive (`chains/*/sample.jsonl`, 119 files, 0.53 GB) and are being extracted into `results/g6_extract/`. H0 failed on the corrected analysis, so by the registered rule no hypothesis is interpreted; the registered robustness items are still computed and reported.
**Human reply:** "I will go with ix as proposed." (chat, 2026-10-18T05:52Z). Decided before anything was computed: model sentence-transformers/LaBSE; the generated continuation of each of the 2,000 sample documents of every step; dispersion = 1 - mean pairwise cosine similarity of the unit-normalised embeddings; 95% CI from a document bootstrap (300 resamples); on the VPS CPU. Recorded as a dated clarification of item (ix) in 07_ANALYSIS_PLAN.md section 5.

## REQ-027 | 2026-10-18T06:09:46+00:00 | DECISION | Status: DONE
**Ask:** G6, robustness items (vii) and (viii). Like (ix), the registration names them without the details, so please fix them before anything is computed. Reply **"vii and viii as proposed"**, or say what to change.
1. **(vii) "metrics with the base tokenizer instead of word splits (fertility-adjusted)"**, proposed: distinct-1 to distinct-4 and the type-token ratio recomputed on the Gemma-3 token ids of each continuation (base tokenizer, no special tokens) instead of words, in the same seeded document order as the word version. Fertility adjustment: the window is the number of tokens that carries the registered 50,000 words in that language, from the seed corpora's words per token in `data/corpora/manifest.json` (EN 50,000 / 0.7314 = 68,362 tokens; BN 50,000 / 0.5625 = 88,889 tokens). CI from 300 document permutations, as for the word version. Reported in T1/T2 and as H1/H2 contrasts on log(token distinct-2 / generation 0), robustness only.
2. **(viii) "n-gram novelty and exact/near-duplicate rates of every synthetic corpus against the seed"**, proposed for each of the 110 synthetic training corpora (the continuations; for the FILTER chains the kept documents) [correction 2026-10-18: 98 corpora, i.e. 86 generated corpora plus the kept documents of the 12 FILTER steps; the 12 REAL-REPEAT steps have no synthetic text]:
   - novelty_n: the share of the corpus's word n-gram occurrences (lower-cased, the registered word split) whose n-gram never occurs in the language's seed corpus, for n = 1, 2, 3 and 4;
   - near-duplicate rate: the share of documents that the pipeline's own near-duplicate test finds in the seed. This is the test the ACCUMULATE-FILTER rule used: MinHash over word 3-grams of the first 400 words, 64 permutations, banded LSH, estimated Jaccard ≥ 0.80, here against the stored seed signatures only;
   - exact-duplicate rate: the share of documents whose first 400 words (lower-cased) equal those of a seed document.

   Reported by chain and generation, descriptive (it also covers the registration's exploratory "n-gram novelty of each synthetic corpus against the seed"). Both items run on the VPS CPU, about 1–2 hours, at no cost.
**Evidence:** `07_ANALYSIS_PLAN.md` §5 (vii) and (viii); `01_PREREGISTRATION.md`, Exploratory. The near-duplicate test: `harness/run_chain.py` (filter stage) and `harness/common.py` (`minhash`, `NearDupIndex`). The files: `results/g6_extract/` (extracted 2026-10-18 from the G4b archive, every file SHA-256 checked against the pack manifest).
**Human reply:** "Yes, do it in the GPU.approve extra budget and vii and viii as proposed" (chat, 2026-10-18T06:56Z). Decided before anything was computed: (vii) and (viii) as proposed; recorded as dated clarifications of items (vii) and (viii) in `07_ANALYSIS_PLAN.md` §5.

## REQ-028 | 2026-10-18T06:59:31+00:00 | BUDGET | Status: DONE
**Ask:** (Proposed by the agent in chat, approved by the authors in chat; recorded by the agent.) Run robustness (ix) on a short Vast.ai GPU rental instead of the VPS CPU. The CPU run measured about 12 minutes per step, about 24 hours for the 119 steps, so the REQ-026 estimate of 2–4 hours was wrong. The agent's chat estimate for the GPU was about US$1. Hard cap set by the agent for this rental: **US$1.50 and 3.0 hours** (`--budget-usd 1.50 --max-hours 3.0`), within the US$50 CG4 ceiling (REQ-020); invoiced CG4 spend before the rental US$38.12, so at most US$39.62 after it.
**Evidence:**
- Offer 41890594: RTX 4090, US$0.448/h, reliability 0.996, United States. Offers in China were passed over because downloads from Hugging Face are unreliable there.
- Image `pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel` (the vast_ops default). Job: `harness/tools/semantic_dispersion.py --device cuda` on the 119 archived samples, LaBSE revision 836121a0533e5664b21c7aacc5d22951f2b8b25b, fp32 with TF32 off.
- The three steps already computed on the VPS CPU (BASE-BN, BASE-EN, GEN0-BN) are kept as a cross-check (`results/semantic_dispersion_cpu_partial.jsonl`).
- Money rules: `vast_ops.py status` at least every 2 hours while the instance exists; everything is pulled before the stop; then the agent stops the instance and files a TEARDOWN request, and the authors delete it.
**Human reply:** "Yes, do it in the GPU.approve extra budget and vii and viii as proposed" (chat, 2026-10-18T06:56Z): approved.

## REQ-029 | 2026-10-18T07:40:53+00:00 | TEARDOWN | Status: DONE
**Ask:** delete Vast.ai instance 56514363 (label CG4-ix, RTX 4090, US$0.448/h; REQ-028), which ran robustness (ix). It is stopped; its disk still bills a few cents a day until it is deleted. It also holds copies of the 119 unscreened sample files, made for this job, which go with it.
**Evidence:**
- Job finished: 119 steps at about 4 s each (`logs/ix_56514363.log`, pulled from the host).
- Results pulled: `results/semantic_dispersion.jsonl` (119 records, all with 2,000 documents, LaBSE revision 836121a0…). SHA-256 15b386c7f970cf35fa9fbed97ee0cee79a0791e08e3c717378f7513b6b2e406c, the same on the host and on the VPS; the log's SHA-256 1972d655caaf141618a50ecc0557e45f4b84376bdd949b035bafac84e2509a51, the same on both.
- Cross-check: the three steps also computed on the VPS CPU (`results/semantic_dispersion_cpu_partial.jsonl`) agree within 1.5e-7.
- Cost: US$0.39 invoiced for this instance (cap US$1.50); CG4 total US$38.51 of the US$50 ceiling.
- Nothing else on the host is needed: its code and samples are copies of files on the VPS.
**Human command:** `vastai destroy instance 56514363` (in the `!` shell: `"/c/Users/Administrator/Desktop/Terminal gaps/.venv/Scripts/vastai.exe" destroy instance 56514363 -y`), then confirm that no volumes remain.
**Human reply:** the authors ran `vastai destroy instance 56514363 -y` in the Claude Code `!` shell (chat, 2026-10-18T08:08Z; output "destroying instance 56514363."). Agent check at 2026-10-18T08:09Z: 0 instances and 0 volumes on the account. Invoiced CG4 total US$38.54 (this instance US$0.42).

## REQ-030 | 2026-10-18T08:59:32+00:00 | GATE | Status: DONE
**Ask:** G6 (analysis). Please read `results/analysis/analysis_report.md` (numbers only; figures F1–F8 beside it) and `results/analysis/audit/pipeline_audit.md`, then reply in chat:
1. **"G6 passed"** if you have both read the report and agree it is complete and reproducible. You then draft the interpretation; G7 writes it up.
2. Or say what is wrong or missing. G6 then stays OPEN.

The registered rule (`08_GATES_AND_CHECKLISTS.md`, G6): "Reproducible; robustness present; authors have read it."
**Evidence:**
- Reproducible: a clean copy of the code, with the inputs taken from the G4b archive, gives **17 of 17 tables and reports byte-identical** (`results/analysis/reproducibility_check.md`). The analysis code was rewritten to the registered analysis before any result was read and tested on synthetic data (31 checks, PASS; `results/deviations.md`).
- Robustness present: (i)–(vi) from the metric records; (vii) token-based diversity and (viii) novelty and duplicates against the seed (REQ-027); (ix) semantic dispersion (REQ-026, run on a GPU under REQ-028); the seed replicates and the registered controls (real-data retraining, word-matched English, compute-matched accumulation).
- **H0 failed** (REQ-025 option A; option B would also fail): EN-ACCUMULATE's perplexity slope is 0.605 of EN-REPLACE's (the rule needs at most 0.5), and EN-REPLACE's distinct-2 rises (+0.0062 per generation) where the registered direction is a fall. By the registered rule no other hypothesis is interpreted: H1 (rule output: inconclusive) and H2 (rule output: not supported) are reported as numbers only.
- Pipeline audit after the failed anchor: no fault. Sampling settings as registered (0 of 334 records differ); distinct-2 reproduced exactly for all 119 steps; placeholder tokens carried exactly by decoding and training; duplicate and empty rates within the limits; 1 of 4,021,761 synthetic training documents is a near-duplicate of a seed document.
- `results/deviations.md` complete; agent evidence and the failure-mode checklist in `signoffs/G6_analysis.md`. The box "design still answers the RQ" is left for the authors.
- What the paper says about the failed anchor, and whether and how it discusses the Bangla comparisons, is the authors' interpretation (G7).
**Human reply:** "G6 passed. Frame-lock: the anchor (H0) failed, so by our registered rule we report the study as a failed anchor and give H1 and H2 as numbers only." (chat, 2026-10-18T10:57Z), after "We have read both" (chat, 2026-10-18T10:56Z). G6 PASSED (`signoffs/G6_analysis.md`). Checked against the registered rule before recording: reproducible (17 of 17 byte-identical; H0, H1, H2 and the real-data control recomputed independently with numpy, identical), robustness present ((i)–(ix)), and both authors have read the report. Frame-lock statement recorded in the sign-off in the authors' words.

## REQ-032 | 2026-10-20T05:53:02+00:00 | BUDGET | Status: DONE
**Ask:** The authors' instruction in chat, recorded by the agent. Run the post-hoc pack that the authors' PC agent wrote, `posthoc_gpu_pack/`, on the VPS. It holds three audit items: #17 cross-decoder evaluation, #19 LaBSE dispersion sensitivity and #18 nonword/bigram analysis in full. All three are post-hoc and descriptive, and no registered number changes. Save the results in one folder for the authors to copy back to their PC. The pack's README states "Expected cost: under US$2.50". The agent set that as the hard cap for this rental: **US$2.50 and 4.0 hours** (`--budget-usd 2.50 --max-hours 4.0`), covering all charges (GPU, disk, bandwidth). This is within the US$50 CG4 ceiling (REQ-020). Invoiced CG4 spend before the rental was US$38.54, so the total stays at or below US$41.04.
**Evidence:**
- **VPS route instead of the pack's Drive route.**
  - The VPS holds the verified archive. Only the 26 steps #17 needs go to the GPU host: 15.1 GB, staged from the archive with every SHA-256 checked against the pack manifest (`posthoc_gpu_pack/vps_route/stage_inputs.py`).
  - The pack's route would download the whole 55.7 GB archive from Google Drive onto the host. That download is billed per GB, and the Drive file would have to be shared by link for the time.
  - #18 and #19 need no GPU. They run on the VPS CPU from `results/g6_extract/` at no cost.
- **Defects found and fixed before any GPU time** (`posthoc_gpu_pack/PATCH_NOTES.md`; originals kept in `posthoc_gpu_pack/_original_from_pc/`):
  - #17 would have sampled with top-k 64. Every checkpoint's `generation_config.json` has Gemma's `top_k: 64`, and HF `generate()` applies it unless top_k is passed. Shown on the VPS: 64–67 tokens kept per step instead of 262,144 at "top-p 1.0".
  - #17's length cap would have been max(n_tokens)+8 instead of the registered 260 (EN) / 338 (BN).
  - #17's seeds came from Python's per-process `hash()`, so they were not fixed.
  - #18 could not find the training corpora (`gen_<g>/synthetic.jsonl`) and would have fallen back to other files.
  - #19 would have picked either sample file by directory order.
- **Smoke test on the VPS CPU** (GEN0-EN, 4 prefixes): the decoder check passed. The registered gen-0 sample NLLs (`sample_scores.jsonl`) were reproduced within 0.004 nats/token.
- **Offer 8993650:** RTX 4090 in Ireland at US$0.546/h including 60 GB disk, with US$0/GB download. Reliability 0.999, driver 595.71 (CUDA 13.2). Instance **56846008** (label CG4-posthoc) was created at 2026-10-20T05:55Z. The first pick, offer 55627444 (Michigan, US$0.428/h), was taken by another renter before create; nothing was created from it.
- **Host software:** image `pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel` (the vast_ops default, also used for REQ-028), with transformers 5.17.0 as in the run.
- **Money rules:**
  - `vast_ops.py status` runs at least every 2 hours while the instance exists.
  - Everything is pulled and checked before the stop.
  - The agent then stops the instance and files a TEARDOWN request; the authors delete it.
**Human reply:** "learn \CG4_model_collapse_lowresource_experiment\posthoc_gpu_pack from this folder as we need to run some GPU things there. And kinsly save it to a specific folder the results. SO that I can copy and take it back to my pc to continue my work in there." followed by "Start now" (chat, 2026-10-20T05:3xZ). Recorded as approval to run the pack within its own stated cost; any need beyond US$2.50 goes back to the authors first.

## REQ-033 | 2026-10-20T06:30:24+00:00 | TEARDOWN | Status: DONE
**Ask:** Delete Vast.ai instance 56846008 (label CG4-posthoc, RTX 4090 in Ireland, US$0.546/h; REQ-032). It ran post-hoc #17.
- It is stopped. Its disk still bills about US$0.012 an hour until it is deleted.
- It holds copies of 26 checkpoints and their archived samples (unscreened text), uploaded for this job, plus the job's 2,600 new continuations. All of these go with it.
**Evidence:**
- **Job finished:** `posthoc17`, 52 of 52 cells, STATUS DONE at 2026-10-20T06:27:32Z (`logs/host_56846008/run.log`).
- **Results pulled and checked:**
  - `out_host.tar.gz` has SHA-256 25bef799feb62e8170bc7d39266d79a97ea745c68f8507ab86b4ba46d0d43976, the same on the host and the VPS.
  - `run.log`, `posthoc17.log` and `probe.log` are the same on both.
  - Unpacked into `results/cg4_posthoc_gpu_results/` and checked file by file against the host's SHA-256 list.
- **Nothing else on the host is needed.** Its inputs are SHA-256-checked copies of archive files on the VPS, and its code is in `posthoc_gpu_pack/`. Only STATUS, `run.log`, `out_host.sha256` and the job log are newer than the tarball, and all of them were pulled.
- **Cost:** US$0.28 invoiced for this instance at 06:29Z (cap US$2.50). CG4 total US$38.83 of the US$50 ceiling.
**Human command:** `vastai destroy instance 56846008`. In the `!` shell: `"/c/Users/Administrator/Desktop/Terminal gaps/.venv/Scripts/vastai.exe" destroy instance 56846008 -y`. Then confirm that no volumes remain.
**Human reply:** The authors ran `vastai destroy instance 56846008 -y` in the Claude Code `!` shell (chat 2026-10-20, about 07:18Z). The output was "destroying instance 56846008."
- Agent check at 2026-10-20T07:18:25Z: 0 instances and 0 volumes on the account. Recorded in `logs/vast_instances.jsonl`.
- Invoiced: US$0.29 for this instance; CG4 total **US$38.84** of the US$50 ceiling.
## REQ-034 | 2026-10-20T12:11:45+00:00 | DECISION | Status: DONE
**Ask:** Post-hoc sensitivity check on the item covariance that Section 3.6 of the manuscript discloses as unmodeled. Proposal: re-derive the key likelihood-based quantities (the H0 attenuation ratio; the H1 and H2 contrasts on log held-out perplexity and log recall ratio, with the registered secondary absolute differences; REPLACE net of REAL-REPEAT in both languages) under an item-paired bootstrap: each draw resamples the 2,000 held-out documents / 600 probes once per language and applies that one resample jointly to every checkpoint and arm; 10,000 draws, fixed seed 20261020; inputs are the released per-item sidecar records, with every registered point estimate asserted equal to the released analysis (below 1e-9) before any resampling is trusted. CPU-only, no training, no registered output changes; reported as a labeled post-hoc item.
**Human reply:** "Yes, run REQ-034" (chat, 2026-10-20). Run the same day. Result: all point estimates reproduced; every registered conclusion unchanged; every item-paired interval narrower than its registered counterpart (width ratios 0.13-0.73); the normalized H2 recall ratio stays unstable (REPLACE recall slope >= 0 in 0.8% EN / 3.4% BN of draws) while its registered secondary absolute version is stable. Outputs: results/analysis/posthoc_paired_bootstrap_2026-10-20/ (paired_boot.py, req034_paired_bootstrap.csv, README.md). Recorded by the agent.

## REQ-035 | 2026-10-24T00:47:43+00:00 | BUDGET + DECISION | Status: DONE
**Ask:** Run `posthoc_gpu_pack2_2026-10-23/` from the VPS (post-hoc, not pre-registered; it changes no registered file, number, test or verdict). Authors' decision (chat, 2026-10-22T22:36Z; confirmed 2026-10-24): run two more seeds per language of REAL-REPEAT and of the top-p 0.95 chain, a larger cross-decoder sample, and the equal-length diversity check on the full 2,000-document samples. It runs three parts:
- (A) eight chains, EN/BN-REAL-REPEAT-s2/-s3 and EN/BN-REPLACE-topp95-s2/-s3, six generations each with the registered recipe, on one rented RTX 4090;
- (B) the cross-decoder evaluation over seeds 0, 2 and 3: 12 REPLACE-family chains at generations 1 to 6 plus six generation-0 models, under both decoders, 200 prefixes per cell (156 cells);
- (C) the equal-length diversity check (Table S12 statistic) on the full 2,000-document samples of all 25 chains, on the VPS CPU.
Budget: a hard cap of **US$15** for this pack (`--budget-usd 15`; all charges: GPU, disk, bandwidth), plus a CG4 ceiling above REQ-020's US$50, because US$38.84 spent plus US$15 comes to US$53.84.
**Evidence:**
- The pack zip's SHA-256 is 0747a7788f074422548f0f9b8a83bb9116c06a65c3eaa49ee273f6ca82e44042, as the authors gave it. The folder in the package root is byte-identical to the zip, and `SHA256SUMS.txt` checks 9 of 9 OK (this VPS, 2026-10-24T00:4xZ). The 22 key package files that the stager sends to the host match the run's SHA-256.
- The pack's estimate (README_RUN.md section 1) is about 19 to 20 GPU-hours, roughly US$9 at US$0.45/h: A about 15.2 h, B about 3 h, setup about 1 h. The run uses `--max-hours` = (15 − spend − 2 reserve) / price. If the cap gets close, priorities 8 to 11 keep complete second seeds.
- Spend before this pack: US$38.84 (invoices, REQ-033, 2026-10-20T07:18Z). It is re-read from the invoices with `vast_ops.py status` before any rental.
- GPU-hours: REQ-020 also set a 100 GPU-h ceiling. The instance records' running times suggest about 75 to 80 GPU-h used so far (the exact figure comes from the invoices). This pack adds about 20 h, so the total could reach about 95 to 100 GPU-h.
- This is a new VPS (Windows Server 2025, installed 2026-10-22). Not yet here:
  - the G4b archive `results/packs/cg4_pack_20261016-232223.tar.gz` (55.69 GB, SHA-256 f51a5dcb…29a1d) and `pack_manifest_20261016-232223.json` (step 1 stages from them, and step 9 needs the archived sample files);
  - the Hugging Face token in `.env`;
  - Python 3.12 and the venv;
  - an SSH key on the Vast account.
**Human reply:** "Authors' approval: run the pack now; cap US$15 for this pack; study ceiling raised from US$50 to US$55." (chat, 2026-10-24, received before 00:46:50Z). Recorded:
- **Pack cap US$15.**
- **CG4 hard ceiling US$55 in total**, replacing REQ-020's US$50.
- Still open (asked in chat 2026-10-24): is REQ-020's 100 GPU-h ceiling raised as well? Until the reply, both limits apply.
- Answer: "And yes the GPU hours celling increased as requested." (chat, 2026-10-24, received before 01:03:23Z). The agent had proposed the reply "raise the GPU-hour ceiling to 125", so: **CG4 hard ceiling US$55 and 125 GPU-h in total**, replacing REQ-020's US$50 / 100 GPU-h. REQ-035 DONE. The run itself still waits for the G4b archive from Google Drive and HF_TOKEN in `.env`.

## REQ-036 | 2026-10-24T16:15:09+00:00 | TEARDOWN | Status: DONE
**Ask:** Delete Vast.ai instance 57450903 (label CG4-posthoc2, RTX 4090 in Pakistan, US$0.616/h; REQ-035). It ran `posthoc_gpu_pack2_2026-10-23`.
- It is stopped (2026-10-24T16:13:38Z). Its disk still bills about US$0.056 an hour until it is deleted.
- It holds the uploaded inputs (batch A and B: archive files checked against the G4b manifest, package files checked against the run's hashes), the eight new chains' weights, synthetic corpora and samples, and the cross-decoder continuations (unscreened text). All of these go with it.
**Evidence:**
- **Jobs finished:** `posthoc2_chains` CHAINS_DONE at 14:27:14Z (48 of 48 steps; `logs/posthoc2_incomplete.txt` empty); `posthoc2_xdec` XDEC_DONE at 15:42:17Z (156 cells; `decoder_check_ok` true); `posthoc2_pack` PACKED at 15:46:21Z.
- **Results pulled and checked** (`results/posthoc_gpu_stage2_2026-10-23/pull/`, 15:47 to 16:13Z):
  - `posthoc2_results_small.tar.gz` (87,968,542 bytes) has SHA-256 6e64ffbbd33cebe7a418918a00e44da57f60f33c2ca1c39d234fbd8b1fa98a16, the same on the host and the VPS.
  - `posthoc2_checkpoints_corpora.tar` (29,495,818,240 bytes) has SHA-256 057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f, the same on the host and the VPS. It is now in `results/packs/` beside the G4b archive, with `pack_manifest_posthoc2_checkpoints_corpora.json` (264 members) and `posthoc2_checkpoints_corpora.tar.sha256`.
  - All 685 files in the host's `posthoc2_files.sha256` match on the VPS: 421 from the small pack (unpacked into `results/posthoc_seeds_2026-10-23/host/`) and 264 members of the big tar.
  - The 10 `logs/posthoc2_*` files are the same on both.
- **Nothing else on the host is needed.** A scan of `/workspace/CG4` for files in neither pack nor the uploaded inputs found only `shared/tokenizer.json`, `logs/environment.json` (both pulled and SHA-256-checked, in `pull/host_other/`) and the four SHA-256 lists (pulled or already on the VPS).
- **Cost:** US$8.95 invoiced for this instance at 16:14Z (14.4 GPU-h; cap US$15). CG4 total US$47.79 of the US$55 ceiling: US$47.50 in the invoice query plus US$0.29 for 56846008, which it does not list.
- **Copies:** after the deletion, the VPS holds the only copy of the eight chains' weights and synthetic corpora until the second copy (README_RUN step 8: Google Drive, folder CG4_backup) is made. The authors may prefer to make that copy first.
**Human command:** `vastai destroy instance 57450903`. In the `!` shell: `"/c/Users/Administrator/Desktop/Terminal gaps/.venv/Scripts/vastai.exe" destroy instance 57450903 -y`. Then confirm that no volumes remain.
**Human reply:** The authors deleted instance 57450903 in the Vast.ai console. The VPS agent confirmed at 2026-10-24T17:05:49Z: 0 instances, 0 volumes. Invoiced: US$9.00 for this instance (14.4 GPU-h; cap US$15); CG4 total US$47.83 of the US$55 ceiling (the invoice query's US$47.54 plus US$0.29 for 56846008). Recorded on the PC from the authors' message of 2026-10-24.
