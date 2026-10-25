# Access to the restricted files

Some files of this study are not in the public repository. This page says what they are, who can have them, how to ask, and on which terms.

## What is restricted

| Files | Why |
|---|---|
| The model checkpoints of every chain and generation, including the generation-0 models (117 checkpoints in the verified run archive) | The authors chose not to redistribute them publicly; as Gemma model derivatives they are shared under the Gemma Terms of Use |
| The full synthetic training corpora of every chain (132 files in the verified run archive) | Size, and the text is unscreened model output that may contain false, offensive or personal content |
| The 2,000-document evaluation samples of all 119 evaluated steps | Same reasons; the public `results/samples/` files are 50-document subsets of them |
| The eight post-hoc chains of 24 October 2026 (seeds 2 and 3 of REAL-REPEAT and REPLACE-topp95): their 48 checkpoints and the 24 synthetic training corpora of the top-p 0.95 chains (archive `posthoc2_checkpoints_corpora.tar`, 29.5 GB), their 48 2,000-document evaluation samples and 48 50-document files, the three-seed cross-decoder continuations (`cross_decoder2_samples.jsonl.gz`, 31,200 continuations) and two host logs that echo short sample snippets | Same reasons; the numbers derived from them are public in `results/posthoc_seeds_2026-10-23/` and `results/posthoc_seeds_analysis_2026-10-24/` |
| The post-hoc cross-decoder continuations (`cross_decoder_samples.jsonl.gz`, 2,600 continuations) and `nonword_top_types.csv` | Newly generated, unscreened text; the numbers derived from them are public in `results/analysis/posthoc_review_2026-10-22/` and `results/cg4_posthoc_gpu_results/` |

## Who can ask

Researchers, including the journal's editors and reviewers during peer review, who want the files for research: checking the reported numbers, re-analysis, or follow-up studies.

## How to ask

E-mail the corresponding author, Md Tahidul Islam (info.mdtahidulislam@gmail.com), with your name, your affiliation (or "independent"), the files you need, and what you will use them for. We aim to reply within 14 days. Reviewers can ask through the journal's editorial office. For the checkpoints, please also confirm that you accept the Gemma Terms of Use (https://ai.google.dev/gemma/terms) and the Gemma Prohibited Use Policy (https://ai.google.dev/gemma/prohibited_use_policy), which apply to the checkpoints and to anything you derive from them.

## Terms

By asking for the files you agree to:

1. use them for research only, and not redistribute them or post them publicly;
2. not use them to train models that are deployed or released;
3. not try to identify any person named in the text, and to tell us about personal or harmful content you find;
4. cite the paper and this release when you report results based on them;
5. delete them when your project ends, unless we agree otherwise;
6. if we tell you that content has been removed from a release (for example personal or harmful text reported to us), delete the affected files or replace them with the corrected version we send.

## Delivery and integrity

Files are sent through a private download link, exactly as archived. Their SHA-256 sums are listed in the pack manifest inside the release asset `cg4_sidecars_from_G4b_2026-10-20.zip` (`cg4_sidecars_bundle/pack_manifest_20261016-232223.json`) and, for the cross-decoder files, in `results/cg4_posthoc_gpu_results/SHA256SUMS.txt`; for the 24 October post-hoc runs, in `results/posthoc_seeds_2026-10-23/SHA256SUMS.txt` and the archive manifest `results/posthoc_seeds_2026-10-23/vps/archive/pack_manifest_posthoc2_checkpoints_corpora.json`, so you can check what you receive against the public lists.

## Preservation

The verified run archive (55.7 GB; SHA-256 `f51a5dcbd919ab99392c1ec4921a3e479c53081dedd746d675bfafa68d429a1d`) is kept in two copies, on the authors' storage and on a private cloud drive, for at least five years after the paper is published. The post-hoc archive of 24 October 2026 (`posthoc2_checkpoints_corpora.tar`, 29.5 GB; SHA-256 `057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f`) is kept beside it.
