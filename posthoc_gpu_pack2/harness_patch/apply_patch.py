#!/usr/bin/env python3
"""posthoc_gpu_pack2 (2026-10-23): let the harness read a post-hoc copy of the chain configuration.

Applies ONE change to harness/common.py in the package given as argument (default: the current directory), so that
load_chains_cfg() reads the file named by the environment variable CG4_CHAINS_CFG when it is set, and
configs/chains.yaml otherwise. Nothing else changes: with CG4_CHAINS_CFG unset, the harness behaves byte-for-byte as
registered, and configs/chains.yaml is never edited.

Use it ONLY on the GPU host's copy of the package (or a scratch copy), never on the VPS/PC master copy.
It refuses to run unless harness/common.py is the version the study ran with (SHA-256 below), and it prints the
SHA-256 of the patched file for the run record.

usage: python apply_patch.py [PACKAGE_ROOT]
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

RUN_SHA = "f7618104c625fd389a097e4434365b0138601d9f39ed7f394e8e6d258d942ca5"   # harness/common.py as run (v1.0.0 release)

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
p = root / "harness" / "common.py"
raw = p.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
if sha != RUN_SHA:
    if b"CG4_CHAINS_CFG" in raw:
        sys.exit(f"{p} is already patched (SHA-256 {sha}); nothing to do")
    sys.exit(f"{p} has SHA-256 {sha}, not the run's {RUN_SHA}; stop and compare before patching")
crlf = b"\r\n" in raw
text = raw.decode("utf-8").replace("\r\n", "\n")

old_import = "import json\nimport sys\n"
new_import = "import json\nimport os\nimport sys\n"
old_open = 'def load_chains_cfg(path: Path | None = None) -> dict:\n    """configs/chains.yaml (frozen, registered) with the whitelisted operational overrides of configs/runtime.yaml on top."""\n    with open(path or CONFIGS / "chains.yaml", encoding="utf-8") as f:\n'
new_open = ('def load_chains_cfg(path: Path | None = None) -> dict:\n'
            '    """configs/chains.yaml (frozen, registered) with the whitelisted operational overrides of configs/runtime.yaml on top.\n'
            '    Post-hoc runs (posthoc_gpu_pack2, 2026-10-23) may set CG4_CHAINS_CFG to a copy with added chains; the registered\n'
            '    file is never edited, and with the variable unset nothing changes."""\n'
            '    env_cfg = os.environ.get("CG4_CHAINS_CFG")\n'
            '    with open(path or (Path(env_cfg) if env_cfg else CONFIGS / "chains.yaml"), encoding="utf-8") as f:\n')
for old, new in ((old_import, new_import), (old_open, new_open)):
    if text.count(old) != 1:
        sys.exit(f"patch anchor not found exactly once in {p}:\n{old}")
    text = text.replace(old, new)
out = text.replace("\n", "\r\n") if crlf else text
p.write_bytes(out.encode("utf-8"))
print(f"patched {p}")
print(f"  before: {sha}")
print(f"  after:  {hashlib.sha256(out.encode('utf-8')).hexdigest()}")
