# Sign-off: G1 corpora

**Status:** PASSED
**Date:** 2026-10-14 (rounds 1, 2 and 3 answered 2026-10-14; closed with the authors' approval of REQ-012 after the clean English round 3, at 2026-10-14T06:16:27Z)
**Author 1:** Md Tahidul Islam   **Author 2:** Maksuda Akter (round 1 read together, every row)

Evidence filed by the agent on 2026-10-13 as REQ-007 (`signoffs/REQUESTS.md`); reading sheet `signoffs/G1_spotcheck_2026-10-13.html`. The agent fills the bracketed fields from the authors' chat reply; the agent's own numbers are marked "agent".

## Evidence reviewed
- [x] data/corpora/manifest.json reviewed; EN/BN token counts matched within 2%: [agent: EN 10,000,387 / BN 10,001,024 tokens, 0.01% apart; EN 7,314,331 / BN 5,625,959 words; held-out 2,000 + fresh 500 / 499; prefixes 16 / 21 tokens and continuation caps 260 / 338 tokens for 12 / 190 words. Authors: confirmed in chat, 2026-10-14]
- [x] Licences recorded for every source: [agent: data/sources/SOURCES_MANIFEST.json, 8 sources: CC BY-SA 4.0 (bnwiki, enwiki, both fresh slices, CrowS-Pairs), CC BY 4.0 (Sangraha verified/ben), ODC-By 1.0 (FineWeb-Edu sample-10BT), BanStereoSet unstated (REQ-005: evaluation only, cited, not redistributed). Confirmed by: both authors in chat, 2026-10-14]
- [x] Held-out sets disjoint from seed corpora (test_sanity.py): [agent: RESULT: PASS on the host, logs/host_55779705/test_sanity_G1.txt]
- [x] 60 BN probes spot-checked by a native reader:
  - Round 1, 2026-10-14, both authors: rejected 13, replaced 0. P17: 12 of 15. P19: 1 of 17.
  - More than 3 of 60, so the language is rebuilt (REQ-009) and gets a second look.
  - Round 2, 2026-10-14 (REQ-010), rebuilt set: rejected 3 of 60. P17: 2 of 7 (a festival, a topic). P106: 1 of 20 (a distractor also true). Meets the rule (≤ 3); the 3 are replaced (REQ-012 repair).
  - Round 3 (REQ-013): 20 changed BN probes shown for information, 0 rejected.
- [x] 60 EN probes:
  - Round 1: rejected 34, replaced 0. P106: 18 of 18. P17: 16 of 17. P19: 0 of 18 (EN-P19-0507 was ticked by a mouse slip; withdrawn 2026-10-14).
  - Round 2, 2026-10-14 (REQ-010), rebuilt set: rejected 7 of 60. P19: 3 of 26 (a missing "the" before an arrondissement). P106: 2 of 22 (a distractor also true). P17: 2 of 6 (a missing "The"; a language). More than 3, so EN is repaired (REQ-012) and gets a third look.
  - Round-2 reply: `signoffs/G1_spotcheck_round2_reply_2026-10-14.txt`.
  - Round 3, 2026-10-14 (REQ-013), set repaired under REQ-012: rejected 0 of 60 English probes not read before (P106 29, P19 26, P36 5). Meets the rule. Reply: `signoffs/G1_spotcheck_round3_reply_2026-10-14.txt`.
  - Rejected rows and reasons: `signoffs/G1_spotcheck_reply_2026-10-14_corrected.txt` (authoritative re-paste without EN-P19-0507; first paste in `G1_spotcheck_reply_2026-10-14.txt`).
- [x] 30 bias pairs per language spot-checked:
  - Round 1: EN 1 of 30 rejected (EN-B0646); BN 4 of 30 (BN-B0128, BN-B1124, BN-B0314, BN-B0840).
  - Handled under REQ-009 item 6 (approved): the 5 rejected pairs and 8 more Bangla pairs with the same detached case ending are excluded (`data/probes/bias_exclusions.json`; EN 1,507 and BN 1,182 pairs remain).

## Failure-mode checklist (tick all)
- [x] Implementation bug checked (tokenizer, truncation, packing, seeds): [agent: token counts and per-language prefix/continuation lengths from the model tokenizer (`data/corpora/manifest.json`); probe selection is deterministic and reproduced exactly before the REQ-012 repair (600 + 600); `harness/tests/test_sanity.py` PASS on the final files (`logs/test_sanity_G1_round3_local.txt`)]
- [x] Every number traceable to results/ or logs/: [agent: manifests, `signoffs/REQUESTS.md` evidence, `data/probes/repair_round2.json`, `logs/decisions.md`]
- [x] Shortcut: diversity change vs length change compared: [agent: not applicable at G1, no generated text yet; checked from G2 on]
- [x] Surprising drops checked against NaN loss, empty generations, script collapse: [agent: not applicable at G1, no training yet; generation 0 is checked at G2]
- [x] No leakage between training, held-out and probe sets; no cross-chain contamination: [agent: test_sanity: held-out disjoint from seed in both languages, fresh slice present; probes are Wikidata cloze sentences built from triples, not corpus documents; no chain has run]
- [x] Run matches chains.yaml and the pre-registration, or deviations.md is updated: [agent: `results/deviations.md` rows for the English P106 frame and the REQ-009 filters, the REQ-012 repair, and fixes (a)/(b)]
- [x] Design still answers the RQ (frame-lock check): [agent: the four registered relations, the paired pool, the strata and 200 probes per stratum are kept; the relation mix shifts (P17 now 17 EN / 18 BN), recorded as an effect on inference]
- [x] New citations resolved: [agent: none added at G1]

## Notes / conditions

Agent notes for the authors (2026-10-13): (a) the Wikidata triples are drawn evenly over each relation's statements (the original `LIMIT 3000` returned the first matches of an object-grouped index, e.g. all P17 triples = Canada); (b) distractors exclude all true objects of the subject fetched from Wikidata (registered rule, 02_DATA_SOURCES.md §3). Neither changes a value in `configs/corpora.yaml`; both are open to the authors' veto in the REQ-007 reply. P17 answers remain uneven (New Zealand is the gold of 26% EN / 28% BN of the P17 probes).

Authors, 2026-10-14 (chat): fixes (a) and (b) approved. After round 1 the authors wrote "G1 passed". The agent keeps this gate OPEN because of the registered rebuild rule (REQUESTS.md REQ-007 note). It passes after the rebuild (REQ-009) and the authors' second look.

Closed 2026-10-14. Round 2 (REQ-010): Bangla 3 of 60 rejected, which meets the rule, and English 7 of 60. The authors' third look at English (REQ-013) rejected 0 of 60 probes from the set repaired under REQ-012. The authors then approved REQ-012 ("Approve"); the question they answered said "Approving closes G1". Per REQ-004 condition (1), generation 0 is retrained and rescored from the final probe files before G2 is filed. Recorded by the agent.

[agent, 2026-10-18, time audit: G1 passed when the authors answered "Approve" at 2026-10-14T06:16:27Z, after the round-3 reply pasted at 06:15:22Z (session log). Two decisions.md lines about this carry hand-typed stamps earlier than the events: "2026-10-14T05:55:00" (round 3 answered; written 06:16:02Z) and "2026-10-14T06:05:00" (G1 PASSED; written 06:18:54Z). The log is append-only; the real times are in its correction line (logs/decisions.md, time correction of 2026-10-18T01:10Z).]
