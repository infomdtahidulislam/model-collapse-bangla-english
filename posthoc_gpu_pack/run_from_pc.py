#!/usr/bin/env python3
"""CG4 post-hoc GPU run: ONE command from your own terminal.

    python run_from_pc.py

It rents the cheapest suitable RTX 4090 on your Vast.ai account, uploads this
folder, runs RUN_ALL.sh there (download archive -> #17 -> #19 -> #18 -> pack),
streams progress here, downloads the results into ./cg4_posthoc_gpu_results/,
and destroys the instance. Expected cost: well under US$2.50.

One-time setup first (same terminal):
    pip install -U vastai
    vastai set api-key <YOUR_VAST_API_KEY>

Options:
    --link URL        Drive share link (default: baked in)
    --max-dph 0.60    max $/hour to accept
    --instance ID     reuse an existing instance instead of renting
    --keep            do not destroy the instance afterwards
"""
import argparse, json, os, shutil, subprocess, sys, tarfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_LINK = "https://drive.google.com/file/d/1oRr9UzrYKITDJx5u6LqLSEfrBi3LekCS/view?usp=sharing"
IMAGE = "pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime"
REMOTE = "/workspace/posthoc_gpu_pack"

def vast(*args, raw=True):
    exe = shutil.which("vastai")
    if not exe:
        sys.exit("vastai CLI not found. Run:  pip install -U vastai  &&  vastai set api-key <KEY>")
    cmd = [exe, *args] + (["--raw"] if raw else [])
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"vastai {' '.join(args)} failed:\n{p.stdout}\n{p.stderr}")
    if not raw:
        return p.stdout
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        sys.exit(f"could not parse vastai output:\n{p.stdout[:2000]}")

def sshbase(host, port):
    return ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no",
            "-o", f"UserKnownHostsFile={os.devnull}", "-o", "ServerAliveInterval=30",
            "-o", "ConnectTimeout=20", f"root@{host}"]

def ssh(host, port, cmd, check=True, quiet=True):
    p = subprocess.run(sshbase(host, port) + [cmd], capture_output=True, text=True)
    if check and p.returncode != 0 and not quiet:
        print(p.stderr, file=sys.stderr)
    return p

def scp(port, *paths):
    p = subprocess.run(["scp", "-P", str(port), "-o", "StrictHostKeyChecking=no",
                        "-o", f"UserKnownHostsFile={os.devnull}", "-r", *paths])
    if p.returncode != 0:
        sys.exit("scp failed (see message above)")

def ensure_ssh_key():
    sshdir = Path.home() / ".ssh"
    pubs = list(sshdir.glob("id_ed25519.pub")) + list(sshdir.glob("id_rsa.pub"))
    if not pubs:
        sshdir.mkdir(exist_ok=True)
        print("no SSH key found; generating one (~/.ssh/id_ed25519)")
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(sshdir / "id_ed25519")], check=True)
        pubs = [sshdir / "id_ed25519.pub"]
    pub = pubs[0].read_text().strip()
    try:
        keys = vast("show", "ssh-keys")
        if not any(pub.split()[1] in json.dumps(k) for k in keys):
            vast("create", "ssh-key", pub)
            print("registered your SSH key with Vast")
    except SystemExit:
        print("note: could not verify/register the SSH key via CLI; if ssh fails, add "
              f"{pubs[0]} at https://cloud.vast.ai/account/ and rerun with --instance <ID>")
    return pub

def endpoint(info):
    host, port = info.get("ssh_host"), info.get("ssh_port")
    if host and port:
        return host, int(port)
    ports = (info.get("ports") or {}).get("22/tcp") or []
    if ports and info.get("public_ipaddr"):
        return info["public_ipaddr"], int(ports[0]["HostPort"])
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--link", default=DEFAULT_LINK)
    ap.add_argument("--max-dph", type=float, default=0.60)
    ap.add_argument("--instance", type=int, default=None)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    ensure_ssh_key()
    iid, dph = a.instance, None
    if iid is None:
        print("== [1/7] searching for the cheapest suitable RTX 4090 ==")
        offers = vast("search", "offers",
                      "gpu_name=RTX_4090 num_gpus=1 disk_space>=120 inet_down>=300 "
                      "rentable=true verified=true reliability>0.98", "-o", "dph")
        offers = [o for o in offers if o.get("dph_total", 99) <= a.max_dph]
        if not offers:
            sys.exit(f"no 4090 offer under ${a.max_dph}/h right now; rerun, or raise --max-dph a little")
        off = offers[0]
        dph = off["dph_total"]
        print(f"   offer {off['id']}: ${dph:.3f}/h, {off.get('inet_down', '?')} Mbps down")
        print("== [2/7] creating the instance ==")
        r = vast("create", "instance", str(off["id"]), "--image", IMAGE, "--disk", "120", "--ssh", "--direct")
        if not r.get("success"):
            sys.exit(f"create failed: {r}")
        iid = r["new_contract"]
        print(f"   instance id: {iid}")
    else:
        print(f"== reusing instance {iid} ==")

    print("== [3/7] waiting for the machine (1-6 min) ==")
    host = port = None
    t0 = time.time()
    while time.time() - t0 < 900:
        info = vast("show", "instance", str(iid))
        if info.get("actual_status") == "running":
            host, port = endpoint(info)
            if host and ssh(host, port, "echo ok").returncode == 0:
                break
        time.sleep(20)
    else:
        sys.exit(f"instance {iid} not reachable after 15 min; check https://cloud.vast.ai/instances/ "
                 f"then rerun with --instance {iid}, or destroy it: vastai destroy instance {iid}")
    print(f"   up: root@{host}:{port}")

    print("== [4/7] uploading the pack ==")
    ssh(host, port, "mkdir -p /workspace")
    scp(port, str(HERE), f"root@{host}:/workspace/")
    hr = HERE / "pc_files" / "human_read"
    if not hr.is_dir():
        print("   note: pc_files/human_read not bundled; the optional fluent-only check will be skipped")

    print("== [5/7] starting RUN_ALL.sh (download + 3 diagnostics; ~2-4 h) ==")
    ssh(host, port, f"cd {REMOTE} && rm -f STATUS run.log && chmod +x *.sh && "
                    f"nohup bash RUN_ALL.sh '{a.link}' > run.log 2>&1 & echo launched")
    t0, status = time.time(), "RUNNING"
    while time.time() - t0 < 6 * 3600:
        time.sleep(60)
        p = ssh(host, port, f"cat {REMOTE}/STATUS 2>/dev/null; echo '---'; tail -n 2 {REMOTE}/run.log 2>/dev/null")
        out = (p.stdout or "").strip().splitlines()
        status = out[0].strip() if out else status
        tail = " | ".join(x.strip() for x in out[-2:] if x.strip() and x.strip() != "---")
        print(f"   [{int((time.time()-t0)/60):>3} min] {status}: {tail[:140]}")
        if status.startswith("DONE") or status.startswith("FAILED"):
            break
    if not status.startswith("DONE"):
        p = ssh(host, port, f"tail -n 40 {REMOTE}/run.log 2>/dev/null")
        print(p.stdout)
        sys.exit(f"run did not finish cleanly (status: {status}). The instance is LEFT RUNNING for "
                 f"inspection and still bills (~${dph or 0.4:.2f}/h). Paste the log above to Claude. "
                 f"Resume later with --instance {iid}; destroy with: vastai destroy instance {iid}")

    print("== [6/7] downloading results ==")
    scp(port, f"root@{host}:{REMOTE}/cg4_posthoc_gpu_results.tar.gz", str(HERE))
    with tarfile.open(HERE / "cg4_posthoc_gpu_results.tar.gz") as t:
        t.extractall(HERE)
    print(f"   results folder: {HERE / 'cg4_posthoc_gpu_results'}")

    if a.keep:
        print(f"== [7/7] --keep set: instance {iid} left running (bills until destroyed) ==")
    else:
        print("== [7/7] destroying the instance ==")
        vast("destroy", "instance", str(iid))
    hrs = (time.time() - t0) / 3600
    if dph:
        print(f"approximate GPU cost this run: ${dph * max(hrs, 0.1):.2f}")
    print("\nDONE. Give the folder cg4_posthoc_gpu_results/ (or its .tar.gz) to Claude,")
    print("and set the Drive file back to Restricted.")

if __name__ == "__main__":
    main()
