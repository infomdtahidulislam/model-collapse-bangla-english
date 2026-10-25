# Kaggle session script (rendered by push_and_poll.py --prepare). Runs two chains side by side, one per T4, with resume.
# Attached datasets: harness bundle, corpora+probes, previous session outputs (checkpoints, synthetic corpora, metrics).
import glob, json, os, shutil, subprocess, sys

SESSION_ID = "__SESSION_ID__"
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "transformers", "accelerate", "datasets", "pyyaml", "jsonschema", "regex"], check=False)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "vllm"], check=False)   # optional fast generation

work = "/kaggle/working/cg4"; os.makedirs(work, exist_ok=True)
bundle = next((p for p in glob.glob("/kaggle/input/*/harness_bundle")), None)
if bundle is None:
    raise SystemExit("harness bundle dataset not attached")
shutil.copytree(bundle, f"{work}/harness", dirs_exist_ok=True)
for sub in ("configs",):
    shutil.copytree(f"{bundle}/{sub}", f"{work}/{sub}", dirs_exist_ok=True)
for sub in ("corpora", "heldout", "probes"):
    src = next((p for p in glob.glob(f"/kaggle/input/*/{sub}")), None)
    if src:
        shutil.copytree(src, f"{work}/data/{sub}", dirs_exist_ok=True)
# previous outputs (resume): copy results/ from attached datasets
for prev in glob.glob("/kaggle/input/*/results"):
    shutil.copytree(prev, f"{work}/results", dirs_exist_ok=True)
cells = json.load(open("cells.json"))          # {"chains": ["EN-ACCUMULATE", "BN-ACCUMULATE"], "until": 6, "max_hours": 8.5, "gen0": ["EN","BN"]}
os.chdir(work)
procs = []
for i, lang in enumerate(cells.get("gen0", [])):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(i % 2))
    procs.append(subprocess.Popen([sys.executable, "harness/run_chain.py", "--gen0", lang, "--session-id", SESSION_ID], env=env))
for p in procs:
    p.wait()
procs = []
for i, chain in enumerate(cells.get("chains", [])):
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(i % 2))
    procs.append(subprocess.Popen([sys.executable, "harness/run_chain.py", "--chain", chain, "--until", str(cells.get("until", 6)),
                                   "--max-hours", str(cells.get("max_hours", 8.5)), "--session-id", SESSION_ID], env=env))
for p in procs:
    p.wait()
# outputs under /kaggle/working/cg4/results are downloaded by push_and_poll.py --poll; drop large synthetic corpora of REPLACE chains if space is short
