#!/usr/bin/env python
"""Upload a staged batch of posthoc_gpu_pack2 (2026-10-23) from the VPS to the rented host.

Adapted from posthoc_gpu_pack/vps_route/upload_inputs.py (as run on 2026-10-20). For batch A or B it sends to
/workspace/CG4 on the host:
  - inputs_<b>.sha256;
  - inputs_<b>_small.tar.gz: every staged file of the batch except the weights and the identical tokenizer.json copies,
    plus one tokenizer.json as shared/tokenizer.json (host_run2.sh puts it back into every checkpoint folder);
  - each model.safetensors, several scp streams at a time, each file retried up to 3 times.
Each file's size is checked on the host; host_run2.sh checks every SHA-256 against inputs_<b>.sha256.

usage: python posthoc_gpu_pack2_2026-10-23/vps_route/upload_inputs2.py --instance ID --batch A|B [--streams 4]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import subprocess
import sys
import tarfile
import time
from pathlib import Path

PACKDIR = Path(__file__).resolve().parents[1]
PKG = PACKDIR.parent
sys.path.insert(0, str(PKG / "harness" / "vast"))
import vast_ops  # noqa: E402

STAGE = PKG / "results" / "posthoc_gpu_stage2_2026-10-23"
REMOTE = "/workspace/CG4"


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}", flush=True)


def scp_to(host: str, port: int, src: Path, dst: str, tries: int = 3) -> float:
    for k in range(1, tries + 1):
        t0 = time.time()
        r = subprocess.run(["scp", *vast_ops.SSH_OPTS, "-q", "-P", str(port), str(src), f"root@{host}:{dst}"], capture_output=True, text=True)
        if r.returncode == 0:
            return time.time() - t0
        log(f"scp of {src.name} -> {dst} failed (attempt {k}/{tries}, exit {r.returncode}): {r.stderr.strip()[-300:]}")
        time.sleep(10 * k)
    raise SystemExit(f"upload failed after {tries} attempts: {src}")


def ssh(host: str, port: int, cmd: str) -> str:
    r = subprocess.run(["ssh", *vast_ops.SSH_OPTS, "-p", str(port), f"root@{host}", cmd], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"ssh failed ({r.returncode}): {cmd}\n{r.stderr.strip()[-500:]}")
    return r.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=int, required=True)
    ap.add_argument("--batch", required=True, choices=("A", "B"))
    ap.add_argument("--streams", type=int, default=4)
    a = ap.parse_args()
    vast_ops.load_env()
    host, port = vast_ops.ssh_target(a.instance)
    lst = STAGE / f"inputs_{a.batch}.sha256"
    rels = [ln.split("  ", 1)[1] for ln in lst.read_text(encoding="utf-8").splitlines() if ln.strip()]
    weights = [r for r in rels if r.endswith("/model.safetensors")]
    toks = [r for r in rels if r.endswith("/checkpoint/tokenizer.json")]
    small = [r for r in rels if r not in set(weights) | set(toks)]
    log(f"batch {a.batch} -> instance {a.instance} (root@{host}:{port}): {len(weights)} weight files, {len(small)} small files, "
        f"{len(toks)} tokenizer copies")
    ssh(host, port, f"mkdir -p {REMOTE} " + " ".join(sorted({f"{REMOTE}/{w.rsplit('/', 1)[0]}" for w in weights})))
    tgz = STAGE / f"inputs_{a.batch}_small.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        for r in small:
            tf.add(STAGE / r, arcname=r)
        if toks:
            tf.add(STAGE / toks[0], arcname="shared/tokenizer.json")
    for src in (lst, tgz):
        dt = scp_to(host, port, src, f"{REMOTE}/{src.name}")
        log(f"uploaded {src.name} ({src.stat().st_size / 1e6:.1f} MB, {dt:.0f} s)")
    t0, done, nbytes = time.time(), 0, 0

    def one(rel: str):
        src = STAGE / rel
        return rel, src.stat().st_size, scp_to(host, port, src, f"{REMOTE}/{rel}")

    with cf.ThreadPoolExecutor(max_workers=a.streams) as ex:
        for rel, size, dt in ex.map(one, weights):
            done += 1; nbytes += size; el = time.time() - t0
            log(f"uploaded {rel} ({size / 1e6:.0f} MB in {dt:.0f} s); {done}/{len(weights)}, {nbytes / 1e9:.2f} GB, {nbytes / 1e6 / max(1, el):.1f} MB/s")
    sizes = {}
    if weights:
        for ln in ssh(host, port, f"cd {REMOTE} && stat -c '%s %n' " + " ".join(weights)).splitlines():
            s, n = ln.split(" ", 1); sizes[n] = int(s)
    bad = [w for w in weights if sizes.get(w) != (STAGE / w).stat().st_size]
    if bad:
        raise SystemExit(f"size differs on the host for {len(bad)} files: {bad}")
    log(f"batch {a.batch}: all {len(weights)} weight files on the host with the right size; host_run2.sh checks SHA-256")


if __name__ == "__main__":
    main()
