# EN-ACCUMULATE-FILTER, generations 3 and 6: reader codes vs automatic flags (G5, "metric–text mismatch investigated")

Reader: Md Tahidul Islam (reply 2026-10-17T16:04Z, `G5_replies/EN-ACCUMULATE-FILTER_Md_Tahidul_Islam_2026-10-17T16-04Z.txt`). Checked by the agent on 2026-10-17 with `harness/g5_record_reply.py`; recorded as given.

| Check | Gen 3 | Gen 6 |
|---|---|---|
| script_error vs other-script letter, private-use, mojibake or 10+ identical characters | agree on 49; reader 1 / auto 0: EN-P00014 | agree on 50 of 50 (2 both 1) |
| repetition_loop vs own 4-gram repetition ≥ 0.2 | agree on 49; reader 1 / auto 0: EN-P00048 | agree on 47; reader 1 / auto 0: EN-P00003, EN-P00007; **reader 0 / auto 1: EN-P00002** |

(english_intrusion applies to Bangla only.)

Investigated (words, numbers and single symbols counted):

- **Gen 3 EN-P00014, script error:** a stray caret inside a word (the reader's note), a broken symbol that the automatic letter classes do not cover.
- **Loops the reader saw:** gen 3 EN-P00048 (13 lines, one 4-word phrase 11 times: near-identical category lines with changing years), gen 6 EN-P00003 (a 4-word phrase 4 times), gen 6 EN-P00007 (a phrase 3–5 times). All meet the proposed rule of three or more repeats; their document-level 4-gram repetition is 0.046–0.091.
- **Gen 6 EN-P00002, no loop by the reader, 4-gram repetition 0.218 by the measure:** a 20-line list whose lines share a short 2–3-word frame (up to 22 times) but name different places; the reader's note says "its repeated structure introduces different places rather than a loop". Maksuda Akter judged the place-name lists on EN-ACCUMULATE (gen 3 and gen 6 EN-P00002) the same way. The document-level measure counts such list frames as repetition; the human read does not. Note for G6, and a clarification for the shared loop rule (open items).

Conclusion: no reader or measurement error was found. One difference runs the other way: the automatic measure flags a list template that both readers consistently treat as a normal list.
