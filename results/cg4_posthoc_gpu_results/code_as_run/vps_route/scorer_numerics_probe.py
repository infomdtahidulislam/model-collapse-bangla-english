#!/usr/bin/env python3
"""Numerics probe for the #17 scorer check (VPS route, 2026-10-20). Runs on the GPU host next to 02_cross_decoder.py.

02's scorer check recomputes the registered sample-NLL statistic (sample_scores.jsonl: prefix + continuation text, <bos>,
every token after it, under the gen-0 model). Its token counts were all equal, but the per-token NLL differed by about 0.003 (EN)
and 0.013 (BN) nats. This probe tests whether that is bf16 rounding from batch shapes. For GEN0-EN and GEN0-BN it computes the
statistic four ways and compares each with the archived values:
  A  bf16, one document at a time: what 02's scorer check does;
  B  bf16, the harness Scorer's own batching. All 2,000 documents are sorted by token length and put in right-padded batches of
     at most 4,096 tokens, with fp32 log-softmax (harness/metrics.py Scorer.nll_batch). This is the registered computation,
     run on this host's torch (2.8.0; the run had 2.13.0);
  C  fp32, one document at a time: a reference for the size of bf16 rounding;
  D  A against C on the same documents, i.e. the bf16 rounding alone.
Writes out/scorer_numerics_probe.csv.   usage: python3 scorer_numerics_probe.py   (from /workspace/posthoc_gpu_pack)
"""
import csv, json, os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT, OUT, DEV = "extracted", "out", "cuda"
os.makedirs(OUT, exist_ok=True)


def per_doc_single(model, tok, texts, max_len):
    out = []
    for t in texts:
        enc = tok(t, return_tensors="pt", truncation=True, max_length=max_len).to(DEV)
        with torch.no_grad():
            logits = model(**enc).logits[0, :-1].float()
        labels = enc["input_ids"][0, 1:]
        out.append((float(-torch.log_softmax(logits, -1).gather(-1, labels.unsqueeze(-1)).sum()), int(labels.shape[0])))
    return out


def per_doc_harness(model, tok, texts, max_len, batch_tokens=4096, chunk=1024):
    """harness/metrics.py Scorer.nll_batch, line for line (right padding, length-sorted batches, chunked fp32 log-softmax)."""
    tok.padding_side = "right"
    out = [None] * len(texts)
    lens = [min(max_len, max(1, len(ids))) for ids in tok(texts, truncation=True, max_length=max_len)["input_ids"]]
    order = sorted(range(len(texts)), key=lambda k: lens[k])
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and (j + 1 - i) * lens[order[j]] <= batch_tokens:
            j += 1
        idx = order[i:j]; i = j
        enc = tok([texts[k] for k in idx], return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(DEV)
        with torch.no_grad():
            logits = model(**enc).logits
            labels = enc["input_ids"][:, 1:]; mask = enc["attention_mask"][:, 1:].float()
            lp = torch.empty(labels.shape, dtype=torch.float32, device=logits.device)
            T = labels.shape[1]
            for b in range(labels.shape[0]):
                for c0 in range(0, T, chunk):
                    c1 = min(T, c0 + chunk)
                    lp[b, c0:c1] = torch.log_softmax(logits[b, c0:c1, :].float(), dim=-1).gather(-1, labels[b, c0:c1].unsqueeze(-1)).squeeze(-1)
        nll = -(lp * mask).sum(1); n = mask.sum(1)
        for k, a, c in zip(idx, nll.tolist(), n.tolist()):
            out[k] = (float(a), int(c))
        del logits, lp
    return out


def stats(xs, ys):
    d = [x[0] / max(1, x[1]) - y[0] / max(1, y[1]) for x, y in zip(xs, ys)]
    return dict(n=len(d), mean_signed=round(sum(d) / len(d), 6), mean_abs=round(sum(abs(v) for v in d) / len(d), 6),
                max_abs=round(max(abs(v) for v in d), 6), token_count_mismatch=sum(int(x[1] != y[1]) for x, y in zip(xs, ys)))


rows = []
for L in ("EN", "BN"):
    sd = os.path.join(ROOT, "results", "chains", f"GEN0-{L}")
    docs = [json.loads(l) for l in open(os.path.join(sd, "sample.jsonl"), encoding="utf-8")]
    reg = {json.loads(l)["doc_id"]: json.loads(l) for l in open(os.path.join(sd, "sample_scores.jsonl"), encoding="utf-8")}
    regv = [(float(reg[d["doc_id"]]["nll_total_ref"]), int(reg[d["doc_id"]]["n_tokens"])) for d in docs]
    max_len = min(1024, max(len(d.get("prefix_ids") or []) + int(d.get("n_tokens") or 0) for d in docs) + 8)
    texts = [(d.get("prefix") or "") + d["text"] for d in docs]
    tok = AutoTokenizer.from_pretrained(os.path.join(sd, "checkpoint"))
    m16 = AutoModelForCausalLM.from_pretrained(os.path.join(sd, "checkpoint"), dtype=torch.bfloat16).to(DEV).eval()
    A = per_doc_single(m16, tok, texts[:50], max_len)
    B = per_doc_harness(m16, tok, texts, max_len)
    del m16; torch.cuda.empty_cache()
    m32 = AutoModelForCausalLM.from_pretrained(os.path.join(sd, "checkpoint"), dtype=torch.float32).to(DEV).eval()
    torch.backends.cuda.matmul.allow_tf32 = False
    C = per_doc_single(m32, tok, texts[:50], max_len)
    del m32; torch.cuda.empty_cache()
    for name, x, y in (("A bf16 single-doc vs archived", A, regv[:50]), ("B bf16 harness batching vs archived (50)", B[:50], regv[:50]),
                       ("B bf16 harness batching vs archived (all 2000)", B, regv), ("C fp32 single-doc vs archived", C, regv[:50]),
                       ("D bf16 single-doc vs fp32 single-doc", A, C)):
        rows.append(dict(language=L, comparison=name, max_len=max_len, **stats(x, y)))
        print(rows[-1], flush=True)
with open(f"{OUT}/scorer_numerics_probe.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"wrote {OUT}/scorer_numerics_probe.csv; torch {torch.__version__}")
