#!/usr/bin/env python3
"""CG4 post-hoc #19: LaBSE dispersion sensitivity.

(a) Corruption ladder: generation-0 samples of each language, with word tokens
    replaced by shuffled-character nonwords at rates 0/5/10/20/40%, plus a
    repetition-loop corruption and (Bangla) a Latin script-mix corruption;
    LaBSE dispersion computed on each corrupted set.
(b) Reference points: dispersion of the confirmatory REPLACE generation-6 sets.
(c) Fluent-only subsets: if pc_files/human_read/ is present, dispersion of the
    human-read files restricted to samples with mean fluency >= 4, next to all 50.

Dispersion is the registered robustness (ix) statistic (harness/tools/semantic_dispersion.py, REQ-026): 1 - mean pairwise
cosine similarity over pairs of different documents, from unit-normalised LaBSE embeddings, in float64, with LaBSE at the
revision (ix) used.

Post-hoc diagnostic (2026-10-20). Not pre-registered; changes no registered number.
Run after 01_fetch.sh:  python3 03_labse_sensitivity.py
On the VPS:             python 03_labse_sensitivity.py --root ../results/g6_extract

VPS-route fixes, 2026-10-20 (PATCH_NOTES.md):
 - Each step's set is the first 50 documents of its sample.jsonl, which is exactly results/samples/<step>_50.jsonl, the
   human-read file. Files are read at the archive's own paths. The old regex search took whichever of the two files the
   directory walk met first.
 - LaBSE is pinned to (ix)'s revision and uses (ix)'s formula. The archive holds no harness to import, so the old code always
   took its fallback, which is the same quantity computed in float32.
 - New --root, --out and --device options. The human-read folder is found next to this script.
"""
import argparse, csv, json, os, random, re, sys, statistics

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="extracted", help="folder holding the archive's results/ paths")
ap.add_argument("--out", default="out")
ap.add_argument("--device", default="")
a = ap.parse_args()
ROOT, OUT = a.root, a.out
os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
import regex as uregex
WORD_RE = uregex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")


# ---------- sample files ----------
def sample_path(chain, gen):
    base = os.path.join(ROOT, "results", "chains", chain)
    return os.path.join(base, "sample.jsonl") if gen == 0 else os.path.join(base, f"gen_{gen}", "sample.jsonl")


N_EMPTY = {}


def texts_of(path, n=50):
    """The first n documents of a step's sample (the human-read set); empty continuations are counted, not skipped."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
            if len(rows) >= n:
                break
    if len(rows) < n:
        sys.exit(f"ERROR: only {len(rows)} documents in {path}")
    N_EMPTY[path] = sum(1 for r in rows if not r.get("text"))
    return rows


for L in ("EN", "BN"):
    if not os.path.exists(sample_path(f"GEN0-{L}", 0)):
        sys.exit(f"ERROR: no generation-0 sample file for {L} ({sample_path(f'GEN0-{L}', 0)}); check extraction")

# ---------- embedding + dispersion ----------
import numpy as np
import torch
import sentence_transformers
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer

MODEL, REVISION = "sentence-transformers/LaBSE", "836121a0533e5664b21c7aacc5d22951f2b8b25b"   # as robustness (ix)
DEVICE = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
if DEVICE.startswith("cuda"):
    torch.backends.cuda.matmul.allow_tf32 = False      # plain fp32, as (ix)
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision("highest")
model = SentenceTransformer(snapshot_download(MODEL, revision=REVISION), device=DEVICE)
disp_src = f"(ix) formula of harness/tools/semantic_dispersion.py; {MODEL}@{REVISION}, max_seq_length {model.max_seq_length}, device {DEVICE}"
print(f"dispersion implementation: {disp_src}; torch {torch.__version__}, sentence-transformers {sentence_transformers.__version__}", flush=True)


def dispersion(texts):
    E = model.encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True,
                     show_progress_bar=False).astype(np.float64)
    n = len(E)
    s = E.sum(0)
    return float(1.0 - (s @ s - n) / (n * (n - 1)))


# ---------- corruptions ----------
rng = random.Random(20261020)
LATIN = "abcdefghijklmnopqrstuvwxyz"


def shuffle_word(w):
    for _ in range(10):
        chars = list(w)
        rng.shuffle(chars)
        s = "".join(chars)
        if s != w:
            return s
    return w + rng.choice(LATIN)


def corrupt_nonwords(text, rate):
    spans = list(WORD_RE.finditer(text))
    k = round(len(spans) * rate)
    if not spans or k == 0:
        return text
    picks = set(rng.sample(range(len(spans)), min(k, len(spans))))
    out, last = [], 0
    for i, m in enumerate(spans):
        out.append(text[last:m.start()])
        out.append(shuffle_word(m.group()) if i in picks else m.group())
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def corrupt_repetition(text):
    words = WORD_RE.findall(text)
    if len(words) < 8:
        return text
    loop = " ".join(words[:4])
    extra = " ".join([loop] * max(1, len(words) // 12))
    return text + " " + extra


def corrupt_scriptmix(text, rate=0.10):
    spans = list(WORD_RE.finditer(text))
    k = round(len(spans) * rate)
    if not spans or k == 0:
        return text
    picks = set(rng.sample(range(len(spans)), min(k, len(spans))))
    out, last = [], 0
    for i, m in enumerate(spans):
        out.append(text[last:m.start()])
        out.append("".join(rng.choice(LATIN) for _ in m.group()) if i in picks else m.group())
        last = m.end()
    out.append(text[last:])
    return "".join(out)


rows = []
for L in ("EN", "BN"):
    base = [r["text"] for r in texts_of(sample_path(f"GEN0-{L}", 0))]
    for rate in (0.0, 0.05, 0.10, 0.20, 0.40):
        rows.append(dict(language=L, corruption="nonword_substitution", rate=rate, n=len(base),
                         dispersion=round(dispersion([corrupt_nonwords(t, rate) for t in base]), 5)))
        print(rows[-1], flush=True)
    rows.append(dict(language=L, corruption="repetition_loop", rate="", n=len(base),
                     dispersion=round(dispersion([corrupt_repetition(t) for t in base]), 5)))
    print(rows[-1], flush=True)
    if L == "BN":
        rows.append(dict(language=L, corruption="latin_script_mix", rate=0.10, n=len(base),
                         dispersion=round(dispersion([corrupt_scriptmix(t) for t in base]), 5)))
        print(rows[-1], flush=True)
    p6 = sample_path(f"{L}-REPLACE", 6)
    if os.path.exists(p6):
        g6 = [r["text"] for r in texts_of(p6)]
        rows.append(dict(language=L, corruption="reference_REPLACE_gen6", rate="", n=len(g6),
                         dispersion=round(dispersion(g6), 5)))
        print(rows[-1], flush=True)

with open(f"{OUT}/labse_corruption.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["language", "corruption", "rate", "n", "dispersion"])
    w.writeheader(); w.writerows(rows)

# ---------- fluent-only subsets (optional) ----------
HR = os.path.join(HERE, "pc_files", "human_read")
frows = []
if os.path.isdir(HR):
    for fn in sorted(os.listdir(HR)):
        m = re.match(r"((EN|BN)-[A-Z-]+)_gen([36])\.csv$", fn)
        if not m:
            continue
        chain, L, g = m.group(1), m.group(2), int(m.group(3))
        path = sample_path(chain, g)
        if not os.path.exists(path):
            print(f"note: no sample file for {chain} gen {g}, skipping fluent subset")
            continue
        flu = {}
        for d in csv.DictReader(open(os.path.join(HR, fn), encoding="utf-8-sig")):
            try:
                flu.setdefault(d["sample_id"], []).append(float(d["fluency_1to5"]))
            except (KeyError, ValueError):
                pass
        for fn2 in os.listdir(HR):
            if fn2.startswith(f"{chain}_gen{g}_fluency"):
                for d in csv.DictReader(open(os.path.join(HR, fn2), encoding="utf-8-sig")):
                    try:
                        flu.setdefault(d["sample_id"], []).append(float(d["fluency_1to5"]))
                    except (KeyError, ValueError):
                        pass
        samples = texts_of(path)
        allt = [r["text"] for r in samples]
        fl = [r["text"] for r in samples
              if flu.get(r.get("prefix_id")) and statistics.mean(flu[r["prefix_id"]]) >= 4]
        row = dict(file=f"{chain}_gen{g}", n_all=len(allt), dispersion_all=round(dispersion(allt), 5),
                   n_fluent=len(fl), dispersion_fluent=round(dispersion(fl), 5) if len(fl) >= 8 else "")
        frows.append(row); print(row, flush=True)
    with open(f"{OUT}/labse_fluent_subset.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "n_all", "dispersion_all", "n_fluent", "dispersion_fluent"])
        w.writeheader(); w.writerows(frows)
else:
    print("note: pc_files/human_read not present; fluent-only subset skipped (optional)")

with open(f"{OUT}/labse_info.json", "w", encoding="utf-8") as f:
    json.dump(dict(dispersion=disp_src, torch=torch.__version__, sentence_transformers=sentence_transformers.__version__,
                   empty_texts_in_sets={os.path.relpath(k, ROOT).replace(os.sep, "/"): v for k, v in N_EMPTY.items()}), f, indent=1)
print(f"\nwrote {OUT}/labse_corruption.csv" + (" and labse_fluent_subset.csv" if frows else "") + " and labse_info.json")
