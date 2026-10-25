# BN-REPLACE, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Md Tahidul Islam (reply 2026-10-17T11:39Z, `G5_replies/BN-REPLACE_Md_Tahidul_Islam_2026-10-17T11-39Z.txt`). Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`, using the screening definitions on the same 50 samples per generation. Recorded as given; no code was changed by the agent.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| english_intrusion vs any Latin letter | agree on 50 of 50 (9 both 1) | agree on 50 of 50 (17 both 1) |
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 43; reader 1 / auto 0: P00020, P00021, P00023, P00024, P00035, P00043, P00044 | agree on 38; reader 1 / auto 0: P00002, P00009, P00018, P00027, P00036, P00037, P00040, P00041, P00042, P00044, P00046; reader 0 / auto 1: P00001 |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 48; reader 1 / auto 0: P00023, P00040 | agree on 48; reader 1 / auto 0: P00042, P00046 |

Investigated (characters and counts only):

- **Gen 6 BN-P00001, script error: possible slip, asked.** Three CJK characters (U+8868, U+8FBE, U+5F0F); the reader's own note says "CJK text appears", but the code is 0. The rubric counts a third script as a script error.
- **Script errors that only the reader saw (18):** every one has a visible broken-character pattern: a combining vowel or consonant sign with no letter before it (gen 3 P00043, P00044; gen 6 P00002, P00009, P00018, P00027, P00037, P00041, P00044), a doubled diacritic (gen 3 P00021, P00024, P00044; gen 6 P00042), a digit glued to a letter inside a word (gen 3 P00020, P00023, P00024, P00035; gen 6 P00036, P00046), broken symbols (gen 3 P00044; gen 6 P00027, P00036, P00041), or a percent sign inside a word (gen 6 P00040). The automatic letter classes cannot see these. Note for G6: a "broken Bengali" screen (stray or doubled marks, digits glued to letters) would match the human script-error code far better than the third-script letter share alone.
- **Repetition (counting words, numbers and single symbols):** gen 3 P00023 is a run of 29 identical tokens (a closing-bracket loop); gen 3 P00040 and gen 6 P00046 repeat one word three times; gen 6 P00042 is one doubled diacritic (a repeat of 2, already a script error). The document-level 4-gram measure sees none of them (it drops symbols, and the loops are local).

Shared-rule proposal sent to both readers on 2026-10-17, from their own practice:

- script error = a third-script letter or a broken character (stray or doubled signs, digits glued into words, broken symbols);
- repetition loop = the same word, phrase or symbol three or more times, in a row or close together.

Under the second rule three earlier codes are a repeat of only 2 and need the reader's decision: BN-ACCUMULATE gen 6 P00019 and P00035, and BN-REPLACE gen 6 P00042.

## Update 2026-10-18: after the authors' G5 decision

Under the decisions in `signoffs/G5_human_read.md`, the reader changed three codes on the page and re-sent it (reply 2026-10-17T23:59Z, recorded
2026-10-18T00:06Z from `G5_replies/BN-REPLACE_Md_Tahidul_Islam_2026-10-17T23-59Z_corrected.txt`):
- gen 6 BN-P00001 script_error 0 → 1 (the CJK characters; decision (c));
- gen 3 BN-P00040 repetition_loop 1 → 0 (the closest three uses of the word span 35 words; decision (b));
- gen 6 BN-P00042 repetition_loop 1 → 0 (repeated only twice; decision (a)).

Nothing else changed. The current comparison with the automatic flags is in `G5_checks/BN-REPLACE_gen3_Md_Tahidul_Islam.json` and
`G5_checks/BN-REPLACE_gen6_Md_Tahidul_Islam.json`.
