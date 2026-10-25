#!/usr/bin/env python3
"""
Download the public sources for CG4 into data/sources/ in the JSONL shape that configs/corpora.yaml, prepare_corpora.py
and build_probes.py expect (02_DATA_SOURCES.md). Run it on the rented host (fast link); --dry-run works offline anywhere.

  python harness/fetch_sources.py --dry-run                    # plan + manifest preview, no network, no `datasets` import
  python harness/fetch_sources.py --all [--max-docs 40000] [--fresh-n 600] [--fresh-after 2025-09-01]
  python harness/fetch_sources.py --bnwiki --enwiki --bn-web --en-web --fresh --crows --banstereoset   # any subset

Output (data/sources/):
  bnwiki_articles.jsonl, enwiki_articles.jsonl, bn_web_slice.jsonl, en_web_slice.jsonl      fields: id, title?, url?, text
  bnwiki_fresh_articles.jsonl, enwiki_fresh_articles.jsonl                                  + created (ISO date of page creation)
  crows_pairs_en.jsonl, banstereoset_bn.jsonl                                               fields: stereo, anti, bias_type, source_id
  SOURCES_MANIFEST.json                                                                     licence, url, counts, sha256 per source
Sources verified 2026-10-12 (ids, configs, licences). BanglaVeilGuard-style private data is not involved here. The licence of
BanStereoSet is not stated in its repository: the manifest records that; REQ-005 (2026-10-13) settled its use (evaluation only, cited, never redistributed).
Network failures never abort the run: the failing source is reported with the request type to file, the others continue,
and the exit code is 1 if a required source is still missing at the end.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SOURCES, ROOT, ensure_dirs, now_iso, sha256_file, utf8_stdout, write_json, log_decision  # noqa: E402

utf8_stdout()
MANIFEST = SOURCES / "SOURCES_MANIFEST.json"
# Wikimedia's API policy wants a contact in the User-Agent; without one the MediaWiki API answered HTTP 429 to every request
# from the rented host (2026-10-13). The public OSF registration page is the contact (no personal e-mail in request headers).
UA = "CG4-model-collapse-research/1.0 (https://osf.io/sra28/; pre-registered academic study) python-requests"
MIN_CHARS = 200           # skip stubs at fetch time; prepare_corpora.py applies the token-length rules afterwards

SPEC = {
    "bnwiki": {"file": "bnwiki_articles.jsonl", "kind": "hf", "hf_id": "wikimedia/wikipedia", "config": "20231101.bn", "required": True,
               "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/", "stride": 1,
               "notes": "Bangla Wikipedia dump 2023-11-01 as parquet on Hugging Face; fields id,url,title,text"},
    "enwiki": {"file": "enwiki_articles.jsonl", "kind": "hf", "hf_id": "wikimedia/wikipedia", "config": "20231101.en", "required": True,
               "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/", "stride": 4,
               "notes": "English Wikipedia dump 2023-11-01; stride + shuffle buffer so the slice is not the first shard only"},
    "en_web": {"file": "en_web_slice.jsonl", "kind": "hf", "hf_id": "HuggingFaceFW/fineweb-edu", "config": "sample-10BT", "required": True,
               "licence": "ODC-By 1.0", "licence_url": "https://opendatacommons.org/licenses/by/1-0/", "stride": 1,
               "notes": "FineWeb-Edu 10BT sample; fields text,id,url,date,score; web/educational domain"},
    "bn_web": {"file": "bn_web_slice.jsonl", "kind": "hf", "hf_id": "ai4bharat/sangraha", "data_dir": "verified/ben", "required": True,
               "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/", "stride": 1,
               "notes": "Sangraha verified Bengali subset (web/news/books, 10.6B tokens); fields doc_id,text"},
    "bnwiki_fresh": {"file": "bnwiki_fresh_articles.jsonl", "kind": "mediawiki", "site": "bn.wikipedia.org", "required": False,
                     "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                     "notes": "pages created recently (MediaWiki recentchanges, new pages, main namespace); plain-text extracts; held-out fresh slice"},
    "enwiki_fresh": {"file": "enwiki_fresh_articles.jsonl", "kind": "mediawiki", "site": "en.wikipedia.org", "required": False,
                     "licence": "CC BY-SA 4.0", "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                     "notes": "as bnwiki_fresh, English"},
    "crows_pairs": {"file": "crows_pairs_en.jsonl", "kind": "csv", "required": True,
                    "url": "https://raw.githubusercontent.com/nyu-mll/crows-pairs/master/data/crows_pairs_anonymized.csv",
                    "licence": "CC BY-SA 4.0", "licence_url": "https://github.com/nyu-mll/crows-pairs/blob/master/LICENSE",
                    "notes": "1,508 pairs; stereo/anti derived from sent_more/sent_less and stereo_antistereo"},
    "banstereoset": {"file": "banstereoset_bn.jsonl", "kind": "csv", "required": True,
                     "url": "https://raw.githubusercontent.com/kamruzzaman15/BanStereoSet/main/BanStereoset.csv",
                     "licence": "unstated in repository; evaluation-only use decided 2026-10-13 (REQ-005): cited, not redistributed, disclosed",
                     "licence_url": "https://github.com/kamruzzaman15/BanStereoSet",
                     "notes": "1,194 rows (Findings ACL 2025); stereo/anti = bangla_context with BLANK filled by bangla_stereotype / bangla_anti_stereotype"},
}
GROUPS = {"bnwiki": ["bnwiki"], "enwiki": ["enwiki"], "bn_web": ["bn_web"], "en_web": ["en_web"], "fresh": ["bnwiki_fresh", "enwiki_fresh"],
          "crows": ["crows_pairs"], "banstereoset": ["banstereoset"]}


# ---------------- helpers ----------------
def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.load(open(MANIFEST, encoding="utf-8"))
    return {"created_at": now_iso(), "sources": {}}


def record(man: dict, name: str, n: int, note_extra: str = "") -> None:
    s = SPEC[name]
    p = SOURCES / s["file"]
    man["sources"][name] = {"name": name, "file": f"data/sources/{s['file']}", "hf_id_or_url": s.get("hf_id") or s.get("url") or s.get("site"),
                            "config": s.get("config") or s.get("data_dir"), "licence": s["licence"], "licence_url": s["licence_url"],
                            "retrieved_at": now_iso(), "n_records": n, "bytes": p.stat().st_size if p.exists() else 0,
                            "sha256": sha256_file(p) if p.exists() else None, "notes": (s["notes"] + ("; " + note_extra if note_extra else ""))}
    man["updated_at"] = now_iso()
    write_json(MANIFEST, man)
    log_decision(f"fetch_sources: {name} -> {s['file']} ({n} records, licence: {s['licence']})")


def write_records(name: str, records) -> int:
    p = SOURCES / SPEC[name]["file"]
    n = 0
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def fail(name: str, err: Exception, request_type: str) -> None:
    print(f"[FAIL] {name}: {type(err).__name__}: {str(err)[:300]}")
    print(f"       -> file a {request_type} request in signoffs/REQUESTS.md (see ../AGENT_PIPELINE.md section 6) and continue; "
          f"the other sources are still fetched.")


# ---------------- Hugging Face datasets ----------------
def fetch_hf(name: str, max_docs: int, seed: int) -> int:
    from datasets import load_dataset          # lazy: not needed for --dry-run
    s = SPEC[name]
    kwargs = {"streaming": True, "split": "train"}
    if s.get("config"):
        ds = load_dataset(s["hf_id"], s["config"], **kwargs)
    else:
        ds = load_dataset(s["hf_id"], data_dir=s["data_dir"], **kwargs)
    ds = ds.shuffle(seed=seed, buffer_size=10_000)
    stride = s.get("stride", 1)

    def gen():
        kept = 0
        for i, row in enumerate(ds):
            if i % stride:
                continue
            text = (row.get("text") or "").strip()
            if len(text) < MIN_CHARS:
                continue
            rec = {"id": str(row.get("id") or row.get("doc_id") or i), "text": text}
            if row.get("title"):
                rec["title"] = row["title"]
            if row.get("url"):
                rec["url"] = row["url"]
            if row.get("date"):
                rec["created"] = str(row["date"])[:10]
            yield rec
            kept += 1
            if kept % 5000 == 0:
                print(f"  [{name}] {kept} docs ...", flush=True)
            if kept >= max_docs:
                break
    return write_records(name, gen())


# ---------------- MediaWiki fresh slices ----------------
def mw_get(session, site: str, params: dict, retries: int = 4) -> dict:
    params = dict(params, format="json", formatversion="2")
    for attempt in range(retries):
        try:
            r = session.get(f"https://{site}/w/api.php", params=params, headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 200:
                return r.json()
            print(f"  [mediawiki] HTTP {r.status_code}; retry {attempt + 1}")
        except Exception as e:  # noqa
            print(f"  [mediawiki] {type(e).__name__}; retry {attempt + 1}")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"MediaWiki API on {site} failed after {retries} attempts")


def fetch_fresh(name: str, fresh_n: int, fresh_after: str) -> int:
    import requests                              # lazy
    s = SPEC[name]
    site = s["site"]
    sess = requests.Session()
    # 1. new pages in the main namespace (recentchanges keeps about 90 days; all are after the base model's release)
    pages: dict[int, dict] = {}
    params = {"action": "query", "list": "recentchanges", "rctype": "new", "rcnamespace": "0", "rclimit": "500",
              "rcprop": "title|ids|timestamp", "rcshow": "!redirect", "rcend": f"{fresh_after}T00:00:00Z"}
    while len(pages) < fresh_n * 3:
        data = mw_get(sess, site, params)
        for rc in data.get("query", {}).get("recentchanges", []):
            if rc.get("timestamp", "") >= f"{fresh_after}T00:00:00Z" and rc.get("pageid"):
                pages[int(rc["pageid"])] = {"title": rc.get("title"), "created": rc["timestamp"]}
        cont = data.get("continue", {}).get("rccontinue")
        if not cont:
            break
        params["rccontinue"] = cont
        time.sleep(0.2)
    print(f"  [{name}] {len(pages)} candidate new pages after {fresh_after}")
    # 2. plain-text extracts (TextExtracts returns one full extract per request when exintro is off)
    out = []
    for pid, meta in pages.items():
        if len(out) >= fresh_n:
            break
        try:
            data = mw_get(sess, site, {"action": "query", "prop": "extracts", "explaintext": "1", "exsectionformat": "plain", "pageids": str(pid)})
        except RuntimeError as e:
            print(f"  [{name}] skip page {pid}: {e}")
            continue
        for pg in data.get("query", {}).get("pages", []):
            text = (pg.get("extract") or "").strip()
            if len(text) >= 2 * MIN_CHARS and not pg.get("missing"):
                out.append({"id": f"fresh-{pid}", "title": pg.get("title") or meta["title"], "url": f"https://{site}/?curid={pid}",
                            "created": meta["created"][:10], "text": text})
        if len(out) % 100 == 0 and out:
            print(f"  [{name}] {len(out)} fresh articles ...", flush=True)
        time.sleep(0.2)
    return write_records(name, out)


# ---------------- bias-pair CSVs ----------------
def fetch_csv(name: str) -> list[dict]:
    import requests                              # lazy
    r = requests.get(SPEC[name]["url"], headers={"User-Agent": UA}, timeout=120)
    r.raise_for_status()
    text = r.content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def fetch_crows(name: str) -> int:
    rows = fetch_csv(name)
    out = []
    for i, r in enumerate(rows):
        more, less, direction = (r.get("sent_more") or "").strip(), (r.get("sent_less") or "").strip(), (r.get("stereo_antistereo") or "").strip()
        if not more or not less:
            continue
        stereo, anti = (more, less) if direction != "antistereo" else (less, more)
        out.append({"source_id": str(r.get("", i) or i), "bias_type": r.get("bias_type"), "direction": direction, "stereo": stereo, "anti": anti})
    return write_records(name, out)


def fetch_banstereoset(name: str) -> int:
    rows = fetch_csv(name)
    out = []
    for i, r in enumerate(rows):
        ctx = (r.get("bangla_context") or "").strip()
        st, an = (r.get("bangla_stereotype") or "").strip(), (r.get("bangla_anti_stereotype") or "").strip()
        if not ctx or not st or not an:
            continue
        if "BLANK" in ctx:
            stereo, anti = ctx.replace("BLANK", st), ctx.replace("BLANK", an)
        else:                                     # intersentence rows: context + continuation
            stereo, anti = f"{ctx} {st}", f"{ctx} {an}"
        out.append({"source_id": str(i), "bias_type": r.get("bias_type"), "stereo": stereo, "anti": anti,
                    "en_context": r.get("context"), "en_stereotype": r.get("stereotype"), "en_anti": r.get("anti_stereotype")})
    return write_records(name, out)


# ---------------- main ----------------
def plan_table(selected: list[str]) -> None:
    print(f"{'source':<14} {'required':<8} {'exists':<6} {'file':<30} {'id / url':<58} {'licence'}")
    for name in selected:
        s = SPEC[name]
        exists = (SOURCES / s["file"]).exists()
        ident = (s.get("hf_id", "") + ("/" + (s.get("config") or s.get("data_dir")) if s.get("hf_id") else "")) or s.get("url") or s.get("site")
        print(f"{name:<14} {str(s['required']):<8} {str(exists):<6} {s['file']:<30} {ident[:58]:<58} {s['licence']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--all", action="store_true")
    for g in GROUPS:
        ap.add_argument(f"--{g.replace('_', '-')}", action="store_true")
    ap.add_argument("--max-docs", type=int, default=40000, help="documents per Wikipedia/web source before cleaning")
    ap.add_argument("--fresh-n", type=int, default=600); ap.add_argument("--fresh-after", default="2025-09-01", help="pages created after this date (base model released 2025-08-05)")
    ap.add_argument("--seed", type=int, default=20261010); ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    a = ap.parse_args()
    ensure_dirs()
    chosen = [n for g, names in GROUPS.items() if (a.all or getattr(a, g.replace("-", "_"))) for n in names]
    if not chosen and not a.dry_run:
        ap.error("choose --all, --dry-run or one or more source flags")
    if a.dry_run:
        print(f"data/sources = {SOURCES}\nplan (dry run; nothing downloaded):")
        plan_table(list(SPEC))
        print(f"\nmanifest -> {MANIFEST.relative_to(ROOT)} with fields name, file, hf_id_or_url, config, licence, licence_url, retrieved_at, n_records, bytes, sha256, notes")
        print("defaults: --max-docs 40000 per Wikipedia/web source (10M tokens per language needs roughly 10-20k cleaned docs), --fresh-n 600 after --fresh-after 2025-09-01")
        print("BanStereoSet: licence unstated in its repository; REQ-005 (2026-10-13) decided evaluation-only use, so no LICENCE request is needed.")
        return
    man = load_manifest()
    done, failed = [], []
    for name in chosen:
        s = SPEC[name]
        p = SOURCES / s["file"]
        if p.exists() and not a.force:
            print(f"[skip] {name}: {p.name} exists ({p.stat().st_size / 1e6:.1f} MB); use --force to re-download")
            if name not in man["sources"]:
                record(man, name, sum(1 for _ in open(p, encoding="utf-8")))
            done.append(name)
            continue
        print(f"[fetch] {name} <- {s.get('hf_id') or s.get('url') or s.get('site')} ({s['licence']})", flush=True)
        t0 = time.time()
        try:
            if s["kind"] == "hf":
                n = fetch_hf(name, a.max_docs, a.seed)
            elif s["kind"] == "mediawiki":
                n = fetch_fresh(name, a.fresh_n, a.fresh_after)
            elif name == "crows_pairs":
                n = fetch_crows(name)
            else:
                n = fetch_banstereoset(name)
            record(man, name, n, f"{time.time() - t0:.0f}s")
            print(f"[ok] {name}: {n} records in {time.time() - t0:.0f}s -> {p.name}")
            done.append(name)
        except Exception as e:  # noqa
            req = "LICENCE" if any(k in str(e).lower() for k in ("401", "403", "gated", "unauthorized", "forbidden")) else "DECISION"
            fail(name, e, req)
            failed.append(name)
            if p.exists():
                p.unlink()
    missing_required = [n for n in SPEC if SPEC[n]["required"] and not (SOURCES / SPEC[n]["file"]).exists()]
    print(f"\ndone: {done}\nfailed: {failed}\nrequired sources still missing: {missing_required}")
    print("Next: python harness/prepare_corpora.py --dry-run   (then --build);  python harness/build_probes.py --fetch --build --bias --spotcheck-csv")
    sys.exit(1 if missing_required else 0)


if __name__ == "__main__":
    main()
