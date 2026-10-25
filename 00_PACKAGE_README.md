# CG4 — Model Collapse in a Low-Resource Language (Bangla vs English)

**Status:** execution package, created 2026-10-10 from the gap scan in `..\phase4_report\RESEARCH_GAP_REPORT.md` (candidate CG4); **revised 2026-10-12 after the authors' internal six-perspective design review** (`logs/design_review_2026-10-12/`): harness bugs fixed before any run, bfloat16, prefix masking, per-request generation seeds, quantity-matched filter, samples from the trained checkpoints, every checkpoint archived, and seven pre-registered robustness phases in a fixed order under the cap. Compute: an **agent-operated pipeline on a rented Vast.ai RTX 4090** (confirmatory ≈ 35 GPU-hours; cap options in `04_RUN_PLAN.md` §3), following `..\AGENT_PIPELINE.md` and `12_VASTAI_RUNBOOK.md`; Kaggle free GPU is the fallback. State on 2026-10-13: Gate 0 PASSED (OSF DOI 10.17605/OSF.IO/SRA28); the GPU phase started on Vast.ai instance 55779705; Gate 1 evidence is filed (REQ-007 in `signoffs/REQUESTS.md`) and generation 0 runs under REQ-004; the current state is in `..\START_HERE.md` and `logs/decisions.md`.
**Audience:** an experiment agent (Claude Code or similar) that will fetch sources, prepare corpora, run the self-training chains, compute metrics and analyse; and the two human authors who own the decisions. Both authors are native readers of Bangla, so every Bangla verification task in `06_HUMAN_TASKS.md` is in-house.
**One-line question:** When a small multilingual language model is trained repeatedly on its own generated text, does it degrade faster in Bangla than in English at matched model size, data budget and recipe, and does accumulating real data change the rate? (Claim scoped to the model–tokenizer–corpus–language tuple; `01_PREREGISTRATION.md`.)

## Read in this order

| # | File | What it is | Who acts |
|---|---|---|---|
| — | `..\AGENT_PIPELINE.md` | Programme-level protocol: roles, secrets, money caps, gate/request protocol, the Vast.ai loop | agent + authors |
| 0 | `00_AGENT_BRIEF.md` | Complete brief: hypotheses, factors, outcomes, deliverables, hard rules | agent + authors |
| 1 | `01_PREREGISTRATION.md` | Text to freeze (tag or OSF) before any run | **authors** (Gate 0) |
| 2 | `02_DATA_SOURCES.md` | Corpora, matching rules, held-out sets, probe sets, licences | agent builds, **authors verify** (Gate 1) |
| 3 | `03_MODELS_AND_TRAINING.md` | Base model (≤300M), tokenizer conditions, training and generation recipes, regimes | agent (Gate 2) |
| 4 | `04_RUN_PLAN.md` + `configs/chains.yaml` | Chains, generations, data budget, compute estimates, Vast.ai decision, Kaggle fallback, resume rules | agent (Gates 3–4) |
| 5 | `05_METRICS.md` | All automatic metrics (no judges, no raters) and their exact definitions | agent |
| 6 | `06_HUMAN_TASKS.md` | The small set of human tasks, with time budgets | **authors** (Gates 1, 3, 5) |
| 7 | `07_ANALYSIS_PLAN.md` | Pre-specified models, decay slopes, bootstrap CIs, figures, robustness | agent, **authors review** (Gate 6) |
| 8 | `08_GATES_AND_CHECKLISTS.md` | Pass criteria per gate, failure-mode checklist, sign-off forms in `signoffs/`, request protocol | both |
| 9 | `09_WRITING_AND_DISCLOSURE.md` | Manuscript skeleton, disclosure, release policy | authors |
| 10 | `10_RISK_REGISTER.md` | Risks and mitigations | both |
| 11 | `11_TEARDOWN_CHECKLIST.md` | Download and verify everything before a rented GPU instance is deleted (agent packs, human deletes) | agent, then **authors** (Gate 4b) |
| 12 | `12_VASTAI_RUNBOOK.md` | **The ordered command list for the whole GPU phase on Vast.ai**, with human steps and requests interleaved | agent |
| — | `harness/` | Runnable scripts: `fetch_sources.py` (public sources → `data/sources/`), corpus preparation, probe-set building, chain runner (generate → filter → train → evaluate), `run_rented.py` (all chains on 1–N GPUs), metrics, analysis, packing, tests | agent |
| — | `harness/vast/` | `vast_ops.py` (search / create / wait / push / run / tail / pull / status / stop / teardown-request; never destroys), `bootstrap.sh` (host setup), `plan_budget.py` (hours and dollars) | agent |
| — | `harness/kaggle/` | Kaggle fallback: session planner and automation | agent |
| — | `schemas/`, `configs/` | Record schemas; chain and corpus configuration (sources and licences verified 2026-10-12) | agent |
| — | `data/`, `logs/`, `results/`, `signoffs/` | Filled during execution (large files git-ignored; manifests committed); `signoffs/REQUESTS.md` is the agent → authors queue | agent, authors |

## Hard rules (summary; full list in `00_AGENT_BRIEF.md` §7)

1. No step advances past a gate without the sign-off file in `signoffs/` filled by a human author; the agent asks through `signoffs/REQUESTS.md` and stops.
2. No human participants, no personal data. Corpora are public text; the only humans involved are the two authors as researchers.
3. Every number in the paper is regenerated from `results/` by `python harness/analyze.py` with a committed config and seed.
4. A crash, an empty generation or a tokenizer error is a bug to fix and log, never a finding.
5. Any departure from `01_PREREGISTRATION.md` is written to `results/deviations.md` before analysis is re-run.
6. Money: every instance has a human-approved cap; the agent never destroys an instance (`11_TEARDOWN_CHECKLIST.md`).

## Quick start for the agent

```powershell
cd "D:\Terminal gaps"
python scripts\pipeline_status.py                 # which gate is open, pending requests
cd CG4_model_collapse_lowresource_experiment
python -m venv .venv; .\.venv\Scripts\Activate.ps1   # py -3.12 if a wheel is missing for Python 3.14
pip install -r harness\requirements.txt
python harness\tests\test_sanity.py               # config + schema checks, no GPU
python harness\fetch_sources.py --dry-run         # the public sources, licences and files the host will download
python harness\vast\plan_budget.py                # the phase ladder: GPU-hours and cost per robustness priority, cap options
python harness\run_rented.py --plan               # the exact job order the host will execute
```
Then follow `12_VASTAI_RUNBOOK.md` section by section; gates are in `08_GATES_AND_CHECKLISTS.md`.
