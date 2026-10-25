#!/usr/bin/env python3
"""
Self-contained HTML reading sheet for a Gate 1 probe spot-check round (06_HUMAN_TASKS.md, 02_DATA_SOURCES.md §3).
Reads data/probes/spotcheck_{EN,BN}.csv (written by `build_probes.py --spotcheck-csv --probes-only`) and writes one
HTML file that the authors open in a browser on the VPS. They tick rejects, write reasons, press "Copy reply" and paste
the text into the Claude Code chat. Round 1 (2026-10-13) also had bias pairs; it was made by a session script, and its
sheet is signoffs/G1_spotcheck_2026-10-13.html.

  python harness/make_spotcheck_sheet.py --round 2 --out signoffs/G1_spotcheck_round2_2026-10-14.html
  python harness/make_spotcheck_sheet.py --round 3 --src data/probes/staging_round3 --out signoffs/G1_spotcheck_round3_2026-10-14.html
Round 3 (REQ-012/REQ-013) reads spotcheck_round3_{EN,BN}.csv from --src: 60 English probes the authors have not read and,
for information, 20 changed Bangla probes; the extra CSV column says what changed since round 2.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import html
import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
PROBES = PKG / "data" / "probes"

CHANGES_ROUND2 = [
    "English occupation sentences now read “The occupation of X is listed as Y.” (was “The occupation of X is Y.”).",
    "Country (P17) probes only use things that have a location: map coordinates, no event date, and a name that is not a date. "
    "Topics, year summaries, relations between countries, events and organisations are gone.",
    "Birthplaces (P19) only use places that belong to a country, so “পৃথিবী” (Earth) and similar are gone, also as wrong options.",
    "English state names take “the” where needed: “the United Kingdom”, “the Kingdom of Italy”, “the Isle of Man”.",
    "Bias pairs are not read again. Your 5 rejected pairs, and 8 more Bangla pairs with the same split case ending as BN-B0128, "
    "are removed (data/probes/bias_exclusions.json).",
]


CHANGES_ROUND3 = [
    "Country (P17) probes now use only settlements and administrative areas (towns, cities, districts, provinces). Languages, "
    "festivals, topics, transport lines, roads, stations, ships, rivers and mountains are gone, and so are overseas territories "
    "such as Bermuda and places with more than one country. Wrong options are present-day countries only (no Mandatory "
    "Palestine, no Inca Empire), and never the country of another place with the same name (there is also a Toronto in England).",
    "Birthplace (P19): a wrong option can no longer contain, or lie inside, the true birthplace (no “Banff” when Wikidata only "
    "says “Canada”).",
    "Occupation (P106): a wrong option can no longer be a broader or narrower job than a true one (“actor” for a “film actor”), "
    "or a kind of a job the person already falls under (“postdoctoral researcher” for a biochemist, who is a researcher). "
    "Wikidata can still miss a job (it lists Narendra Deva only as a writer), so a wrong option can still be true now and then: "
    "reject it as before.",
    "Capital (P36): only places with a single capital in Wikidata. Historical states that list several capitals are gone "
    "(“The capital of the Portuguese Empire is Rio de Janeiro.”).",
    "English “the”: place names that start with a number take it (“the 2nd arrondissement of Lyon”), and so do the places in "
    "country probes (“The Northwest Territories is located in …”).",
    "Everything else is exactly as you read it in round 2, and your 10 rejected probes are replaced. Every change is listed in "
    "data/probes/repair_round2.json.",
]


def probe_rows(lang: str, path: Path | None = None) -> list[list[str]]:
    with open(path or PROBES / f"spotcheck_{lang}.csv", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))[1:]


def probe_table(lang: str, rows: list[list[str]] | None = None) -> str:
    body = []
    for i, r in enumerate(rows if rows is not None else probe_rows(lang), 1):
        pid, stratum, gold, d1, d2, d3 = r[:6]
        note = r[8] if len(r) > 8 and r[8] else ""
        chg = f'<div class="chg">{html.escape(note)}</div>' if note else ""
        body.append(f"""<tr data-id="{html.escape(pid)}"><td class="n">{i}</td><td class="id">{html.escape(pid)}<br><span class="st">{html.escape(stratum)}</span></td>
<td><div class="gold">{html.escape(gold)}</div><ol class="dis"><li>{html.escape(d1)}</li><li>{html.escape(d2)}</li><li>{html.escape(d3)}</li></ol>{chg}</td>
<td class="v"><label><input type="checkbox" class="rej"> reject</label><input type="text" class="note" placeholder="reason"></td></tr>""")
    return (f'<table class="t" lang="{"bn" if lang == "BN" else "en"}"><thead><tr><th>#</th><th>probe</th>'
            f'<th>gold sentence (bold) and the three wrong options</th><th>verdict</th></tr></thead><tbody>{"".join(body)}</tbody></table>')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--src", help="round 3: directory with spotcheck_round3_{EN,BN}.csv (default data/probes/staging_round3)")
    a = ap.parse_args()
    if a.round not in (2, 3):
        raise SystemExit("only rounds 2 and 3 are defined here (round 1 had its own sheet); add the round's change list first")
    if a.round == 3:
        src = Path(a.src) if a.src and Path(a.src).is_absolute() else PKG / (a.src or "data/probes/staging_round3")
        rows = {lang: probe_rows(lang, src / f"spotcheck_round3_{lang}.csv") for lang in ("EN", "BN")}
    else:
        rows = {lang: probe_rows(lang) for lang in ("EN", "BN")}
    n_en, n_bn = len(rows["EN"]), len(rows["BN"])
    r3 = a.round == 3
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    changes = "".join(f"<li>{html.escape(x)}</li>" for x in (CHANGES_ROUND3 if r3 else CHANGES_ROUND2))
    look = "third look (English)" if r3 else "second look"
    rule = ("<b>G1 passes when English has at most 3 rejects out of these 60</b>; rejected probes are then replaced. More than 3 means "
            "English is rebuilt again and you get another look. Bangla already passed in round 2 (3 of 60): its 20 rows below are "
            "changed probes, shown for information, and any Bangla row you reject is replaced without another look."
            if r3 else
            "<b>G1 passes when each language has at most 3 rejects out of 60</b>; rejected probes are then replaced. More than 3 in a "
            "language means that language is rebuilt again and you get another look.")
    since = ("since round 2</b> (your round-2 review; REQ-012)" if r3 else "since round 1</b> (your round-1 review, REQ-009 approved 2026-10-14)")
    h_en = f"English probes ({n_en}, not read before)" if r3 else f"English probes ({n_en})"
    h_bn = f"Bangla probes ({n_bn} changed probes, for information)" if r3 else f"Bangla probes ({n_bn})"
    key = f"cg4-g1-spotcheck-round{a.round}-v1"     # new key: probe ids repeat across rounds, old ticks must not carry over
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CG4 Gate 1 Round {a.round}</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#5f5d57; --line:#dedbd2; --card:#ffffff; --accent:#1f5f8b; --gold:#0d5c2e; --warn:#8a3b12; --chip:#eef3f7; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --gold:#7fd39a; --warn:#f0a67a; --chip:#26303a; }} }}
:root[data-theme="dark"] {{ --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --gold:#7fd39a; --warn:#f0a67a; --chip:#26303a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 "Segoe UI", "Nirmala UI", "Noto Sans Bengali", system-ui, sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 80px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:18px; margin:36px 0 8px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
.sub {{ color:var(--muted); margin:0 0 18px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:14px 16px; margin:12px 0; }}
.card ul {{ margin:6px 0 0 18px; padding:0; }}
.rule {{ border-left:3px solid var(--accent); }}
table.t {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); }}
.t th, .t td {{ border-bottom:1px solid var(--line); padding:8px 10px; vertical-align:top; text-align:left; }}
.t th {{ font-size:13px; color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--card); }}
.t td.n {{ color:var(--muted); width:2.5em; }} .t td.id {{ font:12px/1.4 Consolas, monospace; width:9.5em; overflow-wrap:anywhere; }}
.st {{ display:inline-block; margin-top:3px; font:11px "Segoe UI", sans-serif; background:var(--chip); padding:1px 6px; border-radius:9px; }}
.gold {{ font-weight:650; color:var(--gold); }}
ol.dis {{ margin:4px 0 0 20px; padding:0; color:var(--fg); }}
td.v {{ width:11em; }} td.v input.note {{ width:100%; margin-top:4px; font:13px inherit; padding:3px 5px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--fg); }}
tr.rejected td {{ background:color-mix(in srgb, var(--warn) 12%, transparent); }}
.bar {{ position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line); padding:10px 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
.over {{ color:var(--warn); font-weight:650; }}
.chg {{ margin-top:4px; font-size:12px; color:var(--muted); }}
button {{ font:inherit; padding:6px 14px; border-radius:6px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; }}
textarea {{ width:100%; min-height:90px; font:13px Consolas, monospace; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px; }}
@media (max-width:700px) {{ .t td.id {{ width:6.5em; }} td.v {{ width:7.5em; }} }}
</style></head>
<body><main>
<h1>CG4 Gate 1, round {a.round}: probe {look}</h1>
<p class="sub">Reading sheet for the authors, generated {html.escape(generated)} from the rebuilt probe files on the VPS (`data/probes/`). Local file; do not upload or share it.</p>
<div class="card rule"><b>Rule (02_DATA_SOURCES.md §3).</b> Reject a probe if the gold sentence (bold) is false or ungrammatical, <i>or</i> if any wrong option is true or ungrammatical in a way the gold is not. {rule}<br>
<b>How to answer.</b> Tick <i>reject</i> and write a short reason (English or Bangla), press <b>Copy reply</b> at the bottom and paste the text into the Claude Code chat. Ticks are kept in this browser only. Round 1 is in <code>signoffs/G1_spotcheck_2026-10-13.html</code>.</div>
<div class="card"><b>What changed {since}:<ul>{changes}</ul></div>
<h2>{html.escape(h_en)}</h2>{probe_table("EN", rows["EN"])}
<h2>{html.escape(h_bn)}</h2>{probe_table("BN", rows["BN"])}
<h2>Your reply</h2>
<textarea id="reply" readonly></textarea>
</main>
<div class="bar"><button id="copy">Copy reply</button><span id="count" class="sub" style="margin:0"></span></div>
<script>
const KEY = {json.dumps(key)};
const ROUND = {a.round}, NEN = {n_en}, NBN = {n_bn}, BN_INFO = {json.dumps(r3)};
const rows = [...document.querySelectorAll("tr[data-id]")];
function load() {{ try {{ return JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{ return {{}}; }} }}
function save(s) {{ try {{ localStorage.setItem(KEY, JSON.stringify(s)); }} catch (e) {{}} }}
const state = load();
for (const tr of rows) {{
  const id = tr.dataset.id, cb = tr.querySelector(".rej"), nt = tr.querySelector(".note");
  if (state[id]) {{ cb.checked = !!state[id].r; nt.value = state[id].n || ""; }}
  const upd = () => {{ state[id] = {{ r: cb.checked, n: nt.value }}; tr.classList.toggle("rejected", cb.checked); save(state); render(); }};
  cb.addEventListener("change", upd); nt.addEventListener("input", upd); tr.classList.toggle("rejected", cb.checked);
}}
function render() {{
  const rej = rows.filter(tr => tr.querySelector(".rej").checked);
  const lines = rej.map(tr => "reject " + tr.dataset.id + (tr.querySelector(".note").value ? " - " + tr.querySelector(".note").value : ""));
  const by = p => rej.filter(tr => tr.dataset.id.startsWith(p)).length;
  document.getElementById("reply").value = "G1 spot-check round " + ROUND + ": " + (lines.length ? lines.join("; ") : "no rejections") + ". All other rows ok.";
  const en = by("EN-P"), bn = by("BN-P"), mark = n => n > 3 ? `<span class="over">${{n}} (over 3)</span>` : `${{n}}`;
  document.getElementById("count").innerHTML = BN_INFO
    ? `rejected: English ${{mark(en)}} of ${{NEN}} (G1 allows at most 3), Bangla ${{bn}} of ${{NBN}} (information)`
    : `rejected: English ${{mark(en)}} of ${{NEN}}, Bangla ${{mark(bn)}} of ${{NBN}} (G1 allows at most 3 per language)`;
}}
render();
document.getElementById("copy").addEventListener("click", async () => {{
  const t = document.getElementById("reply"); t.select();
  try {{ await navigator.clipboard.writeText(t.value); }} catch (e) {{ document.execCommand("copy"); }}
}});
</script>
</body></html>"""
    out = Path(a.out) if Path(a.out).is_absolute() else PKG / a.out
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page) // 1024} KB; {n_en} EN + {n_bn} BN probes)")


if __name__ == "__main__":
    main()
