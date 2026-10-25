## REQ-035 | 2026-10-24T00:47:43+00:00 | BUDGET + DECISION | Status: DONE
**Ask:** Run `posthoc_gpu_pack2_2026-10-23/` from the VPS (post-hoc, not pre-registered; it changes no registered file, number, test or verdict). Authors' decision (chat, 2026-10-22T22:36Z; confirmed 2026-10-24): run two more seeds per language of REAL-REPEAT and of the top-p 0.95 chain, a larger cross-decoder sample, and the equal-length diversity check on the full 2,000-document samples. It runs three parts:
- (A) eight chains, EN/BN-REAL-REPEAT-s2/-s3 and EN/BN-REPLACE-topp95-s2/-s3, six generations each with the registered recipe, on one rented RTX 4090;
- (B) the cross-decoder evaluation over seeds 0, 2 and 3: 12 REPLACE-family chains at generations 1 to 6 plus six generation-0 models, under both decoders, 200 prefixes per cell (156 cells);
- (C) the equal-length diversity check (Table S12 statistic) on the full 2,000-document samples of all 25 chains, on the VPS CPU.
Budget: a hard cap of **US$15** for this pack (`--budget-usd 15`; all charges: GPU, disk, bandwidth), plus a CG4 ceiling above REQ-020's US$50, because US$38.84 spent plus US$15 comes to US$53.84.
**Evidence:**
- The pack zip's SHA-256 is 0747a7788f074422548f0f9b8a83bb9116c06a65c3eaa49ee273f6ca82e44042, as the authors gave it. The folder in the package root is byte-identical to the zip, and `SHA256SUMS.txt` checks 9 of 9 OK (this VPS, 2026-10-24T00:4xZ). The 22 key package files that the stager sends to the host match the run's SHA-256.
- The pack's estimate (README_RUN.md section 1) is about 19 to 20 GPU-hours, roughly US$9 at US$0.45/h: A about 15.2 h, B about 3 h, setup about 1 h. The run uses `--max-hours` = (15 − spend − 2 reserve) / price. If the cap gets close, priorities 8 to 11 keep complete second seeds.
- Spend before this pack: US$38.84 (invoices, REQ-033, 2026-10-20T07:18Z). It is re-read from the invoices with `vast_ops.py status` before any rental.
- GPU-hours: REQ-020 also set a 100 GPU-h ceiling. The instance records' running times suggest about 75 to 80 GPU-h used so far (the exact figure comes from the invoices). This pack adds about 20 h, so the total could reach about 95 to 100 GPU-h.
- This is a new VPS (Windows Server 2025, installed 2026-10-22). Not yet here:
  - the G4b archive `results/packs/cg4_pack_20261016-232223.tar.gz` (55.69 GB, SHA-256 f51a5dcb…29a1d) and `pack_manifest_20261016-232223.json` (step 1 stages from them, and step 9 needs the archived sample files);
  - the Hugging Face token in `.env`;
  - Python 3.12 and the venv;
  - an SSH key on the Vast account.
**Human reply:** "Authors' approval: run the pack now; cap US$15 for this pack; study ceiling raised from US$50 to US$55." (chat, 2026-10-24, received before 00:46:50Z). Recorded:
- **Pack cap US$15.**
- **CG4 hard ceiling US$55 in total**, replacing REQ-020's US$50.
- Still open (asked in chat 2026-10-24): is REQ-020's 100 GPU-h ceiling raised as well? Until the reply, both limits apply.
- Answer: "And yes the GPU hours celling increased as requested." (chat, 2026-10-24, received before 01:03:23Z). The agent had proposed the reply "raise the GPU-hour ceiling to 125", so: **CG4 hard ceiling US$55 and 125 GPU-h in total**, replacing REQ-020's US$50 / 100 GPU-h. REQ-035 DONE. The run itself still waits for the G4b archive from Google Drive and HF_TOKEN in `.env`.

## REQ-036 | 2026-10-24T16:15:09+00:00 | TEARDOWN | Status: PENDING
**Ask:** Delete Vast.ai instance 57450903 (label CG4-posthoc2, RTX 4090 in Pakistan, US$0.616/h; REQ-035). It ran `posthoc_gpu_pack2_2026-10-23`.
- It is stopped (2026-10-24T16:13:38Z). Its disk still bills about US$0.056 an hour until it is deleted.
- It holds the uploaded inputs (batch A and B: archive files checked against the G4b manifest, package files checked against the run's hashes), the eight new chains' weights, synthetic corpora and samples, and the cross-decoder continuations (unscreened text). All of these go with it.
**Evidence:**
- **Jobs finished:** `posthoc2_chains` CHAINS_DONE at 14:27:14Z (48 of 48 steps; `logs/posthoc2_incomplete.txt` empty); `posthoc2_xdec` XDEC_DONE at 15:42:17Z (156 cells; `decoder_check_ok` true); `posthoc2_pack` PACKED at 15:46:21Z.
- **Results pulled and checked** (`results/posthoc_gpu_stage2_2026-10-23/pull/`, 15:47 to 16:13Z):
  - `posthoc2_results_small.tar.gz` (87,968,542 bytes) has SHA-256 6e64ffbbd33cebe7a418918a00e44da57f60f33c2ca1c39d234fbd8b1fa98a16, the same on the host and the VPS.
  - `posthoc2_checkpoints_corpora.tar` (29,495,818,240 bytes) has SHA-256 057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f, the same on the host and the VPS. It is now in `results/packs/` beside the G4b archive, with `pack_manifest_posthoc2_checkpoints_corpora.json` (264 members) and `posthoc2_checkpoints_corpora.tar.sha256`.
  - All 685 files in the host's `posthoc2_files.sha256` match on the VPS: 421 from the small pack (unpacked into `results/posthoc_seeds_2026-10-23/host/`) and 264 members of the big tar.
  - The 10 `logs/posthoc2_*` files are the same on both.
- **Nothing else on the host is needed.** A scan of `/workspace/CG4` for files in neither pack nor the uploaded inputs found only `shared/tokenizer.json`, `logs/environment.json` (both pulled and SHA-256-checked, in `pull/host_other/`) and the four SHA-256 lists (pulled or already on the VPS).
- **Cost:** US$8.95 invoiced for this instance at 16:14Z (14.4 GPU-h; cap US$15). CG4 total US$47.79 of the US$55 ceiling: US$47.50 in the invoice query plus US$0.29 for 56846008, which it does not list.
- **Copies:** after the deletion, the VPS holds the only copy of the eight chains' weights and synthetic corpora until the second copy (README_RUN step 8: Google Drive, folder CG4_backup) is made. The authors may prefer to make that copy first.
**Human command:** `vastai destroy instance 57450903`. In the `!` shell: `"/c/Users/Administrator/Desktop/Terminal gaps/.venv/Scripts/vastai.exe" destroy instance 57450903 -y`. Then confirm that no volumes remain.
**Human reply:** [ ]
