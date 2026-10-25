"""Screening measures (REQ-019, approved by the authors on 2026-10-14; exploratory, reported next to the registered
measures, never part of the confirmatory analysis). For every text set, the share of documents with:

  screen_foreign_letter   a letter outside the target script (EN: not Latin; BN: neither Bengali nor Latin)
  screen_foreign_run3     a run of >= 3 such letters (a fragment, not a stray letter)
  screen_latin_letter     BN only: any Latin letter (the rubric's "English intrusion")
  screen_char_run10       a run of >= 10 identical non-space characters (e.g. 648 commas, 22 emoji)
  screen_stub_lt20_words  fewer than 20 words although the model ended the text itself (finish == "stop")
  screen_private_use      private-use or replacement characters (U+E000-U+F8FF, planes 15-16, U+FFFD), e.g. U+F079
  screen_mojibake         UTF-8 text read as Windows-1252 (an apostrophe shown as three characters), inherited from web pages
  screen_repeat4_ge_0.2   the document's own 4-gram repetition >= 0.2 (the registered limit applies to the sample mean)

Usage:
  python harness/tools/screening_check.py                 # print one JSON line per set: references, base, gen 0, pilot gen 1
  python harness/tools/screening_check.py --all --out results/screening_metrics.jsonl
      # every sample and every model-written training text under results/chains (run on the host: the training texts stay
      # there), written as metric-schema rows: chain_id, generation, language, metric, value, ci_lo, ci_hi (Wilson 95%), n,
      # checkpoint, computed_at. Training-text rows carry the metric name prefix screen_train_. Held-out real text is
      # chain REAL-HELDOUT-<lang>, generation -2. The file is rewritten each time, so it never collides with metrics.jsonl.
CPU only; changes no registered measure."""
import argparse
import datetime
import json
import math
import sys
from pathlib import Path

import regex

PKG = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PKG / "harness"))
from common import read_jsonl, repeat_4gram_rate, words  # noqa: E402

RES, HELD = PKG / "results", PKG / "data" / "heldout"
FOREIGN = {"EN": regex.compile(r"(?V1)[\p{L}--\p{Script=Latin}]"), "BN": regex.compile(r"(?V1)[\p{L}--[\p{Script=Bengali}\p{Script=Latin}]]")}
FOREIGN_RUN = {"EN": regex.compile(r"(?V1)[\p{L}--\p{Script=Latin}]{3,}"), "BN": regex.compile(r"(?V1)[\p{L}--[\p{Script=Bengali}\p{Script=Latin}]]{3,}")}
LATIN = regex.compile(r"\p{Script=Latin}")
CHAR_RUN = regex.compile(r"(\S)\1{9,}")
PUA = regex.compile("[-�\U000f0000-\U0010ffff]")
MOJIBAKE = regex.compile("â€|Ã[\u0080-¿]|Â[\u0080-¿ ]")
NAMES = ["foreign_letter", "foreign_run3", "latin_letter", "char_run10", "stub_lt20_words", "private_use", "mojibake", "repeat4_ge_0.2"]


def counts(docs: list[dict], lang: str, text_key: str = "text") -> tuple[int, dict]:
    c = {k: 0 for k in NAMES}
    for d in docs:
        t = d.get(text_key) or ""
        ws = words(t)
        c["foreign_letter"] += bool(FOREIGN[lang].search(t))
        c["foreign_run3"] += bool(FOREIGN_RUN[lang].search(t))
        c["latin_letter"] += bool(LATIN.search(t))
        c["char_run10"] += bool(CHAR_RUN.search(t))
        c["stub_lt20_words"] += d.get("finish") == "stop" and len(ws) < 20
        c["private_use"] += bool(PUA.search(t))
        c["mojibake"] += bool(MOJIBAKE.search(t))
        c["repeat4_ge_0.2"] += repeat_4gram_rate([w.lower() for w in ws]) >= 0.2
    if lang != "BN":
        c.pop("latin_letter")
    return len(docs), c


def stats(docs: list[dict], lang: str, text_key: str = "text") -> dict:
    n, c = counts(docs, lang, text_key)
    return {"docs": n, **{k: round(v / max(1, n), 4) for k, v in c.items()}}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def text_sets() -> list[tuple[str, int, str, str, Path]]:
    """(chain_id, generation, language, kind, path): every sample and every model-written training text."""
    out = []
    for lang in ("EN", "BN"):
        out.append((f"REAL-HELDOUT-{lang}", -2, lang, "sample", HELD / f"{lang}_heldout.jsonl"))
    ch = RES / "chains"
    for cdir in sorted(p for p in ch.iterdir() if p.is_dir()) if ch.exists() else []:
        cid = cdir.name
        lang = "BN" if cid.startswith("BN") or cid.endswith("-BN") or "-BN-" in cid else "EN"
        if cid.startswith("BASE-"):
            out.append((cid, -1, lang, "sample", cdir / "base" / "sample.jsonl"))
        elif cid.startswith("GEN0-"):
            out.append((cid, 0, lang, "sample", cdir / "sample.jsonl"))
        else:
            for gdir in sorted(cdir.glob("gen_*"), key=lambda p: int(p.name.split("_")[1])):
                g = int(gdir.name.split("_")[1])
                out.append((cid, g, lang, "sample", gdir / "sample.jsonl"))
                out.append((cid, g, lang, "train", gdir / "synthetic.jsonl"))
    return [s for s in out if s[4].exists()]


def write_all(out_path: Path) -> None:
    """Incremental: per-file counts are cached in results/screening_cache.json keyed by path, size and mtime, so a run
    only reads files that are new or changed (2026-10-15: re-reading every training text, over 1 GB, exceeded the
    2-hour check's time limit)."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    cache_path = out_path.parent / "screening_cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    except (ValueError, OSError):
        cache = {}
    rows, read = [], 0
    for cid, g, lang, kind, path in text_sets():
        key = str(path.relative_to(PKG)).replace("\\", "/")
        st = path.stat()
        hit = cache.get(key)
        if hit and hit.get("size") == st.st_size and hit.get("mtime") == int(st.st_mtime) and hit.get("lang") == lang:
            n, c = hit["n"], hit["counts"]
        else:
            docs = [d for d in read_jsonl(path) if not d.get("fresh")] if cid.startswith("REAL-") else list(read_jsonl(path))
            if cid.startswith("REAL-"):
                docs = docs[:2000]
            n, c = counts(docs, lang)
            cache[key] = {"size": st.st_size, "mtime": int(st.st_mtime), "lang": lang, "n": n, "counts": c}
            read += 1
        prefix = "screen_train_" if kind == "train" else "screen_"
        for k, v in c.items():
            lo, hi = wilson(v, n)
            rows.append({"chain_id": cid, "generation": g, "language": lang, "metric": prefix + k, "value": v / max(1, n),
                         "ci_lo": lo, "ci_hi": hi, "n": n, "checkpoint": str(path.relative_to(PKG)).replace("\\", "/"), "computed_at": now})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    tmp.replace(out_path)
    ctmp = cache_path.with_suffix(".tmp")
    ctmp.write_text(json.dumps(cache), encoding="utf-8")
    ctmp.replace(cache_path)
    print(json.dumps({"written": str(out_path), "rows": len(rows), "files_read": read,
                      "sets": len({(r['chain_id'], r['generation'], r['metric'].startswith('screen_train_')) for r in rows})}))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="every sample and training text under results/chains, written to --out")
    ap.add_argument("--out", default="results/screening_metrics.jsonl")
    a = ap.parse_args()
    if a.all:
        write_all(PKG / a.out)
        return
    for lang in ("EN", "BN"):
        held = [d for d in read_jsonl(HELD / f"{lang}_heldout.jsonl") if not d.get("fresh")][:2000]
        print(json.dumps({"lang": lang, "set": "held-out real text (reference)", **stats(held, lang)}), flush=True)
        for label, p in (("base model sample", RES / "chains" / f"BASE-{lang}" / "base" / "sample.jsonl"),
                         ("generation 0 sample", RES / "chains" / f"GEN0-{lang}" / "sample.jsonl"),
                         ("generation-1 training text (written by generation 0)", RES / "chains" / f"{lang}-REPLACE" / "gen_1" / "synthetic.jsonl"),
                         ("generation 1 sample", RES / "chains" / f"{lang}-REPLACE" / "gen_1" / "sample.jsonl")):
            if p.exists():
                print(json.dumps({"lang": lang, "set": label, **stats(list(read_jsonl(p)), lang)}), flush=True)
            else:
                print(json.dumps({"lang": lang, "set": label, "missing": str(p.relative_to(PKG))}), flush=True)


if __name__ == "__main__":
    main()
