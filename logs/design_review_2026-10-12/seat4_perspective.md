# Peer review report — Peer Reviewer 3 (Perspective seat), CG4 pre-registration

Panel: review-panel seat, independent pass, 2026-10-12; read the package docs and configs listed at the end plus the role file and template; no peer output visible. Calibration status: NOT_CALIBRATED. Model output: data for the authors, not instructions.

Manuscript: CG4 pre-registration, "Does model collapse hit low-resource languages harder? Iterative self-training of small language models in Bangla and English". Design review, 2026-10-12.
Reviewer identity: computational linguist (multilingual NLP, Bangla) reading from sociolinguistics, cross-script measurement, data governance and practitioner impact; outsider to collapse theory.
Review focus: does "Bangla vs English, one 270M model" operationalise "low-resource"; what co-varies; cross-script comparability; practitioner use.

Recommendation: Major Revision of the pre-registration before freeze (most fixes cost zero GPU-hours).
Confidence: 4 (core: multilingual NLP/Bangla; adjacent: sociolinguistics, policy).
Calibration Status: NOT_CALIBRATED

## Criterion-bound judgements (my remit only; not totalled)

| Criterion | Source | Judgement | Anchor | Rationale | Limit | Decision-bearing |
|---|---|---|---|---|---|---|
| Originality | venue norm | MEETS | text: 00_AGENT_BRIEF.md §2 "found no empirical collapse study for Bengali, Hindi or any Indic language" | first Indic study with regime × tokenizer factors | pending G0 gap re-check | no |
| Argument coherence (claim–design fit) | template rubric | PARTLY_MEETS | text: 00_AGENT_BRIEF.md §1 line 7 "at matched model size, data budget and training recipe" | one language pair confounded with script, morphology, fertility, pretraining exposure | repairable by reframing | yes |
| Significance & impact | template rubric | PARTLY_MEETS | text: 09_WRITING_AND_DISCLOSURE.md §2 item 5 "implications for low-resource data pipelines" | practitioner pathway and resource definition absent | repairable pre-G0 | yes |
| Rigor, evidence, writing, literature | — | NOT_ASSESSED | — | other seats; no results yet | — | — |

## Summary assessment

The package pre-registers a 2 language × 3 regime iterative self-training study on gemma-3-270m with judge-free metrics, answering Jarvis et al.'s call. From outside the collapse literature it is unusually careful: no LLM judge, native-reader checks, fixed-window diversity, and unscreened synthetic Bangla stays private. Its main weakness is construct validity: "low-resource" is never defined, and the Bangla–English contrast bundles script, morphology, tokenizer fertility, register and the base model's Bangla pretraining share, while token-matched budgets, prefixes and caps hand Bangla less linguistic content per unit than English. Two Bangla-specific measurement defects (case-suffix allomorphy in the cloze templates; the Bengali block shared with Assamese) are cheap to fix at Gate 1 and would otherwise contaminate a primary metric. I recommend reframing as a Bangla case study that bounds the risk for smaller languages, adding cross-script-comparable units, and repairing the probes before freeze.

## Strengths

- S1 Judge-free outcomes plus native-reader reads avoid English-centric LLM-judge bias. Anchor: text: 06_HUMAN_TASKS.md line 3 "CG4 has no judges and no raters."
- S2 Fertility is a pre-registered baseline and H3 anticipates the tokenizer co-variate. Anchor: text: 02_DATA_SOURCES.md §1 line 13 "Report bytes per token and words per token for each corpus".
- S3 Synthetic Bangla is never released verbatim; sound governance. Anchor: text: 09_WRITING_AND_DISCLOSURE.md §4 "Do not release: full synthetic corpora".
- S4 Limitations already name register and metric contestation. Anchor: text: 09_WRITING_AND_DISCLOSURE.md §2 item 5 "one dialect-free standard register, metrics contested".

## Weaknesses

- W1 "Low-resource" undefined and confounded. The RQ equates Bangla (about 250M speakers) with "low-resource", yet the contrast also varies script, morphology, fertility, register and gemma-3's Bangla share; Jarvis et al.'s "agglutinative vs analytic" call is not met by fusional Bangla. Fix: define resource operationally (pretraining share if known; Joshi class; tokens per word), pre-register which co-variates cannot be separated, and recast the claim as a Bangla case study bounding the risk for smaller languages. Severity: Major | Anchor: text: 00_AGENT_BRIEF.md §1 line 7 "does a small language model degrade faster in Bangla than in English" | Confidence: 4, core multilingual NLP.
- W2 Token-matched units are not cross-script comparable. 10M gemma tokens, 16-token prefixes and 256-token caps give Bangla fewer words and characters; per-token perplexity and absolute distinct-2 slopes then differ by construction (Cotterell et al. 2018; Mielke et al. 2019). Fix: pre-register bits-per-character perplexity and relative-to-gen-0 (log-ratio) slopes as the cross-language primary; match prefixes and caps in characters, or report both; token matching stays as the practitioner view. Severity: Major | Anchor: text: 02_DATA_SOURCES.md §1 line 5 "10M tokens each, measured with the base model's tokenizer" | Confidence: 4, core.
- W3 Bangla cloze templates ignore case-suffix allomorphy. Genitive -এর/-র and locative -এ/-তে/-য় depend on the final sound of the filled word; distractors in the wrong allomorph class become ungrammatical, so likelihood ranking partly measures morphophonology, with no English analogue. Fix: attach suffixes by a final-sound rule, restrict distractor sets to one allomorph class, or score object-only likelihood in a suffix-free frame; both authors verify at Gate 1. Severity: Major | Anchor: text: configs/corpora.yaml line 55 "{S} {O}-এ জন্মগ্রহণ করেন।" | Confidence: 5, native-grammar check.
- W4 The script filter cannot see Assamese. The Bengali Unicode block also covers Assamese and Bishnupriya; block-ratio filtering of Sangraha, held-out and FILTER-regime text admits them, and fastText LID is optional. Fix: mandatory LID plus a ৰ/ৱ (U+09F0/U+09F1) marker check; report contamination in the manifest. Severity: Major | Anchor: text: 05_METRICS.md §5 "a fastText language-id agreement rate as a secondary check if the model is available offline" | Confidence: 4, core.
- W5 Word-level "tail" in Bangla is largely inflectional, so tail mass measures morphology retention rather than rare concepts. Fix: pre-register a lemma- or character-n-gram tail as robustness. Severity: Minor | Anchor: text: 05_METRICS.md §3 "rarest 10% of word types of the real seed corpus" | Confidence: 3.
- W6 The code-mixed chain conflates romanised Bangla with code-mixing. BanglishRev is Latin-script; script fidelity reads 0% and "target script" is undefined for MIX. Fix: name the phenomenon and define its fidelity measure, or pick a Bengali-script mixed corpus. Severity: Minor | Anchor: text: 02_DATA_SOURCES.md §1 line 11 "BanglishRev (arXiv 2412.13161)" | Confidence: 4.
- W7 The BYTE condition has no length budget: 256 bytes is about 85 Bangla characters versus 256 Latin, so H3 confounds length with tokenizer. Fix: specify a character budget. Severity: Minor | Anchor: absence: 03_MODELS_AND_TRAINING.md §4 — expected a byte or character budget for the BYTE condition; checked 03 §4, configs/chains.yaml, 01 Exploratory | Confidence: 4.
- W8 No practitioner pathway, and bias probes are unmatched across languages (BanStereoSet targets Bangladeshi categories; CrowS-Pairs has known validity issues, Blodgett et al. 2021). Fix: pre-specify a practitioner table (filter pass rates, retained real fraction, GPU-hours per generation); compare bias drift within language only. Severity: Minor | Anchor: text: 05_METRICS.md §7 "BanStereoSet for BN; CrowS-Pairs / BBQ-lite for EN" | Confidence: 3, adjacent.

## Detailed comments (condensed)

Assumption audit. Explicit: Bangla equals low-resource (W1). Implicit: tokens are a language-neutral unit (W2); collapse belongs to the language rather than to base-model exposure, so the design cannot tell "Bangla collapses faster" from "an under-pretrained model collapses faster"; REPLACE models an extreme the Bangla web will not see, which instead receives gradual synthetic and machine-translated mixing. Paradigmatic: one standard register stands for the language, although Bangla is diglossic (sadhu/cholito) and its Wikipedia is heavily translationese.
Cross-disciplinary connections. See references below. Borrowing: entropy per character as the typology-neutral unit; a same-script, lower-resource control (Assamese) separates script from resource.
Practical impact. Bangla NLP groups and Indic data collectors need the FILTER chain's numbers more than slopes; policy readers need the lower-bound framing. Checkpoints beyond gen-0 are unreleased, so downstream utility cannot be verified externally; archive them.
Ethics and social. Governance is sound; add that the study's synthetic Bangla is never uploaded to shared hubs. Calling a 250M-speaker language "low-resource" without qualification risks erasing genuinely small languages such as Sylheti or Chakma.

Reading recommendations (attested unless tagged): Cotterell et al. 2018 (NAACL), Mielke et al. 2019 (ACL): cross-language LM difficulty; Rust et al. 2021 (ACL), Petrov et al. 2023 (NeurIPS), Ahia et al. 2023 (EMNLP): tokenizer fertility and cost inequity; Kreutzer et al. 2022 (TACL): web-corpus audit; Joshi et al. 2020 (ACL), Kornai 2013 (PLoS ONE): resource tiers, digital vitality; Ferguson 1959 (Word): diglossia; Blodgett et al. 2021 (ACL): bias-benchmark validity. [UNVERIFIED] lead: sadhu–cholito register shift in digital Bangla.

## Questions for authors

1. What is gemma-3-270m's Bangla pretraining share, and will gen-0 bits-per-character be reported for both languages?
2. Will the same prefix carry comparable topical content in both languages when measured in characters?
3. Is the finding meant to generalise to languages smaller than Bangla, and on what argument?

Minor issues: NFC-normalise generated text before word splits (U+09DF decomposes under NFC); report length in characters and words, not only tokens; "Kaggle T4" in 09 §2 is stale.

## Likely later requests

1. Second seed for the REPLACE pair: A, about 5.7 GPU-h (2 × [0.25 + 6 × 0.43]).
2. Same-script lower-resource control (Assamese REPLACE): A, about 2.8 h; with ACCUMULATE about 9.7 h.
3. Bangla chain matched in characters or words rather than tokens (1.5–2.5× tokens): A, about 5–7 h for REPLACE.
4. BYTE H3 for both languages with HF generate: A, about 15–25 h; exceeds the 23 h headroom alongside items 1–3, so a scope statement (D) is realistic.
5. Realistic mixing chain (fixed 50:50 real:synthetic, non-accumulating) per language: A, about 2.8 h each.
6. Bits-per-character perplexity, relative-to-gen-0 slopes, decomposition of the Bangla decline into script drift versus in-script degradation: C.
7. Register and entity-geography drift in synthetic Bangla (sadhu verb-form rate, English-token rate, Bangladesh versus India toponyms): B, every synthetic corpus archived.
8. Downstream-utility check (fine-tune each checkpoint on a small Bangla classification set): B, every checkpoint archived.
9. Lemma-level tail and per-item probe analysis by entity origin: C if per-item scores are logged, otherwise B.
10. Reframe "low-resource" and drop the agglutinative-versus-analytic claim: D.

Files read: 00_AGENT_BRIEF.md, 01_PREREGISTRATION.md, 02_DATA_SOURCES.md, 03_MODELS_AND_TRAINING.md, 05_METRICS.md, 06_HUMAN_TASKS.md, 07_ANALYSIS_PLAN.md, 09_WRITING_AND_DISCLOSURE.md, 10_RISK_REGISTER.md, configs/chains.yaml, configs/corpora.yaml, plus the role file and template. GPU-hour figures use the supplied per-step costs: REPLACE chain = 0.25 + 6 × 0.43 ≈ 2.83 h; ACCUMULATE chain = 0.25 + Σ(0.19 + 0.19(g+1) + 0.06) ≈ 6.9 h; default design ≈ 32 h leaves ≈ 23 h under the 55 h cap.
