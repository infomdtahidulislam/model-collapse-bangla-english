# 11 — Teardown checklist: download everything before the GPU instance is deleted (revised 2026-10-12)

Applies to any rented GPU machine and, in reduced form, to the end of every Kaggle session. **The agent performs steps 1–6 and reports; a human performs step 7 (deletion) only after step 6 says VERIFY: OK.** Deleting the instance destroys its disk; nothing is recoverable afterwards. Since the design review, the archive keeps **every** checkpoint and every synthetic corpus: that is what lets later reviewer requests be answered without new training.

## 1. Confirm the run is finished (or at a clean stopping point)
```
python harness/run_rented.py --status        # every confirmatory chain at generation 6; robustness phases run or listed as not run
python harness/tests/test_sanity.py --results
```
If a chain is incomplete, either finish it or record the shortfall in `results/deviations.md` before packing.

## 2. Capture the environment and pack
```
python harness/pack_results.py --with-synthetic            # --checkpoints all is the default
```
Writes `logs/environment.json` (pip freeze, GPU name, driver) and `results/packs/cg4_pack_<timestamp>.tar.gz` plus `pack_manifest_<timestamp>.json` with a SHA-256 per file. Contents:
- always: `results/metrics.jsonl`, every `results/chains/*/gen_*/step.json`, `generate.json`, `filter.json`, `filter_log.jsonl`, `train.json`, `sample.jsonl`, `sample_meta.json`, the sidecars (`heldout_nll.jsonl`, `probe_scores.jsonl`, `bias_scores.jsonl`, `sample_scores.jsonl`), `state.json`, `results/samples/`, `results/analysis/` if present, `logs/`, `configs/`, `data/corpora/manifest.json`, prefixes, **seed corpora**, `data/probes/`, `data/heldout/`
- `--with-synthetic`: every `synthetic*.jsonl` (generated, kept, top-up): about 40–60 MB per 10M-token corpus, ≈ 3–6 GB for the whole design
- checkpoints (bfloat16, ≈ 0.54 GB each): generation-0 checkpoints (2 + the re-seeded and word-matched variants) and every generation of every chain: ≈ 43 GB for phases P0–P4, ≈ 63 GB for everything. Use `--checkpoints final` only if the local disk cannot hold the full archive (then the (B)-class reviewer requests need retraining).

## 3. Download the archive and the manifest
From the control machine (the wrapper resolves host and port and uses scp over SSH):
```
python harness/vast/vast_ops.py pull --instance <iid> --remote results/packs --local results/packs
```
Large archives: if the transfer breaks, re-run the same `pull`, or split on the host (`vast_ops.py ssh --instance <iid> -- "split -b 2G results/packs/cg4_pack_<stamp>.tar.gz results/packs/part_"`), pull the parts and join them locally (`cat part_* > cg4_pack_<stamp>.tar.gz` in Git Bash). At ≈ 200 Mbit/s a 50 GB archive takes about an hour.

## 4. Verify locally (on the authors' computer, not on the instance)
```
python harness/pack_results.py --verify results/packs/cg4_pack_<timestamp>.tar.gz
```
Must print `VERIFY: OK`. Any `[missing]` or `[corrupt]` line means: re-download, or re-pack on the instance, before anything is deleted.

## 5. Unpack and re-run the analysis from the downloaded copy
```
tar -xzf results/packs/cg4_pack_<timestamp>.tar.gz -C .
python harness/analyze.py --robustness
```
`results/analysis/analysis_report.md` must regenerate from the downloaded files alone. This proves the paper no longer depends on the instance.

## 6. Second copy
Copy the archive to a second location (an external drive; a cloud drive only if its quota holds 50–70 GB). Record both locations and the archive SHA-256 in `logs/decisions.md`.

## 6b. File the teardown request (agent)
```
python harness/vast/vast_ops.py teardown-request --instance <iid> --archive cg4_pack_<stamp>.tar.gz --sha256 <hex> --verified-on <YYYY-MM-DD> --second-copy "<location>" --analysis-ok yes
```
This appends a `TEARDOWN` block to `signoffs/REQUESTS.md` with the cost so far and the exact human command. The agent then stops.

## 7. Delete the instance (human)
Only after steps 4–6 and with `signoffs/G4b_teardown.md` filled: `vastai destroy instance <iid>` (on this PC: `~/bin/vastai.cmd destroy instance <iid>` from Git Bash, or `vastai destroy instance <iid>` from PowerShell). Delete, do not stop: a stopped instance keeps billing for storage. Confirm in the Vast.ai console that no volumes or snapshots remain; `python harness/vast/vast_ops.py status` must then list no instance.

## Kaggle sessions (reduced form)
After every session: `kaggle kernels output <user>/<slug> -p results/shards_or_chains/` (via `harness/kaggle/push_and_poll.py --poll`), then `python harness/run_chain.py --status`; synthetic corpora of ACCUMULATE chains and the latest checkpoints must be re-attached as a dataset for the next session, so download them too.

## Sign-off
`signoffs/G4b_teardown.md` records the archive name, SHA-256, verify result, both storage locations, and the deletion date.
