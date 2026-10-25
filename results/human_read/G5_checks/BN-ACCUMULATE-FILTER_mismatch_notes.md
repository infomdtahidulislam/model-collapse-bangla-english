# BN-ACCUMULATE-FILTER, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Maksuda Akter (reply 2026-10-17T09:14Z, `G5_replies/BN-ACCUMULATE-FILTER_Maksuda_Akter_2026-10-17T09-14Z.txt`). Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`, using the screening definitions of `harness/tools/screening_check.py` on the same 50 samples per generation. Recorded as given; no code was changed by the agent.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| english_intrusion vs any Latin letter | agree on 49; reader 0 / auto 1: BN-P00001 | agree on 50 of 50 (6 both 1) |
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 46; reader 1 / auto 0: BN-P00009, BN-P00018, BN-P00027, BN-P00035 | agree on 47; reader 1 / auto 0: BN-P00018, BN-P00026; reader 0 / auto 1: BN-P00012 |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 49; reader 1 / auto 0: BN-P00048 | agree on 49; reader 1 / auto 0: BN-P00010 |

Investigated (characters and counts only):

- **Gen 3 BN-P00001, English intrusion: possible slip, asked.** The only Latin character is `œ` (U+0153 LATIN SMALL LIGATURE OE) inside a Bangla word. The reader's own note says "A Latin letter appears inside a Bangla word", but the code is 0. The page's rule ("English words or any Latin-letter string") and the other reader's practice (single stray Latin letters coded 1) suggest 1. Asked the reader on 2026-10-17.
- **Gen 6 BN-P00012, script error: a quirk of the automatic measure, not of the reading.** The "styled M" is `U+1D440 MATHEMATICAL ITALIC CAPITAL M`. Unicode gives it no Latin script, so `screen_foreign_letter` counts it as a third script. The reader read it as a styled Latin letter (English intrusion 1 with 24 other Latin letters; script error 0), which is the sensible reading. Note for G6: the screening counts math-styled Latin letters as foreign.
- **Script error from stray vowel signs (gen 3 BN-P00018, BN-P00027; gen 6 BN-P00018):** each text has a combining mark with no letter before it, a broken character the automatic letter classes do not see.
- **Script error for numbers (gen 3 BN-P00009, BN-P00035; gen 6 BN-P00026):** these texts contain only ordinary Bengali digits (no ASCII digits, and no number that mixes the two); the reader's notes call them a "corrupt number fragment" or a "stray digit". Whether a misplaced or broken number counts as "garbage characters" is a reading rule both readers should share (asked 2026-10-17).
- **Repetition (gen 3 BN-P00048: "the final word loops", 4-gram repetition 0.000, most repeated word 3-gram twice; gen 6 BN-P00010: "commands and dialogue phrases get stuck in clear loops", 0.034, most repeated 3-gram three times):** local loops below the document-level threshold. The same open rule question as on BN-ACCUMULATE: how many repeats make a "loop".

Conclusion: one possible coding slip (BN-P00001) is put to the reader. The other differences come from the definitions: local loops, broken marks and number fragments the measures cannot see, and one styled letter that the screening counts as foreign.

## Update 2026-10-18: after the authors' G5 decision

Under decision (c) in `signoffs/G5_human_read.md`, the reader changed gen 3 BN-P00001 english_intrusion 0 → 1 (the `œ`) on the page and
re-sent it (reply 2026-10-17T23:53Z, recorded 2026-10-18T00:06Z from
`G5_replies/BN-ACCUMULATE-FILTER_Maksuda_Akter_2026-10-17T23-53Z_corrected.txt`). Nothing else changed. English intrusion now matches
the Latin-letter check on 50 of 50 samples in both generations; the current comparison is in
`G5_checks/BN-ACCUMULATE-FILTER_gen3_Maksuda_Akter.json` and `G5_checks/BN-ACCUMULATE-FILTER_gen6_Maksuda_Akter.json`.
