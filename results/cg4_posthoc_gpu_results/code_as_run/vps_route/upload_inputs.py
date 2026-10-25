#!/usr/bin/env python
"""Upload the staged inputs of #17 from the VPS to the rented host (VPS route, 2026-10-20).

What goes to /workspace/posthoc_gpu_pack/ on the host:
  - 02_cross_decoder.py, host_run_02.sh and inputs.sha256;
  - inputs_small.tar.gz: every staged file except the weights and the 26 identical tokenizer.json copies, plus one
    tokenizer.json as shared/tokenizer.json;
  - the 26 model.safetensors files, several scp streams at a time, each file retried up to 3 times.
Each upload's exit code is checked, and each file's size is checked on the host. host_run_02.sh then checks every file's SHA-256
against inputs.sha256, which comes from the pack manifest.

usage: python posthoc_gpu_pack/vps_route/upload_inputs.py --instance ID [--streams 4] [--only-weights] [--files REL,...]
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

STAGE = PKG / "results" / "posthoc_gpu_stage_2026-10-20"
REMOTE = "/workspace/posthoc_gpu_pack"


def log(msg: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}", flush=True)


def scp_to(host: str, port: int, src: Path, dst: str, tries: int = 3) -> float:
    for k in range(1, tries + 1):
        t0 = time.time()
        r = subprocess.run(["scp", *vast_ops.SSH_OPTS, "-q", "-P", str(port), str(src), f"root@{host}:{dst}"],
                           capture_output=True, text=True)
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
    ap.add_argument("--streams", type=int, default=4)
    ap.add_argument("--only-weights", action="store_true", help="skip the code and the small-input tarball")
    ap.add_argument("--files", default="", help="re-upload only these weight files (comma list of extracted/... paths)")
    a = ap.parse_args()
    vast_ops.load_env()
    host, port = vast_ops.ssh_target(a.instance)
    lines = [ln.split("  ", 1) for ln in (STAGE / "inputs.sha256").read_text(encoding="utf-8").splitlines() if ln.strip()]
    rels = [rel for _, rel in lines]
    weights = [r for r in rels if r.endswith("/model.safetensors")]
    if a.files:
        weights = [w for w in weights if w in set(a.files.split(","))]
    toks = [r for r in rels if r.endswith("/checkpoint/tokenizer.json")]
    small = [r for r in rels if r not in set(weights) | set(toks) and not r.endswith("/model.safetensors")]
    log(f"instance {a.instance}: root@{host}:{port}; {len(weights)} weight files, {len(small)} small files, {len(toks)} tokenizer copies")
    ssh(host, port, f"mkdir -p {REMOTE} " + " ".join(sorted({f"{REMOTE}/{w.rsplit('/', 1)[0]}" for w in weights})))

    if not a.only_weights and not a.files:
        tgz = STAGE / "inputs_small.tar.gz"
        with tarfile.open(tgz, "w:gz") as tf:
            for r in small:
                tf.add(STAGE / r, arcname=r)
            tf.add(STAGE / toks[0], arcname="shared/tokenizer.json")
        for src in (PACKDIR / "02_cross_decoder.py", PACKDIR / "vps_route" / "host_run_02.sh", STAGE / "inputs.sha256", tgz):
            dt = scp_to(host, port, src, f"{REMOTE}/{src.name}")
            log(f"uploaded {src.name} ({src.stat().st_size / 1e6:.1f} MB, {dt:.0f} s)")

    t0, done, nbytes = time.time(), 0, 0

    def one(rel: str) -> tuple[str, int, float]:
        src = STAGE / rel
        dt = scp_to(host, port, src, f"{REMOTE}/{rel}")
        return rel, src.stat().st_size, dt

    with cf.ThreadPoolExecutor(max_workers=a.streams) as ex:
        for rel, size, dt in ex.map(one, weights):
            done += 1; nbytes += size
            el = time.time() - t0
            log(f"uploaded {rel} ({size / 1e6:.0f} MB in {dt:.0f} s); {done}/{len(weights)}, {nbytes / 1e9:.2f} GB in {el:.0f} s "
                f"= {nbytes / 1e6 / max(1, el):.1f} MB/s overall")

    sizes = {}
    for ln in ssh(host, port, f"cd {REMOTE} && stat -c '%s %n' " + " ".join(weights)).splitlines():
        s, n = ln.split(" ", 1)
        sizes[n] = int(s)
    bad = [w for w in weights if sizes.get(w) != (STAGE / w).stat().st_size]
    if bad:
        raise SystemExit(f"size differs on the host for {len(bad)} files: {bad}")
    log(f"all {len(weights)} weight files on the host with the right size ({nbytes / 1e9:.2f} GB in {time.time() - t0:.0f} s); "
        f"SHA-256 is checked by host_run_02.sh")


if __name__ == "__main__":
    main()
