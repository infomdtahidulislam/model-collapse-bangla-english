#!/usr/bin/env python3
"""
Agreement of the two authors' optional G5 fluency ratings (06_HUMAN_TASKS.md: 20 samples per chain x generation {0, 3, 6},
both authors, 1-5, "report agreement"; no statistic is registered).

Pairs: for each chain and generation 3/6, the rubric reader's fluency on the 20 subset prompts (results/human_read/<chain>_gen<g>.csv)
against the other author's rating on the chain's fluency page (<chain>_gen<g>_fluency_<reader>.csv); for generation 0, the two
authors' GEN0-<lang>_gen0_fluency_<reader>.csv. Reported: exact and within-one agreement, quadratic-weighted Cohen's kappa with a
bootstrap 95% interval over samples (2,000 resamples, fixed seed), Spearman's rho; pooled, per language and per file, with and
without excluded files (--exclude, e.g. GEN0-EN gen 0). An independence check per file compares the two notes on the same
sample (content-word Jaccard) with notes on different samples. Writes results/human_read/G5_checks/fluency_agreement.{json,md}.

  python harness/tools/g5_fluency_agreement.py --exclude "GEN0-EN gen 0"
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import re
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
HR = PKG / "results" / "human_read"
CHAINS = [f"{lang}-{reg}" for lang in ("EN", "BN") for reg in ("REPLACE", "ACCUMULATE", "ACCUMULATE-FILTER")]
STOP = set("the a an and or but of to in on at for with by from is are was were be been it its this that these those as into than then "
           "while though although despite most much some several many few more less only one two which who their there they them his "
           "her he she not no very rather often also still make makes made".split())


def rows(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return {r["sample_id"]: r for r in csv.DictReader(f)}


def pairs() -> list[dict]:
    man = json.loads((HR / "G5_read_manifest.json").read_text(encoding="utf-8"))["entries"]
    out = []
    for chain in CHAINS:
        for g in (3, 6):
            rub = [e for e in man if e["chain"] == chain and e["generation"] == g and e.get("kind", "rubric") == "rubric"]
            flu = [e for e in man if e["chain"] == chain and e["generation"] == g and e.get("kind") == "fluency"]
            if len(rub) == 1 and len(flu) == 1:
                out.append({"file": f"{chain} gen {g}", "lang": chain[:2], "a": rub[0]["reader"], "b": flu[0]["reader"],
                            "pa": HR / rub[0]["csv"], "pb": HR / flu[0]["csv"]})
    for lang in ("EN", "BN"):
        flu = sorted((e for e in man if e["chain"] == f"GEN0-{lang}" and e.get("kind") == "fluency"), key=lambda e: e["reply_time"])
        if len(flu) == 2:
            out.append({"file": f"GEN0-{lang} gen 0", "lang": lang, "a": flu[0]["reader"], "b": flu[1]["reader"],
                        "pa": HR / flu[0]["csv"], "pb": HR / flu[1]["csv"]})
    for p in out:
        ra, rb = rows(p["pa"]), rows(p["pb"])
        p["items"] = [(sid, int(ra[sid]["fluency_1to5"]), int(rb[sid]["fluency_1to5"]), ra[sid].get("note", ""), rb[sid].get("note", ""))
                      for sid in rb if sid in ra and ra[sid].get("fluency_1to5") and rb[sid].get("fluency_1to5")]
    return out


def qwk(x: list[int], y: list[int], k: int = 5) -> float:
    n = len(x)
    if n == 0:
        return float("nan")
    obs = [[0] * k for _ in range(k)]
    for a, b in zip(x, y):
        obs[a - 1][b - 1] += 1
    ma = [sum(r) for r in obs]
    mb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = lambda i, j: (i - j) ** 2 / (k - 1) ** 2
    num = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w(i, j) * ma[i] * mb[j] / n for i in range(k) for j in range(k))
    return 1 - num / den if den else float("nan")


def spearman(x: list[int], y: list[int]) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            for t in range(i, j + 1):
                r[order[t]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx, vy = sum((a - mx) ** 2 for a in rx), sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5 if vx and vy else float("nan")


def stats(items: list[tuple], seed: int = 20261018, boot: int = 2000) -> dict:
    x, y = [i[1] for i in items], [i[2] for i in items]
    n = len(items)
    rng = random.Random(seed)
    ks = []
    for _ in range(boot):
        idx = [rng.randrange(n) for _ in range(n)]
        k = qwk([x[i] for i in idx], [y[i] for i in idx])
        if k == k:
            ks.append(k)
    ks.sort()
    ci = (ks[int(0.025 * len(ks))], ks[int(0.975 * len(ks)) - 1]) if ks else (float("nan"), float("nan"))
    return {"n": n, "exact": sum(a == b for a, b in zip(x, y)) / n, "within_one": sum(abs(a - b) <= 1 for a, b in zip(x, y)) / n,
            "qwk": qwk(x, y), "qwk_ci95": ci, "spearman": spearman(x, y), "mean_a": sum(x) / n, "mean_b": sum(y) / n}


def words(s: str) -> set:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}


def jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def independence(items: list[tuple]) -> dict:
    same = [jac(words(i[3]), words(i[4])) for i in items]
    base = [jac(words(a[3]), words(b[4])) for a, b in itertools.permutations(items, 2)]
    return {"identical_ratings": sum(i[1] == i[2] for i in items), "note_overlap_same": sum(same) / len(same), "note_overlap_baseline": sum(base) / len(base)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exclude", action="append", default=[], help='file label to leave out of the "without" version, e.g. "GEN0-EN gen 0"')
    a = ap.parse_args()
    P = pairs()
    per_file = [{"file": p["file"], "raters": f"{p['a']} / {p['b']}", **stats(p["items"]), **independence(p["items"])} for p in P]
    def pooled(sel):
        items = [it for p in P if sel(p) for it in p["items"]]
        return stats(items) if items else None
    versions = {"all files": lambda p: True}
    if a.exclude:
        versions["without " + ", ".join(a.exclude)] = lambda p: p["file"] not in a.exclude
    summary = {}
    for name, sel in versions.items():
        summary[name] = {"pooled": pooled(sel), "EN": pooled(lambda p, s=sel: s(p) and p["lang"] == "EN"),
                         "BN": pooled(lambda p, s=sel: s(p) and p["lang"] == "BN")}
    out = HR / "G5_checks"
    out.mkdir(parents=True, exist_ok=True)
    (out / "fluency_agreement.json").write_text(json.dumps({"per_file": per_file, "summary": summary, "excluded": a.exclude}, indent=1), encoding="utf-8")
    f3 = lambda v: f"{v:.3f}" if v == v else "n/a"
    lines = ["# Optional G5 fluency: agreement between the two authors", "",
             "Made by `harness/tools/g5_fluency_agreement.py`. Quadratic-weighted Cohen's kappa (qwk) with a bootstrap 95% interval over samples; "
             "exact and within-one agreement; Spearman's rho. Independence check: identical ratings and the content-word overlap (Jaccard) of the "
             "two notes on the same sample against notes on different samples.", ""]
    for name, s in summary.items():
        lines += [f"## {name}", "", "| Set | n | exact | within 1 | qwk [95% CI] | Spearman |", "|---|---|---|---|---|---|"]
        for k in ("pooled", "EN", "BN"):
            v = s[k]
            if v:
                lines.append(f"| {k} | {v['n']} | {v['exact']:.2f} | {v['within_one']:.2f} | {f3(v['qwk'])} [{f3(v['qwk_ci95'][0])}, {f3(v['qwk_ci95'][1])}] | {f3(v['spearman'])} |")
        lines.append("")
    lines += ["## Per file", "", "| File | raters (first / second) | n | exact | within 1 | qwk | identical | note overlap (baseline) |", "|---|---|---|---|---|---|---|---|"]
    for r in per_file:
        lines.append(f"| {r['file']} | {r['raters']} | {r['n']} | {r['exact']:.2f} | {r['within_one']:.2f} | {f3(r['qwk'])} | {r['identical_ratings']} of {r['n']} | "
                     f"{r['note_overlap_same']:.2f} ({r['note_overlap_baseline']:.2f}) |")
    (out / "fluency_agreement.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
