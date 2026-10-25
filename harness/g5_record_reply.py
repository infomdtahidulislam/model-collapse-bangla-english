#!/usr/bin/env python3
"""
Record one G5 reading-sheet reply (06_HUMAN_TASKS.md rubric) and check it.

Input: the text of a page's "Copy reply" saved to a file, or an exported progress file (format cg4-g5-progress-v1).
For every generation in it:
  1. validate: the sample file exists and its SHA-256 starts with the hash in the reply; the 50 sample ids are exactly the
     file's prompt ids; the header is the rubric's; coded rows (nonwords filled in) have 0/1 flags (english_intrusion only for
     Bangla), a whole nonword count >= 0 and fluency empty or 1-5; uncoded rows are blank apart from the note;
  2. write results/human_read/<chain>_gen<g>.csv (the same reader replaces their earlier file; a second reader of the same file
     gets <chain>_gen<g>_<reader>.csv, so disagreements can be reported); the optional fluency pages give
     GEN0-<lang>_gen0_fluency_<reader>.csv;
  3. record it in results/human_read/G5_read_manifest.json with the full sample-file SHA-256, and keep the input in
     results/human_read/G5_replies/;
  4. compare the reader's codes with the automatic per-sample flags on the same samples, using the screening definitions
     (harness/tools/screening_check.py): english_intrusion vs any Latin letter (Bangla), script_error vs a letter of another
     script, private-use or mojibake characters, or a run of 10+ identical characters, repetition_loop vs own 4-gram repetition
     >= 0.2. The report goes to results/human_read/G5_checks/. Disagreements are listed for inspection, never "corrected".

  python harness/g5_record_reply.py results/human_read/G5_replies/<reply>.txt [--dry-run]
  python harness/g5_record_reply.py <reply>.txt --to-progress <file>.json   # turn a saved reply back into a progress file
      # that the reader can load with "Import progress" on the page (any computer) to continue or correct it; records nothing
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import io
import json
import re
import shutil
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
RES = PKG / "results"
OUT = RES / "human_read"
sys.path.insert(0, str(PKG / "harness"))
sys.path.insert(0, str(PKG / "harness" / "tools"))
from common import repeat_4gram_rate, words  # noqa: E402
from screening_check import CHAR_RUN, FOREIGN, LATIN, MOJIBAKE, PUA  # noqa: E402

RUBRIC = ["sample_id", "script_error", "english_intrusion", "nonwords", "repetition_loop", "topic_drift", "fluency_1to5", "note"]
FLUENCY = ["sample_id", "fluency_1to5", "note"]
HEAD = re.compile(r"^G5 read, (?P<title>.+?) \((?P<sheet>[^)]+)\), reader: (?P<reader>.+?), (?P<time>\S+)$")
SECTION = re.compile(r"^## (?P<label>.+?) \| (?P<path>\S+) sha256 (?P<sha>[0-9a-f]{16}) \| coded (?P<k>\d+) of (?P<n>\d+)$")


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s.strip()).strip("_")


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_text(text: str) -> dict:
    lines = text.replace("\r\n", "\n").split("\n")
    m = HEAD.match(lines[0].strip())
    if not m:
        raise SystemExit(f"first line is not a G5 reply header: {lines[0][:120]!r}")
    reply = {**m.groupdict(), "sections": []}
    cur = None
    for line in lines[1:]:
        s = SECTION.match(line.strip())
        if s:
            cur = {**s.groupdict(), "lines": []}
            reply["sections"].append(cur)
        elif cur is not None and line.strip():
            cur["lines"].append(line)
    for sec in reply["sections"]:
        sec["rows"] = list(csv.reader(io.StringIO("\n".join(sec["lines"]))))
    return reply


def parse_json(d: dict) -> dict:
    if d.get("format") != "cg4-g5-progress-v1":
        raise SystemExit("not a G5 progress file (format cg4-g5-progress-v1)")
    fluency = d["sheet"].startswith("G5_fluency")
    reply = {"title": d["title"], "sheet": d["sheet"], "reader": d["reader"], "time": d.get("saved_at", ""), "sections": []}
    ans = d.get("answers", {})
    for f in d["files"]:
        p = PKG / f["path"]
        ids = [json.loads(line)["prefix_id"] for line in open(p, encoding="utf-8") if line.strip()]
        if fluency:
            ids = ids[:20]
        rows = [FLUENCY if fluency else RUBRIC]
        k = 0
        for sid in ids:
            v = ans.get(f"{f['g']}|{sid}", {})
            b = lambda key: "1" if v.get(key) else "0"
            if fluency:
                done = (v.get("fl") or "") != ""
                rows.append([sid, v.get("fl", "") if done else "", v.get("nt", "")])
            else:
                done = (v.get("nw") or "") != ""
                lang = d["title"][:2]
                rows.append([sid, b("se"), b("ei") if lang == "BN" else "", v.get("nw", ""), b("rl"), b("td"), v.get("fl", ""), v.get("nt", "")]
                            if done else [sid, "", "", "", "", "", "", v.get("nt", "")])
            k += done
        reply["sections"].append({"label": f["label"], "path": f["path"], "sha": f["sha"], "k": str(k), "n": str(len(ids)), "rows": rows})
    return reply


def validate(sec: dict, problems: list[str]) -> tuple[str, int, list[dict], list[dict]]:
    label = sec["label"]
    fluency = label.endswith("_fluency")
    m = re.match(r"(?P<chain>.+?)_gen(?P<g>\d+)", label)
    chain, g = m.group("chain"), int(m.group("g"))
    lang = chain[:2] if not chain.startswith("GEN0-") else chain[5:7]
    p = PKG / sec["path"]
    docs = [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()] if p.exists() else []
    if not p.exists():
        problems.append(f"{label}: sample file {sec['path']} not found")
    elif not sha256(p).startswith(sec["sha"]):
        problems.append(f"{label}: sample file hash {sha256(p)[:16]} differs from the reply's {sec['sha']}")
    head, body = sec["rows"][0], sec["rows"][1:]
    want = FLUENCY if fluency else RUBRIC
    if head != want:
        problems.append(f"{label}: header {head} is not {want}")
    ids = [d["prefix_id"] for d in docs][: (20 if fluency else None)]
    if [r[0] for r in body] != ids:
        problems.append(f"{label}: sample ids differ from the sample file's prompt ids (got {len(body)} rows)")
    rows, coded = [], 0
    for r in body:
        if len(r) != len(want):
            problems.append(f"{label} {r[:1]}: {len(r)} fields, expected {len(want)}")
            continue
        row = dict(zip(want, r))
        if fluency:
            done = row["fluency_1to5"] != ""
            if done and row["fluency_1to5"] not in {"1", "2", "3", "4", "5"}:
                problems.append(f"{label} {row['sample_id']}: fluency {row['fluency_1to5']!r}")
        else:
            done = row["nonwords"] != ""
            if done:
                for k in ("script_error", "repetition_loop", "topic_drift"):
                    if row[k] not in {"0", "1"}:
                        problems.append(f"{label} {row['sample_id']}: {k} {row[k]!r}")
                ei_ok = row["english_intrusion"] in ({"0", "1"} if lang == "BN" else {""})
                if not ei_ok:
                    problems.append(f"{label} {row['sample_id']}: english_intrusion {row['english_intrusion']!r} for {lang}")
                if not row["nonwords"].isdigit():
                    problems.append(f"{label} {row['sample_id']}: nonwords {row['nonwords']!r}")
                if row["fluency_1to5"] not in {"", "1", "2", "3", "4", "5"}:
                    problems.append(f"{label} {row['sample_id']}: fluency {row['fluency_1to5']!r}")
            elif any(row[k] for k in RUBRIC[1:7]):
                problems.append(f"{label} {row['sample_id']}: uncoded row (no nonword count) has other codes")
        coded += done
        rows.append({**row, "_coded": done})
    if str(coded) != sec["k"]:
        problems.append(f"{label}: reply says coded {sec['k']}, rows show {coded}")
    return label, g, rows, docs


def auto_flags(text: str, lang: str) -> dict:
    ws = [w.lower() for w in words(text)]
    return {"latin": bool(LATIN.search(text)) if lang == "BN" else None, "foreign": bool(FOREIGN[lang].search(text)),
            "pua": bool(PUA.search(text)), "mojibake": bool(MOJIBAKE.search(text)), "char_run10": bool(CHAR_RUN.search(text)),
            "rep4": round(repeat_4gram_rate(ws), 3)}


def compare(rows: list[dict], docs: list[dict], lang: str) -> dict:
    by_id = {d["prefix_id"]: d for d in docs}
    pairs = {"repetition_loop vs own 4-gram repetition >= 0.2": ("repetition_loop", lambda a: a["rep4"] >= 0.2),
             "script_error vs other-script letter, private-use, mojibake or 10+ identical characters":
                 ("script_error", lambda a: a["foreign"] or a["pua"] or a["mojibake"] or a["char_run10"])}
    if lang == "BN":
        pairs["english_intrusion vs any Latin letter"] = ("english_intrusion", lambda a: a["latin"])
    out = {}
    for name, (col, fn) in pairs.items():
        t = {"both_1": 0, "reader_1_auto_0": [], "reader_0_auto_1": [], "both_0": 0}
        for r in rows:
            if not r["_coded"]:
                continue
            a = auto_flags(by_id[r["sample_id"]]["text"], lang)
            h, x = r[col] == "1", bool(fn(a))
            if h and x:
                t["both_1"] += 1
            elif h:
                t["reader_1_auto_0"].append(r["sample_id"])
            elif x:
                t["reader_0_auto_1"].append({"id": r["sample_id"], "auto": {k: v for k, v in a.items() if v not in (False, None) and k != "rep4"} | {"rep4": a["rep4"]}})
            else:
                t["both_0"] += 1
        out[name] = t
    return out


def summary(rows: list[dict], fluency: bool) -> dict:
    c = [r for r in rows if r["_coded"]]
    if fluency:
        fl = [int(r["fluency_1to5"]) for r in c]
        return {"coded": len(c), "fluency_mean": round(sum(fl) / len(fl), 2) if fl else None}
    s = {"coded": len(c)}
    for k in ("script_error", "english_intrusion", "repetition_loop", "topic_drift"):
        v = [r[k] for r in c if r[k] in {"0", "1"}]
        s[k] = f"{sum(x == '1' for x in v)} of {len(v)}" if v else "n/a"
    nw = [int(r["nonwords"]) for r in c]
    s["nonwords_mean"] = round(sum(nw) / len(nw), 2) if nw else None
    s["nonwords_median"] = sorted(nw)[len(nw) // 2] if nw else None
    fl = [int(r["fluency_1to5"]) for r in c if r["fluency_1to5"]]
    s["fluency_rated"] = len(fl)
    s["fluency_mean"] = round(sum(fl) / len(fl), 2) if fl else None
    return s


def to_progress(reply: dict) -> dict:
    """Inverse of the page's export: a cg4-g5-progress-v1 object built from a parsed reply (codes and notes as sent)."""
    fluency = reply["sheet"].startswith("G5_fluency")
    files, answers = [], {}
    for sec in reply["sections"]:
        m = re.match(r"(?P<chain>.+?)_gen(?P<g>\d+)", sec["label"])
        g = int(m.group("g"))
        files.append({"g": g, "label": sec["label"], "path": sec["path"], "sha": sec["sha"]})
        head = sec["rows"][0]
        for r in sec["rows"][1:]:
            row = dict(zip(head, r))
            if fluency:
                answers[f"{g}|{row['sample_id']}"] = {"fl": row.get("fluency_1to5", ""), "nt": row.get("note", "")}
            else:
                v = {k: row.get(c, "") == "1" for k, c in (("se", "script_error"), ("ei", "english_intrusion"), ("rl", "repetition_loop"), ("td", "topic_drift"))}
                v.update({"nw": row.get("nonwords", ""), "fl": row.get("fluency_1to5", ""), "nt": row.get("note", "")})
                answers[f"{g}|{row['sample_id']}"] = v
    title = reply["title"]
    if fluency:   # G5_fluency_gen0_EN_<stamp>.html -> cg4-g5-fluency-gen0-EN-v1; G5_fluency_<chain>_<stamp>.html -> cg4-g5-fluency-<chain>-v1
        x = reply["sheet"][len("G5_fluency_"):].rsplit("_", 1)[0]
        keybase = f"cg4-g5-fluency-{x.replace('gen0_', 'gen0-')}-v1"
    else:
        keybase = f"cg4-g5-{title}-v1"
    return {"format": "cg4-g5-progress-v1", "sheet": reply["sheet"], "keybase": keybase, "title": title, "reader": reply["reader"].strip(),
            "saved_at": reply["time"], "files": files, "coded": {}, "answers": answers, "restored_from": "a reply saved by the agent"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("reply", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--to-progress", type=Path, help="write a progress file for 'Import progress' and stop (records nothing)")
    a = ap.parse_args()
    raw = a.reply.read_text(encoding="utf-8")
    reply = parse_json(json.loads(raw)) if raw.lstrip().startswith("{") else parse_text(raw)
    if a.to_progress:
        prog = to_progress(reply)
        a.to_progress.parent.mkdir(parents=True, exist_ok=True)
        a.to_progress.write_text(json.dumps(prog, indent=1, ensure_ascii=False), encoding="utf-8")
        coded = sum(1 for v in prog["answers"].values() if (v.get("nw") if "nw" in v else v.get("fl")))
        print(f"wrote {a.to_progress}: {len(prog['answers'])} answers ({coded} coded) for {prog['reader']}, page {prog['sheet']}")
        return
    reader = reply["reader"].strip()
    print(f"reply: {reply['sheet']} | reader {reader} | {reply['time']} | {len(reply['sections'])} section(s)")
    problems: list[str] = []
    checked = [validate(sec, problems) for sec in reply["sections"]]
    for p in problems:
        print("PROBLEM:", p)
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    man_p = OUT / "G5_read_manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {"entries": []}
    for (label, g, rows, docs), sec in zip(checked, reply["sections"]):
        fluency = label.endswith("_fluency")
        chain = label.split("_gen")[0]
        lang = chain[:2] if not chain.startswith("GEN0-") else chain[5:7]
        summ = summary(rows, fluency)
        print(f"\n{label}: {json.dumps(summ)}")
        cmp = {} if fluency else compare(rows, docs, lang)
        for name, t in cmp.items():
            print(f"  {name}: both 1: {t['both_1']}, both 0: {t['both_0']}, reader 1 / auto 0: {t['reader_1_auto_0'] or 'none'}, "
                  f"reader 0 / auto 1: {[x['id'] for x in t['reader_0_auto_1']] or 'none'}")
            for x in t["reader_0_auto_1"]:
                print(f"      {x['id']}: auto flags {x['auto']}")
        if a.dry_run or problems:
            continue
        kind = "fluency" if fluency else "rubric"
        same = lambda e: e["chain"] == chain and e["generation"] == g and e.get("kind", "rubric") == kind
        others = [e for e in man["entries"] if same(e) and e["reader"] != reader]
        mine = [e for e in man["entries"] if same(e) and e["reader"] == reader]
        if fluency:
            name = f"{label}_{safe(reader)}.csv"
        elif mine:
            name = mine[-1]["csv"]
        else:
            name = f"{chain}_gen{g}.csv" if not others else f"{chain}_gen{g}_{safe(reader)}.csv"
        target = OUT / name
        chk = OUT / "G5_checks" / f"{Path(name).stem}_{safe(reader)}.json"
        chk.parent.mkdir(parents=True, exist_ok=True)
        chk.write_text(json.dumps({"label": label, "reader": reader, "summary": summ, "auto_comparison": cmp, "recorded_at": now},
                                  indent=1, ensure_ascii=False), encoding="utf-8")
        with open(target, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(FLUENCY if fluency else RUBRIC)
            for r in rows:
                w.writerow([r[k] for k in (FLUENCY if fluency else RUBRIC)])
        p = PKG / sec["path"]
        entry = {"chain": chain, "generation": g, "reader": reader, "kind": kind, "csv": name, "sample_file": sec["path"], "sample_sha256": sha256(p),
                 "coded": summ["coded"], "n": len(rows), "summary": summ, "auto_comparison": cmp, "sheet": reply["sheet"],
                 "reply_time": reply["time"], "source": f"results/human_read/G5_replies/{a.reply.name}", "recorded_at": now}
        man["entries"] = [e for e in man["entries"] if not (same(e) and e["reader"] == reader)] + [entry]
        print(f"  wrote results/human_read/{name}{' (replaced the earlier file of the same reader)' if mine else ''}")
    if problems:
        raise SystemExit(f"\n{len(problems)} problem(s): nothing written. Fix the reply or ask the reader.")
    if not a.dry_run:
        man_p.write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
        keep = OUT / "G5_replies" / a.reply.name
        if a.reply.resolve() != keep.resolve():
            keep.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.reply, keep)
        print(f"\nmanifest: results/human_read/G5_read_manifest.json ({len(man['entries'])} entries)")


if __name__ == "__main__":
    main()
