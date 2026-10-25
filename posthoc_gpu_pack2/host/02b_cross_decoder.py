#!/usr/bin/env python3
"""CG4 post-hoc #17b (posthoc_gpu_pack2, 2026-10-23): cross-decoder evaluation over three training seeds per decoder.

Generalises 02_cross_decoder.py as run on 2026-10-20 (kept beside this file as 02_cross_decoder_as_run_2026-10-20.py).
Changes, nothing else: (1) the chain list is an option and defaults to the REPLACE chains of seeds 0, 2 and 3 under both
training decoders (top-p 1.0: EN/BN-REPLACE, -s2, -s3; top-p 0.95: EN/BN-REPLACE-topp95, -topp95-s2, -topp95-s3);
(2) each chain is scored under ITS OWN generation-0 model (gen0_id in the chain's step.json: GEN0-EN-s2 for the -s2
chains), which is the reference the registered sample-NLL statistic uses (run_chain.py: reference_checkpoint =
CHAINS/<gen0>/checkpoint), so the scorer check compares like with like; every generation-0 model used gets its own
generation-0 cell; (3) --n defaults to 200 prefixes per cell (the first 200 of the step's sample.jsonl; the first 50 are
the human-read set) and the scorer check uses --check-n (default 50) documents per step; (4) outputs carry the prefix
given by --tag (default cross_decoder2). Seeds are unchanged (zlib.crc32 of "<chain>|<gen>|<top_p>" plus the batch
offset, batch 25), so the first 50 continuations of every seed-0 cell use the same seeds as the 2026-10-20 run.

Original description (2026-10-20):
CG4 post-hoc #17: cross-decoder evaluation of the archived checkpoints.

For each REPLACE-family checkpoint (EN/BN confirmatory REPLACE and the top-p 0.95
pair, generations 1-6, plus the two generation-0 models), draw 50 continuations
from the chain's own archived evaluation prefixes under BOTH decoders
(top-p 1.00 and top-p 0.95, temperature 1.0, ancestral sampling), then score each
continuation's mean per-token NLL (nats) under the same language's generation-0
model. Also reports each generated set's out-of-seed-vocabulary token share.

Post-hoc diagnostic (2026-10-20, internal audit follow-up). Not pre-registered;
changes no registered number. Fresh fixed seeds per cell; comparisons are valid
within this diagnostic only.

Run after 01_fetch.sh (or the VPS route's staged upload):  python3 02_cross_decoder.py

VPS-route fixes, 2026-10-20 (posthoc_gpu_pack/PATCH_NOTES.md):
 - The decoders are the registered ones: top-k off, temperature 1.0, top_p 1.0 or 0.95, passed as generate() keyword
   arguments. The checkpoints' generation_config.json holds Gemma's defaults (top_k 64, top_p 0.95), which generate()
   would otherwise apply. A start-up decoder check confirms this from the processed scores.
 - max_new_tokens is the registered cap of the step's own sample (sample_meta.json: EN 260, BN 338), not max(n_tokens) + 8.
 - Seeds come from zlib.crc32; Python's hash() of a string changes with every process, so the old seeds were not fixed.
 - Files are read at the archive's own paths (results/chains/<chain>[/gen_<g>]/...), not found by regex search.
 - A sampled <pad> token stays in the continuation, as in the registered vLLM sampling; only the first <eos> ends it.
 - Scorer check: the registered statistic of sample_scores.jsonl is recomputed for the first 50 archived documents of every
   step, to show that the host reproduces the registered gen-0 scorer.
"""
import argparse, csv, gc, gzip, io, json, math, os, sys, time, zlib

ap = argparse.ArgumentParser()
ap.add_argument("--root", default="extracted", help="folder holding the archive's results/ and data/ paths")
ap.add_argument("--out", default="out")
ap.add_argument("--steps", default="", help="tests only: comma list of chain:gen (default: every step of --chains)")
ap.add_argument("--chains", default="EN-REPLACE,EN-REPLACE-s2,EN-REPLACE-s3,EN-REPLACE-topp95,EN-REPLACE-topp95-s2,EN-REPLACE-topp95-s3,"
                                    "BN-REPLACE,BN-REPLACE-s2,BN-REPLACE-s3,BN-REPLACE-topp95,BN-REPLACE-topp95-s2,BN-REPLACE-topp95-s3")
ap.add_argument("--n", type=int, default=200, help="prefixes per cell (the first 50 are the human-read set)")
ap.add_argument("--check-n", type=int, default=50, help="documents per step in the scorer check")
ap.add_argument("--tag", default="cross_decoder2", help="prefix of the output file names")
ap.add_argument("--max-new", type=int, default=0, help="tests only: override the registered max_new_tokens")
ap.add_argument("--batch", type=int, default=25)
ap.add_argument("--device", default="")
a = ap.parse_args()
ROOT, OUT = a.root, a.out
os.makedirs(OUT, exist_ok=True)

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer
import regex as uregex

WORD_RE = uregex.compile(r"[\p{L}\p{M}‌‍]+|\p{N}+")  # registered split (harness/common.py words())
DEV = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = torch.bfloat16                      # the registered sampling and scoring dtype (configs: training.dtype)
CHAINS = [c for c in a.chains.split(",") if c]
TAG = a.tag
DECODERS = (1.0, 0.95)
SAMPLING = dict(do_sample=True, temperature=1.0, top_k=0)   # top_k=0: no top-k, as vLLM's SamplingParams in the run


def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}", flush=True)


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def lang_of(name):
    return name.split("-")[1] if name.startswith("GEN0-") else name[:2]


def gen0_of(chain):
    """The chain's own generation-0 model, from its generation-1 step record (gen0_id), as run_chain.py used it."""
    with open(os.path.join(step_dir(chain, 1), "step.json"), encoding="utf-8") as f:
        g0 = json.load(f).get("gen0_id")
    if not g0:
        fail(f"{chain}: gen_1/step.json has no gen0_id")
    return g0


def step_dir(name, gen):
    base = os.path.join(ROOT, "results", "chains", name)
    return base if gen == 0 else os.path.join(base, f"gen_{gen}")


# ---------- inputs ----------
def load_rows(path, n):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if not (isinstance(d.get("prefix_ids"), list) and d["prefix_ids"]):
                fail(f"row without prefix_ids in {path}: {d.get('doc_id')}")
            rows.append(d)
            if len(rows) >= n:
                break
    if len(rows) < n:
        fail(f"only {len(rows)} rows in {path}")
    return rows


def build_vocab(lang):
    path = os.path.join(ROOT, "data", "corpora", f"{lang}_seed.jsonl")
    vocab = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            for w in WORD_RE.findall(json.loads(line)["text"]):
                vocab.add(w.lower())
    log(f"seed vocabulary {lang}: {len(vocab)} types ({path})")
    return vocab


# ---------- model helpers ----------
def load_model(path):
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, dtype=DTYPE).to(DEV).eval()
    return tok, model


def special(tok):
    bos = tok.bos_token_id
    if bos is None:
        fail("tokenizer has no BOS id; gemma-3 requires BOS (03_MODELS_AND_TRAINING.md)")
    pad = tok.pad_token_id if tok.pad_token_id is not None else bos
    return bos, pad, tok.eos_token_id


def generate_batch(model, tok, prefix_ids_list, top_p, max_new, seed):
    torch.manual_seed(seed)
    bos, pad, eos = special(tok)
    seqs = [[bos] + list(p) for p in prefix_ids_list]
    width = max(len(s) for s in seqs)
    input_ids = torch.full((len(seqs), width), pad, dtype=torch.long)
    attn = torch.zeros((len(seqs), width), dtype=torch.long)
    for i, s in enumerate(seqs):                      # left padding for generation
        input_ids[i, width - len(s):] = torch.tensor(s)
        attn[i, width - len(s):] = 1
    input_ids, attn = input_ids.to(DEV), attn.to(DEV)
    with torch.no_grad():
        out = model.generate(input_ids=input_ids, attention_mask=attn, top_p=top_p, max_new_tokens=max_new,
                             pad_token_id=pad, eos_token_id=eos, bos_token_id=bos, **SAMPLING)
    conts = []
    for i in range(len(seqs)):
        c = out[i, width:].tolist()
        if eos is not None and eos in c:
            c = c[:c.index(eos)]                      # continuation tokens only, EOS excluded; padding only follows EOS
        conts.append(c)
    return conts


def score_batch(scorer, tok, prefix_ids_list, cont_list):
    """Mean per-token NLL (nats) of each continuation under the scorer, prefix as context."""
    bos, _, _ = special(tok)
    nlls = []
    for prefix_ids, cont in zip(prefix_ids_list, cont_list):
        if not cont:
            nlls.append(float("nan")); continue
        ids = torch.tensor([[bos] + list(prefix_ids) + list(cont)], device=DEV)
        with torch.no_grad():
            logits = scorer(ids).logits[0, :-1].float()
        targets = ids[0, 1:]
        start = len(prefix_ids)                       # first continuation position in targets
        lp = torch.log_softmax(logits[start:], dim=-1)
        tok_nll = -lp[torch.arange(len(cont), device=DEV), targets[start:]]
        nlls.append(tok_nll.mean().item())
    return nlls


def decoder_check(model, tok, prefix_ids, steps=24):
    """One short generation per decoder with the processed scores returned. top_p 1.0 must leave every vocabulary entry
    finite (no top-k and no top-p truncation); top_p 0.95 must keep exactly the top-p set of the raw logits under the HF
    rule (ascending sort, cumulative probability <= 1 - top_p removed), and nothing caps it at 64 (top-k off)."""
    bos, pad, eos = special(tok)
    ids = torch.tensor([[bos] + list(prefix_ids)], device=DEV)
    res = {}
    for top_p in DECODERS:
        torch.manual_seed(12345)
        with torch.no_grad():
            o = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), top_p=top_p, max_new_tokens=steps,
                               pad_token_id=pad, eos_token_id=eos, bos_token_id=bos, output_scores=True, output_logits=True,
                               return_dict_in_generate=True, **SAMPLING)
        V = int(o.scores[0].shape[-1])
        kept = [int(torch.isfinite(s[0]).sum()) for s in o.scores]
        expect = []
        for lg in o.logits:
            if top_p >= 1.0:
                expect.append(V); continue
            srt = torch.sort(lg[0].float(), descending=False)[0]
            cum = srt.softmax(dim=-1).cumsum(dim=-1)
            expect.append(V - int((cum <= (1 - top_p)).sum()))
        res[str(top_p)] = dict(steps=len(kept), vocab=V, kept_min=min(kept), kept_max=max(kept),
                               steps_matching_rule=sum(abs(k - e) <= 1 for k, e in zip(kept, expect)), kept=kept, expected=expect)
    ok = (res["1.0"]["kept_min"] == res["1.0"]["vocab"]
          and res["0.95"]["steps_matching_rule"] == res["0.95"]["steps"] and res["0.95"]["steps"] > 0)
    return ok, res


def scorer_check(key, stok, smodel):
    """The registered statistic of sample_scores.jsonl (harness metrics.sample_under_reference): prefix + continuation text,
    tokenised with <bos>, NLL summed over every token after <bos> under the language's gen-0 model, truncated at the
    registered max_len (longest prefix_ids + n_tokens of the step's 2,000 documents + 8, at most 1024). Recomputed for the
    first n archived documents, one at a time, and compared per document."""
    sd = step_dir(*key)
    docs, max_len = [], 0
    with open(os.path.join(sd, "sample.jsonl"), encoding="utf-8") as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            max_len = max(max_len, len(d.get("prefix_ids") or []) + int(d.get("n_tokens") or 0))
            if i < a.check_n:
                docs.append(d)
    max_len = min(1024, max_len + 8)
    reg = {}
    with open(os.path.join(sd, "sample_scores.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            reg[r["doc_id"]] = r
    diffs, n_mis = [], 0
    for d in docs:
        enc = stok((d.get("prefix") or "") + d["text"], return_tensors="pt", truncation=True, max_length=max_len).to(DEV)
        with torch.no_grad():
            logits = smodel(**enc).logits[0, :-1].float()
        labels = enc["input_ids"][0, 1:]
        nll = float(-torch.log_softmax(logits, dim=-1).gather(-1, labels.unsqueeze(-1)).sum())
        n = int(labels.shape[0])
        r = reg[d["doc_id"]]
        n_mis += int(n != int(r["n_tokens"]))
        diffs.append(abs(nll / max(1, n) - float(r["nll_total_ref"]) / max(1, int(r["n_tokens"]))))
    return dict(chain=key[0], gen=key[1], n_docs=len(docs), max_len=max_len, n_token_count_mismatch=n_mis,
                mean_abs_diff_nll_per_token=round(sum(diffs) / len(diffs), 6), max_abs_diff_nll_per_token=round(max(diffs), 6))


# ---------- main ----------
t_start = time.time()
G0 = {c: gen0_of(c) for c in CHAINS}
gen0_ids = sorted({g for g in G0.values() if g}, key=lambda g: (lang_of(g) != "EN", g))
need = [(g, 0) for g in gen0_ids] + [(c, g) for c in CHAINS for g in range(1, 7)]
ref_of = lambda key: key[0] if key[1] == 0 else G0[key[0]]          # the scoring model of a step
if a.steps:
    sel = set(a.steps.split(","))
    need = [k for k in need if f"{k[0]}:{k[1]}" in sel]
    if not need:
        fail(f"--steps matched nothing: {a.steps}")
langs = sorted({lang_of(k[0]) for k in need})
refs = sorted({ref_of(k) for k in need}, key=lambda g: (lang_of(g) != "EN", g))
for key in [(g, 0) for g in refs] + need:
    sd = step_dir(*key)
    for f in ("checkpoint/config.json", "checkpoint/model.safetensors", "sample.jsonl", "sample_meta.json", "sample_scores.jsonl"):
        if not os.path.exists(os.path.join(sd, f)):
            fail(f"missing {os.path.join(sd, f)}; check the extraction / upload")
gpu = torch.cuda.get_device_name(0) if DEV.startswith("cuda") else "none"
log(f"{len(need)} steps x {len(DECODERS)} decoders, {a.n} prefixes each; scorers {refs}; device {DEV} ({gpu}); "
    f"torch {torch.__version__}, transformers {transformers.__version__}")

vocab = {L: build_vocab(L) for L in langs}
scorers = {}
for g0 in refs:
    log(f"loading generation-0 scorer {g0}")
    scorers[g0] = load_model(os.path.join(step_dir(g0, 0), "checkpoint"))

L0 = refs[0]
first_prefix = load_rows(os.path.join(step_dir(L0, 0), "sample.jsonl"), 1)[0]["prefix_ids"]
dec_ok, dec_res = decoder_check(scorers[L0][1], scorers[L0][0], first_prefix)
log(f"decoder check ({L0} model): top_p 1.0 keeps {dec_res['1.0']['kept_min']}..{dec_res['1.0']['kept_max']} of "
    f"{dec_res['1.0']['vocab']}; top_p 0.95 keeps {dec_res['0.95']['kept_min']}..{dec_res['0.95']['kept_max']}, "
    f"{dec_res['0.95']['steps_matching_rule']}/{dec_res['0.95']['steps']} steps match the top-p rule -> {'OK' if dec_ok else 'FAILED'}")
checks = dict(started_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t_start)), device=DEV, gpu=gpu, torch=torch.__version__,
              transformers=transformers.__version__, dtype=str(DTYPE), sampling=dict(SAMPLING), decoders=list(DECODERS),
              n_prefixes=a.n, check_n=a.check_n, chains=CHAINS, gen0_of_chain={c: G0[c] for c in CHAINS},
              decoder_check_ok=dec_ok, decoder_check=dec_res)
if not dec_ok:
    with open(f"{OUT}/{TAG}_checks.json", "w", encoding="utf-8") as f:
        json.dump(checks, f, indent=1)
    fail("decoder check failed: generate() does not sample with the registered decoders (see cross_decoder_checks.json)")

sc_rows = []
for key in need:
    sc_rows.append(scorer_check(key, *scorers[ref_of(key)]))
    log(f"scorer check {key[0]} gen {key[1]}: mean |diff| {sc_rows[-1]['mean_abs_diff_nll_per_token']}, "
        f"max {sc_rows[-1]['max_abs_diff_nll_per_token']} nats/token, token-count mismatches {sc_rows[-1]['n_token_count_mismatch']}")
with open(f"{OUT}/{TAG}_scorer_check.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(sc_rows[0].keys())); w.writeheader(); w.writerows(sc_rows)

summary = []
raw = open(f"{OUT}/{TAG}_samples.jsonl.gz", "wb")
sink = io.TextIOWrapper(gzip.GzipFile(fileobj=raw, mode="wb", mtime=0), encoding="utf-8")
for key in need:
    name, gen = key
    L = lang_of(name)
    sd = step_dir(name, gen)
    rows = load_rows(os.path.join(sd, "sample.jsonl"), a.n)
    with open(os.path.join(sd, "sample_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    max_new = a.max_new or int(meta["max_new_tokens"])
    prefix_ids_list = [r["prefix_ids"] for r in rows]
    tok, model = (scorers[name] if gen == 0 else load_model(os.path.join(sd, "checkpoint")))
    for top_p in DECODERS:
        seed = zlib.crc32(f"{name}|{gen}|{top_p}".encode()) & 0x7FFFFFFF
        t0 = time.time()
        conts = []
        for b in range(0, len(prefix_ids_list), a.batch):
            conts += generate_batch(model, tok, prefix_ids_list[b:b + a.batch], top_p, max_new, seed + b)
        stok, smodel = scorers[ref_of(key)]
        nlls = score_batch(smodel, stok, prefix_ids_list, conts)
        texts = [tok.decode(c, skip_special_tokens=True) for c in conts]
        words = [[w.lower() for w in WORD_RE.findall(t)] for t in texts]
        ntok = sum(len(w) for w in words)
        oov = sum(1 for ws in words for w in ws if w not in vocab[L])
        ok = [x for x in nlls if not math.isnan(x)]
        if len(ok) < 2:
            fail(f"{name} gen {gen} top_p {top_p}: only {len(ok)} non-empty continuations")
        mean = sum(ok) / len(ok)
        sd_nll = (sum((x - mean) ** 2 for x in ok) / (len(ok) - 1)) ** 0.5
        summary.append(dict(chain=name, gen=gen, gen0=ref_of(key), decoder_top_p=top_p, n=len(ok),
                            mean_nll_nats=round(mean, 4), sd_nll=round(sd_nll, 4),
                            mean_len_tokens=round(sum(len(c) for c in conts) / len(conts), 1),
                            token_oov_share=round(oov / ntok, 5) if ntok else "",
                            n_empty=len(conts) - len(ok), cap_hit_share=round(sum(1 for c in conts if len(c) >= max_new) / len(conts), 3),
                            max_new_tokens=max_new, seed=seed))
        log(f"{json.dumps(summary[-1])} ({time.time() - t0:.0f} s)")
        for r, c, t, x in zip(rows, conts, texts, nlls):
            sink.write(json.dumps(dict(chain=name, gen=gen, decoder_top_p=top_p,
                                       prefix_id=r.get("prefix_id"), nll=x,
                                       n_tokens=len(c), finish="length" if len(c) >= max_new else "stop", text=t),
                                  ensure_ascii=False) + "\n")
    if gen != 0:
        del model; gc.collect()
        if DEV.startswith("cuda"):
            torch.cuda.empty_cache()

sink.close(); raw.close()
with open(f"{OUT}/{TAG}_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(summary[0].keys())); w.writeheader(); w.writerows(summary)
checks.update(finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), seconds=round(time.time() - t_start),
              cells=len(summary), steps=[f"{k[0]}:{k[1]}" for k in need],
              scorer_check_max_abs_diff=max(r["max_abs_diff_nll_per_token"] for r in sc_rows),
              scorer_check_token_count_mismatches=sum(r["n_token_count_mismatch"] for r in sc_rows))
with open(f"{OUT}/{TAG}_checks.json", "w", encoding="utf-8") as f:
    json.dump(checks, f, indent=1)
log(f"wrote {OUT}/{TAG}_summary.csv ({len(summary)} cells), {TAG}_samples.jsonl.gz, "
    f"{TAG}_scorer_check.csv and {TAG}_checks.json")
