#!/usr/bin/env python3
"""Checks of the posthoc_gpu_pack2 results against posthoc_gpu_pack2_2026-10-23/README_RUN.md section 4.

Post-hoc (2026-10-24, PC). Reads the take-home folder results/posthoc_seeds_2026-10-23/ (unzipped from
results/posthoc_seeds_2026-10-23.zip), the pack, and registered records (configs, harness, the sidecar bundle, Table S12,
the 2026-10-20 cross-decoder files). Writes checks.md and out/checks_steps.csv: numbers, hashes and log lines only. The
restricted continuation files are read in memory for counts, lengths and equality tests; no text from them is written
or printed.

usage: python -B checks_posthoc2.py <package root> <analysis folder>
"""
import difflib, gzip, hashlib, json, re, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PKG, A = Path(sys.argv[1]), Path(sys.argv[2])
R = PKG / "results"
T = R / "posthoc_seeds_2026-10-23"
H = T / "host"
X = H / "results" / "posthoc2_cross_decoder"
ZIP_SHA = "75725fb11785aa128f50548c580a2e3111bf6290ba2d4d5eac30d34d57c80b77"
NEW = [f"{L}-{arm}-s{k}" for k in (2, 3) for arm in ("REAL-REPEAT", "REPLACE-topp95") for L in ("EN", "BN")]
M, PROBLEMS = [], []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ok(cond, what):
    if not cond:
        PROBLEMS.append(what)
    return "yes" if cond else "**NO**"


def lines(p):
    return Path(p).read_text(encoding="utf-8", errors="replace").splitlines()


def flat(d, pre=""):
    o = {}
    for k, v in d.items():
        if isinstance(v, dict):
            o.update(flat(v, pre + k + "."))
        else:
            o[pre + k] = v
    return o


def lang(chain):
    return "EN" if re.search(r"(^|-)EN(-|$)", chain) else "BN"


def rng(s, nd=6):
    return f"{s.min():.{nd}f} to {s.max():.{nd}f}"


# ------------------------------------------------------------------ 0. folder
M += ["# Checks of the posthoc_gpu_pack2 results (README_RUN.md section 4)", "",
      f"Written by `scripts/checks_posthoc2.py` ({datetime.now(timezone.utc):%Y-%m-%dT%H:%MZ}) from the take-home folder "
      "`results/posthoc_seeds_2026-10-23/` and the registered records named below. Numbers, hashes and log lines only; no "
      "model-written text is shown. A failed check is marked **NO** and listed at the end.", ""]
zsha = sha(R / "posthoc_seeds_2026-10-23.zip")
zrec = (R / "posthoc_seeds_2026-10-23.zip.sha256").read_text().split()[0]
sums = []
for l in lines(T / "SHA256SUMS.txt"):
    if l.strip():
        h, p = l.split(None, 1)
        sums.append((h, p.strip().lstrip("*")))
good = [p for h, p in sums if (T / p).is_file() and sha(T / p) == h]
present = {f.relative_to(T).as_posix() for f in T.rglob("*") if f.is_file()} - {"SHA256SUMS.txt"}
listed = {p for _, p in sums}
M += ["## 0. Take-home folder", "",
      f"- `results/posthoc_seeds_2026-10-23.zip`: SHA-256 `{zsha}`. Same as given by the authors: "
      f"{ok(zsha == ZIP_SHA, 'zip SHA-256')}; same as the `.sha256` file beside it: {ok(zrec == zsha, 'zip .sha256 file')}.",
      f"- `SHA256SUMS.txt` lists {len(sums)} files; {len(good)} are present with matching SHA-256: "
      f"{ok(len(good) == len(sums) == 504, 'SHA256SUMS.txt: 504 files')}. Files in the folder but not listed: "
      f"{len(present - listed)}; listed but missing: {len(listed - present)}.", ""]

# ------------------------------------------------------------------ 1. inputs, patch, plan, software
setup, xdec = lines(H / "logs" / "posthoc2_setup.log"), lines(H / "logs" / "posthoc2_xdec.log")
la = next((l for l in setup if l.startswith("batch A:")), "(no line)")
lb = next((l for l in xdec if l.startswith("batch B:")), "(no line)")
nA = sum(1 for l in lines(T / "vps" / "staging" / "inputs_A.sha256") if l.strip())
nB = sum(1 for l in lines(T / "vps" / "staging" / "inputs_B.sha256") if l.strip())
cfg_host = {l.split()[1]: l.split()[0] for l in setup if re.match(r"^[0-9a-f]{64}  configs/", l)}
reg_cfg = sha(PKG / "configs" / "chains.yaml")
ph_cfg = sha(PKG / "posthoc_gpu_pack2_2026-10-23" / "configs" / "chains_posthoc_2026-10-23.yaml")
ph_cfg_t = sha(H / "configs" / "chains_posthoc_2026-10-23.yaml")
before = next((l.split()[-1] for l in setup if l.strip().startswith("before:")), "")
after = next((l.split()[-1] for l in setup if l.strip().startswith("after:")), "")
run_common, host_common = sha(PKG / "harness" / "common.py"), sha(H / "harness" / "common.py")
diff = list(difflib.unified_diff(lines(PKG / "harness" / "common.py"), lines(H / "harness" / "common.py"),
                                 "harness/common.py (as run)", "host/harness/common.py (patched)", n=0, lineterm=""))
changed = [l for l in diff[2:] if l[:1] in "+-"]
plan = lines(H / "logs" / "posthoc2_plan.txt")
jobs = [re.search(r"--chain (\S+)", l).group(1) for l in plan if "run_chain.py" in l]
prios = [int(m.group(1)) for l in plan for m in [re.match(r"^P(\d+) ", l)] if m]
other = [l for l in plan if l.strip() and not re.match(r"^P\d+ ", l) and "run_chain.py --chain" not in l]
setup_ok = any(l.startswith("== setup OK") for l in setup)


def freeze(p):
    d = {}
    for l in lines(p):
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:==|@)\s*(\S+)", l.strip())
        if m and not l.strip().startswith("#"):
            d[m.group(1).lower().replace("_", "-")] = m.group(2)
    return d


fz, pins = freeze(H / "logs" / "posthoc2_pip_freeze.txt"), freeze(PKG / "harness" / "vast" / "pins_gen0.txt")
pin_diff = {k: (v, fz.get(k)) for k, v in pins.items() if (fz.get(k) or "").split("+")[0] != v.split("+")[0]}
status = (H / "STATUS_posthoc2").read_text().strip()
smi = " ".join(lines(H / "logs" / "posthoc2_nvidia_smi.txt"))
stage = [l.split("Z ", 1)[1] for l in lines(T / "vps" / "logs" / "posthoc_gpu_stage2.log") if " done: " in l]
M += ["## 1. Inputs, patch, plan, software", "",
      f"- Batch A: setup log `{la}`; `inputs_A.sha256` lists {nA} files: {ok('all 110 files match' in la and nA == 110, 'batch A')}. "
      f"Batch B: cross-decoder log `{lb}`; `inputs_B.sha256` lists {nB} files: {ok('all 450 files match' in lb and nB == 450, 'batch B')}. "
      f"VPS staging log: {'; '.join(stage)}.",
      f"- Configs on the host (setup log): `chains.yaml` {cfg_host.get('configs/chains.yaml', '?')[:16]}..., the registered file on the PC "
      f"{reg_cfg[:16]}...: {ok(cfg_host.get('configs/chains.yaml') == reg_cfg, 'registered chains.yaml on host')}; "
      f"`chains_posthoc_2026-10-23.yaml` {cfg_host.get('configs/chains_posthoc_2026-10-23.yaml', '?')[:16]}..., same as the pack copy "
      f"and the take-home copy: {ok(cfg_host.get('configs/chains_posthoc_2026-10-23.yaml') == ph_cfg == ph_cfg_t, 'post-hoc config')}.",
      f"- Patched `harness/common.py`: before `{before}` (the PC's registered `harness/common.py` is `{run_common}`: "
      f"{ok(before == run_common, 'patch before-hash')}); after `{after}` (the take-home `host/harness/common.py` is `{host_common}`: "
      f"{ok(after == host_common, 'patch after-hash')}). The patch only adds `import os` and lets `load_chains_cfg()` read `CG4_CHAINS_CFG` when it is set ({len(changed)} changed lines): "
      f"{ok(len([l for l in changed if l.startswith('-')]) == 2 and all(('CG4_CHAINS_CFG' in l) or ('env_cfg' in l) or l[1:].strip() == 'import os' or 'configs/chains.yaml (frozen' in l or 'file is never edited' in l for l in changed if l.startswith('+')), 'patch scope')}:",
      "", "```diff", *diff, "```", "",
      f"- Plan (`posthoc2_plan.txt`): {len(jobs)} jobs, priorities {sorted(set(prios))}, chains {', '.join(jobs)}. Exactly the eight "
      f"post-hoc chains, each once: {ok(sorted(jobs) == sorted(NEW), 'plan chains')}; no generation-0 or base job: "
      f"{ok(not [j for j in jobs if j.startswith(('GEN0', 'BASE'))] and not other, 'plan has other jobs')}. Setup ended `== setup OK`: "
      f"{ok(setup_ok, 'setup OK')}. `STATUS_posthoc2` reads `{status}`.",
      f"- Software (`posthoc2_pip_freeze.txt`): vllm {fz.get('vllm')}, torch {fz.get('torch')}, transformers {fz.get('transformers')}, "
      f"tokenizers {fz.get('tokenizers')}, accelerate {fz.get('accelerate')}: the README's pins (vllm 0.31.0, torch 2.13.0, "
      f"transformers 5.17.0): {ok(fz.get('vllm') == '0.31.0' and (fz.get('torch') or '').startswith('2.13.0') and fz.get('transformers') == '5.17.0', 'pinned stack')}. "
      f"All {len(pins)} pins of `harness/vast/pins_gen0.txt` (the generation-0 stack) match the freeze: "
      f"{ok(not pin_diff, 'pins_gen0 mismatch: ' + str(pin_diff))}. GPU: {'RTX 4090' if 'RTX 4090' in smi else '?'}.", ""]

# ------------------------------------------------------------------ 2. the eight chains
z = zipfile.ZipFile(R / "cg4_sidecars_from_G4b_2026-10-20.zip")
ZR = "cg4_sidecars_bundle/results/chains/"
RUN_SPECIFIC = re.compile(
    r"^(chain_id|variant|session_id|seed|seed_offset|gen0_id|created_at|checkpoint_sha256|previous_checkpoint)$"
    r"|^train\.(final_loss|loss_first|loss_curve|train_seconds|trainer_metrics\..+)$"
    r"|^(sample|generate)\.(seed|tokens|generate_seconds|mean_\w+|cap_hit_rate|empty_rate|exact_duplicate_rate)$|^generate\.docs$"
    r"|^(train|training_set)\.(synthetic_docs|synthetic_target_tokens|target_tokens|tokens|masked_prefix_tokens|train_blocks"
    r"|train_tokens|optimizer_steps|eos_target_docs|eos_context_only_docs)$")
COMP = re.compile(r"^(train|training_set)\.(real_docs|synthetic_docs|tokens|target_tokens|train_blocks|train_tokens|optimizer_steps)$")
rows, comp = [], {}
for c in NEW:
    L, k, seed0 = c[:2], c.rsplit("-s", 1)[1], c.rsplit("-s", 1)[0]
    pair = f"{L}-REPLACE-s{k}"
    st = json.loads((H / "results" / "chains" / c / "state.json").read_text())
    comp[c] = st.get("completed")
    for g in range(1, 7):
        p = H / "results" / "chains" / c / f"gen_{g}" / "step.json"
        if not p.exists():
            PROBLEMS.append(f"{c} generation {g}: no step.json")
            continue
        fs = flat(json.loads(p.read_text(encoding="utf-8")))
        r0 = flat(json.loads(z.read(f"{ZR}{seed0}/gen_{g}/step.json")))
        rp = flat(json.loads(z.read(f"{ZR}{pair}/gen_{g}/step.json")))
        sdiff = sorted(x for x in set(fs) | set(r0) if not RUN_SPECIFIC.match(x) and fs.get(x) != r0.get(x))
        same_comp = all(fs.get(x) == r0.get(x) for x in set(fs) | set(r0) if COMP.match(x)) if "REAL-REPEAT" in c else None
        prev = fs["previous_checkpoint"].split("/results/chains/")[-1]
        rows.append(dict(
            chain=c, generation=g, seed=fs["seed"], sample_seed=fs.get("sample.seed"), seed_offset=fs["seed_offset"],
            gen0_id=fs["gen0_id"], training_text_top_p=(fs.get("generate.sampling.top_p") if "topp95" in c else None),
            chain_top_p=fs.get("sampling.top_p"), eval_sample_top_p=fs.get("sample.sampling.top_p"),
            sample_docs=fs.get("sample.docs"), sample_empty_rate=fs.get("sample.empty_rate"),
            real_docs=fs.get("training_set.real_docs"), synthetic_docs=fs.get("training_set.synthetic_docs"),
            train_tokens=fs.get("train.train_tokens"), optimizer_steps=fs.get("train.optimizer_steps"),
            final_loss=fs["train.final_loss"], loss_nan=fs["train.nan"],
            final_loss_seed0_chain=r0["train.final_loss"], final_loss_REPLACE_same_seed=rp["train.final_loss"],
            seeds_equal_REPLACE_same_seed=(fs["seed"] == rp["seed"] and fs.get("sample.seed") == rp.get("sample.seed")),
            gen0_equal_REPLACE_same_seed=(fs["gen0_id"] == rp["gen0_id"]),
            previous_checkpoint_ok=(prev == (f"{fs['gen0_id']}/checkpoint" if g == 1 else f"{c}/gen_{g - 1}/checkpoint")),
            settings_equal_seed0_chain=not sdiff, settings_differing=";".join(sdiff),
            real_repeat_training_set_equal_seed0=same_comp))
st = pd.DataFrame(rows)
(A / "out").mkdir(parents=True, exist_ok=True)
st.to_csv(A / "out" / "checks_steps.csv", index=False)
M += ["## 2. The eight chains", "",
      "Per step: `host/results/chains/<chain>/gen_<g>/step.json`; the registered step records come from "
      "`results/cg4_sidecars_from_G4b_2026-10-20.zip`. All values per step are in `out/checks_steps.csv`.", "",
      "| chain | generations done | final training loss, generations 1 to 6 | seeds (step) | offset | gen0_id | top-p: evaluation sample / training text |",
      "|---|---|---|---|---|---|---|"]
for c in NEW:
    s = st[st.chain == c]
    tt = s.training_text_top_p.dropna().unique()
    M.append(f"| {c} | {comp[c]} | {' '.join(f'{v:.4f}' for v in s.final_loss)} | {s.seed.min()} to {s.seed.max()} | "
             f"{s.seed_offset.iloc[0]} | {s.gen0_id.iloc[0]} | {'/'.join(map(str, s.eval_sample_top_p.unique()))} / "
             f"{'/'.join(map(str, tt)) if len(tt) else 'real text only'} |")
exp_top = st.apply(lambda r: (r.eval_sample_top_p == (0.95 if "topp95" in r.chain else 1.0))
                   and (r.training_text_top_p == 0.95 if "topp95" in r.chain else True), axis=1)
M += ["",
      f"- All six generations done for each chain (`state.json` and a `step.json` per generation): "
      f"{ok(all(comp[c] == [1, 2, 3, 4, 5, 6] for c in NEW) and len(st) == 48, 'six generations each')}; no NaN loss: "
      f"{ok(not st.loss_nan.any(), 'NaN loss')}; 2,000-document evaluation sample at every step: {ok((st.sample_docs == 2000).all(), 'sample docs')} "
      f"(empty-continuation rate {st.sample_empty_rate.min():.4f} to {st.sample_empty_rate.max():.4f}).",
      f"- Top-p as specified (evaluation samples 1.0 for REAL-REPEAT, 0.95 for topp95; topp95 training text 0.95): {ok(exp_top.all(), 'top-p')}.",
      f"- Paired with the registered REPLACE chain of the same seed: same step seed and sample seed at every generation: "
      f"{ok(st.seeds_equal_REPLACE_same_seed.all(), 'seed pairing')}; same generation-0 model: {ok(st.gen0_equal_REPLACE_same_seed.all(), 'gen0 pairing')} "
      f"(seed offset 1000 for s2, 2000 for s3); each step starts from the chain's previous checkpoint (generation 1 from its "
      f"generation-0 model): {ok(st.previous_checkpoint_ok.all(), 'previous checkpoint')}.",
      f"- Registered recipe: every `step.json` setting equals that of the registered seed-0 chain of the same arm at the same "
      f"generation (EN/BN-REAL-REPEAT, EN/BN-REPLACE-topp95), apart from run-specific fields (ids, seeds, times, losses, sample "
      f"statistics and, for topp95, the sizes that follow from the generated text): {ok(st.settings_equal_seed0_chain.all(), 'settings: ' + '; '.join(st.settings_differing.unique()))}. "
      f"The REAL-REPEAT training sets have the same sizes as the registered REAL-REPEAT at every generation (real documents, tokens, "
      f"blocks, optimizer steps): {ok(st.real_repeat_training_set_equal_seed0.dropna().all(), 'REAL-REPEAT training set')}.",
      "- Final training loss beside the registered seed-0 chain of the same arm (mean over generations 1 to 6): " +
      "; ".join(f"{c} {st[st.chain == c].final_loss.mean():.4f} vs {st[st.chain == c].final_loss_seed0_chain.mean():.4f}" for c in NEW) + "."]
mp = pd.read_json(H / "results" / "metrics_posthoc_2026-10-23.jsonl", lines=True)
reg = pd.read_json(R / "metrics.jsonl", lines=True)
same_set = all(set(mp[(mp.chain_id == c) & (mp.generation == g)].metric) ==
               set(reg[(reg.chain_id == c.rsplit("-s", 1)[0]) & (reg.generation == g)].metric) for c in NEW for g in range(1, 7))
gen0s = sorted({f"GEN0-{c[:2]}-s{c.rsplit('-s', 1)[1]}" for c in NEW})
gen0_in_reg = all(((reg.chain_id == g0) & (reg.generation == 0)).any() for g0 in gen0s)
ck = all(r.checkpoint.endswith(f"/results/chains/{r.chain_id}/gen_{r.generation}/checkpoint") for r in mp.itertuples())
nan_new = int(mp.value.isna().sum())
nan_reg = int(reg[reg.chain_id.isin({c.rsplit('-s', 1)[0] for c in NEW}) & reg.generation.between(1, 6)].value.isna().sum())
M += [f"- `metrics_posthoc_2026-10-23.jsonl`: {len(mp):,} records = {mp.chain_id.nunique()} chains x {mp.generation.nunique()} generations x "
      f"{mp.metric.nunique()} metrics: {ok(len(mp) == 2112 and mp.chain_id.nunique() == 8 and mp.metric.nunique() == 44, 'metric record count')}; "
      f"duplicates {int(mp.duplicated(['chain_id', 'generation', 'metric']).sum())}; the same metrics per step as the registered seed-0 "
      f"chains: {ok(same_set, 'metric set')}; each record names its own step's checkpoint: {ok(ck, 'metric checkpoints')}; empty values "
      f"{nan_new} (registered seed-0 counterparts: {nan_reg}). The generation-0 points of the new chains ({', '.join(gen0s)}) are "
      f"registered records in `results/metrics.jsonl`: {ok(gen0_in_reg, 'gen0 records')}.", ""]

# ------------------------------------------------------------------ 3. cross-decoder
cj = json.loads((X / "cross_decoder2_checks.json").read_text())
dc = cj.get("decoder_check", {})
sys.path.insert(0, str(PKG / "harness"))
from common import load_chains_cfg  # noqa: E402
import analyze as AN  # noqa: E402
meta = AN.chain_meta(load_chains_cfg(PKG / "posthoc_gpu_pack2_2026-10-23" / "configs" / "chains_posthoc_2026-10-23.yaml"))
g0 = {c: (m.get("gen0") or f"GEN0-{m['language']}") for c, m in meta.items()}
g0map_ok = all(g0[c] == v for c, v in cj.get("gen0_of_chain", {}).items()) and len(cj.get("gen0_of_chain", {})) == 12
sc = pd.read_csv(X / "cross_decoder2_scorer_check.csv")
sc20 = pd.read_csv(R / "cg4_posthoc_gpu_results" / "cross_decoder_scorer_check.csv")
for d in (sc, sc20):
    d["language"] = d.chain.map(lang)
hi = sc[sc.mean_abs_diff_nll_per_token > 0.016].sort_values("mean_abs_diff_nll_per_token", ascending=False)
both = sc.merge(sc20, on=["chain", "gen"], suffixes=("", "_20"))
sm = pd.read_csv(X / "cross_decoder2_summary.csv")
sm["language"] = sm.chain.map(lang)
exp_g0 = sm.apply(lambda r: r.gen0 == (r.chain if r.chain.startswith("GEN0") else g0[r.chain]), axis=1)
short = sm[sm.n < 200]
recs, texts = [], {}
with gzip.open(X / "cross_decoder2_samples.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        key = (r["chain"], r["gen"], r["decoder_top_p"], r["prefix_id"])
        texts[key] = r["text"]
        recs.append({k: r[k] for k in ("chain", "gen", "decoder_top_p", "prefix_id", "nll", "n_tokens")})
sd = pd.DataFrame(recs)
sd["language"] = sd.chain.map(lang)
cellsize = sd.groupby(["chain", "gen", "decoder_top_p"]).size()
ids_same = all(len({tuple(sorted(g.prefix_id)) for _, g in sd[sd.language == L].groupby(["chain", "gen", "decoder_top_p"])}) == 1
               for L in ("EN", "BN"))
empty = sd[sd.n_tokens == 0]
agg = sd[sd.n_tokens > 0].groupby(["chain", "gen", "decoder_top_p"]).agg(n=("nll", "size"), m=("nll", "mean")).reset_index()
chk = sm.merge(agg, on=["chain", "gen", "decoder_top_p"], suffixes=("", "_file"))
old = {}
with gzip.open(R / "cg4_posthoc_gpu_results" / "cross_decoder_samples.jsonl.gz", "rt", encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        old[(r["chain"], r["gen"], r["decoder_top_p"], r["prefix_id"])] = (r["text"], r["nll"], r["n_tokens"])
shared = [k for k in old if k in texts]
same = [k for k in shared if old[k][0] == texts[k]]
sdi = sd.set_index(["chain", "gen", "decoder_top_p", "prefix_id"])["nll"]
sdn = sd.set_index(["chain", "gen", "decoder_top_p", "prefix_id"])["n_tokens"]
same_fin = [k for k in same if np.isfinite(old[k][1]) and np.isfinite(sdi.loc[k])]
dsame = np.array([abs(old[k][1] - sdi.loc[k]) for k in same_fin])
same_len_tok = all(old[k][2] == sdn.loc[k] for k in same)
kmax = same_fin[int(np.argmax(dsame))] if len(dsame) else None
old_ids = {L: sorted({k[3] for k in old if lang(k[0]) == L}) for L in ("EN", "BN")}
new_ids = {L: sorted(sd[sd.language == L].prefix_id.unique()) for L in ("EN", "BN")}
M += ["## 3. Cross-decoder over three seeds", "",
      f"- `cross_decoder2_checks.json`: `decoder_check_ok` {cj.get('decoder_check_ok')}: {ok(cj.get('decoder_check_ok') is True, 'decoder check')} (" +
      "; ".join(f"top-p {kk}: {v['steps_matching_rule']} of {v['steps']} steps follow the rule, {v['kept_min']} to {v['kept_max']} of {v['vocab']} tokens kept"
                for kk, v in dc.items()) +
      f"). {cj.get('n_prefixes')} prefixes per cell, scorer check on {cj.get('check_n')} documents per step; torch {cj.get('torch')}, "
      f"transformers {cj.get('transformers')}. Each chain scored under its own generation-0 model (the step's gen0_id): {ok(g0map_ok, 'gen0 map')}.",
      f"- Scorer check (`cross_decoder2_scorer_check.csv`, the registered sample-NLL statistic recomputed on the host for the first "
      f"{int(sc.n_docs.max())} archived documents of each step): {len(sc)} rows (72 chain steps and 6 generation-0 models): "
      f"{ok(len(sc) == 78 and (sc.n_docs == 50).all(), 'scorer rows')}; token-count mismatches {int(sc.n_token_count_mismatch.sum())}: "
      f"{ok(int(sc.n_token_count_mismatch.sum()) == 0, 'token-count mismatches')}. Mean |diff| {rng(sc.mean_abs_diff_nll_per_token)} nats/token "
      f"(EN {rng(sc[sc.language == 'EN'].mean_abs_diff_nll_per_token)}, BN {rng(sc[sc.language == 'BN'].mean_abs_diff_nll_per_token)}); "
      f"max |diff| per row {rng(sc.max_abs_diff_nll_per_token)}. On 2026-10-20 ({len(sc20)} rows): mean |diff| {rng(sc20.mean_abs_diff_nll_per_token)} "
      f"(EN {rng(sc20[sc20.language == 'EN'].mean_abs_diff_nll_per_token)}, BN {rng(sc20[sc20.language == 'BN'].mean_abs_diff_nll_per_token)}). "
      f"Rows above 0.016: {len(hi)}, " + ", ".join(f"{r.chain} generation {r.gen} ({r.mean_abs_diff_nll_per_token:.6f}, max {r.max_abs_diff_nll_per_token:.6f})" for r in hi.itertuples()) +
      f"; both are BN rows, where every row is between {sc[sc.language == 'BN'].mean_abs_diff_nll_per_token.min():.4f} and "
      f"{sc[sc.language == 'BN'].mean_abs_diff_nll_per_token.max():.4f}. The {len(both)} steps checked in both runs differ by "
      f"{rng((both.mean_abs_diff_nll_per_token - both.mean_abs_diff_nll_per_token_20).abs())} in mean |diff|.",
      f"- Cells (`cross_decoder2_summary.csv`): {len(sm)} = 78 steps x 2 decoders: {ok(len(sm) == 156 and sm[['chain', 'gen', 'decoder_top_p']].drop_duplicates().shape[0] == 156, 'cell count')}; "
      f"200 draws in every cell, n + n_empty = 200: {ok(((sm.n + sm.n_empty) == 200).all() and (cellsize == 200).all(), 'draws per cell')}; "
      f"usable draws per cell: {', '.join(f'{int(v)} cells with {int(k)}' for k, v in sm.n.value_counts().sort_index(ascending=False).items())}. The cells with 199: " +
      "; ".join(f"{r.chain} generation {r.gen}, evaluation top-p {r.decoder_top_p} (n_empty {r.n_empty})" for r in short.itertuples()) +
      f". In the samples file these are {len(empty)} records with 0 tokens and no NLL: "
      f"{ok(len(empty) == len(short) == 3 and empty.nll.isna().all(), 'empty continuations')}. The generation-0 model named in each cell is "
      f"the chain's own: {ok(exp_g0.all(), 'summary gen0')}. Every cell has the same 200 prefix ids within a language: {ok(ids_same, 'prefix ids')}; "
      f"cell means recomputed from the samples file equal the summary (max |diff| {float((chk.mean_nll_nats - chk.m).abs().max()):.5f} at its 4 "
      f"decimals; n equal: {ok((chk.n == chk.n_file).all() and float((chk.mean_nll_nats - chk.m).abs().max()) <= 5.1e-5, 'summary vs samples')}). "
      f"Generation cap: EN {', '.join(str(int(x)) for x in sorted(sm[sm.language == 'EN'].max_new_tokens.unique()))}, BN {', '.join(str(int(x)) for x in sorted(sm[sm.language == 'BN'].max_new_tokens.unique()))} tokens; "
      f"share of draws at the cap EN {rng(sm[sm.language == 'EN'].cap_hit_share, 2)}, BN {rng(sm[sm.language == 'BN'].cap_hit_share, 2)}.",
      f"- Against the 2026-10-20 run (same seeds for the first 50 draws of the seed-0 cells): its prefix ids are the first 50 of each "
      f"language here: {ok(all(new_ids[L][:50] == old_ids[L] for L in ('EN', 'BN')), '2026-10-20 prefix ids')}. Of the {len(shared)} draws in "
      f"both runs, {len(same)} continuations are identical ({100 * len(same) / max(1, len(shared)):.1f}%; the host's torch changed from "
      f"2.8.0+cu129 to 2.13.0+cu130, so identical seeds need not give identical samples); identical ones also have the same token "
      f"count: {ok(same_len_tok, 'identical continuations, token counts')}. Their NLL differs by a median {np.median(dsame):.4f} nats/token "
      f"(95th percentile {np.percentile(dsame, 95):.4f}; the largest, {dsame.max():.4f}, is for a continuation of {int(sdn.loc[kmax])} "
      f"tokens, where the per-token mean rests on few tokens)." if len(dsame) else
      f"- Against the 2026-10-20 run: {len(shared)} shared draws, none identical.", ""]

# ------------------------------------------------------------------ 4. full-sample check: validation and run
val = pd.read_csv(T / "full_sample_check_validation" / "full_sample_equal_length_K100_n50_m40_B2000_seed20261023.csv")
s12 = pd.read_csv(R / "analysis" / "posthoc_review_2026-10-22" / "prefix_paired_diversity_equal_K100.csv")
vv = val.merge(s12, on=["chain", "quantity"], suffixes=("", "_S12"))
cols = ["point", "range_lo", "range_hi"]
close = max(float((vv[c] - vv[c + "_S12"]).abs().max()) for c in cols)
vlog = {}
for l in Path(T / "vps" / "logs" / "posthoc2_full_sample_validation.log").read_text(encoding="utf-8-sig").splitlines():
    m = re.match(r"^(\S+)\s+(\S+)\s+([+-]\d\.\d{5}) \[([+-]\d\.\d{5}), ([+-]\d\.\d{5})\] words/step (\d+)", l.strip())
    if m:
        vlog[(m.group(1), m.group(2))] = tuple(float(x) for x in m.group(3, 4, 5)) + (int(m.group(6)),)
strict = len(vlog) == 17 and all(
    (key in vlog) and all(abs(a - b) < 1e-12 for a, b in zip(vlog[key][:3], (r.point_S12, r.range_lo_S12, r.range_hi_S12)))
    and vlog[key][3] == r.words_per_step_S12 for r in vv.itertuples() for key in [(r.chain, r.quantity)])
ints = all((vv[c] == vv[c + "_S12"]).all() for c in ("words_per_step", "prefixes_at_full_K")) and \
    float((vv.median_words_per_prefix - vv.median_words_per_prefix_S12).abs().max()) < 1e-9
fs_ = pd.read_csv(T / "full_sample_check" / "full_sample_equal_length_K100_n2000_m1600_B500_seed20261024.csv")
fs_g0 = fs_.apply(lambda r: (pd.isna(r.gen0) if "topp95" in r.chain else r.gen0 == g0[r.chain]), axis=1)
ex = vv.set_index("chain")
M += ["## 4. Full-sample equal-length check", "",
      f"- Validation (`full_sample_check_validation/`, 50 prefixes, subsets of 40, 2,000 subsets, seed 20261023): {len(val)} chains, "
      f"{len(vv)} matched to Supplementary Table S12 (`results/analysis/posthoc_review_2026-10-22/prefix_paired_diversity_equal_K100.csv`). "
      f"Point and stability range, as the run printed them at 5 decimals from full precision (`vps/logs/posthoc2_full_sample_validation.log`), "
      f"equal every Table S12 value: {ok(len(vv) == len(s12) == 17 and strict, 'Table S12 values')}. The 6-decimal CSV agrees within its precision "
      f"(largest difference {close:.6f}; re-rounding it to 5 decimals splits three ties that end in 5 at the sixth decimal). Words per step, "
      f"prefixes at full K and median words per prefix identical: {ok(ints, 'Table S12 counts')}. "
      "README examples: " + "; ".join(
          f"{c} {ex.loc[c, 'point']:+.5f} [{ex.loc[c, 'range_lo']:+.5f}, {ex.loc[c, 'range_hi']:+.5f}], {int(ex.loc[c, 'words_per_step']):,} words"
          for c in ("EN-REPLACE", "EN-REPLACE-topp95", "BN-ACCUMULATE-SUBSAMPLE")) + ".",
      f"- Run (`full_sample_check/`, 2,000 prefixes, subsets of 1,600, 500 subsets, seed 20261024): {len(fs_)} chains (17 registered + 8 "
      f"post-hoc): {ok(len(fs_) == 25 and set(fs_.chain) == set(meta), 'full-sample chains')}; {', '.join(f'{int(x):,}' for x in sorted(fs_.n_prefixes.unique()))} prefixes each; "
      f"generation-0 model as configured (none for the topp95 chains, whose statistic is the raw slope over generations 1 to 6): "
      f"{ok(fs_g0.all(), 'full-sample gen0')}. Results: see the analysis.", ""]

# ------------------------------------------------------------------ 5. spend
inst = json.loads(lines(T / "vps" / "logs" / "vast_instances_57450903.jsonl")[0])
ev = json.loads(lines(T / "vps" / "logs" / "vast_events_57450903.jsonl")[0])
t0 = datetime.fromisoformat(inst["created_at"])
t1 = datetime.fromisoformat(ev["at"])
hours = (t1 - t0).total_seconds() / 3600
last = [l for l in lines(T / "vps" / "logs" / "vast_status_2026-10-24.log") if l.strip().startswith("57450903")][-1].split()
man = json.loads((T / "vps" / "archive" / "pack_manifest_posthoc2_checkpoints_corpora.json").read_text())
tsha = (T / "vps" / "archive" / "posthoc2_checkpoints_corpora.tar.sha256").read_text().split()[0]
M += ["## 5. Spend", "",
      f"- Instance 57450903 (RTX 4090, offer US$0.616/h): created {inst['created_at']}, stopped {ev['at']} = {hours:.2f} h "
      f"(US${hours * 0.616:.2f} at the offer price, before disk and bandwidth); last status line before the stop: {last[6]} GPU-h, US${last[7]}. "
      "Deleted by the authors; the VPS agent confirmed 0 instances and 0 volumes at 2026-10-24T17:05:49Z (REQ-036).",
      "- Invoiced for this pack: US$9.00 for 14.4 GPU-h, cap US$15 (pre-run estimate 19 to 20 GPU-h, about US$9 at US$0.45/h). "
      "CG4 total US$47.83 of the US$55 ceiling (invoice query US$47.54 plus US$0.29 for 56846008); 125 GPU-h ceiling.",
      f"- The big archive `posthoc2_checkpoints_corpora.tar` ({man['archive_bytes']:,} bytes, SHA-256 `{man['archive_sha256']}`; the "
      f"`.sha256` file agrees: {ok(tsha == man['archive_sha256'] == '057497215410c11a4b6aa585995294253f0398b53674ce023c6d1fb292f0f08f', 'big tar SHA-256')}; "
      f"manifest {len(man['files'])} members) "
      "stays on the VPS in `results/packs/`; the authors are making the second copy in Google Drive `CG4_backup`. Not needed for the analysis.", ""]
M += ["## Result", "", "All checks passed." if not PROBLEMS else "Failed checks:\n\n" + "\n".join(f"- {p}" for p in PROBLEMS), ""]
(A / "checks.md").write_text("\n".join(M), encoding="utf-8")
print("\n".join(M[-3:]))
print(f"problems: {len(PROBLEMS)}")
