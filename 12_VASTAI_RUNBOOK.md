# 12 — Vast.ai runbook for CG4 (agent-operated, author-gated; revised 2026-10-12)

The ordered step list for the whole GPU phase on one rented RTX 4090 host. Every command is exact and runs from this package folder on the **control machine** (since 2026-10-13 the authors' Windows Server VPS running Claude Code, REQ-006) unless marked **host**; host commands are sent with `vast_ops.py run/ssh`. Human steps and the request types the agent files (`signoffs/REQUESTS.md`, protocol in `..\AGENT_PIPELINE.md` §6) are interleaved. Budget: `04_RUN_PLAN.md` §3; teardown: `11_TEARDOWN_CHECKLIST.md`; gates: `08_GATES_AND_CHECKLISTS.md`. Nothing after a gate runs while that gate is OPEN. On the VPS the Vast.ai CLI is `vastai` from the project venv `..\.venv` (first on PATH); the laptop needed `%USERPROFILE%\bin\vastai.cmd` (`..\PRE_START_CHECKLIST.md` §H). `vast_ops.py` finds either by itself.

Budget frame (pre-pilot estimates, `harness/vast/plan_budget.py`): confirmatory design ≈ 35 GPU-h; with the pre-registered robustness phases in order: 41 h (+ second seed), 42.5 h (+ word-matched EN), 46 h (+ no-synthetic control), 49 h (+ REPLACE to generation 10), 55 h (+ third seed), 61 h (+ compute-matched accumulation), 66 h (+ top-p 0.95). Cap options A/B/C in `04_RUN_PLAN.md` §3; the approved cap and the measured rates after the pilot decide how many phases run.

## 1. Offline preparation (control machine; no money spent)

```powershell
cd "D:\Terminal gaps\CG4_model_collapse_lowresource_experiment"
python harness\tests\test_sanity.py                            # must print RESULT: PASS
python harness\fetch_sources.py --dry-run                      # plan of sources and licences (no network)
python harness\vast\plan_budget.py                             # the phase ladder, GPU-hours, cost, cap options
python harness\run_rented.py --plan                            # the exact job order the host will execute
python ..\scripts\gap_check.py CG4_recheck "model collapse low-resource language Bengali Bangla synthetic data recursive training" "--arxiv=all:\"model collapse\" AND (all:Bengali OR all:Bangla OR all:\"low-resource\")" > logs\gap_recheck_2026-MM-DD.txt
```
- The gap re-check (G11/G28; add `--no-openalex` on HTTP 429) is Gate 0 evidence. A new empirical Bangla/Indic collapse study → file a `DECISION` request with the sub-gap restated; do not proceed.
- File three requests and stop: `DECISION` (the design-review changes to confirm, `signoffs/REQUESTS.md` REQ-001), `BUDGET` (cap option A/B/C) and `GATE` G0 (`signoffs/G0_preregistration.md`, ethics statement, authorship, prereg freeze). `.env`, the Gemma licence and the SSH key were completed on 2026-10-12; REQ-001 and REQ-002 were resolved on 2026-10-13 (cap B) and the sign-off was pre-filled the same day.
- **HUMAN:** DECISION replied, BUDGET DONE, G0 PASSED, balance loaded. Nothing is rented before all four.

## 2. Rent (control machine)

Criteria: `RTX_4090`, 1 GPU, ≥ 24 GB VRAM, **≥ 200 GB disk** (checkpoints ≈ 0.54 GB × up to 120, synthetic corpora ≈ 6 GB, sources ≈ 3 GB, vLLM/torch ≈ 15 GB), reliability > 0.98, ≥ 200 Mbit/s down, CUDA ≥ 12.8, price ≤ US$0.45/h. Interruptible (bid) offers are acceptable because every stage is cached and `run_rented.py` resumes; a stage in progress (≤ 1.5 h) is lost on interruption. On-demand is simpler; use it if the price difference is < US$0.10/h.

```powershell
python harness\vast\vast_ops.py search --gpu RTX_4090 --max-price 0.45 --min-disk 200 --min-cuda 13.0   # add --interruptible to see bid offers; 13.0: generation 0 ran torch 2.13.0+cu130
python harness\vast\vast_ops.py create --offer <offer_id> --label CG4-run1 --disk 200 --budget-usd 30 --max-hours 70   # cap B, approved 2026-10-13 (signoffs/REQUESTS.md REQ-002)
python harness\vast\vast_ops.py wait --instance <iid>                                             # until "SSH ready" and the GPU line
python harness\vast\vast_ops.py status                                                            # confirms price and 0.0 h
```
Record offer id, instance id, price and GPU in `logs/decisions.md` (the wrapper does this). If `wait` times out, `status` shows the instance; if it never reaches `running`, file a `TEARDOWN` request for it and pick another offer.

## 3. Host setup, sources, corpora and probes (Gate 1 evidence)

```powershell
python harness\vast\vast_ops.py push --instance <iid>                 # package code + configs (no results/sources)
python harness\vast\vast_ops.py push-env --instance <iid>             # /workspace/.env, mode 600
python harness\vast\vast_ops.py run  --instance <iid> --name bootstrap -- bash harness/vast/bootstrap.sh
python harness\vast\vast_ops.py tail --instance <iid> --name bootstrap          # until "[bootstrap] done"; check "HF login ok" and the vLLM/transformers versions
python harness\vast\vast_ops.py run  --instance <iid> --name fetch -- python harness/fetch_sources.py --all
python harness\vast\vast_ops.py tail --instance <iid> --name fetch              # until "done: [...]"; exit code 1 means a required source is missing
python harness\vast\vast_ops.py run  --instance <iid> --name corpora -- "python harness/prepare_corpora.py --dry-run && python harness/prepare_corpora.py --build"
python harness\vast\vast_ops.py tail --instance <iid> --name corpora            # "[ok] manifest written"; check the 2% token-match warning and the per-language lengths
python harness\vast\vast_ops.py run  --instance <iid> --name probes -- "python harness/build_probes.py --fetch --build --bias --spotcheck-csv"
python harness\vast\vast_ops.py tail --instance <iid> --name probes             # "[pool] N triples eligible in both languages"; 200 per stratum expected
python harness\vast\vast_ops.py ssh  --instance <iid> -- python harness/tests/test_sanity.py
python harness\vast\vast_ops.py pull --instance <iid> --remote data/corpora/manifest.json --local data\corpora\manifest.json
python harness\vast\vast_ops.py pull --instance <iid> --remote data/sources/SOURCES_MANIFEST.json --local data\sources\SOURCES_MANIFEST.json
python harness\vast\vast_ops.py pull --instance <iid> --remote data/probes --local data\probes          # spotcheck_EN.csv, spotcheck_BN.csv (gold + 3 distractor sentences), probe and bias files
```
- Timing: bootstrap ≈ 10 min; fetch ≈ 20–40 min; corpora ≈ 20–30 min (tokenizer counting + MinHash over ~160k docs); probes ≈ 10 min (Wikidata SPARQL is rate-limited; `--fetch` retries). Total ≈ 1–1.5 h ≈ US$0.50.
- File the `GATE` G1 request (evidence: both manifests, both spot-check CSVs, the bias files, the sanity-test output). The BanStereoSet licence is already decided (REQ-005, 2026-10-13: use for evaluation only, cite, disclose); no LICENCE request is needed unless a new source appears. Then, per REQ-004, start the base metrics and generation 0 for both languages while waiting for the G1 reply.
- **HUMAN (both authors read Bangla):** split the 60 BN and 60 EN probes (each row shows the gold sentence and three distractor sentences); return `data/probes/spotcheck_*.csv` with verdicts (`vast_ops.py push` sends the edited CSVs back; rejected probes are replaced by `build_probes.py --build --spotcheck-csv` for the affected language); fill `signoffs/G1_corpora.md`.
- **Idle cost while waiting:** ≈ US$0.40/h (≈ US$10/day) while running; ≈ US$0.08/h (≈ US$2/day) stopped, which is the 200 GB disk only. Options the agent chooses explicitly and logs:
  - (a) Keep it running if the authors answer within a few hours. The authors can pre-approve in the BUDGET reply that base metrics and generation 0 may run before G1: they depend only on the corpora, which the human check rarely changes.
  - (b) Otherwise pull results and checkpoints, then `stop --instance <iid> --reason ...`. The disk, the environment and every file stay. When the authors answer, run `start --instance <iid>`, then `wait`. If the GPU was rented by someone else meanwhile, the start stays in `scheduling`: rent a new instance and re-push the data and the pulled checkpoints (§7). `status` counts GPU-hours against the cap only while the instance runs; stop/start times are recorded in `logs/vast_events.jsonl`.
  - **Authors' rule (2026-10-14): always copy everything to the VPS before stopping an instance.** That means results, checkpoints, logs, and any host-only data needed to continue elsewhere. Check that nothing on the host is newer than the pull, then stop. A stopped instance may never restart.
  - **Risk of (b), seen on 2026-10-14:** the stopped instance's GPU was rented by someone else within 4 hours, and the restart then waited in `scheduling` ("hours to weeks"). Its data could leave only through Vast's instance-to-instance copy, which failed between two hosts (`Permission denied (publickey)` for `vastai_kaalia`). Before stopping, pull everything needed to continue elsewhere: results, checkpoints, and `data/sources` if a corpus rebuild is possible. If the wait is only a few hours, prefer (a).
  - (c) For a wait of more than about a day: pack (`pack_results.py --checkpoints none`), `pull`, `stop`, and file a `TEARDOWN`; the next instance repeats §3 in ≈ 1 h.

## 4. Base metrics, generation 0 and the pilot (Gates 2 and 3)

```powershell
python harness\vast\vast_ops.py run  --instance <iid> --name smoke -- python harness/tests/smoke_gpu.py   # added 2026-10-13: train -> vLLM -> score -> vLLM on a few dozen docs in /workspace/smoke_gpu (minutes); must end with "RESULT: PASS" before gen-0 starts on a new host
python harness\vast\vast_ops.py run  --instance <iid> --name gen0 -- "python harness/run_chain.py --base EN && python harness/run_chain.py --base BN && python harness/run_chain.py --gen0 GEN0-EN --session-id gen0 && python harness/run_chain.py --gen0 GEN0-BN --session-id gen0"
python harness\vast\vast_ops.py tail --instance <iid> --name gen0            # base ≈ 5 min per language; gen-0 ≈ 15–25 min per language on a 4090
python harness\vast\vast_ops.py ssh  --instance <iid> -- python harness/run_chain.py --status
python harness\vast\vast_ops.py pull --instance <iid> --remote results/metrics.jsonl --local results\metrics.jsonl
python harness\vast\vast_ops.py pull --instance <iid> --remote results/samples --local results\samples            # BASE-*_base_50.jsonl, GEN0-*_gen0_50.jsonl
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/GEN0-EN/step.json --local results\chains\GEN0-EN\step.json
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/GEN0-BN/step.json --local results\chains\GEN0-BN\step.json
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/GEN0-EN/checkpoint --local results\chains\GEN0-EN\checkpoint   # 0.54 GB each; protects against a lost instance
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/GEN0-BN/checkpoint --local results\chains\GEN0-BN\checkpoint
```
- G2 evidence (`03_MODELS_AND_TRAINING.md` §6): from `results/metrics.jsonl` the `BASE-*` (generation −1) and `GEN0-*` rows for `log_ppl_heldout`, `bpb_heldout`, `tail_fact_recall_{HEAD,MID,TAIL}` (floor rule: CI above 0.25), the gen-0 `sample_meta.json` (`exact_duplicate_rate` ≤ 0.05, `empty_rate` ≤ 0.05, cap-hit rate) and `script_docs_ge95`; `logs/environment.json` (versions). File `GATE` G2 and stop. Pre-approval option: the authors may pass G2 on the numbers alone within the same day.
- Pilot (after G2 PASSED): one REPLACE step per language, then the measured projection.
```powershell
python harness\vast\vast_ops.py run  --instance <iid> --name pilot -- python harness/run_rented.py --gpus 1 --skip-gen0 --skip-robustness --chains EN-REPLACE BN-REPLACE --until 1
python harness\vast\vast_ops.py tail --instance <iid> --name pilot          # ≈ 30–40 min per language
python harness\vast\vast_ops.py pull --instance <iid> --remote results/samples --local results\samples        # EN-REPLACE_gen1_50.jsonl, BN-REPLACE_gen1_50.jsonl
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/EN-REPLACE/gen_1/step.json --local results\chains\EN-REPLACE\gen_1\step.json
python harness\vast\vast_ops.py pull --instance <iid> --remote results/chains/BN-REPLACE/gen_1/step.json --local results\chains\BN-REPLACE\gen_1\step.json
python harness\vast\vast_ops.py ssh  --instance <iid> -- "python harness/vast/plan_budget.py --measured"       # writes logs/throughput.csv on the host, prints the measured ladder
python harness\vast\vast_ops.py pull --instance <iid> --remote logs --local logs\host_<iid>          # into a subfolder: never over the control machine's logs\decisions.md (2026-10-13)
```
- G3 evidence: both 50-sample files, both `step.json` (generation record with duplicate/empty rates and lengths in words; train record; sample record), the measured ladder. State which robustness phases fit under the approved cap (the pre-registered order decides which); if even the confirmatory design exceeds the cap, file a `BUDGET` request (raise) or propose scale rule 2 (10M → 5M tokens) as a `DECISION`. File `GATE` G3 and stop.
- **HUMAN:** read the samples (bug-as-insight check), confirm the phases, fill `signoffs/G3_pilot.md`.

## 5. Full run (Gate 4)

```powershell
python harness\vast\vast_ops.py status                                         # hours used so far (H_used)
python harness\vast\vast_ops.py run  --instance <iid> --name chains -- python harness/run_rented.py --gpus 1 --skip-gen0 --max-priority <P> --max-hours <max_hours - H_used - 2>
python harness\vast\vast_ops.py tail --instance <iid> --name chains           # "=== P1 confirmatory chains", then "[gpu0] ... START/END" lines; a step every 0.5–2 h
python harness\vast\vast_ops.py ssh  --instance <iid> -- python harness/run_chain.py --status
python harness\vast\vast_ops.py status                                         # cost vs cap: at least every 2 h of wall-clock
```
- `<P>` is the highest robustness priority the authors approved at G3 (omit to run every phase the deadline allows); `--max-hours` stops NEW steps before the cap, a step in progress finishes.
- **Dollar ceiling (authors, 2026-10-14): CG4 must not exceed US$50 in total (REQ-020; it was US$40), including what is already spent and the final pack and download.**
  - Set `--max-hours` from dollars, not only from GPU-hours: `(50 - invoiced spend from vast_ops.py status - 6) / price per hour`.
  - The US$6 reserve covers the step in progress and G4b. G4b is an archive of about 45–70 GB, and this host bills US$0.039/GB, plus 2–3 h of instance time.
  - If a phase does not fit, the pre-registered priority order drops the last ones first (P7, then P6) and reports them as not run. The pilot's generation 1 of the two REPLACE chains is reused; `run_rented.py` skips completed work and can be re-run with the same command after any interruption.
- Interim pulls (cheap; protect against a lost interruptible instance): after every finished ACCUMULATE generation, `pull --remote results/metrics.jsonl`, `pull --remote results/samples`, and the chain's latest `checkpoint` directory.
- Expected (pre-pilot): REPLACE chain ≈ 2.8 h, ACCUMULATE and FILTER ≈ 6.5–7.5 h each, confirmatory total ≈ 35 GPU-h ≈ 1.5 days wall-clock; robustness phases as in §0.
- G4 evidence: `run_chain.py --status` (every confirmatory chain at generation 6; robustness phases listed as run / not run), `python harness/tests/test_sanity.py --results` on the host, the step records. File `GATE` G4 together with the teardown evidence of §6 (one request pair, one human sitting).

## 6. Pack, pull, verify, analyse, teardown request (Gate 4b)

```powershell
python harness\vast\vast_ops.py ssh  --instance <iid> -- "python harness/run_rented.py --status && python harness/tests/test_sanity.py --results"
python harness\vast\vast_ops.py run  --instance <iid> --name pack -- python harness/pack_results.py --with-synthetic
python harness\vast\vast_ops.py tail --instance <iid> --name pack             # "[ok] N files, X GB uncompressed -> results/packs/cg4_pack_<stamp>.tar.gz"
python harness\vast\vast_ops.py pull --instance <iid> --remote results/packs --local results\packs       # archive (≈ 45–70 GB with all checkpoints) + pack_manifest_<stamp>.json
python harness\pack_results.py --verify results\packs\cg4_pack_<stamp>.tar.gz                           # control machine: must print VERIFY: OK
tar -xzf results\packs\cg4_pack_<stamp>.tar.gz -C .                                                      # Git Bash tar; or 7-Zip
python harness\analyze.py --robustness                                                                   # results/analysis/analysis_report.md regenerates from the download alone
Get-FileHash results\packs\cg4_pack_<stamp>.tar.gz -Algorithm SHA256                                      # record in logs/decisions.md with both storage locations
python harness\vast\vast_ops.py teardown-request --instance <iid> --archive cg4_pack_<stamp>.tar.gz --sha256 <hex> --verified-on 2026-MM-DD --second-copy "<drive path>" --analysis-ok yes
```
- The second copy goes to an external drive (50–70 GB). `scp` resumes badly on a large archive: if a pull fails midway, re-run the same `pull` or split on the host (`11_TEARDOWN_CHECKLIST.md` §3).
- File `GATE` G4b with the `TEARDOWN` request. **HUMAN:** fill `signoffs/G4b_teardown.md`, then `vastai destroy instance <iid>`, then confirm in the console that no volumes remain. The agent never destroys.
- `vast_ops.py status` must show no instance afterwards; keeping the host for phases that did not fit the cap is a new `BUDGET` request.

## 7. Resume after an interruption

- Stopped instance whose GPU was rented by someone else meanwhile (`start` stays in `scheduling`): rent a new instance (§2, `--min-cuda 13.0`), then `push`, `push-env` and bootstrap. `bootstrap.sh` installs the generation-0 library versions from `harness/vast/pins_gen0.txt` and stops on any mismatch (log it, and note a changed stack in `results/deviations.md` before any chain step). Copy `results/` from the VPS to the host with `scp -r` (`push` skips `results/` and `.safetensors`; the generation-0 checkpoints are in `results/chains/GEN0-*`). Check each copied `checkpoint/` directory against `checkpoint_sha256` in that chain's `step.json`, then continue. That value is `harness/common.py` `sha256_dir`, a hash over every file in the directory, not over `model.safetensors` alone. The old stopped instance still bills its disk: file a `TEARDOWN` for it once the new host holds everything.

- Job died, instance alive (OOM, crash, SSH drop): fix the cause (§8), then re-run exactly the same `run` command; every stage is cached (`generate.json`, `filter.json`, `train.json`, `sample_meta.json`), so at most one stage is repeated.
- Interruptible instance lost (outbid) or host failure: the disk is gone. A new instance repeats §2–§3 (≈ 1 h, no human gates needed if the configs are unchanged: corpora are deterministic given the sources and seed, but the manifest SHA-256 must match the Gate 1 manifest; if the upstream data changed and the hashes differ, file a `DECISION`). Generation 0 is retrained unless its checkpoints were pulled (§4 does that). Chain progress resumes from the last pulled checkpoint; without checkpoints a chain restarts at generation 1. Log the loss in `results/deviations.md` only if it changes what is reported (it should not: the re-run is the same design and seed).

## 8. Failure handling (fix, log in `logs/decisions.md`, never a finding)

| Symptom | Likely cause | Action |
|---|---|---|
| `NaN loss` SystemExit in a step | numerical issue (bf16 is the stable setting for gemma-3; a NaN is then a real bug) | retry once as is; on the second NaN lower `training.micro_batch_seqs` in `configs/runtime.yaml` (already 4 since 2026-10-13, so 2; effective batch unchanged); third NaN → `DECISION` (e.g. lr 1e-4, goes to `deviations.md`). Max 3 attempts per step (pre-registration) |
| vLLM refuses the model dtype or outputs garbage | `dtype` not bfloat16 | keep `training.dtype: bfloat16`; never run gemma-3 in float16 on the rented host |
| CUDA OOM during training | micro batch 8 × 1,024 with the 262k-vocabulary logits (seen on the RTX 4090 on 2026-10-13) | `training.micro_batch_seqs: 4` in `configs/runtime.yaml` (set 2026-10-13; never edit the frozen `chains.yaml`); log it |
| CUDA OOM or hang in vLLM generation | `gpu_memory_utilization 0.85` while scorer memory is still held | the generation runs in its own stage; lower to 0.7 in `run_chain.py generate()`; or uninstall vLLM to force the HF fallback (3–5× slower) and re-plan |
| `exact_duplicate_rate` > 0.05 or `empty_rate` > 0.05 in `generate.json` / `sample_meta.json` | seeding or EOS/tokenizer problem | inspect the corpus; fix; delete the stage cache and regenerate; never train on it (pre-registered bug rule) |
| `generated tokens within 5% of the budget` fails | generation stopped early | re-run the stage (it resumes); check `finish` reasons |
| script ratio of BN generations < 0.95 at generation 1 of REPLACE | expected to fall over generations, not at gen 1 | compare with the gen-0 sample; if gen-0 is already off-script, G2 should have failed: re-open G2 as a `DECISION` |
| `length_unit is 'words' but manifest.json has no per-language lengths` | corpora built with an old config | re-run `prepare_corpora.py --build` on the host, then `test_sanity.py` |
| `cannot resolve match_words_of_BN` | manifest missing | corpora must be built (Gate 1) before the word-matched chain's gen-0 |
| `transformers` cannot load `google/gemma-3-270m` | version < 4.56 or gated download | `pip install -U transformers`; check HF login in the bootstrap log; `LICENCE` request if 401/403 |
| `cosine_with_min_lr` unknown scheduler | transformers too old | `pip install -U "transformers>=4.56"` (bootstrap pins it) |
| Wikidata SPARQL 429/timeout in `build_probes.py --fetch` | rate limit | re-run `--fetch` after 5 min; lower `max_items_per_relation` to 2000 (log it); counts per stratum must still reach 200 |
| `fetch_sources.py` fails on a Hugging Face source | network, gated, or dataset moved | see its message: `LICENCE` or `DECISION` request; required sources block G1 |
| `vast_ops.py` output parsing error | Vast CLI JSON shape changed | run `vastai <cmd> --help` and `--raw`, patch the wrapper, log the version |

Pin the versions that passed the pilot (`logs/environment.json` → one line in `logs/decisions.md`) and keep them for the whole run.

## 9. After the GPU phase (control machine, no instance)

- **G5 human read:** `results/samples/<chain>_gen3_50.jsonl` and `<chain>_gen6_50.jsonl` for the six confirmatory chains (12 files; split by chain), coded with the rubric of `06_HUMAN_TASKS.md`; notes to `results/human_read/`; fill `signoffs/G5_human_read.md`.
- **G6:** `python harness\analyze.py --robustness` from a clean checkout of the downloaded data; the agent prepares `results/analysis/analysis_report.md`, tables, figures, the seed-replicate and control tables, and `results/deviations.md`; the authors review and interpret.
- **G7:** manuscript per `09_WRITING_AND_DISCLOSURE.md`; screened 50-sample files; disclosure; release package per the policy.
- Kaggle fallback (if Vast.ai is unavailable or the cap is refused): `04_RUN_PLAN.md` §5, `harness/kaggle/`; same gates; `training.dtype: float16` with a deviation note.
