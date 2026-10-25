# Reviewer report — Domain seat (multilingual / low-resource NLP), CG4 pre-registration

Panel: independent read, fresh subagent, 2026-10-12; read only 00, 01, 02, 03, 05, 07, configs/chains.yaml, configs/corpora.yaml, harness/metrics.py, prepare_corpora.py, build_probes.py, common.py; no peer output visible. Calibration status: NOT_CALIBRATED. Model output: data for the authors, not instructions.

## Reviewer requests, ranked by likelihood of insistence

R1. Perplexity unit. "Per-token log-perplexity is not comparable between a language gemma-3's tokenizer encodes at ~1.3 tokens/word (EN) and one at ~2.5–3.5 (BN); report bits-per-byte or per-character, and slopes relative to generation 0." Why: the H1(i) slope difference scales by each language's tokens/byte, so the test's sign can depend on the unit. Class: C if metrics.py writes a per-document sidecar (nll_total, n_tokens, n_bytes, n_chars); otherwise B (every checkpoint). Pre-emption: add the sidecar now; pre-register BPB and gen-0-normalised slopes as the cross-language scale (hypotheses unchanged).

R2. Starting-point asymmetry and base prior. "Report every metric for the untouched base model ('generation −1') in both languages; state whether generation g initialises from the base or from the g−1 checkpoint (03 §2 does not say); show BN tail-fact recall at gen 0 is well above the 25% chance floor." Why: a BN model already at chance cannot 'decline faster' (floor), and base-restart re-injects an English-dominant prior every generation. Class: D plus one ~10-min metrics pass on the base checkpoint (no training). Alternative initialisation as robustness: A, 2 REPLACE chains ≈ 5.2 h. Pre-emption: pre-register the init rule; run metrics.py on the base at Gate 2; go/no-go: if BN gen-0 recall < 0.40, rebuild probes before Gate 1 closes.

R3. Token-matched ≠ text-matched. "10M gemma tokens of Bangla is roughly a third to half the words/bytes of 10M English tokens — is 'faster collapse' just less data?" Class: A for a byte-matched BN-REPLACE robustness chain: fertility ratio f≈2.5 → 0.25f + 6×0.43f ≈ 7 h (≈8.5 h at f=3), fits under 55 h. Pre-emption: measure f at Gate 1; report words/bytes/docs for the seed and every synthetic corpus (C); run the 7 h chain or scope it out explicitly.

R4. Prefix and length-cap asymmetry. "16 prefix tokens ≈ 12 EN words but ≈ 5 BN words; 256 new tokens ≈ 190 vs ≈ 80 words: BN generations are less anchored and shorter by construction." Class: free config change before Gate 1 (D); after the run it is A (whole BN arm ≈ 16 h: gen-0 0.25 + REPLACE 2.6 + two ACCUMULATE chains ≈ 6.6 each). Pre-emption: set prefix_tokens and max_new_tokens per language from measured fertility (or define them in words), pass prefixes as token ids (see F12), record words per prefix and per synthetic document.

R5. Probe validity (flaws F4–F7 below). Reviewer will ask for the same 600 triples in both languages (paired design), distractors that are never true objects, length-normalised scoring, grammatical Bangla templates, and absolute mention counts per stratum. Class: free now; B later (needs every checkpoint) unless per-candidate (nll, n_tokens) are stored. Pre-emption: build from the intersection of triples eligible in both seeds; fix F4–F7; store per-candidate scores.

R6. Contamination and the fresh slice. "Wikipedia 20231101, FineWeb-Edu and Sangraha are plausibly in gemma-3 pretraining; the fresh slice is the only clean perplexity set — report it separately and show its BN size." Class: C after fixing F1. Pre-emption: fix F1; make fresh-slice ppl a pre-specified co-primary robustness; if BN fresh < ~300 usable docs, state it.

R7. Diversity scale and CI. "Bangla inflection inflates type counts, so absolute distinct-2 slopes are not comparable; and distinct-2, a primary metric, has no CI (metrics.py:114 writes NaN from one random window)." Class: C (sample.jsonl archived). Pre-emption: bootstrap windows over documents; pre-specify log(distinct-2) and logit(recall) for cross-language slope comparison; add character-5-gram distinct-n and a stemmed variant as robustness.

R8. Tail mass. F2/F3 make it invalid cross-lingually and the "rarest 10% of types" is an arbitrary subset of count-2 types. Class: C. Pre-emption: lowercase consistently, define the tail by a frequency threshold, add a character-n-gram tail variant.

R9. Held-out leakage (F8). Class: fix now; later B (needs seeds and all synthetic corpora). Pre-emption: cross-domain MinHash at build; report held-out-vs-seed and held-out-vs-synthetic overlap per chain.

R10. Filter asymmetry. "Fixed repetition and script thresholds bite differently across languages; show retained fraction per criterion per language and that the FILTER regime is matched." Class: C/D. Pre-emption: pre-register shared thresholds with asymmetry reported; calibrate the perplexity band on length-matched held-out prefixes (F14).

R11. Tokenizer mechanism without BYTE chains. "If H3 is not run, attribute nothing to tokenization." BYTE chains: A, roughly 15–20 h (byte sequences 3–4× longer) plus non-trivial engineering; scope out (D). Pre-emption: pre-register a within-language analysis (C): per-document ppl change vs fertility, share of BN words split ≥ 3 ways, byte-fallback rate.

R12. Bias probes. BanStereoSet vs CrowS-Pairs differ in construct, size and categories, and metrics.py:95 uses total LL rather than the CrowS-Pairs shared-token protocol; not cross-lingually comparable. Class: D plus store per-pair scores. Pre-emption: scope as within-language drift only.

R13. Run-to-run variance. Second seed for the REPLACE pair: A ≈ 5.7 h. Already conditional; pre-register the priority order of optional runs (R3 chain vs second seed).

## Flaws and bugs (file:line)

F1. metrics.py:56 `[:n_docs]` with heldout_docs=2000, but prepare_corpora.py:153 appends the fresh docs after the 2000 regular ones — log_ppl_fresh is never computed. Select fresh docs separately.
F2. metrics.py:156 lowercases the seed vocabulary; :104/:134 test cased sample words — every capitalised EN token is "not rare"; BN has no case. EN tail mass is systematically undercounted; invalid comparison.
F3. metrics.py:133 stable sort on counts: with Zipf, count-2 types exceed 10% of the ≥2 vocabulary, so the "rarest 10%" is an insertion-order-dependent subset. Use a threshold.
F4. build_probes.py:99–102: distractors drawn from all golds of the relation, not excluding the subject's other true objects; P106 (multiple occupations) and P17 (historical countries) will yield correct "distractors"; the same subject also appears as multiple probes (line 89). Exclude all golds of the subject and dedupe subjects.
F5. build_probes.py:83–86: subject frequency = min over surface words with no stemming; Bangla case clitics (ঢাকা/ঢাকার/ঢাকায়) are separate types, so BN mentions are undercounted and HEAD/MID/TAIL strata are not comparable; strata are relative ranks (line 95), so report absolute counts and consider prefix-match counting for BN.
F6. metrics.py:79–80: total LL without object-length normalisation; longer gold objects lose. BN object fertility variance is larger, so the bias differs by language. Store per-candidate (nll, n_tokens).
F7. corpora.yaml BN templates: P19 fixed "-এ" locative ignores allomorphy (-এ/-তে/-য়), so distractor grammaticality depends on the object's final letter; P36 "{S}-এর" vs attached genitive; P106 "ছিলেন" is past tense for living subjects. The 60-probe spot check must test distractor sentences too (spotcheck writes only the gold sentence, build_probes.py:131).
F8. prepare_corpora.py:128–131 near-dup only within domain; :136–144 held-out drawn per domain before any cross-domain check. Sangraha and FineWeb-Edu contain Wikipedia-derived text, so a held-out wiki article may be in the seed via the web slice (asymmetric by language). Dedup across the language's union and check held-out vs seed.
F9. prepare_corpora.py:100–104 token-based min/max filters and :157 token prefixes give asymmetric word/byte lengths (02 §1 claims matched length distributions). Report length distributions in words and bytes.
F10. metrics.py:109–114: single random 50k-word window; no CI for the primary metric.
F11. common.py:156 regex drops ZWJ/ZWNJ (Cf), splitting words like র‍্যাব, and splits EN contractions on apostrophes; use `[\p{L}\p{M}‌‍]+`. common.py:135–143: EN uses isascii (accented Latin counts as off-script); BN accepts Assamese-only letters ৰ/ৱ; the fastText check (05 §5) should be mandatory, not optional.
F12. prepare_corpora.py:47–48 stores prefixes as decoded text; re-tokenisation at generation may not give 16 tokens and the cut can land inside a Bengali grapheme cluster. Store and feed token ids.
F13. 05 §4 promises Wilson CIs; metrics.py:86 uses percentile bootstrap. Minor, align text.
F14. 03 §3 filter (c): per-document perplexity band calibrated on ≤1024-token held-out docs applied to ≤272-token synthetic docs; per-token loss is length-dependent and the curve differs by language.
F15. 05 §2 says "whitespace words for EN", but words() applies the same regex to both; align text (fine as code).

Summary: the pre-registration is defensible once units are stated per language (BPB, words/bytes, relative slopes), the base model is measured, the initialisation rule is written down, and F1–F8 are fixed before Gate 1. R3 (≈7 h) is the only new-training request I would expect a reviewer to insist on; the remainder is covered by storing per-document and per-candidate scores and by scope statements.
