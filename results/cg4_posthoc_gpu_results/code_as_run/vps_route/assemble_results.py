#!/usr/bin/env python
"""Assemble the take-home folder results/cg4_posthoc_gpu_results/ (VPS route, 2026-10-20).

- Checks the pulled host archive logs/host_56846008/out_host.tar.gz against the SHA-256 the host wrote (out_host.sha256). Unpacks
  out/* into the folder and the host's run.log into logs/host_run_02.log, then checks every unpacked file against the
  host's list.
- Copies the code as run into code_as_run/: the three patched scripts, vps_route/, PATCH_NOTES.md, patches.diff, and the PC
  originals' SHA256SUMS.txt.
- Writes SHA256SUMS.txt over every file in the folder, then zips the folder to
  results/cg4_posthoc_gpu_results_2026-10-20.zip and writes the zip's SHA-256 next to it.
The folder and the zip hold unscreened synthetic text (cross_decoder_samples.jsonl.gz; the word types in
nonword_top_types.csv): private storage only.

usage: python posthoc_gpu_pack/vps_route/assemble_results.py
"""
from __future__ import annotations

import hashlib
import shutil
import tarfile
import zipfile
from pathlib import Path

PACKDIR = Path(__file__).resolve().parents[1]
PKG = PACKDIR.parent
RES = PKG / "results" / "cg4_posthoc_gpu_results"
PULL = PKG / "logs" / "host_56846008"          # out_host.tar.gz + out_host.sha256 pulled from the host, next to its logs
ZIP = PKG / "results" / "cg4_posthoc_gpu_results_2026-10-20.zip"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while b := f.read(1 << 22):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    host = {}
    for ln in (PULL / "out_host.sha256").read_text(encoding="utf-8").splitlines():
        if ln.strip():
            h, name = ln.split(None, 1)
            host[name.lstrip("*").strip()] = h
    if sha(PULL / "out_host.tar.gz") != host["out_host.tar.gz"]:
        raise SystemExit("out_host.tar.gz differs from the host's SHA-256: pull it again")
    (RES / "logs").mkdir(parents=True, exist_ok=True)
    with tarfile.open(PULL / "out_host.tar.gz") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.name.startswith("out/") and "/" not in m.name[4:]:
                dest = RES / m.name[4:]
            elif m.name == "run.log":
                dest = RES / "logs" / "host_run_02.log"
            else:
                raise SystemExit(f"unexpected member in the host archive: {m.name}")
            with tf.extractfile(m) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    bad = [n for n, h in host.items() if n.startswith("out/") and sha(RES / n[4:]) != h]
    if bad:
        raise SystemExit(f"unpacked files differ from the host's SHA-256: {bad}")
    print(f"host results unpacked and checked: {len([n for n in host if n.startswith('out/')])} files")
    # the run.log inside the tarball is a snapshot taken while packing; the one pulled afterwards (logs/host_56846008/, SHA-256
    # equal to the host's final file) is complete, so it replaces the snapshot; the numerics probe's log goes beside it
    for src, name in (("run.log", "host_run_02.log"), ("probe.log", "host_scorer_numerics_probe.log")):
        p = PKG / "logs" / "host_56846008" / src
        if p.exists():
            shutil.copy2(p, RES / "logs" / name)

    code = RES / "code_as_run"
    if code.exists():
        shutil.rmtree(code)
    (code / "vps_route").mkdir(parents=True)
    for f in ("02_cross_decoder.py", "03_labse_sensitivity.py", "04_nonword_bigram.py", "PATCH_NOTES.md", "patches.diff"):
        shutil.copy2(PACKDIR / f, code / f)
    for f in sorted((PACKDIR / "vps_route").glob("*")):
        if f.is_file():
            shutil.copy2(f, code / "vps_route" / f.name)
    shutil.copy2(PACKDIR / "_original_from_pc" / "SHA256SUMS.txt", code / "SHA256SUMS_original_from_pc.txt")
    shutil.copy2(PKG / "results" / "posthoc_gpu_stage_2026-10-20" / "inputs.sha256", code / "inputs_17.sha256")

    files = sorted(p for p in RES.rglob("*") if p.is_file() and PULL not in p.parents and p.name != "SHA256SUMS.txt")
    lines = [f"{sha(p)}  {p.relative_to(RES).as_posix()}" for p in files]
    (RES / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"SHA256SUMS.txt: {len(lines)} files")

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files + [RES / "SHA256SUMS.txt"]:
            z.write(p, arcname=f"cg4_posthoc_gpu_results/{p.relative_to(RES).as_posix()}")
    with zipfile.ZipFile(ZIP) as z:
        if z.testzip() is not None:
            raise SystemExit("zip test failed")
    zh = sha(ZIP)
    ZIP.with_name(ZIP.name + ".sha256").write_text(f"{zh}  {ZIP.name}\n", encoding="utf-8", newline="\n")
    print(f"zip: {ZIP} ({ZIP.stat().st_size / 1e6:.1f} MB, {len(files) + 1} files, CRC OK), SHA-256 {zh}")


if __name__ == "__main__":
    main()
