#!/usr/bin/env python3
"""
Pack everything the paper needs before deleting a rented instance (or ending a Kaggle session).

  python harness/pack_results.py --checkpoints none    # results (no synthetic corpora, no checkpoints), logs, manifests, seed corpora, environment
  python harness/pack_results.py --with-synthetic      # also synthetic*.jsonl (synthetic, kept, top-up; a few GB)
  python harness/pack_results.py --checkpoints final   # also gen-0 and last-generation checkpoints per chain
  python harness/pack_results.py --checkpoints all     # DEFAULT: every checkpoint (bf16, ~0.54 GB each; ~40-50 GB for the whole design)
Default since 2026-10-12 (design review): --checkpoints all. Every per-generation checkpoint plus every synthetic corpus is
what makes later reviewer requests answerable without new training. Writes results/packs/cg4_pack_<timestamp>.tar.gz and
pack_manifest.json (SHA-256 per file). Download the archive, verify the hashes locally with --verify <archive>, and only then
delete the instance.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import tarfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAINS, DATA, LOGS, RESULTS, ROOT, all_chains, load_chains_cfg, now_iso, read_json, sha256_file, utf8_stdout, write_json  # noqa: E402

utf8_stdout()


def capture_environment() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    env = {"captured_at": now_iso(), "python": sys.version, "platform": platform.platform()}
    for name, cmd in (("pip_freeze", [sys.executable, "-m", "pip", "freeze"]), ("nvidia_smi", ["nvidia-smi"]), ("nvidia_smi_query", ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv"])):
        try:
            env[name] = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
        except Exception as e:  # noqa
            env[name] = f"unavailable: {e}"
    write_json(LOGS / "environment.json", env)


def select_files(with_synthetic: bool, checkpoints: str) -> list[Path]:
    files: list[Path] = []
    for p in RESULTS.rglob("*"):
        if not p.is_file() or "packs" in p.parts:
            continue
        if p.name.startswith("synthetic") and not with_synthetic:
            continue
        if "checkpoint" in p.parts or "trainer" in p.parts:
            continue
        files.append(p)
    files += [p for p in LOGS.rglob("*") if p.is_file()]
    for sub in ("corpora/manifest.json", "corpora/prefixes_EN.jsonl", "corpora/prefixes_BN.jsonl", "corpora/EN_seed.jsonl", "corpora/BN_seed.jsonl"):
        if (DATA / sub).exists():
            files.append(DATA / sub)
    files += [p for p in (DATA / "probes").rglob("*") if p.is_file()]
    files += [p for p in (DATA / "heldout").rglob("*") if p.is_file()]
    files += [p for p in (ROOT / "configs").rglob("*") if p.is_file()]
    if checkpoints != "none":
        cfg = load_chains_cfg()
        wanted = [d / "checkpoint" for d in sorted(CHAINS.glob("GEN0-*")) if (d / "checkpoint").exists()]
        for c in all_chains(cfg):
            st = read_json(CHAINS / c["id"] / "state.json", {"completed": []})
            gens = st["completed"] if checkpoints == "all" else ([max(st["completed"])] if st["completed"] else [])
            for g in gens:
                wanted.append(CHAINS / c["id"] / f"gen_{g}" / "checkpoint")
        for d in wanted:
            files += [p for p in d.rglob("*") if p.is_file()] if d.exists() else []
    return sorted(set(files))


def pack(with_synthetic: bool, checkpoints: str) -> Path:
    capture_environment()
    files = select_files(with_synthetic, checkpoints)
    out_dir = RESULTS / "packs"; out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    manifest = {"created_at": now_iso(), "with_synthetic": with_synthetic, "checkpoints": checkpoints, "files": {}}
    total = 0
    for p in files:
        rel = str(p.relative_to(ROOT)); manifest["files"][rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}; total += p.stat().st_size
    man_path = out_dir / f"pack_manifest_{stamp}.json"; write_json(man_path, manifest)
    archive = out_dir / f"cg4_pack_{stamp}.tar.gz"
    # compresslevel 1: tarfile's default level 9 ran at ~7 MB/s on one core (G4b, 2026-10-16: ~3 h for 73 GB); level 1 keeps most
    # of the gain on the jsonl files, and --verify checks every file's SHA-256 either way
    with tarfile.open(archive, "w:gz", compresslevel=1) as tar:
        for p in files:
            tar.add(p, arcname=str(p.relative_to(ROOT)))
        tar.add(man_path, arcname=f"results/packs/{man_path.name}")
    print(f"[ok] {len(files)} files, {total / 1e9:.2f} GB uncompressed -> {archive} ({archive.stat().st_size / 1e9:.2f} GB)")
    print("Next: download the archive and the manifest, run --verify locally, then delete the instance.")
    return archive


def verify(archive: Path) -> None:
    import hashlib
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        man_name = next((n for n in names if "pack_manifest_" in n), None)
        if not man_name:
            raise SystemExit("manifest missing from archive")
        manifest = json.load(tar.extractfile(man_name))
        bad = 0
        for rel, info in manifest["files"].items():
            member = tar.extractfile(rel)
            if member is None:
                print(f"[missing] {rel}"); bad += 1; continue
            h = hashlib.sha256()
            while True:
                b = member.read(1 << 20)
                if not b:
                    break
                h.update(b)
            if h.hexdigest() != info["sha256"]:
                print(f"[corrupt] {rel}"); bad += 1
    print("VERIFY:", "OK" if bad == 0 else f"{bad} problems")
    sys.exit(1 if bad else 0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-synthetic", action="store_true"); ap.add_argument("--checkpoints", choices=["none", "final", "all"], default="all")
    ap.add_argument("--verify", type=Path)
    a = ap.parse_args()
    if a.verify:
        verify(a.verify)
    else:
        pack(a.with_synthetic, a.checkpoints)


if __name__ == "__main__":
    main()
