#!/usr/bin/env python
"""Stage the inputs of 02_cross_decoder.py (#17) from the VPS copy of the G4b archive, for upload to a rented GPU.

VPS route (2026-10-20). It replaces 01_fetch.sh, the Google Drive download and extraction on the GPU host. The VPS already
holds the archive (results/packs/cg4_pack_20261016-232223.tar.gz, verified at G4b) and its G6 extraction (results/g6_extract/,
every file SHA-256 checked). So only the 26 steps #17 needs go to the GPU host: 15.1 GB instead of the 55.7 GB archive.

Staged layout = the archive's own paths under <stage>/extracted/:
  results/chains/GEN0-{EN,BN}/                                    (generation 0)
  results/chains/{EN,BN}-REPLACE{,-topp95}/gen_{1..6}/            (24 steps)
    checkpoint/{config.json,generation_config.json,model.safetensors,tokenizer.json,tokenizer_config.json}
    sample.jsonl, sample_meta.json, sample_scores.jsonl
  data/corpora/{EN,BN}_seed.jsonl

Sources, in order:
  1. results/g6_extract/ (the non-checkpoint files);
  2. results/chains/ (the checkpoints already on the VPS);
  3. one streaming pass through the archive for the rest.
Every staged file's SHA-256 is checked against the pack manifest. Files already staged with the right hash are kept, so a run
can be resumed. Writes <stage>/inputs.sha256 (sha256sum -c format), which the host checks after the upload. The sample files
hold unscreened model text, so the stage lives under results/.

usage: python posthoc_gpu_pack/vps_route/stage_inputs.py [--stage DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import time
from pathlib import Path

PACKDIR = Path(__file__).resolve().parents[1]
PKG = PACKDIR.parent
ARCHIVE = PKG / "results" / "packs" / "cg4_pack_20261016-232223.tar.gz"
MANIFEST = PKG / "results" / "packs" / "pack_manifest_20261016-232223.json"
G6 = PKG / "results" / "g6_extract"
LOG = PKG / "logs" / "posthoc_gpu_stage.log"
DEFAULT_STAGE = PKG / "results" / "posthoc_gpu_stage_2026-10-20"

STEPS = [("GEN0-EN", 0), ("GEN0-BN", 0)] + [(c, g) for c in ("EN-REPLACE", "EN-REPLACE-topp95", "BN-REPLACE", "BN-REPLACE-topp95")
                                            for g in range(1, 7)]
CKPT = ("config.json", "generation_config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json")
SIDE = ("sample.jsonl", "sample_meta.json", "sample_scores.jsonl")
SEEDS = ("data/corpora/EN_seed.jsonl", "data/corpora/BN_seed.jsonl")
CHUNK = 1 << 22


def step_rel(chain: str, gen: int) -> str:
    return f"results/chains/{chain}" + ("" if gen == 0 else f"/gen_{gen}")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(CHUNK):
            h.update(b)
    return h.hexdigest()


def write_verified(src, dst: Path, want: str) -> bool:
    """Copy the stream `src` to dst through a .part file; keep it only if its SHA-256 is `want`."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    h = hashlib.sha256()
    with open(tmp, "wb") as fo:
        while b := src.read(CHUNK):
            h.update(b)
            fo.write(b)
    if h.hexdigest() != want:
        tmp.unlink()
        return False
    tmp.replace(dst)
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=str(DEFAULT_STAGE))
    a = ap.parse_args()
    stage = Path(a.stage)
    ext = stage / "extracted"
    files = json.load(open(MANIFEST, encoding="utf-8"))["files"]
    want = ([f"{step_rel(c, g)}/checkpoint/{f}" for c, g in STEPS for f in CKPT]
            + [f"{step_rel(c, g)}/{f}" for c, g in STEPS for f in SIDE] + list(SEEDS))
    missing = [p for p in want if p not in files]
    if missing:
        raise SystemExit(f"not in the pack manifest: {missing}")
    total = sum(files[p]["bytes"] for p in want)
    verified: dict[str, str] = {}
    for rel in want:
        dst = ext / rel
        if dst.exists() and dst.stat().st_size == files[rel]["bytes"] and sha256_file(dst) == files[rel]["sha256"]:
            verified[rel] = files[rel]["sha256"]
    log(f"start: {len(want)} files wanted ({total / 1e9:.2f} GB) for {len(STEPS)} steps; {len(verified)} already staged -> {stage}")

    left = []
    for rel in want:
        if rel in verified:
            continue
        for src in (G6 / rel, PKG / rel):
            if src.exists() and src.stat().st_size == files[rel]["bytes"]:
                with open(src, "rb") as fi:
                    ok = write_verified(fi, ext / rel, files[rel]["sha256"])
                if ok:
                    verified[rel] = files[rel]["sha256"]
                    break
                log(f"note: {src.relative_to(PKG)} differs from the manifest; not used")
        else:
            left.append(rel)
    log(f"local copies done: {len(verified)} of {len(want)} staged; {len(left)} to extract from the archive")

    if left:
        need = set(left)
        t0 = time.time()
        log(f"archive pass: {ARCHIVE.name}, {sum(files[p]['bytes'] for p in left) / 1e9:.2f} GB to extract")
        with tarfile.open(ARCHIVE, "r|gz") as tar:
            for m in tar:
                if not m.isfile():
                    continue
                rel = m.name.lstrip("./")
                if rel not in need:
                    continue
                if not write_verified(tar.extractfile(m), ext / rel, files[rel]["sha256"]):
                    raise SystemExit(f"SHA-256 mismatch for {rel} (archive member {m.name})")
                verified[rel] = files[rel]["sha256"]
                need.discard(rel)
                log(f"extracted {rel} ({len(left) - len(need)}/{len(left)}, {time.time() - t0:.0f} s)")
                if not need:
                    break
        if need:
            raise SystemExit(f"not found in the archive: {sorted(need)}")
        log(f"archive pass done in {time.time() - t0:.0f} s")

    lines = [f"{verified[rel]}  extracted/{rel}" for rel in want]
    (stage / "inputs.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    log(f"done: {len(want)} files ({total / 1e9:.2f} GB) staged, every SHA-256 equal to the pack manifest; list in {stage / 'inputs.sha256'}")


if __name__ == "__main__":
    main()
