#!/usr/bin/env python
"""Stage the inputs of posthoc_gpu_pack2 (2026-10-23) from the VPS copy of the G4b archive, for upload to a rented GPU.

Adapted from posthoc_gpu_pack/vps_route/stage_inputs.py (as run on 2026-10-20). The staged tree mirrors the package
root, so the host runs the harness in place at /workspace/CG4:

  batch A (needed before the chains can start; about 2.4 GB):
    results/chains/GEN0-{EN,BN}-{s2,s3}/   checkpoint files, step.json, sample.jsonl, sample_meta.json, sample_scores.jsonl
    harness/, configs/{chains,corpora,runtime}.yaml, schemas/, data/corpora, data/heldout, data/probes (package copies)
    posthoc_gpu_pack2_2026-10-23/ (this pack)
  batch B (needed only by 02b_cross_decoder.py after the chains; about 27 GB; may upload while the chains run):
    results/chains/GEN0-{EN,BN}/ and {EN,BN}-REPLACE{,-s2,-s3,-topp95}/gen_{1..6}/ with the same files

Sources for archive members, in order: results/g6_extract/, the VPS working copy results/chains/, then one streaming pass
through the archive. Every archive member is checked against the pack manifest; the package files (harness, configs,
schemas, data) are checked against the SHA-256 values below, which are those of the run (v1.0.0 release and the PC copy).
Writes <stage>/inputs_A.sha256 and <stage>/inputs_B.sha256 (sha256sum -c format, paths relative to the stage root).
The sample files hold unscreened model text, so the stage lives under results/ and stays private.

usage: python posthoc_gpu_pack2_2026-10-23/vps_route/stage_inputs2.py [--stage DIR] [--batch A|B|AB]
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
LOG = PKG / "logs" / "posthoc_gpu_stage2.log"
DEFAULT_STAGE = PKG / "results" / "posthoc_gpu_stage2_2026-10-23"

STEPS_A = [(f"GEN0-{L}-{s}", 0) for L in ("EN", "BN") for s in ("s2", "s3")]
STEPS_B = [(f"GEN0-{L}", 0) for L in ("EN", "BN")] + [
    (f"{L}-{c}", g) for L in ("EN", "BN") for c in ("REPLACE", "REPLACE-s2", "REPLACE-s3", "REPLACE-topp95") for g in range(1, 7)]
CKPT = ("config.json", "generation_config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json")
SIDE = ("step.json", "sample.jsonl", "sample_meta.json", "sample_scores.jsonl")

# package files as run (SHA-256 of the v1.0.0 release copy and the PC copy, 2026-10-23)
PKG_SHA = {
    "configs/chains.yaml": "c911895ecc1f6b0079b1bd919eff6f6f2b69e229a9939a5382131cb9db9c1084",
    "configs/corpora.yaml": "129d8d7c993660902fbace0693485f20763923bd08443798c60add1417069710",
    "harness/run_chain.py": "b1e27dcbc90a3d67cf70813ce79490f4863dd30068acabe6d2031c04307027c2",
    "harness/metrics.py": "18d32088f653e2bc9b75616a62ffb95056f1884ab9209d1c68ad997f100d125f",
    "harness/common.py": "f7618104c625fd389a097e4434365b0138601d9f39ed7f394e8e6d258d942ca5",
    "harness/run_rented.py": "908377a00156afcba8d3b5410a952d39ac4b48c9297467a232bad3d839bb0e07",
    "harness/vast/bootstrap.sh": "669c8a434b84831bc1b6a08c75d6fbfbd4c4289adb31816d1ab721bb88869314",
    "harness/vast/pins_gen0.txt": "dc6135440fd43cb71e80b47ca0f5268b4347575932dab5f2f33d25505f56a237",
    "data/corpora/BN_seed.jsonl": "f686c5c34943fe3a65085d879682d1d538270bafff7de0bd07260b1ee106e3d9",
    "data/corpora/BN_seed_minhash.npy": "23ab733131f63174d861d87be425d514a277a2d7bb9e436549b1bf17487e9159",
    "data/corpora/EN_seed.jsonl": "ca73a1b32f2194de88c90cb98a547fd37f152c9e8146c9d93a696afe1ef071bc",
    "data/corpora/EN_seed_minhash.npy": "5e18e6759662ae6c54b0b26ad4b59defba7f3940c9e4b75d0960ebca89162feb",
    "data/corpora/manifest.json": "205384491380b25ee199c775cc3c7d88bc0ccc16d7ff1bf9bf040ce84d0e7311",
    "data/corpora/prefixes_BN.jsonl": "dbf1f3bf5c69cfc579380aad9f577581071d0d807f70b598b45a34f838d8fcb6",
    "data/corpora/prefixes_EN.jsonl": "c1bb8bde6c3e0cf616343e293d1976fd6ba26ad54bc5367ee3705548ce3249ab",
    "data/heldout/BN_heldout.jsonl": "ec86d2078aec15b9c221f210385d6402719e600e8cedf7afd3d546d8f6e5196e",
    "data/heldout/EN_heldout.jsonl": "78ce31f01ca65f4ff44b3ef71c79a556c3ac072629f54011b034cbdb35c0fd18",
    "data/probes/BN_bias.jsonl": "0fbae0d5a8513f1f8d6ae0456959978c033730d0ccf215945430c9c73948546b",
    "data/probes/BN_tail_facts.jsonl": "9ece2bfa28a115f7c20d1c63433511900a0a3e9f4a6b4ce84b44bf963c969eed",
    "data/probes/EN_bias.jsonl": "e73f1115dcff124e8f9afb6f74da58bc497da852477667a70e2d11310fe0312b",
    "data/probes/EN_tail_facts.jsonl": "f76e822d9d0f54e818884c79c9b4a05f33a69236e9017312021b1ad9efdf7107",
    "data/probes/bias_exclusions.json": "07f2e0df6dc49d405acebb0d1de5d8bbde2af538f13a06469e0a9038d6585c80",
}
PKG_DIRS = ("harness", "schemas")                       # copied whole (minus __pycache__); the key files are checked above
PKG_FILES = ("configs/runtime.yaml",)
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


def write_verified(src, dst: Path, want: str | None) -> str | None:
    """Copy the stream to dst through a .part file; return its SHA-256, or None (and no file) if it is not `want`."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    h = hashlib.sha256()
    with open(tmp, "wb") as fo:
        while b := src.read(CHUNK):
            h.update(b)
            fo.write(b)
    if want is not None and h.hexdigest() != want:
        tmp.unlink()
        return None
    tmp.replace(dst)
    return h.hexdigest()


def stage_archive_members(want: list[str], stage: Path, files: dict) -> dict[str, str]:
    missing = [p for p in want if p not in files]
    if missing:
        raise SystemExit(f"not in the pack manifest: {missing[:10]} ... ({len(missing)})")
    verified: dict[str, str] = {}
    for rel in want:
        dst = stage / rel
        if dst.exists() and dst.stat().st_size == files[rel]["bytes"] and sha256_file(dst) == files[rel]["sha256"]:
            verified[rel] = files[rel]["sha256"]
    left = []
    for rel in want:
        if rel in verified:
            continue
        for src in (G6 / rel, PKG / rel):
            if src.exists() and src.stat().st_size == files[rel]["bytes"]:
                with open(src, "rb") as fi:
                    got = write_verified(fi, stage / rel, files[rel]["sha256"])
                if got:
                    verified[rel] = got
                    break
                log(f"note: {src} differs from the manifest; not used")
        else:
            left.append(rel)
    log(f"local copies: {len(verified)} of {len(want)} staged; {len(left)} to extract from the archive")
    if left:
        need = set(left); t0 = time.time()
        with tarfile.open(ARCHIVE, "r|gz") as tar:
            for m in tar:
                if not m.isfile():
                    continue
                rel = m.name.lstrip("./")
                if rel not in need:
                    continue
                got = write_verified(tar.extractfile(m), stage / rel, files[rel]["sha256"])
                if not got:
                    raise SystemExit(f"SHA-256 mismatch for {rel}")
                verified[rel] = got; need.discard(rel)
                if not need:
                    break
        if need:
            raise SystemExit(f"not found in the archive: {sorted(need)[:10]}")
        log(f"archive pass done in {time.time() - t0:.0f} s")
    return verified


def stage_package(stage: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel, want in PKG_SHA.items():
        src = PKG / rel
        got = sha256_file(src)
        if got != want:
            raise SystemExit(f"{rel}: SHA-256 {got} is not the run's {want}; stop and compare (do not stage a changed file)")
    rels = list(PKG_SHA) + list(PKG_FILES)
    for d in PKG_DIRS:
        rels += [p.relative_to(PKG).as_posix() for p in sorted((PKG / d).rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    for d in sorted(PACKDIR.rglob("*")):
        if d.is_file() and "__pycache__" not in d.parts:
            rels.append(d.relative_to(PKG).as_posix())
    for rel in dict.fromkeys(rels):
        with open(PKG / rel, "rb") as fi:
            out[rel] = write_verified(fi, stage / rel, None)
    log(f"package files staged: {len(out)} (key files match the run's SHA-256)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default=str(DEFAULT_STAGE))
    ap.add_argument("--batch", default="AB", choices=("A", "B", "AB"))
    a = ap.parse_args()
    stage = Path(a.stage)
    files = json.load(open(MANIFEST, encoding="utf-8"))["files"]
    for b in a.batch:
        steps = STEPS_A if b == "A" else STEPS_B
        want = [f"{step_rel(c, g)}/checkpoint/{f}" for c, g in steps for f in CKPT] + [f"{step_rel(c, g)}/{f}" for c, g in steps for f in SIDE]
        total = sum(files[p]["bytes"] for p in want if p in files)
        log(f"batch {b}: {len(want)} archive files ({total / 1e9:.2f} GB) for {len(steps)} steps -> {stage}")
        verified = stage_archive_members(want, stage, files)
        if b == "A":
            verified.update(stage_package(stage))
        lines = [f"{verified[rel]}  {rel}" for rel in verified]
        (stage / f"inputs_{b}.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        log(f"batch {b} done: {len(lines)} files listed in inputs_{b}.sha256")


if __name__ == "__main__":
    main()
