#!/usr/bin/env python
"""Robustness (ix), as fixed by the authors in REQ-026 (2026-10-18; 07_ANALYSIS_PLAN.md §5): semantic dispersion of the
2,000-document sample of every step under sentence-transformers/LaBSE.

Input: the generated continuation ("text"; the prefix is excluded) of each document in a step's sample.jsonl, embedded with
LaBSE (the model's 256-token maximum) and unit-normalised. Statistic: dispersion = 1 - mean pairwise cosine similarity over
all pairs of different documents = 1 - (|sum e|^2 - n) / (n (n - 1)). 95% CI: document bootstrap, 300 resamples, seed =
config seed + generation (as the other sample metrics); within a resample, pairs formed by two copies of the same document are
left out: mean = (|sum w e|^2 - sum w^2) / (n^2 - sum w^2) with w the copy counts, which equals the point formula when w = 1.

Writes one record per step to results/semantic_dispersion.jsonl (schema as results/metrics.jsonl, metric
"semantic_dispersion_labse"); steps already present are skipped, so a run can be resumed. Runs on CPU.

usage: python harness/tools/semantic_dispersion.py [--root results/g6_extract/results/chains] [--only GLOB] [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, LOGS, load_chains_cfg, log_decision, now_iso, read_jsonl, utf8_stdout  # noqa: E402

utf8_stdout()
MODEL = "sentence-transformers/LaBSE"
REVISION = "836121a0533e5664b21c7aacc5d22951f2b8b25b"   # pinned at the first download (2026-10-18), the same on every machine
METRIC = "semantic_dispersion_labse"
B = 300


def dispersion(E: np.ndarray) -> float:
    n = len(E)
    s = E.sum(0)
    return float(1.0 - (s @ s - n) / (n * (n - 1)))


def boot_ci(E: np.ndarray, seed: int, B: int = B) -> tuple[float, float]:
    n = len(E)
    rng = np.random.default_rng(seed)
    W = np.stack([np.bincount(rng.integers(0, n, n), minlength=n) for _ in range(B)]).astype(np.float64)   # B x n copy counts
    S = W @ E.astype(np.float64)
    w2 = (W ** 2).sum(1)
    vals = 1.0 - ((S * S).sum(1) - w2) / (n * n - w2)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def self_check() -> None:
    rng = np.random.default_rng(0)
    E = rng.normal(size=(50, 8))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    brute = np.mean([E[i] @ E[j] for i in range(50) for j in range(50) if i != j])
    assert abs(dispersion(E) - (1 - brute)) < 1e-12
    w = np.ones(50)
    S = w @ E
    assert abs((1 - ((S @ S) - (w ** 2).sum()) / (2500 - (w ** 2).sum())) - dispersion(E)) < 1e-12
    assert abs(dispersion(np.tile(E[:1], (10, 1)))) < 1e-12        # identical documents: dispersion 0


def step_of(p: Path) -> tuple[str, int]:
    parts = p.parts
    i = parts.index("chains")
    chain = parts[i + 1]
    if chain.startswith("BASE-"):
        return chain, -1
    if chain.startswith("GEN0-"):
        return chain, 0
    return chain, int(parts[i + 2].split("_")[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(RESULTS / "g6_extract" / "results" / "chains"))
    ap.add_argument("--only", default="**/sample.jsonl")
    ap.add_argument("--out", default=str(RESULTS / "semantic_dispersion.jsonl"))
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="tests only: embed the first N documents of each file (0 = all)")
    ap.add_argument("--device", default="cpu", help="cpu (VPS) or cuda (rented GPU, REQ-028); fp32 either way, TF32 off on cuda")
    ap.add_argument("--no-log", action="store_true", help="do not write a decisions.md line (on a rented host)")
    a = ap.parse_args()
    self_check()
    out = Path(a.out)
    done = {(r["chain_id"], r["generation"]) for r in read_jsonl(out)} if out.exists() else set()
    from common import chain_meta  # noqa: E402
    meta = chain_meta(load_chains_cfg())

    def order(p: Path) -> tuple:
        """Base and generation-0 models first, then the confirmatory chains, then the robustness chains in priority order."""
        c, g = step_of(p)
        pr = -1 if c.startswith(("BASE-", "GEN0-")) else int((meta.get(c) or {}).get("priority") or 0)
        return (pr, c, g)

    files = sorted(Path(a.root).glob(a.only), key=order)
    todo = [p for p in files if step_of(p) not in done]
    logf = LOGS / "semantic_dispersion.log"

    def log(msg: str) -> None:
        line = f"{now_iso()} {msg}"
        print(line, flush=True)
        with open(logf, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"{len(files)} sample files under {a.root}; {len(done)} steps already done; {len(todo)} to do")
    if not todo:
        return
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    if a.device.startswith("cuda"):
        import torch
        torch.backends.cuda.matmul.allow_tf32 = False      # plain fp32, as on the CPU
        torch.backends.cudnn.allow_tf32 = False
        torch.set_float32_matmul_precision("highest")
    path = snapshot_download(MODEL, revision=REVISION)
    revision = Path(path).name
    model = SentenceTransformer(path, device=a.device)
    import torch
    log(f"model {MODEL} revision {revision}, max_seq_length {model.max_seq_length}, device {a.device}, torch {torch.__version__}")
    seed0 = int(load_chains_cfg()["seed"])
    for p in todo:
        chain, gen = step_of(p)
        t0 = time.time()
        docs = list(read_jsonl(p))
        texts = [d["text"] for d in docs][: a.limit or None]
        E = model.encode(texts, batch_size=a.batch, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        val = dispersion(E.astype(np.float64))
        lo, hi = boot_ci(E, seed0 + gen)
        rec = {"chain_id": chain, "generation": gen, "metric": METRIC, "value": val, "ci_lo": lo, "ci_hi": hi, "n": len(texts),
               "checkpoint": f"{MODEL}@{revision}", "computed_at": now_iso(),
               "sample_file": str(p.resolve().relative_to(RESULTS.parent.resolve())).replace("\\", "/"),
               "sample_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "language": chain.split("-")[1] if chain.startswith(("BASE-", "GEN0-")) else chain[:2]}
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        log(f"{chain} gen {gen}: {val:.5f} [{lo:.5f}, {hi:.5f}], n {len(texts)}, {time.time() - t0:.0f} s")
    if not a.no_log and Path(a.out).resolve() == (RESULTS / "semantic_dispersion.jsonl").resolve() and a.only == "**/sample.jsonl":
        n = sum(1 for _ in read_jsonl(out))
        log_decision(f"robustness (ix) computed (REQ-026): {METRIC} for {n} steps under {MODEL}@{revision}, written to "
                     f"results/semantic_dispersion.jsonl (log logs/semantic_dispersion.log).")


if __name__ == "__main__":
    main()
