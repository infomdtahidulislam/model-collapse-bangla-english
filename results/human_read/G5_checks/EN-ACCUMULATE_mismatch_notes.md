# EN-ACCUMULATE, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Maksuda Akter. The recorded reply is 2026-10-17T12:04Z (`G5_replies/EN-ACCUMULATE_Maksuda_Akter_2026-10-17T12-04Z.txt`). A first reply at 12:01Z was not recorded: its gen 3 header said "coded 50 of 50" while row EN-P00000 was blank (49 coded). The 12:04Z reply differs from it only in that row, now coded. Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`; recorded as given.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 50 of 50 (14 both 1) | agree on 49; reader 1 / auto 0: EN-P00005 |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 49; reader 1 / auto 0: EN-P00000 | agree on 48; reader 1 / auto 0: EN-P00030, EN-P00041 |

(english_intrusion applies to Bangla only.)

Investigated:

- **Gen 6 EN-P00005, script error:** the text contains `<unused4218>`, one of Gemma's reserved placeholder tokens written out as text. It is plain ASCII, so no automatic check sees it. The reader's note names it ("an unused token"). The same artifact is in gen 6 EN-P00023 and EN-P00030 and in gen 3 EN-P00004; there the automatic check also fires because of other-script letters. Across all sample files, 31 of 119 contain such tokens (1–3 of 50 samples), none at generation 0 or base, also in EN-REAL-REPEAT (note for G6; open item for the shared rules).
- **Repetition (words, numbers and single symbols counted):** gen 3 EN-P00000 (bullet items: a word pair 4 times, a 3-word phrase 3 times), gen 6 EN-P00030 (a run of 4 identical tokens, repeated country labels), gen 6 EN-P00041 (a run of 3, a word pair 4 times). All three meet the proposed rule of three or more repeats; the document-level 4-gram measure (0.000–0.014) misses these local loops.
- Optional fluency: gen 6 EN-P00001 (in the 20-prompt subset) has no fluency rating; 19 of 20 rated.

Conclusion: no reader or measurement error was found. The differences are a tokenizer artifact the screens cannot see and local loops below the document-level threshold.
