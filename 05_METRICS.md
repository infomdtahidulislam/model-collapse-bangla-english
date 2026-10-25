# 05 — Metrics (all automatic; exact definitions; revised 2026-10-12)

Every metric is computed by `harness/metrics.py` for one checkpoint from fixed inputs created at Gate 1 (held-out set, fresh slice, probe sets, bias pairs) and from the checkpoint's own fixed-prefix sample (2,000 documents, `03_MODELS_AND_TRAINING.md` §4). Record schema: `schemas/metric.schema.json` (`chain_id`, `generation`, `metric`, `value`, `n`, `ci_lo`, `ci_hi`, `checkpoint`). Per-item scores are written next to every step so that other scoring rules can be applied later without a GPU: `heldout_nll.jsonl`, `probe_scores.jsonl`, `bias_scores.jsonl`, `sample_scores.jsonl`. The untouched base model is scored as generation −1 (`BASE-<lang>`).

## 1. Held-out perplexity (primary)

Negative log-likelihood of the generation-g model on the frozen regular held-out set (2,000 human documents, ≤ 1,024 tokens, disjoint and MinHash-deduplicated against the seed) and, separately, on the fresh slice (Wikipedia pages created after the base model's release). Reported as:
- `log_ppl_heldout` / `log_ppl_fresh`: document-macro mean of per-document mean NLL in nats (the pre-registered token-scale primary), CI by bootstrap over documents;
- `log_ppl_micro_*`: token-micro NLL (total NLL / total tokens);
- `bpb_*` and `bpc_*`: bits per UTF-8 byte and per character (total NLL / total bytes or characters / ln 2), CI by bootstrap over documents of the ratio of sums. Bits per byte is the tokenizer-independent co-primary unit for the cross-language contrast, because per-token perplexity depends on each language's tokens per word.
The sidecar stores per-document NLL, tokens, bytes, characters and words.

## 2. Lexical diversity (primary: distinct-2 as log-ratio to generation 0)

On the sample's generated continuations (prefixes excluded), word tokens lower-cased, split by one grapheme-aware rule for both languages (runs of letters/marks including ZWJ/ZWNJ, or digits): distinct-n for n = 1…4 and type–token ratio on a fixed 50,000-token window taken from the documents in a seeded order (window start pre-specified at 0), MTLD (threshold 0.72), unigram and bigram entropy (bits), and character-5-gram distinctness as an inflection-robust variant. CIs come from 300 random permutations of the documents (subsampling without replacement; a with-replacement bootstrap duplicates documents and biases distinct-n downward). The analysis uses log(distinct-2 / distinct-2 at generation 0) for the cross-language contrast (scale-free) and reports the raw values.

## 3. Tail mass

Share of window tokens that belong to the rarest 10% of seed-corpus word types among types with ≥ 2 occurrences (lower-cased on both sides; deterministic tie-break by count then type). Falls as the tail is forgotten. Reported with the same permutation CI; a character-n-gram variant is a planned secondary analysis on the archived samples.

## 4. Tail-fact recall (primary: log-ratio to generation 0)

600 frozen cloze probes per language built from the same Wikidata triples in both languages (paired pool; `02_DATA_SOURCES.md` §3), stratified HEAD/MID/TAIL by subject mention frequency in that language's seed. Rule A (pre-registered): score the full sentence log-likelihood of the gold completion and three same-relation distractors that are not true objects of the subject; correct if gold ranks first. Rule B (robustness): object-conditional log-likelihood per object token (sentence NLL minus NLL of the frame before the object, divided by object tokens), which removes the preference for short objects. Reported overall and per stratum with Wilson CIs (`tail_fact_recall_*`, `tail_fact_recall_norm_*`); the sidecar stores every candidate's NLL and token counts. Floor rule: a stratum or language whose generation-0 recall CI includes chance (0.25) is excluded from H1(iii) and reported.

## 5. Language and script fidelity

Share of letters in the target script per sample document (Bengali block for BN; Latin script for EN, accented letters included), averaged, with the share of documents ≥ 95% in script (Wilson CI). A fastText language-id agreement rate is computed at Gate 1 on the seed corpora (Assamese shares the Bengali block) and reported in the manifest.

## 6. Degeneration and length

Repeated-4-gram rate per document and the share of documents with ≥ 50% repeated 4-grams; empty-continuation rate; mean and median generated length in tokens, words, characters and bytes; cap-hit rate; the exact-duplicate rate of the generated corpus (`generate.json`). Length is reported alongside every diversity metric (shortcut check).

## 7. Generated-text perplexity under the generation-0 model

Per-document NLL of the sample (prefix + continuation) under the language's generation-0 checkpoint: mean, SD and the 5th/95th percentiles (`sample_nll_ref_*`), sidecar `sample_scores.jsonl`. The narrowing of this distribution across generations is the classic collapse signature; computed for every chain at no extra training cost.

## 8. Bias probes (within-language only)

Stereotype preference score = share of pairs where the stereotypical sentence has the higher total log-likelihood (BanStereoSet for BN; CrowS-Pairs for EN), Wilson CI, per-pair NLLs in the sidecar. The two sets differ in construct and categories, so drift is compared within a language only.

## 9. Fertility

Tokens per word of the generated continuations under the base tokenizer, and the seed corpora's words/bytes/characters per token (manifest), used to interpret the budget-unit question and the EN-REPLACE-WM chain.

## 10. Filter statistics (ACCUMULATE-FILTER only)

Pass rate per criterion (script, repetition, perplexity band, near-duplicate) and overall, top-up rounds, generated tokens, kept tokens and any shortfall (`filter.json`, per-document reasons in `filter_log.jsonl`).

## 11. What is reported alongside every metric

Sample size, the fixed window or n, the tokenizer, length statistics in tokens/words/chars/bytes, and the per-item sidecar, so that a reviewer can see when a diversity change is a length change and can re-score without the GPU.
