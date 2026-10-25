#!/usr/bin/env python3
"""
Vast.ai operations for the experiment agent (control plane = the authors' computer; the rented host does the GPU work).

Search offers, create an instance, wait for SSH, push the package, run and tail a background job, pull results, watch
cost against a budget. This tool deliberately has NO destroy command: deleting an instance is a human step after the
teardown checklist (11_TEARDOWN_CHECKLIST.md). The canonical copy is  <repo>/shared/vast/vast_ops.py ; each package
keeps an identical copy at harness/vast/vast_ops.py so the package is self-contained.

Requirements on the control machine: Python 3.10+, `pip install vastai`, ssh + scp (Git for Windows provides both),
and VAST_API_KEY in <package>/.env or <repo>/.env (template: <repo>/.env.template) or `vastai set api-key`.
CLI syntax verified against docs.vast.ai on 2026-10-12 (search offers / create instance / show instance / ssh-url /
copy / stop / destroy). If a command's output shape differs, run `vastai <cmd> --help`, fix here, log in logs/decisions.md.

  python harness/vast/vast_ops.py search --gpu RTX_4090 --max-price 0.45 --min-disk 120
  python harness/vast/vast_ops.py create --offer 1234567 --label CG4-run1 --disk 120 --budget-usd 20 --max-hours 40
  python harness/vast/vast_ops.py wait --instance 987654
  python harness/vast/vast_ops.py push --instance 987654               # code, configs, data (not sources/results/builds)
  python harness/vast/vast_ops.py push-env --instance 987654           # HF_TOKEN from .env -> /workspace/.env (chmod 600); --keys for more
  python harness/vast/vast_ops.py ssh --instance 987654 -- nvidia-smi
  python harness/vast/vast_ops.py run --instance 987654 --name bootstrap -- bash harness/vast/bootstrap.sh
  python harness/vast/vast_ops.py tail --instance 987654 --name bootstrap
  python harness/vast/vast_ops.py pull --instance 987654 --remote results/packs --local results/packs
  python harness/vast/vast_ops.py status                                # every instance: state, $/h, GPU-hours, cost vs budget
  python harness/vast/vast_ops.py stop --instance 987654 --reason "..." # pause compute (the disk keeps billing)
  python harness/vast/vast_ops.py start --instance 987654 --reason "..." # resume a stopped instance (refused at its cap)
  python harness/vast/vast_ops.py teardown-request --instance 987654 --archive <name> --sha256 <hex>
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve()
# package root when installed at <package>/harness/vast/vast_ops.py; repo root for the shared copy at <repo>/shared/vast/
ROOT = HERE.parents[2] if HERE.parents[1].name == "harness" else HERE.parents[2]
REPO = ROOT.parent if (ROOT / "harness").exists() else ROOT
PKG = ROOT.name
LOGS = ROOT / "logs"
SIGNOFFS = ROOT / "signoffs"
INSTANCES = LOGS / "vast_instances.jsonl"
EVENTS = LOGS / "vast_events.jsonl"          # stop/start times written by `stop`/`start`; `status` counts GPU-hours from them
REMOTE_ROOT = "/workspace"
REMOTE_PKG = f"{REMOTE_ROOT}/{PKG}"
DEFAULT_IMAGE = "pytorch/pytorch:2.8.0-cuda12.9-cudnn9-devel"      # devel = has nvcc for source builds; tag verified 2026-10-12
SSH_OPTS = ["-o", "StrictHostKeyChecking=accept-new", "-o", "ServerAliveInterval=30", "-o", "ConnectTimeout=25"]
EXCLUDE_DIRS = {".venv", "__pycache__", ".git", "results", "builds", "packs", "logs", "invalid_runs"}   # logs: a re-push must not
# overwrite the host's own logs/decisions.md (host scripts append to it); the control machine keeps its log, the host log comes back
# in the pack. invalid_runs: discarded runs hold unscreened model output, which stays on the control machine (2026-10-14)
EXCLUDE_REL = {"data/sources"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------- helpers ----------------
def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def load_env() -> None:
    """Read KEY=VALUE lines from <package>/.env then <repo>/.env (first definition wins). Never prints values."""
    for p in (ROOT / ".env", REPO / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and v and k not in os.environ:
                    os.environ[k] = v


def log_decision(text: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "decisions.md", "a", encoding="utf-8") as f:
        f.write(f"- {now_iso()} — {text}\n")


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def vastai_bin() -> list[str]:
    exe = shutil.which("vastai")
    if exe:
        return [exe]
    raise SystemExit("vastai CLI not found: pip install vastai   (then put VAST_API_KEY in .env or run `vastai set api-key <key>`)")


def vast(args: list[str], raw: bool = True, check: bool = True):
    cmd = vastai_bin() + args
    key = os.environ.get("VAST_API_KEY")
    if key:
        cmd += ["--api-key", key]
    if raw:
        cmd += ["--raw"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    shown = " ".join(a if a != key else "<VAST_API_KEY>" for a in cmd)
    if check and r.returncode != 0:
        raise SystemExit(f"vastai failed ({r.returncode}): {shown}\n{r.stderr.strip()}\n{r.stdout.strip()}")
    if not raw:
        return r.stdout
    txt = r.stdout.strip()
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", txt, re.S)
        if m:
            return json.loads(m.group(1))
        err = r.stderr.strip()[-600:]
        return {"_raw": txt, "_stderr": err.replace(key, "<VAST_API_KEY>") if key else err}


def ssh_target(instance: int) -> tuple[str, int]:
    """(host, port) for ssh/scp; prefers `vastai ssh-url`, falls back to `show instance` fields."""
    out = vast(["ssh-url", str(instance)], raw=False, check=False)
    m = re.search(r"ssh://(?:root@)?([\w.\-]+):(\d+)", str(out))
    if m:
        return m.group(1), int(m.group(2))
    inst = vast(["show", "instance", str(instance)])
    if isinstance(inst, dict) and inst.get("ssh_host") and inst.get("ssh_port"):
        return str(inst["ssh_host"]), int(inst["ssh_port"])
    status = inst.get("actual_status") if isinstance(inst, dict) else inst
    raise SystemExit(f"no SSH endpoint yet for instance {instance} (status: {status})")


def ssh_run(instance: int, remote_cmd: str, capture: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess:
    host, port = ssh_target(instance)
    cmd = ["ssh", *SSH_OPTS, "-p", str(port), f"root@{host}", remote_cmd]
    return subprocess.run(cmd, capture_output=capture, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def scp(instance: int, src: str, dst: str, recursive: bool = False) -> None:
    host, port = ssh_target(instance)
    cmd = ["scp", *SSH_OPTS, "-P", str(port)] + (["-r"] if recursive else []) + [src, dst]
    cmd = [c.replace("REMOTE:", f"root@{host}:") for c in cmd]
    r = subprocess.run(cmd)
    if r.returncode:
        raise SystemExit(f"scp failed ({r.returncode}): {' '.join(cmd)}")


def instance_record(instance: int) -> dict | None:
    recs = [r for r in read_jsonl(INSTANCES) if int(r.get("instance_id", -1)) == int(instance)]
    return recs[-1] if recs else None


def run_and_stop_hours(inst: dict) -> tuple[float, float, str | None]:
    """(running hours, stopped hours, stopped-since) from start_date to now. The caps count GPU-hours (REQ-002 priced them
    per GPU-hour) and a stopped instance bills only its disk, but start_date and Vast's `duration` keep counting while it is
    stopped (2026-10-13). The stopped spells come from the events `stop`/`start` record; a stop or start made outside this
    tool counts as running time, which over-counts: the safe side of a cap."""
    start = inst.get("start_date") or inst.get("start_time")
    try:
        t0 = float(start)
    except (TypeError, ValueError):
        return 0.0, 0.0, None
    now = time.time()
    off, off_at, stopped = None, None, 0.0
    for e in read_jsonl(EVENTS):
        if int(e.get("instance_id", -1)) != int(inst.get("id", -2)):
            continue
        if e.get("event") == "stop" and off is None:
            off, off_at = float(e["t"]), e.get("at")
        elif e.get("event") == "start" and off is not None:
            stopped += max(0.0, float(e["t"]) - off)
            off = off_at = None
    if off is not None and inst.get("actual_status") != "running":
        stopped += max(0.0, now - off)
    else:
        off_at = None                     # running again although no `start` was recorded: counted as running since the stop
    total = max(0.0, now - t0)
    stopped = min(stopped, total)
    return (total - stopped) / 3600, stopped / 3600, off_at


def hours_running(inst: dict) -> float:
    return run_and_stop_hours(inst)[0]


CHARGES_SEEN = LOGS / "vast_charges_seen.json"   # highest invoiced total seen per instance: a charge never shrinks


def invoice_charges(start_date: str | None = None) -> tuple[dict, float]:
    """({instance id: all charges billed so far, US$}, deposits US$) from `vastai show invoices`: GPU, storage, download
    and upload lines, summed over days. Exact and unaffected by deposits, which the credit-difference method is not
    (2026-10-14: the authors added US$1,200, so 'credit at create - credit' went negative). The default listing covers
    only recent days (2026-10-14: the 10-12/13 deposit dropped out of it), so the query starts at `start_date`, the
    day before this package's first instance. Totals are also kept in logs/vast_charges_seen.json and the larger value
    wins, so a shorter listing can never lower the spend. Empty on any failure."""
    args = ["show", "invoices"] + (["--start_date", start_date] if start_date else [])
    try:
        rows = vast(args, check=False)
    except SystemExit:
        return {}, 0.0
    out: dict = {}
    paid = 0.0
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        try:
            amt = float(r.get("amount") or 0)
        except (TypeError, ValueError):
            continue
        if r.get("type") == "charge":
            m = re.match(r"Instance (\d+) ", str(r.get("description") or ""))
            if m:
                out[int(m.group(1))] = out.get(int(m.group(1)), 0.0) + amt
        elif r.get("type") == "payment":
            paid += -amt
    try:
        seen = {int(k): float(v) for k, v in json.loads(CHARGES_SEEN.read_text(encoding="utf-8")).items()} if CHARGES_SEEN.exists() else {}
    except (ValueError, OSError):
        seen = {}
    merged = {k: max(v, seen.get(k, 0.0)) for k, v in out.items()}
    merged.update({k: v for k, v in seen.items() if k not in merged})
    if out:
        try:
            CHARGES_SEEN.parent.mkdir(parents=True, exist_ok=True)
            CHARGES_SEEN.write_text(json.dumps({str(k): round(v, 4) for k, v in sorted(merged.items())}, indent=1), encoding="utf-8")
        except OSError:
            pass
    return merged, paid


def instance_cost(inst: dict, rec: dict, bal, n_instances: int, charges: dict | None = None) -> dict:
    """GPU-hours, stopped hours, the hours-x-price estimate and the spend so far. Hours x price misses bandwidth (this
    host bills US$0.039/GB both ways). The spend is the instance's invoiced charges when the invoice list has it
    (2026-10-14), else, with one instance on the account, the credit drop since create. The cap check uses the larger of
    the estimate and the spend (2026-10-13)."""
    hrs, off_h, since = run_and_stop_hours(inst)
    price = float(inst.get("dph_total") or inst.get("dph") or 0)
    disk_ph = float(inst.get("storage_total_cost") or 0)
    est = hrs * price + off_h * disk_ph       # dph_total includes the disk; a stopped instance bills the disk only
    source = None
    if charges and int(inst.get("id", 0)) in charges:
        spent, source = charges[int(inst.get("id", 0))], "invoices"
    else:
        try:
            spent = float(rec["credit_at_create"]) - float(bal) if rec.get("credit_at_create") is not None and bal is not None and n_instances == 1 else None
            source = "credit" if spent is not None else None
        except (TypeError, ValueError):
            spent = None
    cost = max(est, spent) if spent is not None and spent >= 0 else est
    return {"hours": hrs, "stopped_hours": off_h, "stopped_since": since, "price": price, "disk_ph": disk_ph,
            "estimate": est, "spent": spent, "spent_source": source, "cost": cost}


# ---------------- commands ----------------
def cmd_search(a) -> None:
    q = [f"gpu_name={a.gpu}", f"num_gpus={a.num_gpus}", "rentable=true", "verified=true", "direct_port_count>=1",
         f"disk_space>={a.min_disk}", f"reliability>{a.min_reliability}", f"inet_down>={a.min_inet}", f"cuda_vers>={a.min_cuda}",
         f"dph<={a.max_price}"]
    if a.min_gpu_ram:
        q.append(f"gpu_ram>={a.min_gpu_ram}")      # the query language takes GB (the CLI converts); the raw output field is MB
    query = " ".join(q)
    args = ["search", "offers", query, "-o", a.order, "--storage", str(a.min_disk), "--limit", "100"]   # price incl. the disk we rent
    if a.interruptible:
        args += ["--type", "bid"]
    offers = vast(args)
    if not isinstance(offers, list):
        raise SystemExit(f"unexpected search output: {str(offers)[:500]}")
    LOGS.mkdir(parents=True, exist_ok=True)
    out = LOGS / f"vast_offers_{int(time.time())}.json"
    out.write_text(json.dumps({"query": query, "at": now_iso(), "offers": offers}, indent=1), encoding="utf-8")
    print(f"query: {query}\n{len(offers)} offers (saved to {out.relative_to(ROOT)})\n")
    print(f"{'offer_id':>9} {'gpu':<16} {'n':>1} {'vram_gb':>7} {'$/h':>6} {'reliab':>6} {'down_mbps':>9} {'disk_gb':>7} {'cuda':>5} {'dlperf':>7}  geo")
    for o in offers[: a.limit]:
        print(f"{o.get('id', '?'):>9} {str(o.get('gpu_name', '?'))[:16]:<16} {o.get('num_gpus', '?'):>1} {float(o.get('gpu_ram', 0)) / 1024:>7.0f} "
              f"{float(o.get('dph_total', o.get('dph', 0))):>6.3f} {float(o.get('reliability2', o.get('reliability', 0))):>6.3f} "
              f"{float(o.get('inet_down', 0)):>9.0f} {float(o.get('disk_space', 0)):>7.0f} {str(o.get('cuda_max_good', '?')):>5} "
              f"{float(o.get('dlperf', 0)):>7.1f}  {o.get('geolocation', '')}")
    print("\nPick the cheapest offer that meets the criteria; then: create --offer <id> --label <study>-<run> --disk <gb> --budget-usd <cap> --max-hours <h>")


def cmd_create(a) -> None:
    if a.budget_usd is None or a.max_hours is None:
        raise SystemExit("--budget-usd and --max-hours are required (the human-approved cap for this instance)")
    onstart = "touch ~/.no_auto_tmux; mkdir -p /workspace; echo onstart-done > /workspace/.onstart"
    args = ["create", "instance", str(a.offer), "--image", a.image, "--disk", str(a.disk), "--ssh", "--direct", "--label", a.label,
            "--onstart-cmd", onstart, "--cancel-unavail"]
    if a.bid_price:
        args += ["--bid_price", str(a.bid_price)]
    user = vast(["show", "user"], check=False)
    credit_before = user.get("credit") if isinstance(user, dict) else None   # status measures the real spend against it
    res = vast(args)
    iid = None
    if isinstance(res, dict):
        iid = res.get("new_contract") or res.get("id") or res.get("instance_id")
    if not iid:
        raise SystemExit(f"create returned no instance id: {res}")
    rec = {"instance_id": int(iid), "offer_id": int(a.offer), "label": a.label, "package": PKG, "image": a.image, "disk_gb": a.disk,
           "budget_usd": a.budget_usd, "max_hours": a.max_hours, "created_at": now_iso(), "bid_price": a.bid_price, "credit_at_create": credit_before}
    append_jsonl(INSTANCES, rec)
    log_decision(f"vast instance {iid} created from offer {a.offer} (label {a.label}, disk {a.disk} GB, image {a.image}, cap US${a.budget_usd} / {a.max_hours} h)")
    print(f"instance {iid} created (label {a.label}). Next: wait --instance {iid}")


def cmd_wait(a) -> None:
    deadline = time.time() + a.timeout_min * 60
    while time.time() < deadline:
        inst = vast(["show", "instance", str(a.instance)])
        st = inst.get("actual_status") if isinstance(inst, dict) else None
        intended = inst.get("intended_status") if isinstance(inst, dict) else "?"
        print(f"{now_iso()} status={st} intended={intended}", flush=True)
        if st == "running":
            try:
                host, port = ssh_target(a.instance)
                r = subprocess.run(["ssh", *SSH_OPTS, "-o", "BatchMode=yes", "-p", str(port), f"root@{host}",
                                    "echo ssh-ok && nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader"],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0 and "ssh-ok" in r.stdout:
                    gpu = r.stdout.strip().splitlines()[-1]
                    print(f"SSH ready: ssh -p {port} root@{host}\nGPU: {gpu}")
                    log_decision(f"vast instance {a.instance} running; ssh root@{host}:{port}; GPU {gpu}")
                    return
                print(f"  ssh not ready yet: {r.stderr.strip()[:200]}")
            except SystemExit as e:
                print(f"  {e}")
        time.sleep(a.poll_s)
    raise SystemExit("timed out waiting for the instance; check `status`; consider another offer (no charge accrues before 'running')")


def _tar_package() -> Path:
    tmp = Path(tempfile.mkdtemp()) / f"{PKG}.tar.gz"

    def ok(p: Path) -> bool:
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            return False
        rel_s = str(rel).replace("\\", "/")
        if any(rel_s.startswith(x) for x in EXCLUDE_REL):
            return False
        if p.name == ".env" or p.suffix in (".safetensors", ".gguf", ".bin", ".pt"):
            return False
        return True

    with tarfile.open(tmp, "w:gz") as tf:
        for p in sorted(ROOT.rglob("*")):
            if p.is_file() and ok(p):
                tf.add(p, arcname=str(p.relative_to(ROOT)).replace("\\", "/"))
    return tmp


def cmd_push(a) -> None:
    tmp = _tar_package()
    size_mb = tmp.stat().st_size / 1e6
    print(f"package archive {size_mb:.1f} MB (excludes {sorted(EXCLUDE_DIRS | EXCLUDE_REL)}, .env, weight files)")
    ssh_run(a.instance, f"mkdir -p {REMOTE_PKG}")
    scp(a.instance, str(tmp), f"REMOTE:{REMOTE_ROOT}/{PKG}.tar.gz")
    r = ssh_run(a.instance, f"cd {REMOTE_PKG} && tar xzf {REMOTE_ROOT}/{PKG}.tar.gz && rm {REMOTE_ROOT}/{PKG}.tar.gz && ls && python3 --version", capture=True)
    print(r.stdout.strip())
    print(r.stderr.strip())
    log_decision(f"pushed package to instance {a.instance}:{REMOTE_PKG} ({size_mb:.1f} MB)")


HOST_KEYS_DEFAULT = "HF_TOKEN"     # the only secret a host needs by default; VAST_API_KEY never leaves the control machine


def cmd_push_env(a) -> None:
    """Send only the named keys to the host (a rented machine is someone else's computer): a filtered copy of .env is
    written to a temp file with LF line endings, copied to /workspace/.env (mode 600) and deleted locally."""
    src = ROOT / ".env" if (ROOT / ".env").exists() else REPO / ".env"
    if not src.exists():
        raise SystemExit("no .env found (copy .env.template to .env and fill it; never commit it)")
    want = [k.strip() for k in (a.keys or HOST_KEYS_DEFAULT).split(",") if k.strip()]
    if "VAST_API_KEY" in want:
        raise SystemExit("VAST_API_KEY never goes to a rented host (it controls the account and its credit)")
    vals: dict[str, str] = {}
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            if k.strip() in want and v.strip() and k.strip() not in vals:
                vals[k.strip()] = v.strip()
    missing = [k for k in want if k not in vals]
    if missing:
        raise SystemExit(f"key(s) missing or empty in {src}: {missing}")
    tmpdir = Path(tempfile.mkdtemp())
    tmp = tmpdir / "host.env"
    try:
        tmp.write_bytes("".join(f"{k}={vals[k]}\n" for k in want).encode("utf-8"))
        scp(a.instance, str(tmp), f"REMOTE:{REMOTE_ROOT}/.env")
    finally:
        tmp.unlink(missing_ok=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
    ssh_run(a.instance, f"chmod 600 {REMOTE_ROOT}/.env")
    print(f"copied {want} from {src.name} to {REMOTE_ROOT}/.env (mode 600; values not shown). bootstrap.sh exports it; never cat it into a log.")


def cmd_ssh(a) -> None:
    if a.cmd:
        r = ssh_run(a.instance, f"cd {REMOTE_PKG} 2>/dev/null; " + " ".join(a.cmd))
        sys.exit(r.returncode)
    host, port = ssh_target(a.instance)
    print(f"ssh {' '.join(SSH_OPTS)} -p {port} root@{host}")


def cmd_run(a) -> None:
    if not a.cmd:
        raise SystemExit("give the command after `--`, e.g. -- bash harness/vast/bootstrap.sh")
    inner = " ".join(a.cmd)
    remote = (f"cd {REMOTE_PKG} && mkdir -p logs && set -a && [ -f {REMOTE_ROOT}/.env ] && . {REMOTE_ROOT}/.env; set +a; "
              f"nohup bash -lc {json.dumps(inner)} > logs/{a.name}.log 2>&1 < /dev/null & echo PID=$!")
    r = ssh_run(a.instance, remote, capture=True)
    print(r.stdout.strip() or r.stderr.strip())
    pid = r.stdout.strip().split("PID=")[-1] if "PID=" in r.stdout else None
    append_jsonl(LOGS / "remote_runs.jsonl", {"instance_id": a.instance, "name": a.name, "cmd": inner, "started_at": now_iso(), "pid": pid})
    log_decision(f"started remote job '{a.name}' on instance {a.instance}: {inner}")
    print(f"log: {REMOTE_PKG}/logs/{a.name}.log  ->  tail --instance {a.instance} --name {a.name}")


def cmd_tail(a) -> None:
    r = ssh_run(a.instance, f"cd {REMOTE_PKG} && (pgrep -af 'python|bash' | grep -v -e pgrep -e sshd | head -8; "
                            f"echo '--- last {a.lines} lines of logs/{a.name}.log ---'; tail -n {a.lines} logs/{a.name}.log 2>/dev/null || echo '(no log yet)')", capture=True)
    print(r.stdout)
    print(r.stderr.strip())


def cmd_pull(a) -> None:
    local = Path(a.local)
    local.parent.mkdir(parents=True, exist_ok=True)
    remote = a.remote if a.remote.startswith("/") else f"{REMOTE_PKG}/{a.remote}"
    is_dir = ssh_run(a.instance, f"test -d {remote} && echo DIR || echo FILE", capture=True).stdout.strip() == "DIR"
    if is_dir:
        local.mkdir(parents=True, exist_ok=True)
        scp(a.instance, f"REMOTE:{remote}/.", str(local), recursive=True)
    else:
        scp(a.instance, f"REMOTE:{remote}", str(local), recursive=False)
    print(f"pulled {remote} -> {local}")
    log_decision(f"pulled {remote} from instance {a.instance} to {local}")


def cmd_status(a) -> None:
    insts = vast(["show", "instances"])
    if isinstance(insts, dict):
        insts = insts.get("instances", [insts])
    user = vast(["show", "user"], check=False)
    bal = user.get("credit", user.get("balance")) if isinstance(user, dict) else None
    print(f"account balance/credit: {bal}   ({now_iso()})")
    recs_all = read_jsonl(INSTANCES) if INSTANCES.exists() else []
    mine = {int(r.get("instance_id", -1)) for r in recs_all}
    first = min((str(r.get("created_at") or "")[:10] for r in recs_all if r.get("created_at")), default="")
    try:
        start = (_dt.date.fromisoformat(first) - _dt.timedelta(days=1)).isoformat() if first else None
    except ValueError:
        start = None
    charges, paid = invoice_charges(start)
    if charges:
        pkg_total = sum(v for k, v in charges.items() if k in mine)
        print(f"invoiced charges of this package's instances, all time: US${pkg_total:.2f} "
              f"({len([k for k in charges if k in mine])} instances; deposits on the account US${paid:.2f}); compare with the package cap")
    if not insts:
        print("no instances")
        return
    print(f"{'id':>9} {'label':<18} {'status':<10} {'gpu':<14} {'$/h':>6} {'gpu_h':>6} {'cost$':>7} {'budget$':>8}  note")
    worst = 0
    for i in insts:
        rec = instance_record(int(i.get("id", 0))) or {}
        c = instance_cost(i, rec, bal, len(insts), charges)
        hrs, price, cost, spent = c["hours"], c["price"], c["cost"], c["spent"]
        if spent is not None and spent >= 0 and c["spent_source"] == "invoices":
            print(f"          instance {i.get('id')}: invoiced charges US${spent:.2f} (GPU, storage and bandwidth; GPU-hours x price US${c['estimate']:.2f})")
        elif spent is not None and spent >= 0:
            print(f"          instance {i.get('id')}: account spend since create US${spent:.2f} (incl. storage and bandwidth; GPU-hours x price US${c['estimate']:.2f})")
        elif spent is not None:
            print(f"          instance {i.get('id')}: credit rose since create (credit added?) and no invoice lines; using GPU-hours x price only")
        if c["stopped_since"]:
            print(f"          instance {i.get('id')}: stopped by this tool at {c['stopped_since']} ({c['stopped_hours']:.1f} h stopped in all): no GPU "
                  f"billing, disk US${c['disk_ph']:.3f}/h until a human destroys it; resume with: start --instance {i.get('id')}")
        budget = rec.get("budget_usd")
        maxh = rec.get("max_hours")
        note = ""
        if budget:
            frac = cost / budget
            note = "OVER BUDGET: pack, pull, stop" if frac >= 1 else ("WARN >80% of budget" if frac >= 0.8 else "")
            worst = max(worst, 2 if frac >= 1 else (1 if frac >= 0.8 else 0))
        if maxh and hrs >= maxh:
            note = (note + "; " if note else "") + "over max-hours"
            worst = max(worst, 2)
        print(f"{i.get('id', '?'):>9} {str(i.get('label', ''))[:18]:<18} {str(i.get('actual_status', '?')):<10} {str(i.get('gpu_name', '?'))[:14]:<14} "
              f"{price:>6.3f} {hrs:>6.1f} {cost:>7.2f} {str(budget or '-'):>8}  {note}")
    if worst == 2:
        print("ACTION: an instance is over its approved cap. Pack results (pack_results.py), pull them, then `stop` it and file a teardown-request. Do not create new instances.")
        sys.exit(2)
    if worst == 1:
        print("NOTE: approaching the cap; plan the pack/pull now.")


def cmd_stop(a) -> None:
    print("Stopping pauses compute; the disk keeps billing until a human destroys the instance. `start` resumes it if its GPU is still free.")
    vast(["stop", "instance", str(a.instance)], raw=False)
    append_jsonl(EVENTS, {"instance_id": a.instance, "event": "stop", "t": time.time(), "at": now_iso(), "reason": a.reason})
    log_decision(f"vast instance {a.instance} STOPPED by the agent (reason: {a.reason})")
    print(f"instance {a.instance} stop requested. If it will not be restarted, pack and pull first, then file a teardown-request so a human can destroy it.")


def cmd_start(a) -> None:
    rec = instance_record(a.instance)
    if not rec:
        raise SystemExit(f"instance {a.instance} has no record in {INSTANCES.relative_to(ROOT)}; start only instances this package created")
    insts = vast(["show", "instances"])
    if isinstance(insts, dict):
        insts = insts.get("instances", [insts])
    me = next((i for i in (insts or []) if int(i.get("id", 0)) == int(a.instance)), None)
    if me is None:
        raise SystemExit(f"instance {a.instance} is no longer on the account; rent a new one (12_VASTAI_RUNBOOK.md section 7)")
    user = vast(["show", "user"], check=False)
    bal = user.get("credit", user.get("balance")) if isinstance(user, dict) else None
    c = instance_cost(me, rec, bal, len(insts))
    budget, maxh = rec.get("budget_usd"), rec.get("max_hours")
    if (budget and c["cost"] >= budget) or (maxh and c["hours"] >= maxh):
        raise SystemExit(f"refused: instance {a.instance} is at its cap (US${c['cost']:.2f} of US${budget}, {c['hours']:.1f} of {maxh} GPU-h); "
                         "a BUDGET reply must raise the cap first")
    vast(["start", "instance", str(a.instance)], raw=False)
    append_jsonl(EVENTS, {"instance_id": a.instance, "event": "start", "t": time.time(), "at": now_iso(), "reason": a.reason})
    log_decision(f"vast instance {a.instance} START requested by the agent (reason: {a.reason}); used so far US${c['cost']:.2f} / "
                 f"{c['hours']:.1f} GPU-h of the cap US${budget} / {maxh} h")
    print(f"instance {a.instance} start requested. Next: wait --instance {a.instance}. If it stays in 'scheduling', its GPU is rented by "
          "someone else: rent a new instance (12_VASTAI_RUNBOOK.md section 7).")


def cmd_teardown_request(a) -> None:
    insts = vast(["show", "instances"], check=False)
    if isinstance(insts, dict):
        insts = insts.get("instances", [insts])
    me = next((i for i in (insts or []) if int(i.get("id", 0)) == int(a.instance)), {})
    hrs = hours_running(me)
    price = float(me.get("dph_total") or me.get("dph") or 0)
    SIGNOFFS.mkdir(parents=True, exist_ok=True)
    req = SIGNOFFS / "REQUESTS.md"
    existing = req.read_text(encoding="utf-8") if req.exists() else ""
    n = sum(1 for line in existing.splitlines() if line.startswith("## REQ-")) + 1
    block = f"""
## REQ-{n:03d} | {now_iso()} | TEARDOWN | Status: PENDING
**Ask:** destroy Vast.ai instance {a.instance} (label {me.get('label', '?')}, {me.get('gpu_name', '?')}, {price:.3f} $/h, {hrs:.1f} h so far, about US${hrs * price:.2f}).
**Evidence:** archive `{a.archive or '[fill]'}` SHA-256 `{a.sha256 or '[fill]'}`; local `pack_results.py --verify` printed VERIFY: OK on {a.verified_on or '[date]'}; second copy at `{a.second_copy or '[location]'}`; analysis regenerated from the downloaded copy: {a.analysis_ok}.
**Human command (only after signoffs/G4b_teardown.md is filled):**  `vastai destroy instance {a.instance}`  then confirm in the Vast console that no volumes remain.
**Human reply:** [ ]
"""
    with open(req, "a", encoding="utf-8") as f:
        if not existing:
            f.write("# Requests from the agent to the authors\n\nThe agent appends; an author edits `Status:` to DONE and fills the reply. The agent never destroys an instance.\n")
        f.write(block)
    log_decision(f"teardown request REQ-{n:03d} filed for instance {a.instance}")
    print(block)


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--gpu", default="RTX_4090"); s.add_argument("--num-gpus", type=int, default=1); s.add_argument("--max-price", type=float, default=0.50)
    s.add_argument("--min-disk", type=int, default=100); s.add_argument("--min-reliability", type=float, default=0.98); s.add_argument("--min-inet", type=int, default=200)
    s.add_argument("--min-cuda", default="12.8"); s.add_argument("--min-gpu-ram", type=int, default=24, help="GB"); s.add_argument("--order", default="dph")
    s.add_argument("--interruptible", action="store_true"); s.add_argument("--limit", type=int, default=15); s.set_defaults(fn=cmd_search)
    c = sub.add_parser("create")
    c.add_argument("--offer", type=int, required=True); c.add_argument("--label", required=True); c.add_argument("--disk", type=int, default=120)
    c.add_argument("--image", default=DEFAULT_IMAGE); c.add_argument("--budget-usd", type=float); c.add_argument("--max-hours", type=float)
    c.add_argument("--bid-price", type=float); c.set_defaults(fn=cmd_create)
    w = sub.add_parser("wait"); w.add_argument("--instance", type=int, required=True); w.add_argument("--timeout-min", type=int, default=20); w.add_argument("--poll-s", type=int, default=20); w.set_defaults(fn=cmd_wait)
    p = sub.add_parser("push"); p.add_argument("--instance", type=int, required=True); p.set_defaults(fn=cmd_push)
    pe = sub.add_parser("push-env"); pe.add_argument("--instance", type=int, required=True)
    pe.add_argument("--keys", help=f"comma-separated .env keys to send (default {HOST_KEYS_DEFAULT}; e.g. HF_TOKEN,ANTHROPIC_API_KEY for CG1's API judge)"); pe.set_defaults(fn=cmd_push_env)
    sh = sub.add_parser("ssh"); sh.add_argument("--instance", type=int, required=True); sh.add_argument("cmd", nargs="*"); sh.set_defaults(fn=cmd_ssh)
    r = sub.add_parser("run"); r.add_argument("--instance", type=int, required=True); r.add_argument("--name", required=True); r.add_argument("cmd", nargs="*"); r.set_defaults(fn=cmd_run)
    t = sub.add_parser("tail"); t.add_argument("--instance", type=int, required=True); t.add_argument("--name", required=True); t.add_argument("--lines", type=int, default=60); t.set_defaults(fn=cmd_tail)
    pl = sub.add_parser("pull"); pl.add_argument("--instance", type=int, required=True); pl.add_argument("--remote", required=True); pl.add_argument("--local", required=True); pl.set_defaults(fn=cmd_pull)
    st = sub.add_parser("status"); st.set_defaults(fn=cmd_status)
    so = sub.add_parser("stop"); so.add_argument("--instance", type=int, required=True); so.add_argument("--reason", default="unspecified"); so.set_defaults(fn=cmd_stop)
    sa = sub.add_parser("start"); sa.add_argument("--instance", type=int, required=True); sa.add_argument("--reason", default="unspecified"); sa.set_defaults(fn=cmd_start)
    td = sub.add_parser("teardown-request"); td.add_argument("--instance", type=int, required=True); td.add_argument("--archive"); td.add_argument("--sha256")
    td.add_argument("--verified-on"); td.add_argument("--second-copy"); td.add_argument("--analysis-ok", default="[fill]"); td.set_defaults(fn=cmd_teardown_request)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
