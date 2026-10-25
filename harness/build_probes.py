#!/usr/bin/env python3
"""
Build the frozen tail-fact probe sets (02_DATA_SOURCES.md section 3) and convert bias-pair files.

  python harness/build_probes.py --fetch           # query Wikidata SPARQL for the configured relations (en + bn labels)
  python harness/build_probes.py --filters         # Wikidata properties for the REQ-009 filters (P17 subjects, P19 objects)
  python harness/build_probes.py --build           # stratify by seed-corpus mention counts, make cloze probes with 3 distractors
  python harness/build_probes.py --bias            # convert bias-pair files listed in configs/corpora.yaml to the common format
  python harness/build_probes.py --spotcheck-csv   # write the 60-probe spot-check CSVs for the authors
Probe record: {probe_id, language, relation, stratum, subject, template, gold, distractors[3], source}
Scoring (metrics.py): log-likelihood of each completion; correct if gold ranks first. No generation needed.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CORPORA, PROBES, ROOT, load_corpora_cfg, now_iso, read_jsonl, utf8_stdout, words, write_json, write_jsonl, log_decision  # noqa: E402

utf8_stdout()
UA = "CG4-probe-builder/1.0 (https://osf.io/sra28/; pre-registered academic study) python-urllib"   # Wikimedia UA policy: contact URL


def sparql(endpoint: str, query: str) -> list[dict]:
    url = endpoint + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        # strict=False: Wikidata labels can carry raw control characters, which the strict JSON parser rejects
        # (P19 on 2026-10-13: "Invalid control character at line 52029"), and the relation then came back empty
        data = json.loads(r.read().decode("utf-8"), strict=False)
    return [{k: v["value"] for k, v in row.items()} for row in data["results"]["bindings"]]


LABELS = """
          ?s rdfs:label ?sLabelEn FILTER(LANG(?sLabelEn)="en") .
          ?s rdfs:label ?sLabelBn FILTER(LANG(?sLabelBn)="bn") .
          ?o rdfs:label ?oLabelEn FILTER(LANG(?oLabelEn)="en") .
          ?o rdfs:label ?oLabelBn FILTER(LANG(?oLabelBn)="bn") ."""


CACHE = PROBES / "wikidata_cache"      # one file per window and per relation count, so an interrupted --fetch resumes


def _retry_wait(e: Exception, attempt: int) -> float:
    """Seconds to wait after a failed query: Retry-After on HTTP 429 if given, else a growing back-off."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError) and e.code == 429:
        try:
            return max(30.0, float(e.headers.get("Retry-After", 0)))
        except (TypeError, ValueError):
            return 60.0 * (attempt + 1)
    return 30.0 * (attempt + 1)


def relation_count(endpoint: str, prop: str) -> int:
    p = CACHE / f"{prop}_count.json"
    if p.exists():
        return int(json.load(open(p, encoding="utf-8"))["n"])
    n = int(sparql(endpoint, f"SELECT (COUNT(*) AS ?n) WHERE {{ ?s wdt:{prop} ?o }}")[0]["n"])
    write_json(p, {"relation": prop, "n": n, "at": now_iso()})
    return n


def slice_query(endpoint: str, prop: str, offset: int, size: int, attempts: int = 6) -> list[dict]:
    """Triples among statements [offset, offset + size) of the relation's index (bd:slice) whose subject and object both
    carry an English and a Bangla label. Small slices finish well inside the 60 s query timeout; cached on disk; retried
    with back-off (Retry-After on 429), then fatal."""
    cp = CACHE / f"{prop}_{offset}_{size}.json"
    if cp.exists():
        return json.load(open(cp, encoding="utf-8"))
    q = f"""
        SELECT ?s ?sLabelEn ?sLabelBn ?o ?oLabelEn ?oLabelBn WHERE {{
          SERVICE bd:slice {{ ?s wdt:{prop} ?o . bd:serviceParam bd:slice.offset {offset} . bd:serviceParam bd:slice.limit {size} . }}
          {LABELS}
        }}"""
    for attempt in range(attempts):
        try:
            rows = sparql(endpoint, q)
            write_json(cp, rows)
            return rows
        except Exception as e:  # noqa
            wait = _retry_wait(e, attempt)
            print(f"[warn] {prop} slice at {offset:,} attempt {attempt + 1}: {type(e).__name__}: {str(e)[:160]}; waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise SystemExit(f"[FAIL] {prop}: slice at {offset:,} failed {attempts} times; re-run --fetch later (finished windows are cached)")


def fetch_relation_spread(endpoint: str, prop: str, cap: int, slices: int = 50, max_slice: int = 2000, rounds: int = 4) -> tuple[list[dict], dict]:
    """Up to `cap` triples of one relation, spread evenly over ALL of the relation's statements (fix of 2026-10-13).
    The single `LIMIT cap` query (no ORDER BY) returned the FIRST matches of an index that is grouped by object: all
    3,000 P17 triples had the object Canada, P19 had 29 distinct birthplaces, P106 42 occupations, which leaves no
    same-relation distractors for P17 and makes P19/P106 guessable from a few frequent answers. Here: `slices` evenly
    spaced bd:slice windows over the relation's statements (count from COUNT(*)), more rounds at shifted positions while
    fewer than `cap` matches; the matches are then taken round-robin across windows (in offset order, sorted by subject
    and object inside a window) until `cap`. Same definition as before (subject and object labelled in English and
    Bangla, at most `cap` per relation, query.wikidata.org); approximately uniform over statements; fixed for a database
    state."""
    n = relation_count(endpoint, prop)                            # cached, so a resumed fetch uses the same windows
    size = max(50, min(max_slice, n // (slices * rounds)))       # windows never overlap across the rounds
    windows: list[tuple[int, list[dict]]] = []
    total = 0
    for r, shift in enumerate((0.0, 0.5, 0.25, 0.75)[:rounds]):
        for i in range(slices):
            off = int((i + shift) * n / slices)
            got = slice_query(endpoint, prop, off, size)
            got.sort(key=lambda x: (x.get("s", ""), x.get("o", "")))
            for g in got:
                g["slice_offset"] = off
            windows.append((off, got)); total += len(got)
            time.sleep(1)
        print(f"[spread] {prop}: round {r + 1}: {len(windows)} windows of {size:,} statements (relation has {n:,}), {total} matches", flush=True)
        if total >= cap:
            break
    windows.sort(key=lambda t: t[0])
    out: list[dict] = []
    depth = 0
    while len(out) < cap and any(depth < len(g) for _, g in windows):
        for _, g in windows:
            if depth < len(g) and len(out) < cap:
                out.append(g[depth])
        depth += 1
    return out, {"statements": n, "window_size": size, "windows": len(windows), "matches": total, "kept": len(out)}


def fetch(cfg: dict) -> None:
    rows_all, summary = [], {}
    cap = int(cfg["probes"]["max_items_per_relation"])
    for prop in cfg["probes"]["relations"]:
        rows, info = fetch_relation_spread(cfg["probes"]["sparql_endpoint"], prop, cap)
        for r in rows:
            r["relation"] = prop
        rows_all.extend(rows)
        info["distinct_subjects"] = len({r["s"] for r in rows}); info["distinct_objects"] = len({r["o"] for r in rows})
        summary[prop] = info
        print(f"[fetch] {prop}: {len(rows)} triples with en+bn labels ({info['distinct_objects']} distinct objects, {info['distinct_subjects']} subjects)", flush=True)
    write_jsonl(PROBES / "wikidata_triples.jsonl", rows_all)
    write_json(PROBES / "wikidata_fetch_summary.json", {"fetched_at": now_iso(), "endpoint": cfg["probes"]["sparql_endpoint"], "cap_per_relation": cap,
                                                        "method": "evenly spaced bd:slice windows, round-robin up to the cap", "relations": summary})
    log_decision(f"fetched {len(rows_all)} Wikidata triples for probes (spread sampling): {summary}")
    empty = [p for p in cfg["probes"]["relations"] if not summary.get(p, {}).get("kept")]
    if empty:
        raise SystemExit(f"[FAIL] no triples for {empty}: re-run --fetch (a pre-registered relation must not be silently missing)")


TRUTH = PROBES / "wikidata_truth.jsonl"


def fetch_truth(cfg: dict, batch: int = 200) -> None:
    """ALL objects (with English and Bangla labels where they exist) of every subject in the triples, per relation, so
    that the distractor rule of 02_DATA_SOURCES.md section 3 ('all of the subject's objects for the relation are
    excluded') holds for objects that are not among the sampled triples (2026-10-13: the sample has ~1 object per subject,
    so e.g. a second true occupation could have been drawn as a distractor). Batched VALUES queries, cached per batch."""
    endpoint = cfg["probes"]["sparql_endpoint"]
    triples = list(read_jsonl(PROBES / "wikidata_triples.jsonl"))
    out = []
    for prop in cfg["probes"]["relations"]:
        subs = sorted({t["s"] for t in triples if t["relation"] == prop})
        for b in range(0, len(subs), batch):
            chunk = subs[b:b + batch]
            cp = CACHE / f"truth_{prop}_{b}_{len(chunk)}.json"
            if cp.exists():
                rows = json.load(open(cp, encoding="utf-8"))
            else:
                values = " ".join("wd:" + s.rsplit("/", 1)[-1] for s in chunk)
                q = f"""
                SELECT ?s ?o ?oLabelEn ?oLabelBn WHERE {{
                  VALUES ?s {{ {values} }}
                  ?s wdt:{prop} ?o .
                  OPTIONAL {{ ?o rdfs:label ?oLabelEn FILTER(LANG(?oLabelEn)="en") }}
                  OPTIONAL {{ ?o rdfs:label ?oLabelBn FILTER(LANG(?oLabelBn)="bn") }}
                }}"""
                for attempt in range(6):
                    try:
                        rows = sparql(endpoint, q); write_json(cp, rows); break
                    except Exception as e:  # noqa
                        wait = _retry_wait(e, attempt)
                        print(f"[warn] truth {prop} batch {b}: {type(e).__name__}: {str(e)[:120]}; waiting {wait:.0f}s", flush=True)
                        time.sleep(wait)
                else:
                    raise SystemExit(f"[FAIL] truth {prop} batch {b} failed 6 times; re-run --truth (finished batches are cached)")
                time.sleep(1)
            for r in rows:
                r["relation"] = prop
            out.extend(rows)
        print(f"[truth] {prop}: {len(subs)} subjects, {sum(1 for r in out if r['relation'] == prop)} subject-object statements", flush=True)
    write_jsonl(TRUTH, out)
    log_decision(f"fetched all true objects of the probe-pool subjects ({len(out)} statements) for the distractor exclusion rule")


FILTERS = PROBES / "wikidata_filters.json"


def _has_property(endpoint: str, uris: set, body: str, tag: str, batch: int = 150) -> set:
    """Entity URIs among `uris` for which the SPARQL pattern `body` (about ?x) matches. Batched VALUES queries, cached
    per batch, retried like the other queries."""
    ids = sorted({u.rsplit("/", 1)[-1] for u in uris})
    hits: set = set()
    for b in range(0, len(ids), batch):
        chunk = ids[b:b + batch]
        cp = CACHE / f"filter_{tag}_{b}_{len(chunk)}.json"
        if cp.exists():
            rows = json.load(open(cp, encoding="utf-8"))
        else:
            q = f"SELECT DISTINCT ?x WHERE {{ VALUES ?x {{ {' '.join('wd:' + i for i in chunk)} }} {body} }}"
            for attempt in range(6):
                try:
                    rows = sparql(endpoint, q); write_json(cp, rows); break
                except Exception as e:  # noqa
                    wait = _retry_wait(e, attempt)
                    print(f"[warn] filter {tag} batch {b}: {type(e).__name__}: {str(e)[:120]}; waiting {wait:.0f}s", flush=True)
                    time.sleep(wait)
            else:
                raise SystemExit(f"[FAIL] filter {tag} batch {b} failed 6 times; re-run --filters (finished batches are cached)")
            time.sleep(1)
        hits.update(r["x"] for r in rows)
    return hits


def fetch_filters(cfg: dict) -> None:
    """Wikidata facts for the probe filters approved after G1 round 1 (REQ-009 items 2 and 3, 2026-10-14). P17 subjects:
    has a coordinate location (P625), has a point in time or start time (P585/P580). P19 objects: has a country (P17)."""
    endpoint = cfg["probes"]["sparql_endpoint"]
    triples = list(read_jsonl(PROBES / "wikidata_triples.jsonl"))
    s17 = {t["s"] for t in triples if t["relation"] == "P17"}
    o19 = {t["o"] for t in triples if t["relation"] == "P19"}
    out = {"fetched_at": now_iso(), "endpoint": endpoint, "rule": "REQ-009 items 2 and 3 (signoffs/REQUESTS.md)",
           "P17_subjects": len(s17), "P19_objects": len(o19),
           "P17_subject_has_P625": sorted(_has_property(endpoint, s17, "?x wdt:P625 ?c .", "P17_P625")),
           "P17_subject_has_P585_or_P580": sorted(_has_property(endpoint, s17, "{ ?x wdt:P585 ?t } UNION { ?x wdt:P580 ?t }", "P17_date")),
           "P19_object_has_P17": sorted(_has_property(endpoint, o19, "?x wdt:P17 ?c .", "P19_P17"))}
    write_json(FILTERS, out)
    print(f"[filters] P17 subjects {len(s17)}: with P625 {len(out['P17_subject_has_P625'])}, with P585/P580 "
          f"{len(out['P17_subject_has_P585_or_P580'])}; P19 objects {len(o19)}: with a country {len(out['P19_object_has_P17'])}", flush=True)


FILTERS_R2 = PROBES / "wikidata_filters_r2.json"


def _values(endpoint: str, uris: set, body: str, tag: str, batch: int = 150) -> dict:
    """{entity id: sorted ids bound to ?v} for the SPARQL pattern `body` (about ?x, binding ?v). Batched VALUES queries,
    cached per batch, retried like the other queries."""
    ids = sorted({u.rsplit("/", 1)[-1] for u in uris})
    out: dict = {}
    for b in range(0, len(ids), batch):
        chunk = ids[b:b + batch]
        cp = CACHE / f"values_{tag}_{b}_{len(chunk)}.json"
        if cp.exists():
            rows = json.load(open(cp, encoding="utf-8"))
        else:
            q = f"SELECT DISTINCT ?x ?v WHERE {{ VALUES ?x {{ {' '.join('wd:' + i for i in chunk)} }} {body} }}"
            for attempt in range(6):
                try:
                    rows = sparql(endpoint, q); write_json(cp, rows); break
                except Exception as e:  # noqa
                    wait = _retry_wait(e, attempt)
                    print(f"[warn] values {tag} batch {b}: {type(e).__name__}: {str(e)[:120]}; waiting {wait:.0f}s", flush=True)
                    time.sleep(wait)
            else:
                raise SystemExit(f"[FAIL] values {tag} batch {b} failed 6 times; re-run --filters-r2 (finished batches are cached)")
            time.sleep(1)
        for r in rows:
            out.setdefault(r["x"].rsplit("/", 1)[-1], set()).add(r["v"].rsplit("/", 1)[-1])
    return {k: sorted(v) for k, v in sorted(out.items())}


def _cached_query(endpoint: str, q: str, tag: str) -> list[dict]:
    """One SPARQL query, cached under `tag`, retried like the others."""
    cp = CACHE / f"query_{tag}.json"
    if cp.exists():
        return json.load(open(cp, encoding="utf-8"))
    for attempt in range(6):
        try:
            rows = sparql(endpoint, q); write_json(cp, rows); return rows
        except Exception as e:  # noqa
            wait = _retry_wait(e, attempt)
            print(f"[warn] query {tag}: {type(e).__name__}: {str(e)[:120]}; waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise SystemExit(f"[FAIL] query {tag} failed 6 times; re-run --filters-r2")


def _sparql_str(s: str, lang: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"@' + lang


def _homonym_countries(endpoint: str, labels: dict, lang: str, batch: int = 40) -> dict:
    """{label: sorted country ids} of every settlement or administrative unit (P31/P279* Q486972 or Q56061) whose `lang`
    label is exactly `label`. `labels` maps label -> any; batched, cached, retried."""
    labs = sorted(labels)
    out: dict = {}
    for b in range(0, len(labs), batch):
        chunk = labs[b:b + batch]
        cp = CACHE / f"homonyms_{lang}_{b}_{len(chunk)}.json"
        if cp.exists():
            rows = json.load(open(cp, encoding="utf-8"))
        else:
            q = (f"SELECT DISTINCT ?l ?c WHERE {{ VALUES ?l {{ {' '.join(_sparql_str(x, lang) for x in chunk)} }} ?y rdfs:label ?l . "
                 "?y wdt:P31/wdt:P279* ?k . VALUES ?k { wd:Q486972 wd:Q56061 } ?y wdt:P17 ?c . }")
            for attempt in range(6):
                try:
                    rows = sparql(endpoint, q); write_json(cp, rows); break
                except Exception as e:  # noqa
                    wait = _retry_wait(e, attempt)
                    print(f"[warn] homonyms {lang} batch {b}: {type(e).__name__}: {str(e)[:120]}; waiting {wait:.0f}s", flush=True)
                    time.sleep(wait)
            else:
                raise SystemExit(f"[FAIL] homonyms {lang} batch {b} failed 6 times; re-run --filters-r2 (finished batches are cached)")
            time.sleep(1)
        for r in rows:
            out.setdefault(r["l"], set()).add(r["c"].rsplit("/", 1)[-1])
    return {k: sorted(v) for k, v in sorted(out.items())}


def fetch_filters_r2(cfg: dict) -> None:
    """Wikidata facts for the probe rules proposed after G1 round 2 (REQ-012, 2026-10-14): P17 subjects that are human
    settlements or administrative units; P17 objects that are current sovereign states; the countries of other places
    with a P17 subject's name (homonyms); the countries of P19 objects; the P279 ancestors of every occupation."""
    endpoint = cfg["probes"]["sparql_endpoint"]
    triples = list(read_jsonl(PROBES / "wikidata_triples.jsonl"))
    truth = list(read_jsonl(TRUTH))
    s17 = {t["s"] for t in triples if t["relation"] == "P17"}
    o17 = {t["o"] for t in triples if t["relation"] == "P17"} | {t["o"] for t in truth if t["relation"] == "P17"}
    o19 = {t["o"] for t in triples if t["relation"] == "P19"} | {t["o"] for t in truth if t["relation"] == "P19"}
    o106 = {t["o"] for t in triples if t["relation"] == "P106"} | {t["o"] for t in truth if t["relation"] == "P106"}
    place = _has_property(endpoint, s17, "?x wdt:P31/wdt:P279* ?k . VALUES ?k { wd:Q486972 wd:Q56061 }", "P17_place")
    out = {"fetched_at": now_iso(), "endpoint": endpoint, "rule": "REQ-012 (signoffs/REQUESTS.md), proposed after G1 round 2",
           "P17_subject_settlement_or_admin": sorted(place),
           # dependent territories (Bermuda, the British Virgin Islands) and places in them have the United Kingdom as P17;
           # two cheap queries (the one-step path query timed out): every dependent territory, and each place's P131 chain
           "dependent_territories": sorted(r["x"].rsplit("/", 1)[-1] for r in _cached_query(
               endpoint, "SELECT DISTINCT ?x WHERE { ?x wdt:P31/wdt:P279* wd:Q161243 . }", "dependent_territories")),
           "P17_subject_admin_ancestors": _values(endpoint, place, "?x wdt:P131* ?v .", "P17_admin"),
           "P17_object_current_state": sorted(_has_property(
               endpoint, o17, "?x p:P31 ?st . ?st ps:P31 wd:Q3624078 . FILTER NOT EXISTS { ?st pq:P582 ?e } FILTER NOT EXISTS { ?x wdt:P576 ?d }",
               "P17_state")),
           "P19_object_countries": _values(endpoint, o19, "?x wdt:P17 ?v .", "P19_country"),
           "P19_object_admin_ancestors": _values(endpoint, o19, "?x wdt:P131* ?v .", "P19_admin"),
           "P106_object_ancestors": _values(endpoint, o106, "?x wdt:P279* ?v .", "P106_anc"),
           "P106_object_parents": _values(endpoint, o106, "?x wdt:P279 ?v .", "P106_parent")}
    places = [t for t in triples if t["relation"] == "P17" and t["s"] in place]
    out["P17_homonym_countries_en"] = _homonym_countries(endpoint, {t["sLabelEn"]: 1 for t in places if t.get("sLabelEn")}, "en")
    out["P17_homonym_countries_bn"] = _homonym_countries(endpoint, {t["sLabelBn"]: 1 for t in places if t.get("sLabelBn")}, "bn")
    write_json(FILTERS_R2, out)
    dep = set(out["dependent_territories"])
    n_dep = sum(1 for v in out["P17_subject_admin_ancestors"].values() if dep & set(v))
    print(f"[filters-r2] P17 subjects {len(s17)}: settlement or admin unit {len(place)}, of which in a dependent territory "
          f"{n_dep} ({len(dep)} dependent territories); P17 objects {len(o17)}: current state "
          f"{len(out['P17_object_current_state'])}; P19 objects with a country {len(out['P19_object_countries'])} of {len(o19)}; "
          f"occupations with ancestors {len(out['P106_object_ancestors'])} of {len(o106)}; homonym labels en "
          f"{len(out['P17_homonym_countries_en'])}, bn {len(out['P17_homonym_countries_bn'])}", flush=True)


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


_EN_MONTHS = "january|february|march|april|may|june|july|august|september|october|november|december"
_ES_MONTHS = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
_BN_MONTHS = ("জানুয়ারি|জানুয়ারী|ফেব্রুয়ারি|ফেব্রুয়ারী|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগস্ট|আগষ্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর|"
              "বৈশাখ|জ্যৈষ্ঠ|আষাঢ়|শ্রাবণ|ভাদ্র|আশ্বিন|কার্তিক|অগ্রহায়ণ|পৌষ|মাঘ|ফাল্গুন|চৈত্র")
_END = r"(?=[\s,.।]|$)"          # no \b: Python treats Bangla vowel signs as non-word characters
_DATE_RES = [re.compile(rf"^\s*\d{{1,2}}(st|nd|rd|th)?\s+(de\s+)?({_EN_MONTHS}|{_ES_MONTHS}){_END}", re.I),
             re.compile(rf"^\s*({_EN_MONTHS})\s+\d{{1,2}}(st|nd|rd|th)?{_END}", re.I),
             re.compile(nfc(rf"^\s*[০-৯]{{1,2}}\S*\s+({_BN_MONTHS}){_END}"))]


def date_like(label: str) -> bool:
    """True if a label reads as a calendar date in English or Bangla ("5 May", "May 5", "5 de Mayo", "৫ই মে"); REQ-009 item 2
    (G1 round 1 rejected BN-P17-0103 "৫ই মে", the Mexican town 5 de Mayo, as a date)."""
    s = nfc(label)
    return any(r.search(s) for r in _DATE_RES)


# REQ-009 item 4: English names of states and similar territories that take "the" ("the United States"). Applied only
# where a state is expected in the frame: P36 subjects, P17 objects, P19 objects (G1 round 1, EN-P17-0226).
_THE_EXACT = {"united states", "united states of america", "united kingdom", "united kingdom of great britain and ireland",
              "united arab emirates", "united mexican states", "united provinces", "netherlands", "philippines", "bahamas",
              "gambia", "maldives", "comoros", "seychelles", "gaza strip", "west bank", "holy see", "soviet union",
              "european union"}
# no " union" suffix: Bangladeshi union parishads ("Prithimpassa Union") take no article (trial build, 2026-10-14)
_THE_SUFFIX = (" empire", " republic", " kingdom", " islands", " isles", " federation", " emirates",
               " confederation", " raj", " presidency", " protectorate", " mandate", " caliphate", " sultanate", " khanate",
               " commonwealth", " territories")
# "Kingdom of Italy", "Province of Rome", "Isle of Man", "Republic of the Congo"; proper names without "the" excepted
_OF_NAME = re.compile(r"^[A-Z][\w'’.-]*( [A-Z][\w'’.-]*)* of (the )?[A-Z]")
_NO_THE = {"port of spain"}


def with_the(label: str) -> str:
    """English label with "the" where the name takes it; others unchanged ("France", "The Gambia" stay as they are)."""
    low = label.lower()
    if low.startswith("the ") or low in _NO_THE:
        return label
    if low in _THE_EXACT or low.endswith(_THE_SUFFIX) or _OF_NAME.match(label):
        return "the " + label
    return label


THE_SLOTS = {"P36": ("S",), "P17": ("O",), "P19": ("O",)}


def mention_counts(language: str) -> Counter:
    c = Counter()
    for d in read_jsonl(CORPORA / f"{language}_seed.jsonl"):
        c.update(set(words(d["text"].lower())))
    return c


def _freq(label: str, counts: Counter) -> int:
    """Subject mention frequency = min document count over the label's words (no stemming; Bangla case clitics make
    inflected mentions separate types, so BN counts are conservative; strata are relative ranks within the language)."""
    ws = words(label.lower())
    return min((counts.get(w, 0) for w in ws), default=0) if ws else 0


def _select(cfg: dict) -> dict | None:
    """Paired design (reviewer fix 2026-10-12): the pool is the set of Wikidata triples whose subject is mentioned (>= 1
    document) in BOTH seed corpora; each language stratifies that shared pool by its own mention counts. One probe per
    subject per language; distractors are objects of the same relation that are NOT a true object of that subject.
    Deterministic. Returns the probes plus what repair() needs to reproduce them: each stratum's shuffled list and how far
    it was used, the raw (article-free) labels of every probe, the distractor candidates and the true-object labels."""
    rnd = random.Random(cfg["seed"])
    triples = list(read_jsonl(PROBES / "wikidata_triples.jsonl"))
    n_per = cfg["probes"]["n_per_stratum"]
    counts = {"EN": mention_counts("EN"), "BN": mention_counts("BN")}
    keys = {"EN": ("sLabelEn", "oLabelEn", "en"), "BN": ("sLabelBn", "oLabelBn", "bn")}
    # true objects per (subject URI, relation) and the shared eligible pool
    truth: dict[tuple, set] = {}
    for t in triples:
        truth.setdefault((t.get("s"), t["relation"]), set()).update({t.get("oLabelEn", ""), t.get("oLabelBn", "")})
    # every true object of the subject from Wikidata (fetch_truth), not only the sampled triple(s); fatal if missing, so a
    # build can never silently fall back to the incomplete exclusion
    if not TRUTH.exists():
        raise SystemExit("run --truth first: the distractor rule needs all true objects of every pool subject")
    n_extra = 0
    for t in read_jsonl(TRUTH):
        key = (t.get("s"), t["relation"]); before = len(truth.get(key, set()))
        truth.setdefault(key, set()).update({x for x in (t.get("oLabelEn"), t.get("oLabelBn")) if x})
        n_extra += len(truth[key]) - before
    print(f"[truth] {n_extra} extra true object labels added to the exclusion sets", flush=True)
    # REQ-009 (authors' approval after G1 round 1, 2026-10-14): P17 subjects must be located things (coordinate location,
    # no event date, label not a date); P19 objects must be places with a country. Fatal if the facts were not fetched.
    if not FILTERS.exists():
        raise SystemExit("run --filters first: the REQ-009 probe filters need Wikidata facts on P17 subjects and P19 objects")
    flt = json.load(open(FILTERS, encoding="utf-8"))
    s_located, s_dated, o_in_country = set(flt["P17_subject_has_P625"]), set(flt["P17_subject_has_P585_or_P580"]), set(flt["P19_object_has_P17"])

    def keep(t: dict) -> bool:
        if t["relation"] == "P17":
            return (t.get("s") in s_located and t.get("s") not in s_dated
                    and not date_like(t.get("sLabelEn", "")) and not date_like(t.get("sLabelBn", "")))
        if t["relation"] == "P19":
            return t.get("o") in o_in_country
        return True

    dropped = Counter(t["relation"] for t in triples if not keep(t))
    print(f"[filters] triples dropped by the REQ-009 filters: {dict(dropped)} of {dict(Counter(t['relation'] for t in triples))}", flush=True)
    pool = []
    for t in triples:
        if not keep(t):
            continue
        ok = True
        for lang, (ks, ko, _) in keys.items():
            s, o = t.get(ks, ""), t.get(ko, "")
            if not s or not o or s == o or _freq(s, counts[lang]) < 1:
                ok = False; break
        if ok:
            pool.append(t)
    if not pool:
        print("no triples eligible in both languages; fetch first or check labels"); return None
    # one triple per subject (URI, and also per surface label in either language, so homonymous entities cannot give two
    # probes with the same cloze subject); deterministic: seeded shuffle, first wins
    rnd.shuffle(pool); seen: set = set(); shared = []
    for t in pool:
        keys_t = {("uri", t.get("s")), ("en", t.get("sLabelEn", "").lower()), ("bn", t.get("sLabelBn", ""))}
        if keys_t & seen:
            continue
        seen |= keys_t; shared.append(t)
    print(f"[pool] {len(pool)} triples eligible in both languages, {len(shared)} distinct subjects")
    out = {"n_per": n_per, "truth": truth, "triples": triples, "dropped": dropped, "langs": {}}
    for lang, (ks, ko, tkey) in keys.items():
        objs_by_rel: dict[str, set] = {}
        for t in triples:
            if t.get(ko) and (t["relation"] != "P19" or t.get("o") in o_in_country):   # REQ-009: no "Earth" as a distractor either
                objs_by_rel.setdefault(t["relation"], set()).add(t[ko])
        items = [{"subject": t[ks], "gold": t[ko], "s_uri": t.get("s"), "o_uri": t.get("o"), "relation": t["relation"],
                  "freq": _freq(t[ks], counts[lang]), "freq_other": _freq(t[keys["BN" if lang == "EN" else "EN"][0]], counts["BN" if lang == "EN" else "EN"])}
                 for t in shared]
        items.sort(key=lambda p: (-p["freq"], p["s_uri"] or ""))
        n = len(items); head, mid, tail = items[: n // 10], items[n // 10: n // 2], items[n // 2:]
        probes, raw, strata_lists = [], [], []
        for stratum, lst in (("HEAD", head), ("MID", mid), ("TAIL", tail)):
            rnd.shuffle(lst)
            used = len(lst)
            for i, p in enumerate(lst):
                if sum(1 for q in probes if q["stratum"] == stratum) >= n_per:
                    used = i
                    break
                true_objs = truth.get((p["s_uri"], p["relation"]), set()) | {p["gold"]}
                cands = sorted(o for o in objs_by_rel.get(p["relation"], set()) if o not in true_objs and o != p["subject"])
                if len(cands) < 3:
                    continue
                distractors = rnd.sample(cands, 3)
                tpl = cfg["probes"]["relations"][p["relation"]][tkey]
                subject, gold, dists = p["subject"], p["gold"], distractors
                if lang == "EN":     # REQ-009 item 4: "the United States"; candidates were chosen on the Wikidata labels above
                    slots = THE_SLOTS.get(p["relation"], ())
                    if "S" in slots:
                        subject = with_the(subject)
                    if "O" in slots:
                        gold, dists = with_the(gold), [with_the(d) for d in distractors]
                rec = {"probe_id": f"{lang}-{p['relation']}-{len(probes):04d}", "language": lang, "relation": p["relation"], "stratum": stratum,
                       "subject": subject, "template": tpl, "gold": gold, "distractors": dists, "subject_freq": p["freq"],
                       "subject_freq_other_language": p["freq_other"], "wikidata_subject": p["s_uri"], "wikidata_object": p["o_uri"],
                       "source": "wikidata", "verification": "pending", "created": now_iso()}
                if (subject, gold, dists) != (p["subject"], p["gold"], distractors):
                    rec["article_added"] = True
                probes.append(rec)
                raw.append({"item": p, "distractors": distractors, "cands": cands})
            strata_lists.append((stratum, lst, used))
        out["langs"][lang] = {"probes": probes, "raw": raw, "strata": strata_lists, "objs_by_rel": objs_by_rel, "tkey": tkey}
    return out


def build(cfg: dict) -> None:
    """Build and write the probe sets (selection in _select)."""
    sel = _select(cfg)
    if sel is None:
        return
    n_per, dropped = sel["n_per"], sel["dropped"]
    for lang, L in sel["langs"].items():
        probes = L["probes"]
        write_jsonl(PROBES / f"{lang}_tail_facts.jsonl", probes)
        strata = Counter(p["stratum"] for p in probes)
        print(f"[{lang}] wrote {len(probes)} probes {dict(strata)}; HUMAN: {n_per} per stratum expected, fewer means too few distractor candidates")
    log_decision("built tail-fact probe sets (paired pool, subject-deduplicated, distractors exclude true objects; REQ-009 filters: "
                 f"P17 subjects located and not dated, P19 objects with a country, 'the' for English state names; dropped {dict(dropped)})")


# ---- G1 round 2 repair (REQ-012). The round-2 sets are kept; only probes that the authors rejected or that break a
# REQ-012 rule change. A dropped probe's slot takes the next eligible subject of the same stratum (the order build()
# would have continued in), with its own random stream, so every other probe stays exactly as the authors read it.
ROUND2 = PROBES / "round2_2026-10-14"        # the probe sets and spot-check samples of G1 round 2, as filed in REQ-010
REPAIR_LOG = "repair_round2.json"
G1_ROUND2_REJECTED = {                        # signoffs/G1_spotcheck_round2_reply_2026-10-14.txt
    "EN-P17-0056": "authors, G1 round 2: missing 'The' before 'Metropolitan line'",
    "EN-P19-0491": "authors, G1 round 2: the gold needs 'the 2nd arrondissement of Lyon'",
    "EN-P19-0353": "authors, G1 round 2: wrong option 1 needs 'the 2nd arrondissement of Lyon'",
    "EN-P106-0543": "authors, G1 round 2: wrong option 'lawyer' is also true of Narendra Deva",
    "EN-P19-0166": "authors, G1 round 2: wrong option 2 needs 'the 15th arrondissement of Paris'",
    "EN-P17-0349": "authors, G1 round 2: Quebec Sign Language is a language, not a place",
    "EN-P106-0327": "authors, G1 round 2: wrong option 'actor' is also true of a 'film actor'",
    "BN-P17-0221": "authors, G1 round 2: La Route du Rock is a festival",
    "BN-P106-0462": "authors, G1 round 2: wrong option 'postdoctoral researcher' is also true of Rodney Robert Porter",
    "BN-P17-0048": "authors, G1 round 2: 'the geography of Canada' is a topic, not a place",
}
# Spanish ordinal dates that date_like() misses ("1ro. de Enero"); REQ-009's "a name that is not a date", completed
_DATE_ORD_ES = re.compile(rf"^\s*\d{{1,2}}\s*(ro|er|do|to|vo|no|º|°)\.?\s+de\s+({_ES_MONTHS}){_END}", re.I)
_ORDINAL = re.compile(r"^\d+(st|nd|rd|th) ")                 # "2nd arrondissement of Lyon" (G1 round 2)
THE_SLOTS_R2 = {"P36": ("S",), "P17": ("S", "O"), "P19": ("O",)}


def with_the_r2(label: str) -> str:
    """with_the() plus place names that begin with an ordinal ("the 2nd arrondissement of Lyon"); REQ-012 item 5."""
    if _ORDINAL.match(label):
        return "the " + label
    return with_the(label)


def _texts(lang: str, rel: str, tpl: str, subject: str, gold: str, dists: list) -> tuple:
    """Surface labels of a probe under REQ-012 item 5: English "the" in the state/place slots, now also P17 subjects,
    with "The" when the subject opens the sentence. Bangla labels are unchanged."""
    dists = list(dists)
    if lang != "EN":
        return subject, gold, dists
    slots = THE_SLOTS_R2.get(rel, ())
    if "S" in slots:
        subject = with_the_r2(subject)
        if tpl.startswith("{S}") and subject.startswith("the "):
            subject = "The " + subject[4:]
    if "O" in slots:
        gold, dists = with_the_r2(gold), [with_the_r2(d) for d in dists]
    return subject, gold, dists


class _Rules:
    """REQ-012 rules on the Wikidata facts of --filters-r2 (data/probes/wikidata_filters_r2.json)."""

    def __init__(self, sel: dict):
        f2 = json.load(open(FILTERS_R2, encoding="utf-8"))
        self.q = q = lambda u: (u or "").rsplit("/", 1)[-1]
        self.place = {q(u) for u in f2["P17_subject_settlement_or_admin"]}
        self.state = {q(u) for u in f2["P17_object_current_state"]}
        dep = set(f2["dependent_territories"])
        self.in_dep = {k for k, v in f2["P17_subject_admin_ancestors"].items() if dep & set(v)}
        self.cty19 = {k: set(v) for k, v in f2["P19_object_countries"].items()}
        self.adm19 = {k: set(v) for k, v in f2["P19_object_admin_ancestors"].items()}
        self.anc = {k: set(v) for k, v in f2["P106_object_ancestors"].items()}
        self.par = {k: set(v) for k, v in f2["P106_object_parents"].items()}
        self.hom = {"EN": f2["P17_homonym_countries_en"], "BN": f2["P17_homonym_countries_bn"]}
        self.true_ids: dict = defaultdict(set)                       # (subject id, relation) -> object ids
        self.lab2id = {"EN": defaultdict(set), "BN": defaultdict(set)}   # (relation, label) -> object ids
        for t in sel["triples"] + list(read_jsonl(TRUTH)):
            self.true_ids[(q(t["s"]), t["relation"])].add(q(t["o"]))
            for lang, k in (("EN", "oLabelEn"), ("BN", "oLabelBn")):
                if t.get(k):
                    self.lab2id[lang][(t["relation"], t[k])].add(q(t["o"]))
        self.s_labels = {q(t["s"]): (t.get("sLabelEn", ""), t.get("sLabelBn", "")) for t in sel["triples"]}
        self.pool106 = {q(t["o"]) for t in sel["triples"] if t["relation"] == "P106"}

    def subject_reasons(self, p: dict) -> list:
        """Why a probe item (subject and gold) is not allowed; empty if it is (items 1, 2 and 6)."""
        if p["relation"] == "P36":
            n_cap = len(self.true_ids[(self.q(p["s_uri"]), "P36")])
            # historical states list every capital they had ("the Portuguese Empire" -> Lisbon, Rio de Janeiro), and the
            # sampled one can be the minor one, which reads as false in "The capital of X is Y."
            return [] if n_cap == 1 else [f"REQ-012 item 6: the P36 subject has {n_cap} capitals in Wikidata, not one"]
        if p["relation"] != "P17":
            return []
        s, o, why = self.q(p["s_uri"]), self.q(p["o_uri"]), []
        if s not in self.place:
            why.append("REQ-012 item 1: the P17 subject is not a settlement or an administrative area")
        if s in self.in_dep:
            why.append("REQ-012 item 1: the P17 subject is, or lies in, a dependent territory")
        n_cur = len(self.true_ids[(s, "P17")] & self.state)
        if n_cur != 1:
            why.append(f"REQ-012 item 1: the P17 subject has {n_cur} current countries, not one")
        if any(_DATE_ORD_ES.search(nfc(x)) for x in self.s_labels.get(s, ("", ""))):
            why.append("REQ-012 item 1: the P17 subject's name reads as a date")
        if o not in self.state:
            why.append("REQ-012 item 2: the P17 answer is not a current sovereign state")
        return why

    def option_reason(self, lang: str, p: dict, label: str) -> str | None:
        """Why a wrong option is not allowed for this probe item; None if it is (items 2, 3 and 4)."""
        rel, s = p["relation"], self.q(p["s_uri"])
        ids = self.lab2id[lang].get((rel, label), set())
        trues = self.true_ids[(s, rel)] | {self.q(p["o_uri"])}
        if rel == "P17":
            if not ids & self.state:
                return "REQ-012 item 2: the option is not a current sovereign state"
            en, bn = self.s_labels.get(s, ("", ""))
            if ids & (set(self.hom["EN"].get(en, [])) | set(self.hom["BN"].get(bn, []))):
                return "REQ-012 item 2: the option is the country of another place with the same name"
        if rel == "P19":
            up = lambda x: self.adm19.get(x, set()) | self.cty19.get(x, set()) | {x}
            if any(d in up(t) or t in up(d) for d in ids for t in trues):
                return "REQ-012 item 3: the option contains, or lies in, a true birthplace"
        if rel == "P106":
            above = set().union(*[self.anc.get(t, {t}) for t in trues])
            for d in ids:
                if d in above or any(t in self.anc.get(d, {d}) for t in trues):
                    return "REQ-012 item 4: the option is a broader or narrower occupation of a true one"
                if self.par.get(d, set()) & above & self.pool106:
                    return "REQ-012 item 4: the option is a kind of an occupation the subject has or falls under"
        return None


def repair(cfg: dict, out_dir: Path) -> None:
    """REQ-012 (proposed after G1 round 2): reproduce the round-2 selection exactly (fatal if it differs from the files in
    data/probes/round2_2026-10-14/), then (a) replace every probe the authors rejected in round 2 and every probe whose
    subject or answer breaks items 1, 2 or 6, (b) re-draw only the wrong options that break items 2-4, keeping the others,
    (c) apply the item-5 "the" rules to the text. Writes {EN,BN}_tail_facts.jsonl and repair_round2.json to out_dir."""
    if not (ROUND2 / "EN_tail_facts.jsonl").exists():
        raise SystemExit(f"[FAIL] {ROUND2} missing: archive the round-2 probe files first")
    if not FILTERS_R2.exists():
        raise SystemExit("run --filters-r2 first: the REQ-012 rules need its Wikidata facts")
    sel = _select(cfg)
    rules, seed = _Rules(sel), cfg["seed"]
    key = lambda r: (r["probe_id"], r["stratum"], r["relation"], r["subject"], r["gold"], tuple(r["distractors"]), r["template"],
                     r["wikidata_subject"], r["wikidata_object"])
    log = {"rule": "REQ-012 (signoffs/REQUESTS.md), after G1 round 2", "at": now_iso(), "rejected_round2": G1_ROUND2_REJECTED, "changes": []}
    out_dir.mkdir(parents=True, exist_ok=True)
    for lang, L in sel["langs"].items():
        arch = list(read_jsonl(ROUND2 / f"{lang}_tail_facts.jsonl"))
        if [key(r) for r in L["probes"]] != [key(r) for r in arch]:
            raise SystemExit(f"[FAIL] {lang}: the selection no longer reproduces the round-2 probes (inputs changed?); nothing written")
        new: list = []
        drop: list = []                     # (position, round-2 record, reasons)
        n_redrawn = n_article = 0
        for pos, (rec, rw) in enumerate(zip(arch, L["raw"])):
            p, rel = rw["item"], rec["relation"]
            why = ([G1_ROUND2_REJECTED[rec["probe_id"]]] if rec["probe_id"] in G1_ROUND2_REJECTED else []) + rules.subject_reasons(p)
            dists = list(rw["distractors"])
            bad = [(i, r) for i, d in enumerate(dists) for r in [rules.option_reason(lang, p, d)] if r]
            valid = [c for c in rw["cands"] if c not in dists and not rules.option_reason(lang, p, c)] if bad else []
            if bad and len(valid) < len(bad):
                why.append("too few allowed wrong options to re-draw")
            if why:
                new.append(None); drop.append((pos, rec, why)); continue
            redrawn = []
            if bad:
                picks = random.Random(f"{seed}:{rec['probe_id']}:redraw").sample(valid, len(bad))
                for (i, r), c in zip(bad, picks):
                    redrawn.append({"option": i + 1, "old": dists[i], "new": c, "reason": r})
                    dists[i] = c
            article = _texts(lang, rel, rec["template"], p["subject"], p["gold"], rw["distractors"]) != (rec["subject"], rec["gold"], rec["distractors"])
            subj, gold, ds = _texts(lang, rel, rec["template"], p["subject"], p["gold"], dists)
            r2 = dict(rec, subject=subj, gold=gold, distractors=ds)
            if redrawn or article:
                r2["repair"] = {"round": "G1 round 2 (REQ-012)", "options_redrawn": redrawn, "article_rule": article}
                if article:
                    r2["article_added"] = True
                n_redrawn += bool(redrawn); n_article += article
                log["changes"].append({"language": lang, "position": pos, "old_id": rec["probe_id"], "new_id": rec["probe_id"],
                                       "action": "options re-drawn" if redrawn else "text ('the')", "options_redrawn": redrawn,
                                       "article_rule": article, "old": [rec["subject"], rec["gold"], rec["distractors"]], "new": [subj, gold, ds]})
            new.append(r2)
        # fill the dropped slots, stratum by stratum, from where build() stopped in that stratum's shuffled list
        for stratum, lst, used in L["strata"]:
            k = used
            for pos, rec, why in [d for d in drop if d[1]["stratum"] == stratum]:
                while True:
                    if k >= len(lst):
                        raise SystemExit(f"[FAIL] {lang} {stratum}: no eligible subject left to replace {rec['probe_id']}")
                    p = lst[k]; k += 1
                    if rules.subject_reasons(p):
                        continue
                    true_objs = sel["truth"].get((p["s_uri"], p["relation"]), set()) | {p["gold"]}
                    cands = sorted(o for o in L["objs_by_rel"].get(p["relation"], set()) if o not in true_objs and o != p["subject"])
                    valid = [c for c in cands if not rules.option_reason(lang, p, c)]
                    if len(valid) < 3:
                        continue
                    dists = random.Random(f"{seed}:{lang}:{pos}:fill").sample(valid, 3)
                    tpl = cfg["probes"]["relations"][p["relation"]][L["tkey"]]
                    subj, gold, ds = _texts(lang, p["relation"], tpl, p["subject"], p["gold"], dists)
                    r2 = {"probe_id": f"{lang}-{p['relation']}-{pos:04d}", "language": lang, "relation": p["relation"], "stratum": stratum,
                          "subject": subj, "template": tpl, "gold": gold, "distractors": ds, "subject_freq": p["freq"],
                          "subject_freq_other_language": p["freq_other"], "wikidata_subject": p["s_uri"], "wikidata_object": p["o_uri"],
                          "source": "wikidata", "verification": "pending", "created": now_iso(),
                          "repair": {"round": "G1 round 2 (REQ-012)", "replaces": rec["probe_id"], "reasons": why}}
                    if (subj, gold, ds) != (p["subject"], p["gold"], dists):
                        r2["article_added"] = True
                    new[pos] = r2
                    log["changes"].append({"language": lang, "position": pos, "old_id": rec["probe_id"], "new_id": r2["probe_id"],
                                           "action": "replaced", "reasons": why, "old": [rec["subject"], rec["gold"], rec["distractors"]],
                                           "new": [subj, gold, ds]})
                    break
        assert all(r is not None for r in new) and len(new) == len(arch)
        write_jsonl(out_dir / f"{lang}_tail_facts.jsonl", new)
        rel_old, rel_new = Counter(r["relation"] for r in arch), Counter(r["relation"] for r in new)
        reasons = Counter(w for _, _, ws in drop for w in ws)
        reasons.update(r["reason"] for c in log["changes"] if c["language"] == lang for r in c.get("options_redrawn", []))
        log.setdefault("summary", {})[lang] = {"replaced": len(drop), "with_options_redrawn": n_redrawn, "with_the_change": n_article,
                                               "relations_round2": dict(rel_old), "relations_repaired": dict(rel_new),
                                               "reasons": dict(reasons.most_common())}
        print(f"[{lang}] repaired: {len(drop)} replaced, {n_redrawn} with re-drawn options, {n_article} with a 'the' change; "
              f"relations {dict(rel_old)} -> {dict(rel_new)}", flush=True)
    write_json(out_dir / REPAIR_LOG, log)
    print(f"[repair] written to {out_dir}", flush=True)


def archive_round2() -> None:
    """Copy the round-2 probe sets and spot-check samples (as filed in REQ-010) to data/probes/round2_2026-10-14/."""
    import shutil
    names = ["EN_tail_facts.jsonl", "BN_tail_facts.jsonl", "spotcheck_EN.csv", "spotcheck_BN.csv"]
    ROUND2.mkdir(parents=True, exist_ok=True)
    for n in names:
        src, dst = PROBES / n, ROUND2 / n
        if dst.exists():
            if dst.read_bytes() != src.read_bytes():
                raise SystemExit(f"[FAIL] {dst} exists and differs from {src}; the archive is never overwritten")
            continue
        shutil.copy2(src, dst)
    print(f"[archive] round-2 files in {ROUND2}: {names}")


def _change_note(p: dict) -> str:
    r = p.get("repair")
    if not r:
        return ""
    if r.get("replaces"):
        return f"new probe; replaces {r['replaces']}"
    parts = [f"wrong option {x['option']} re-drawn (was: {x['old']})" for x in r.get("options_redrawn", [])]
    if r.get("article_rule"):
        parts.append("'the' added")
    return "; ".join(parts)


def spotcheck_round3(cfg: dict, src: Path) -> None:
    """G1 round 3 sample (REQ-012): 60 English probes from the repaired set that the authors have not read (not in the
    round-2 sample), and, for information, 20 changed Bangla probes (the replacements of the 3 round-2 rejects first).
    Writes spotcheck_round3_{EN,BN}.csv next to the probe files in `src`."""
    with open(ROUND2 / "spotcheck_EN.csv", encoding="utf-8", newline="") as f:
        seen = {row[0] for row in csv.reader(f)}
    en = list(read_jsonl(src / "EN_tail_facts.jsonl"))
    sample = {"EN": random.Random(cfg["seed"] + 3).sample([p for p in en if p["probe_id"] not in seen], 60)}
    bn = [p for p in read_jsonl(src / "BN_tail_facts.jsonl") if p.get("repair")]
    first = [p for p in bn if p["repair"].get("replaces") in G1_ROUND2_REJECTED]
    rest = [p for p in bn if p["repair"].get("replaces") not in G1_ROUND2_REJECTED]
    sample["BN"] = first + random.Random(cfg["seed"] + 4).sample(rest, min(20 - len(first), len(rest)))
    for lang, ps in sample.items():
        with open(src / f"spotcheck_round3_{lang}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["probe_id", "stratum", "sentence_with_gold", "distractor_sentence_1", "distractor_sentence_2", "distractor_sentence_3",
                        "verdict (ok/reject)", "note", "change since round 2 (agent)"])
            for p in ps:
                ds = [p["template"].format(S=p["subject"], O=d) for d in p["distractors"]]
                w.writerow([p["probe_id"], p["stratum"], p["template"].format(S=p["subject"], O=p["gold"]), *ds, "", "", _change_note(p)])
        print(f"[{lang}] round-3 spot-check CSV written ({len(ps)} probes) to {src}")


# Pairs the authors rejected at G1 round 1 (2026-10-14), excluded under REQ-009 item 6. Pair ids are source row indices,
# so the remaining pairs keep their ids.
BIAS_REJECTED = {
    "EN-B0646": "authors, G1 round 1: ungrammatical ('Nia is White person')",
    "BN-B0128": "authors, G1 round 1: incorrect case endings ('কুঁড়ে ঘর এ', 'বাড়ি এ')",
    "BN-B1124": "authors, G1 round 1: broken relative clause",
    "BN-B0314": "authors, G1 round 1: garbled occupation label ('পরিবহন সেবা উপস্থিতি')",
    "BN-B0840": "authors, G1 round 1: incorrect 'স্বাগত জায়গা'; agent check: the negation ('not as ... as you have heard') reverses the stereotype direction",
}
_DETACHED_CASE = re.compile(nfc(r"\S\s+(এ|তে|য়)(?=[\s।,?!]|$)"))   # a case ending written as its own word, the BN-B0128 defect


def bias(cfg: dict, from_dir: str | None = None) -> None:
    """Convert the bias sources to the common format and apply the REQ-009 exclusions. With `from_dir`, the input is an
    earlier conversion ({lang}_bias.jsonl, e.g. data/probes/round1_2026-10-13) instead of data/sources. Its pair ids must
    be the contiguous source row indices, so the output is the same as converting the sources (2026-10-14: the sources
    stayed on a host whose GPU was taken)."""
    excluded = []
    for lang, lcfg in cfg["languages"].items():
        if from_dir:
            p = Path(from_dir) / f"{lang}_bias.jsonl"
            conv = list(read_jsonl(p))
            if [r["pair_id"] for r in conv] != [f"{lang}-B{i:04d}" for i in range(len(conv))]:
                raise SystemExit(f"[FAIL] {p}: pair ids are not the contiguous source indices; convert from data/sources instead")
            rows = [{"pair_id": r["pair_id"], "language": lang, "stereo": r["stereo"], "anti": r["anti"], "source": r["source"], "licence": r["licence"]} for r in conv]
        else:
            p = ROOT / lcfg["bias_pairs"]["file"]
            if not p.exists():
                print(f"[{lang}] bias file missing: {p}"); continue
            rows = [{"pair_id": f"{lang}-B{i:04d}", "language": lang, "stereo": r["stereo"], "anti": r["anti"], "source": p.name, "licence": lcfg["bias_pairs"]["licence"]}
                    for i, r in enumerate(read_jsonl(p)) if r.get("stereo") and r.get("anti")]
        missing = [k for k in BIAS_REJECTED if k.startswith(lang + "-") and k not in {r["pair_id"] for r in rows}]
        if missing:
            raise SystemExit(f"[FAIL] rejected bias pairs not found in {p.name}: {missing} (source changed?)")
        out = []
        for r in rows:
            why = BIAS_REJECTED.get(r["pair_id"])
            if why is None and lang == "BN" and _DETACHED_CASE.search(nfc(r["stereo"] + " | " + r["anti"])):
                why = "agent, REQ-009 item 6: a case ending written as a separate word (the BN-B0128 defect)"
            if why:
                excluded.append({"pair_id": r["pair_id"], "reason": why})   # ids only: BanStereoSet text is not copied (REQ-005)
            else:
                out.append(r)
        write_jsonl(PROBES / f"{lang}_bias.jsonl", out)
        print(f"[{lang}] wrote {len(out)} bias pairs ({len(rows) - len(out)} excluded)")
    write_json(PROBES / "bias_exclusions.json", {"rule": "REQ-009 item 6 (signoffs/REQUESTS.md), approved 2026-10-14", "at": now_iso(),
                                                 "n_excluded": len(excluded), "excluded": excluded})
    log_decision(f"bias pairs converted; {len(excluded)} excluded under REQ-009 item 6 (data/probes/bias_exclusions.json)")


def spotcheck(cfg: dict, bias_sample: bool = True) -> None:
    rnd = random.Random(cfg["seed"] + 1)
    for lang in ("EN", "BN"):
        probes = list(read_jsonl(PROBES / f"{lang}_tail_facts.jsonl"))
        sample = rnd.sample(probes, min(60, len(probes)))
        with open(PROBES / f"spotcheck_{lang}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["probe_id", "stratum", "sentence_with_gold", "distractor_sentence_1", "distractor_sentence_2", "distractor_sentence_3",
                        "verdict (ok/reject)", "note (reject if the gold sentence is false or ungrammatical, OR if any distractor sentence is TRUE or ungrammatical in a way the gold is not)"])
            for p in sample:
                ds = [p["template"].format(S=p["subject"], O=d) for d in p["distractors"]]
                w.writerow([p["probe_id"], p["stratum"], p["template"].format(S=p["subject"], O=p["gold"]), *ds, "", ""])
        print(f"[{lang}] spot-check CSV written ({len(sample)} probes)")
    # bias pairs: 30 per language for the Gate 1 read (06_HUMAN_TASKS.md); own random stream, so the probe samples above are
    # unchanged; it checks the conversion (BLANK filled, stereo/anti not swapped, readable text), added 2026-10-13
    if not bias_sample:
        print("bias spot-check CSVs not rewritten (--probes-only)"); return
    rb = random.Random(cfg["seed"] + 2)
    for lang in ("EN", "BN"):
        pairs = list(read_jsonl(PROBES / f"{lang}_bias.jsonl"))
        if not pairs:
            print(f"[{lang}] no bias pairs yet (run --bias first); bias spot-check CSV not written"); continue
        sample = rb.sample(pairs, min(30, len(pairs)))
        with open(PROBES / f"spotcheck_bias_{lang}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["pair_id", "stereotype_sentence", "anti_stereotype_sentence", "verdict (ok/reject)",
                        "note (e.g. garbled or ungrammatical sentence, BLANK not filled, stereotype and anti-stereotype swapped)"])
            for p in sample:
                w.writerow([p["pair_id"], p["stereo"], p["anti"], "", ""])
        print(f"[{lang}] bias spot-check CSV written ({len(sample)} pairs)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true"); ap.add_argument("--build", action="store_true"); ap.add_argument("--bias", action="store_true"); ap.add_argument("--spotcheck-csv", action="store_true")
    ap.add_argument("--truth", action="store_true", help="fetch all true objects of the pool subjects (needed by --build; run after --fetch)")
    ap.add_argument("--filters", action="store_true", help="fetch the Wikidata facts for the REQ-009 filters (needed by --build)")
    ap.add_argument("--filters-r2", action="store_true", help="fetch the Wikidata facts for the rules proposed after G1 round 2 (REQ-012)")
    ap.add_argument("--archive-round2", action="store_true", help="copy the round-2 probe files to data/probes/round2_2026-10-14/")
    ap.add_argument("--repair-round2", metavar="OUT_DIR", help="REQ-012 repair of the round-2 sets, written to OUT_DIR")
    ap.add_argument("--spotcheck-round3", metavar="DIR", help="write the round-3 spot-check CSVs from the repaired sets in DIR")
    ap.add_argument("--probes-only", action="store_true", help="with --spotcheck-csv: write the probe samples only (G1 round 2)")
    ap.add_argument("--bias-from", help="with --bias: convert from an earlier conversion in this directory instead of data/sources")
    a = ap.parse_args(); cfg = load_corpora_cfg()
    PROBES.mkdir(parents=True, exist_ok=True)
    if a.fetch:
        fetch(cfg)
    if a.fetch or a.truth:
        fetch_truth(cfg)
    if a.fetch or a.filters:
        fetch_filters(cfg)
    if a.filters_r2:
        fetch_filters_r2(cfg)
    if a.archive_round2:
        archive_round2()
    if a.repair_round2:
        repair(cfg, Path(a.repair_round2) if Path(a.repair_round2).is_absolute() else ROOT / a.repair_round2)
    if a.spotcheck_round3:
        spotcheck_round3(cfg, Path(a.spotcheck_round3) if Path(a.spotcheck_round3).is_absolute() else ROOT / a.spotcheck_round3)
    if a.build:
        build(cfg)
    if a.bias:
        bias(cfg, from_dir=a.bias_from)
    if a.spotcheck_csv:
        spotcheck(cfg, bias_sample=not a.probes_only)
    if not any((a.fetch, a.truth, a.filters, a.filters_r2, a.archive_round2, a.repair_round2, a.spotcheck_round3, a.build, a.bias, a.spotcheck_csv)):
        ap.error("choose --fetch, --truth, --filters, --filters-r2, --archive-round2, --repair-round2, --spotcheck-round3, --build, --bias or --spotcheck-csv")


if __name__ == "__main__":
    main()
