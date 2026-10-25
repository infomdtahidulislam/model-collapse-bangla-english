#!/usr/bin/env python
"""G6: extract what the archive-based analysis needs from the G4b archive, in one streaming pass.

Skips the checkpoints' weights and tokenizer copies (model.safetensors, tokenizer.json, tokenizer_config.json, config.json,
generation_config.json); extracts everything else (synthetic corpora, the 2,000-document samples, step/filter/generate/train
records, per-item sidecars, seed corpora, logs) into results/g6_extract/ (unscreened model text stays inside results/).
Each extracted file's SHA-256 is checked against the pack manifest. Progress goes to logs/g6_extract.log.

usage: python harness/tools/g6_extract.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import tarfile
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
PACK = PKG / "results" / "packs" / "cg4_pack_20261016-232223.tar.gz"
MANIFEST = PKG / "results" / "packs" / "pack_manifest_20261016-232223.json"
OUT = PKG / "results" / "g6_extract"
LOG = PKG / "logs" / "g6_extract.log"
SKIP = {"model.safetensors", "tokenizer.json", "tokenizer_config.json", "config.json", "generation_config.json"}


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    files = json.load(open(MANIFEST, encoding="utf-8"))["files"]          # {path: {"sha256": ..., "bytes": ...}}
    want = {p: v["sha256"] for p, v in files.items()}
    OUT.mkdir(parents=True, exist_ok=True)
    n_ok = n_skip = n_bad = 0
    t0 = time.time()
    log(f"start: {PACK.name} -> {OUT.relative_to(PKG)}")
    with tarfile.open(PACK, "r|gz") as tar:
        for m in tar:
            if not m.isfile():
                continue
            name = m.name.split("/")[-1]
            if name in SKIP:
                n_skip += 1
                continue
            rel = m.name.lstrip("./")
            dest = OUT / rel
            if dest.resolve() != dest.resolve().absolute() or not str(dest.resolve()).startswith(str(OUT.resolve())):
                raise SystemExit(f"unsafe path in archive: {m.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            src = tar.extractfile(m)
            with open(dest, "wb") as f:
                while True:
                    b = src.read(1 << 20)
                    if not b:
                        break
                    h.update(b)
                    f.write(b)
            exp = want.get(rel) or want.get(m.name)
            if exp and h.hexdigest() != exp:
                n_bad += 1
                log(f"SHA-256 MISMATCH {rel}")
            else:
                n_ok += 1
            if (n_ok + n_bad) % 100 == 0:
                log(f"extracted {n_ok + n_bad} files ({n_bad} mismatches), skipped {n_skip}, {time.time() - t0:.0f} s")
    log(f"done: extracted {n_ok + n_bad} files, {n_bad} SHA-256 mismatches, skipped {n_skip} checkpoint files, {time.time() - t0:.0f} s")
    if n_bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
