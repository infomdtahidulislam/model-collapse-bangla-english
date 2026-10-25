# CG4 post-hoc GPU results (2026-10-20T06:27Z)

Diagnostics #17 (`cross_decoder_*`), #19 (`labse_*`) and #18 full (`nonword_*`).

They were run post-hoc, after the internal audit. They are not pre-registered, and no registered number changed.

The pack is `posthoc_gpu_pack/`, written by the PC agent. It was run on the VPS route, with the fixes in `code_as_run/PATCH_NOTES.md`. The request is REQ-032 in `signoffs/REQUESTS.md`.

| Item | Ran on | When (UTC) | Software |
|---|---|---|---|
| #17 `02_cross_decoder.py` | Vast.ai instance 56846008, NVIDIA GeForce RTX 4090, driver 595.71.05, Ireland | 2026-10-20 06:12:44 to 06:27:30 (883 s) | torch 2.8.0+cu129 (image `pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel`), transformers 5.17.0, tokenizers 0.23.3, safetensors 0.8.0, regex 2026.9.29; bf16 |
| #17 numerics probe `scorer_numerics_probe.py` | same host | 2026-10-20, started about 06:14, CSV written 06:15 | same |
| #19 `03_labse_sensitivity.py` | the authors' VPS, CPU | 2026-10-20 05:50:12 to 06:02:58 | torch 2.14.1+cpu, sentence-transformers 6.1.0, LaBSE revision 836121a0533e5664b21c7aacc5d22951f2b8b25b |
| #18 `04_nonword_bigram.py` | the authors' VPS, CPU | 2026-10-20 05:50:10 to 05:56:15 | Python 3.12.10, regex 2026.9.29 |

**Inputs**

- G4b archive `cg4_pack_20261016-232223.tar.gz`, SHA-256 `f51a5dcb…29a1d`.
- #17 used 210 files (26 steps), each checked against the pack manifest on the VPS and again on the host (`code_as_run/inputs_17.sha256`).
- #18 and #19 used `results/g6_extract/`, the G6 extraction of the same archive, with every file checked against the manifest.

**Checks**

- #17 decoder check: OK.
- #17 scorer check: token counts equal for all 1,300 documents. The NLL differences are the size of bf16 rounding (`scorer_numerics_probe.csv`).
- #18 equals robustness (viii) (`nonword_crosscheck_viii.csv`).
