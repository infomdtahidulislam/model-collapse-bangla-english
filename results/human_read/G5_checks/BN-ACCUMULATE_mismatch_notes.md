# BN-ACCUMULATE, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Md Tahidul Islam (reply 2026-10-17T08:33Z, `G5_replies/BN-ACCUMULATE_Md_Tahidul_Islam_2026-10-17T08-33Z.txt`). Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`, using the screening definitions of `harness/tools/screening_check.py` on the same 50 samples per generation.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| english_intrusion vs any Latin letter | agree on 50 of 50 (7 both 1) | agree on 50 of 50 (12 both 1) |
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 48; reader 1 / auto 0: BN-P00010, BN-P00040 | agree on 50 of 50 (5 both 1) |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 48; reader 1 / auto 0: BN-P00010, BN-P00030 | agree on 47; reader 1 / auto 0: BN-P00019, BN-P00030, BN-P00035 |

The automatic flags never fired on a sample the reader left unflagged. Every difference is a pattern the reader saw and the automatic definitions cannot see:

- **Gen 3 BN-P00010** (script error and repetition): 17 hyphens in 16 short runs (at most 2 in a row) through about 1,000 characters. `screen_char_run10` needs 10 identical characters in an unbroken run, and `words()` drops the hyphen, so the 4-gram repetition is 0.000.
- **Gen 3 BN-P00040** (script error): three generic currency signs `¤` (U+00A4), a placeholder for a lost symbol. The automatic check covers letters, private-use, mojibake and runs only.
- **Gen 3 BN-P00030, gen 6 BN-P00030** (repetition): a short Tibetan or label fragment repeats locally; over the whole document the 4-gram repetition is 0.000.
- **Gen 6 BN-P00019, BN-P00035** (repetition): a phrase recurs (its most repeated word 3-gram occurs twice); the 4-gram repetition is 0.027 and 0.000. The rubric says "repeats … over and over"; whether twice counts is a reading rule for both readers to keep consistent (asked 2026-10-17).

Conclusion: no reader or measurement error was found. The measures and the human read differ in definition: document-level n-gram shares and letter classes against local loops and symbol garbage. This matches the authors' G4 caveat on spaced-symbol loops (`signoffs/G4_chains.md`).

## Update 2026-10-18: after the authors' G5 decision

Under decision (a) in `signoffs/G5_human_read.md` (a word or phrase repeated only twice is not a loop), the reader changed gen 6 BN-P00019 and BN-P00035
repetition_loop 1 → 0 on the page and re-sent it (reply 2026-10-17T23:41Z, recorded 2026-10-17T23:48Z from
`G5_replies/BN-ACCUMULATE_Md_Tahidul_Islam_2026-10-17T23-41Z_corrected.txt`). Nothing else changed. The current comparison with the
automatic flags is in `G5_checks/BN-ACCUMULATE_gen3_Md_Tahidul_Islam.json` and `G5_checks/BN-ACCUMULATE_gen6_Md_Tahidul_Islam.json`.
