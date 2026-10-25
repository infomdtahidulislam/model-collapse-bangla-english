# 02 — Corpora, held-out sets, probe sets and prefixes (revised 2026-10-12)

Principle: two seed corpora matched in size, domain mix and cleaning; held-out text that no chain could have trained on; probe sets built once from the same facts in both languages and frozen. Everything carries source, licence and SHA-256 in `data/corpora/manifest.json`. Implementation: `harness/fetch_sources.py`, `prepare_corpora.py`, `build_probes.py`.

## 1. Seed corpora (10M base-model tokens each)

| Language | Sources (verified 2026-10-12; **HUMAN** confirms licences at Gate 1) | Domain |
|---|---|---|
| BN | `wikimedia/wikipedia` 20231101.bn (CC BY-SA 4.0); `ai4bharat/sangraha` verified/ben (CC BY 4.0; web, news, books) | encyclopaedic 50% / web 50% |
| EN | `wikimedia/wikipedia` 20231101.en (CC BY-SA 4.0); `HuggingFaceFW/fineweb-edu` sample-10BT (ODC-By 1.0) | encyclopaedic 50% / web 50% |

Matching and cleaning rules: same number of base-model tokens (±2%); Unicode NFC; documents of 64–1,024 tokens (longer ones truncated); ≥ 95% of letters in the target script; exact duplicates removed; MinHash near-duplicates (word 3-gram shingles, 64 permutations, Jaccard ≥ 0.8) removed across the **whole pool of a language**, all domains in one index, so a Wikipedia article reproduced inside a web source cannot survive in two places; held-out documents are drawn from that deduplicated pool before the seed is sampled. The manifest reports, per language, tokens, words, bytes, characters, words/bytes/characters per token (the fertility baseline), document-length percentiles in tokens, words and bytes, and near-duplicates removed per domain. Known limitation, stated in the paper: FineWeb-Edu is classifier-filtered educational text and Sangraha is general web text, so curation is not identical; seed-quality proxies (base-model bits per byte, repetition rate) are reported per language.

## 2. Held-out human text (perplexity)

- Regular set: 2,000 documents per language from the same deduplicated pool, disjoint from the seed by document id and by near-duplicate test.
- Fresh slice: up to 500 Wikipedia pages per language created after 2025-09-01 (the base model was released 2025-08-05), fetched live from the MediaWiki API, cleaned the same way and tested against the pool so a new page that copies an old article is dropped. The fresh slice is scored separately and is the contamination-free perplexity set; its size is reported (and stated as a limitation if below 300 usable documents).
- Frozen at Gate 1 with SHA-256.

## 3. Tail-fact probe sets (paired across languages)

Purpose: measure forgetting of rare facts without any judge.
- Source: Wikidata triples (relations P36 capital, P17 country, P19 birthplace, P106 occupation) with labels in both English and Bangla. Up to 3,000 per relation, drawn evenly over all of the relation's statements (evenly spaced `bd:slice` windows of the statement index, matches taken round-robin; `build_probes.py --fetch`, summary in `data/probes/wikidata_fetch_summary.json`). Added 2026-10-13 before Gate 1: a plain `LIMIT 3000` returns the first matches of an index grouped by object (all P17 triples were "Canada"), which leaves no same-relation distractors.
- Paired pool: only triples whose subject is mentioned (≥ 1 document) in **both** seed corpora are eligible; each language then stratifies that shared pool by its own subject mention frequency into HEAD (top 10%), MID, TAIL (bottom 50%). One probe per subject (by Wikidata id and by surface label); 200 per stratum, 600 per language; each record keeps the Wikidata ids and both languages' mention counts so probes can be paired in analysis.
- Cloze frames keep the object slot bare (no case suffix, no article), so gold and distractors share an identical frame and Bangla suffix allomorphy or English a/an cannot favour a candidate; the subject frame is constant within a probe. Distractors: three objects of the same relation that are not true objects of that subject (all of the subject's objects for the relation are excluded: every object of every pool subject is fetched from Wikidata by `build_probes.py --truth` into `data/probes/wikidata_truth.jsonl`, not only the sampled triple; 2026-10-13). Scoring rules A and B in `05_METRICS.md` §4.
- Filters added after G1 round 1 (REQ-009, approved by both authors on 2026-10-14; `results/deviations.md`):
  - **P17 subjects** must be located and undated: a coordinate location (P625), no P585/P580, and a label that does not read as a date in either language. Round 1 rejected topics, year summaries, bilateral relations, events and an organisation as "located in" a country.
  - **P19 objects** must be places with a country (P17); round 1 rejected "পৃথিবী" (Earth).
  - **English state names** take "the" in state slots (P36 subjects, P17 and P19 objects), as in "the United States".
  - **English P106 frame:** "The occupation of {S} is listed as {O}." (was "The occupation of {S} is {O}."; `configs/corpora.yaml`).
  - **Bias pairs** the authors rejected, plus Bangla pairs with a detached case ending ("বাড়ি এ"), are excluded (`data/probes/bias_exclusions.json`).
  - Facts come from `build_probes.py --filters` (`data/probes/wikidata_filters.json`). The round-1 files are kept in `data/probes/round1_2026-10-13/`.
- Rules added after G1 round 2 (REQ-012, approved by both authors on 2026-10-14; `results/deviations.md`):
  - **P17 subjects** are human settlements or administrative areas (Wikidata P31/P279 of Q486972 or Q56061).
    - Excluded: dependent territories and places in them (Bermuda), places with more than one present-day country, and names that read as a Spanish date.
    - Round 2 rejected a sign language and a festival; a transport line and "geography of Canada" had passed the coordinates test too.
  - **P17 golds and wrong options** are present-day sovereign states. No wrong option is the country of another place with the same name (there is a Toronto in England).
  - **P19 wrong options** neither contain nor lie in a true birthplace (P131/P17).
  - **P106 wrong options** are neither a broader or narrower occupation (P279) of a true one ("actor" for a "film actor") nor a kind of an occupation the subject already falls under ("postdoctoral researcher" for a biochemist).
  - **English "the"** before place names that start with an ordinal ("the 2nd arrondissement of Lyon") and before P17 subjects ("The Northwest Territories …").
  - **P36 subjects** have a single capital in Wikidata. Historical states with several capitals are out.
  - **Applied by repair, not by redrawing.** `build_probes.py --repair-round2` reproduces the round-2 sets exactly, then:
    - replaces rejected or rule-breaking probes with the next eligible subject of the same stratum;
    - re-draws only the rule-breaking wrong options;
    - applies the "the" rule.
    - Facts: `build_probes.py --filters-r2` (`data/probes/wikidata_filters_r2.json`). Changes: `data/probes/repair_round2.json`. Round-2 files: `data/probes/round2_2026-10-14/`.
- **HUMAN** (Gate 1): both authors split 60 BN probes and 60 EN probes; the spot-check CSV shows the gold sentence and the three distractor sentences; reject if the gold sentence is false or ungrammatical, or if a distractor sentence is true or ungrammatical in a way the gold is not; rejected probes are replaced by rebuilding for that language.
- Floor rule (Gate 2): a stratum or language whose generation-0 recall CI includes chance (0.25) is rebuilt (easier relations or more frequent subjects) before Gate 1 closes, else excluded from H1(iii) and reported.

## 4. Bias probes (within-language drift only)

- BN: BanStereoSet (Findings ACL 2025; arXiv 2409.11638), stereotype vs anti-stereotype pairs; licence unstated in its repository. **Decided 2026-10-13 (REQ-005):** used for evaluation only, cited, never redistributed, missing licence disclosed in the data statement; the authors email the dataset authors for permission during writing (G7).
- EN: CrowS-Pairs (CC BY-SA 4.0), frozen choice (BBQ-lite dropped). Scored by total log-likelihood preference; per-pair NLLs stored. The two sets differ in construct and categories, so no cross-language comparison is made.

## 5. Generation prefixes

Fixed set of 10,000 prefixes per language: the first 12 **words** of randomly sampled seed documents (seed 20261010), converted to a per-language token count from the measured words-per-token of that seed corpus (≈ 16 Gemma tokens for English, more for Bangla), stored as text **and token ids** so re-tokenisation cannot change the prefix or split a Bengali grapheme cluster. The same prefixes are used at every generation so topic coverage stays comparable (topic-tail collapse is therefore out of scope by design, stated). Every generation request carries its own seed, so a prefix reused within a corpus gets a new continuation. The first 2,000 prefixes in file order are the fixed sample prefixes used to evaluate every checkpoint. Continuations: up to 190 words (per-language token cap), temperature 1.0, top-p 1.0; the top-p 0.95 robustness pair is the only other setting.

## 6. Outputs of this stage

`data/corpora/{EN,BN}_seed.jsonl` (+ `*_seed_minhash.npy` caches), `data/heldout/{EN,BN}_heldout.jsonl` (regular + fresh with a `fresh` flag), `data/probes/{EN,BN}_tail_facts.jsonl`, `data/probes/{EN,BN}_bias.jsonl`, `data/probes/spotcheck_{EN,BN}.csv`, `data/corpora/prefixes_{EN,BN}.jsonl`, `data/corpora/manifest.json` (with per-language `prefix_tokens` and `max_new_tokens`), and `signoffs/G1_corpora.md`.
