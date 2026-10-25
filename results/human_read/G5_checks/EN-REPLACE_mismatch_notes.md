# EN-REPLACE, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Maksuda Akter (reply 2026-10-17T16:59Z, `G5_replies/EN-REPLACE_Maksuda_Akter_2026-10-17T16-59Z.txt`). Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`; recorded as given.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 50 of 50 (27 both 1) | agree on 48; reader 1 / auto 0: EN-P00002, EN-P00036 |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 48; reader 1 / auto 0: EN-P00000, EN-P00043 | agree on 48; reader 1 / auto 0: EN-P00002, EN-P00041 |

(english_intrusion applies to Bangla only.)

Investigated (words, numbers and single symbols counted):

- **Gen 6 EN-P00002, script error and loop:** a run of 5 semicolons (repeated punctuation) in a list; a broken symbol pattern the letter classes do not cover, and a local loop.
- **Gen 6 EN-P00036, script error:** the placeholder token `<unused2248>`, which no screen sees. On this page the gen 3 placeholders (EN-P00004 `<unused3326>`, EN-P00005 `<unused3663>`) are also coded 1, and those texts also have other-script letters.
- **Emoji:** gen 6 EN-P00020 has an ordinary emoji coded as no script error (the reader's note); the automatic check agrees.
- **Loops:** gen 3 EN-P00000 ("awards" 4 times, a word pair 4 times), gen 6 EN-P00041 ("Alaska" 3 times in a row), gen 6 EN-P00002 (5 semicolons in a row) meet the rule of three or more repeats. Gen 3 EN-P00043 ("virus" 3 times, not adjacent) is a borderline case for "close together", like BN-REPLACE gen 3 P00040 (final decision list).

Conclusion: no reader or measurement error was found; the differences are a placeholder token and punctuation runs that the screens cannot see, and local loops below the document-level threshold.
