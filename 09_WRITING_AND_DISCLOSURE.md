# 09 — Writing, disclosure and release

## 1. Publication venue
Publication planning is not part of the study record and is not kept here.

## 2. Manuscript skeleton (plan approved first, then the full text)
1. Introduction: synthetic text is entering training data everywhere; collapse evidence is English-only; the position paper's call; RQ and hypotheses.
2. Related work: model collapse and its theory (Shumailov et al. 2024; Dohmatob et al. 2024; Gerstgrasser et al. 2024; Guo et al. 2024); fairness collapse (Proskurina et al. 2026); low-resource threat (Jarvis et al. 2026); tokenizer fragmentation in Bangla (Bhowmik et al. 2025; Roy et al. 2026); Bangla resources. Resolve every identifier before citing.
3. Method: corpora and matching (tokens, words, bytes; word-matched lengths); paired probes; base model and its generation −1 metrics; regimes; generation (per-request seeds, prefix masking) and training recipes; metrics and units (bits per byte, log-ratio slopes); pre-registration link and the design-review record; compute (one rented RTX 4090, bfloat16, GPU-hours used).
4. Results: anchor first (H0), then H1, H2 with the decision rule; seed replicates and the three controls (word-matched English, no-synthetic, compute-matched accumulation) where run; per-stratum recall; generated-text perplexity under the gen-0 model; exploratory bias drift; robustness; qualitative samples (screened) with the rubric counts.
5. Discussion: implications for Bangla data pipelines and, as a hypothesis, for smaller languages; limitations (one language pair, one base model, inseparable co-variates of language: script, morphology, fertility, corpus curation, base-model prior; one seed per cell except the REPLACE pair; 10M-token budget; six generations; one dialect-free standard register; metrics contested; robustness phases not run under the cap listed); what would falsify the claim.
6. Ethics, disclosure, data availability, CRediT.

For G7 (decided 2026-10-18 with G5, `signoffs/G5_human_read.md`): report the optional fluency rating in short form in the human-read part, for example: "Both authors also rated fluency (1–5) on a fixed 20-prompt subset of each read file and of generation 0; agreement was quadratic-weighted kappa 0.813 [0.761, 0.854] over 259 pairs. The English generation-0 set was excluded because its independence could not be established." Numbers from `results/human_read/G5_checks/fluency_agreement.md` (the version without GEN0-EN); the full table stays in that file.

## 3. AI-use disclosure (adapt to the journal template)

The paragraph below is a planning placeholder; the final declaration is in the article.
"Study design, literature scan and the experiment harness were developed with the help of AI tools. All outcome metrics are computed automatically; no language model was used to judge or label outputs. The authors designed the hypotheses, verified corpora and probe sets, read generated samples, interpreted the results and wrote the manuscript."

For G7 (recorded 2026-10-17): in the G5 human read both authors used Grammarly to correct the grammar of their English reading notes; every code was assigned by the authors (`signoffs/G5_human_read.md`, Notes). This does not conflict with the sentence above. Check the venue's AI policy at G7 for whether grammar-tool use should be mentioned, for example: "The authors' reading notes were grammar-checked with Grammarly; all qualitative codes were assigned by the authors."

## 4. Release policy
Release: harness, configs, corpus manifest with document ids and source pointers (not redistributed text where licences forbid it), probe sets, metric records, step records with checkpoint hashes, analysis outputs, and the screened 50-sample files. Do not release: full synthetic corpora (size and possible toxic content; available on request under a research agreement), model checkpoints beyond generation 0 unless licence terms of the base model permit, any token or key.

## 5. Authorship (agreed 2026-10-13)
1. **Md Tahidul Islam** — corresponding author; ORCID 0009-0004-6798-892X; info.mdtahidulislam@gmail.com.
2. **Maksuda Akter** — ORCID 0009-0004-5808-518X; srabontikhan50@gmail.com.

Affiliation (both): Department of Computer Science and Engineering, CCN University of Science & Technology, Cumilla, Bangladesh. Both are bachelor's students; no supervising faculty author (the authors may add one before submission; it would need a line in `results/deviations.md` only if it changes who does a gated human task).

CRediT roles: by the authors' decision of 2026-10-13 the roles are assigned at Gate 7 from the record of who did what (`signoffs/` and `logs/decisions.md` name the person for every human task), not in advance. The manuscript's CRediT statement lists human contributions only; the AI-assisted parts are covered by the disclosure in section 3.

## 6. Pre-registration, ethics, funding and competing interests (stated by the authors 2026-10-13)
- Pre-registration statement: "The study design, hypotheses, decision rule, robustness ladder and analysis plan were pre-registered on the Open Science Framework before any training run (registered 13 October 2026, public, DOI 10.17605/OSF.IO/SRA28; https://osf.io/sra28/). The registration archives the frozen pre-registration document, the chain and corpus configuration files and a SHA-256 freeze record." Cite the DOI in the Method section (skeleton item 3) and in the Data Availability statement; any deviation goes in the deviations table with a pointer to the registered text.
- Ethics statement: "This study involved no human participants; it used publicly available text corpora and model outputs only. The authors' institution has no research ethics committee, and no ethics review was sought. The study was conducted independently by the authors." (Add, for venues with an ethics-statement section: the synthetic Bangla and English corpora are not released and never uploaded to shared hubs; see section 4.)
- Data statement, BanStereoSet (REQ-005, 2026-10-13): "The Bangla bias probe uses BanStereoSet (Kamruzzaman et al., Findings of ACL 2025), obtained from the authors' public repository, which carries no explicit licence. It was used for evaluation only and is not redistributed with this work." If the dataset authors reply to the permission email, add: "The dataset authors granted permission for this use on [date]."
- Funding statement: "This research received no external funding. The rented GPU time was paid for by the authors."
- Competing interests: "The authors declare no competing interests."
- Data and code availability: as in section 4.
