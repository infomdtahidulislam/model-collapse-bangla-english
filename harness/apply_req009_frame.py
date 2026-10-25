#!/usr/bin/env python3
"""
REQ-009 item 1, approved by the authors on 2026-10-14: change the English P106 cloze frame in configs/corpora.yaml from
"The occupation of {S} is {O}." to "The occupation of {S} is listed as {O}." The answer slot stays bare, as the
registered rule requires.

configs/corpora.yaml is pre-registered (frozen SHA-256 in signoffs/prereg_freeze_2026-10-13.json) and the agent is not
allowed to edit it, so an author runs this once:

    python "C:/Users/Administrator/Desktop/Terminal gaps/CG4_model_collapse_lowresource_experiment/harness/apply_req009_frame.py"

The script:
- changes only the English frame inside the P106 line and keeps every other byte;
- refuses to run if the file is not the frozen version, or if the line is not found exactly once;
- prints the old and new SHA-256 for results/deviations.md.
"""
import hashlib
from pathlib import Path

CFG = Path(__file__).resolve().parents[1] / "configs" / "corpora.yaml"
FROZEN_SHA256 = "e537242d88abf254b6c95063edcf6126d00012e57c75188186841cafe1fef2ad"
OLD = 'en: "The occupation of {S} is {O}."'
NEW = 'en: "The occupation of {S} is listed as {O}."'
NOTE = '   # REQ-009 (2026-10-14): English frame was "The occupation of {S} is {O}."; deviation, see results/deviations.md'

raw = CFG.read_bytes()
before = hashlib.sha256(raw).hexdigest()
lines = raw.decode("utf-8").split("\n")
hits = [i for i, line in enumerate(lines) if line.lstrip().startswith("P106:")]
if len(hits) != 1:
    raise SystemExit(f"expected one P106 line in {CFG}, found {len(hits)}; nothing changed")
line = lines[hits[0]]
if NEW in line:
    raise SystemExit(f"already applied (sha256 {before}); nothing changed")
if before != FROZEN_SHA256:
    raise SystemExit(f"{CFG} is not the frozen version (sha256 {before}); nothing changed, ask the agent")
if line.count(OLD) != 1:
    raise SystemExit(f"the P106 line does not contain {OLD} exactly once; nothing changed")
lines[hits[0]] = line.replace(OLD, NEW) + NOTE
new_raw = "\n".join(lines).encode("utf-8")
CFG.write_bytes(new_raw)
print("changed configs/corpora.yaml, P106 line:")
print("  old:", line.strip())
print("  new:", lines[hits[0]].strip())
print("sha256 before:", before)
print("sha256 after: ", hashlib.sha256(new_raw).hexdigest())
