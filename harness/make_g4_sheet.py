#!/usr/bin/env python3
"""
Self-contained HTML reading sheet for the Gate 4 read (REQ-021). The automatic G4 checks passed; two measured patterns need
the authors' eyes before they decide the gate:

  A/B  letters of other scripts spreading under REPLACE (exploratory screening, REQ-019): EN-REPLACE and BN-REPLACE gen 6
  C/D  repetition in the top-p 0.95 REPLACE pair: EN-REPLACE-topp95 and BN-REPLACE-topp95 gen 6

Each section shows 10 of the 50 fixed prompts (`results/samples/*_50.jsonl`), generation 0 next to generation 6 for the same
prompt, with the automatic numbers on top. The letters that the screening counts are highlighted with the same definitions as
`harness/tools/screening_check.py`. Rows are drawn with a fixed seed from the samples that show the pattern. The authors tick a
row only for a technical fault, answer the questions, press "Copy reply" and paste the text into the Claude Code chat.

The page holds unscreened synthetic text, so it is written inside results/ (results/human_read/) and must not be shared.

  python harness/make_g4_sheet.py --out results/human_read/G4_read_2026-10-17.html
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import random
import sys
from pathlib import Path

import regex

PKG = Path(__file__).resolve().parents[1]
RES = PKG / "results"
sys.path.insert(0, str(PKG / "harness"))
from common import repeat_4gram_rate, words  # noqa: E402

SEED = 20261017
N_ROWS = 10
# same letter classes as harness/tools/screening_check.py (FOREIGN, LATIN), as runs so a word is marked once
HL = {"EN": regex.compile(r"(?V1)(?P<frn>[\p{L}--\p{Script=Latin}]+)"),
      "BN": regex.compile(r"(?V1)(?P<lat>\p{Script=Latin}+)|(?P<frn>[\p{L}--[\p{Script=Bengali}\p{Script=Latin}]]+)")}
FOREIGN = {"EN": regex.compile(r"(?V1)[\p{L}--\p{Script=Latin}]"), "BN": regex.compile(r"(?V1)[\p{L}--[\p{Script=Bengali}\p{Script=Latin}]]")}
LATIN = regex.compile(r"\p{Script=Latin}")

YES_PARTLY_NO = [("yes", "yes"), ("partly", "partly"), ("no", "no")]
SECTIONS = [
    {"key": "A", "lang": "EN", "chain": "EN-REPLACE", "select": "foreign",
     "title": "A. English: letters of other scripts (EN-REPLACE, generation 6)",
     "what": "Under REPLACE, more English documents contain letters of other scripts (Cyrillic, Arabic, Thai and others) in every generation. "
             "The highlighted runs are exactly what the screening counts. The question is what they are.",
     "cols": [("GEN0-EN", 0, "gen 0"), ("EN-REPLACE", 3, "REPLACE gen 3"), ("EN-REPLACE", 6, "REPLACE gen 6"), ("EN-REPLACE", 10, "REPLACE gen 10"),
              ("EN-ACCUMULATE", 6, "ACCUMULATE gen 6"), ("EN-ACCUMULATE-FILTER", 6, "FILTER gen 6")],
     "nums": [("screen_foreign_letter", "documents with a letter of another script (exploratory)", 3),
              ("screen_foreign_run3", "documents with a run of 3 or more such letters (exploratory)", 3),
              ("script_docs_ge95", "documents at least 95% in Latin script (registered)", 3)],
     "qs": [("qA", "What are the highlighted letters in the generation-6 text mostly?",
             [("pieces", "words or pieces of other languages mixed into the English"), ("belong", "names or terms that belong in the text"),
              ("broken", "broken characters (a technical fault)"), ("unsure", "mixed or unsure")])]},
    {"key": "B", "lang": "BN", "chain": "BN-REPLACE", "select": "latin",
     "title": "B. Bangla: Latin and other-script letters (BN-REPLACE, generation 6)",
     "what": "Under REPLACE, more Bangla documents contain Latin letters in every generation. Latin runs are highlighted in one colour, "
             "letters of a third script (neither Bengali nor Latin) in another. Only a Bangla reader can say whether this is natural Bangla writing or damage.",
     "cols": [("GEN0-BN", 0, "gen 0"), ("BN-REPLACE", 3, "REPLACE gen 3"), ("BN-REPLACE", 6, "REPLACE gen 6"), ("BN-REPLACE", 10, "REPLACE gen 10"),
              ("BN-ACCUMULATE", 6, "ACCUMULATE gen 6"), ("BN-ACCUMULATE-FILTER", 6, "FILTER gen 6")],
     "nums": [("screen_latin_letter", "documents with a Latin letter (exploratory)", 3),
              ("screen_foreign_letter", "documents with a letter of a third script (exploratory)", 3),
              ("script_docs_ge95", "documents at least 95% in Bengali script (registered)", 3)],
     "qs": [("qB", "What are the highlighted Latin letters in the generation-6 Bangla mostly?",
             [("codemix", "English words or names a Bangla writer would use"), ("noise", "English pieces or nonsense inside Bangla sentences"),
              ("broken", "broken characters (a technical fault)"), ("unsure", "mixed or unsure")]),
            ("qB2", "Apart from them, is the generation-6 text still readable Bangla?", YES_PARTLY_NO)]},
    {"key": "C", "lang": "EN", "chain": "EN-REPLACE-topp95", "select": "repeat",
     "title": "C. English: repetition at top-p 0.95 (EN-REPLACE-topp95, generation 6)",
     "what": "The top-p 0.95 chain writes more and more documents that repeat themselves. These rows are drawn from the documents whose own "
             "4-gram repetition is at least 0.2; each row shows its value. The question is whether the repetition is language that loops, or broken output.",
     "cols": [("GEN0-EN", 0, "gen 0"), ("EN-REPLACE-topp95", 1, "top-p 0.95 gen 1"), ("EN-REPLACE-topp95", 3, "top-p 0.95 gen 3"),
              ("EN-REPLACE-topp95", 6, "top-p 0.95 gen 6"), ("EN-REPLACE", 6, "REPLACE gen 6 (top-p 1.0)")],
     "nums": [("degenerate_docs", "documents whose own 4-gram repetition is at least 0.5", 3),
              ("screen_repeat4_ge_0.2", "documents whose own 4-gram repetition is at least 0.2 (exploratory)", 3),
              ("repeat_4gram_rate", "mean 4-gram repetition", 3), ("distinct_2", "distinct word pairs", 3), ("mean_length_words", "mean length (words)", 0)],
     "qs": [("qC", "What does the repetition look like?",
             [("loops", "readable sentences that repeat words or phrases"), ("broken", "broken or meaningless text (a technical fault)"),
              ("unsure", "mixed or unsure")])]},
    {"key": "D", "lang": "BN", "chain": "BN-REPLACE-topp95", "select": "repeat",
     "title": "D. Bangla: repetition at top-p 0.95 (BN-REPLACE-topp95, generation 6)",
     "what": "The same pattern in Bangla. These rows are drawn from the documents whose own 4-gram repetition is at least 0.2.",
     "cols": [("GEN0-BN", 0, "gen 0"), ("BN-REPLACE-topp95", 1, "top-p 0.95 gen 1"), ("BN-REPLACE-topp95", 3, "top-p 0.95 gen 3"),
              ("BN-REPLACE-topp95", 6, "top-p 0.95 gen 6"), ("BN-REPLACE", 6, "REPLACE gen 6 (top-p 1.0)")],
     "nums": [("degenerate_docs", "documents whose own 4-gram repetition is at least 0.5", 3),
              ("screen_repeat4_ge_0.2", "documents whose own 4-gram repetition is at least 0.2 (exploratory)", 3),
              ("repeat_4gram_rate", "mean 4-gram repetition", 3), ("distinct_2", "distinct word pairs", 3), ("mean_length_words", "mean length (words)", 0)],
     "qs": [("qD", "What does the repetition look like?",
             [("loops", "readable sentences that repeat words or phrases"), ("broken", "broken or meaningless text (a technical fault)"),
              ("unsure", "mixed or unsure")]),
            ("qD2", "Apart from the repetition, is the generation-6 text readable Bangla?", YES_PARTLY_NO)]},
]
GATE_Q = ("qG4", "Gate 4, after this read:", [("passed", "G4 passed"), ("not", "G4 not passed (say why in the note)")])

CSS = """
:root { --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6a675f; --line:#dedbd2; --card:#ffffff; --accent:#1f5f8b; --g0:#244b6b; --g1:#6b2f12; --warn:#8a3b12;
        --hl-frn:#f6d58e; --hl-lat:#bfe0f5; --hl-fg:#1d1d1b; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124;
        --accent:#7fb4dc; --g0:#9cc3e6; --g1:#f0b38c; --warn:#f0a67a; --hl-frn:#7a5a14; --hl-lat:#1f4f6e; --hl-fg:#f4f2ee; } }
:root[data-theme="dark"] { --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --g0:#9cc3e6; --g1:#f0b38c;
        --warn:#f0a67a; --hl-frn:#7a5a14; --hl-lat:#1f4f6e; --hl-fg:#f4f2ee; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 "Segoe UI", "Nirmala UI", "Noto Sans Bengali", system-ui, sans-serif; }
main { max-width:1200px; margin:0 auto; padding:24px 16px 90px; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:19px; margin:40px 0 8px; border-bottom:1px solid var(--line); padding-bottom:6px; }
.sub { color:var(--muted); margin:6px 0 14px; }
.card { background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:14px 16px; margin:12px 0; }
.card ol, .card ul { margin:6px 0 4px 20px; padding:0; } .card li { margin:3px 0; }
.wrap { overflow-x:auto; }
table.m { border-collapse:collapse; background:var(--card); border:1px solid var(--line); margin:8px 0; font-size:14px; }
.m th, .m td { border-bottom:1px solid var(--line); padding:5px 10px; text-align:left; } .m td.v { font-variant-numeric:tabular-nums; text-align:right; }
.q { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; margin:10px 0; }
.q .opts { display:flex; gap:6px 16px; flex-wrap:wrap; margin:6px 0; } .q .qnote { width:100%; }
table.t { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); table-layout:fixed; }
.t th, .t td { border-bottom:1px solid var(--line); padding:8px 10px; vertical-align:top; text-align:left; overflow-wrap:anywhere; }
.t th { font-size:13px; color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--card); }
.t th:first-child, .t td.n { width:4.2em; color:var(--muted); white-space:nowrap; } .t th:last-child, td.flag { width:10.5em; }
.pre { color:var(--muted); font-size:13px; margin-bottom:3px; }
.g0 { color:var(--g0); white-space:pre-wrap; } .g1 { color:var(--g1); white-space:pre-wrap; }
.info { color:var(--muted); font-size:12px; margin-top:6px; }
mark { color:var(--hl-fg); border-radius:3px; padding:0 1px; } mark.frn { background:var(--hl-frn); } mark.lat { background:var(--hl-lat); }
input[type=text] { width:100%; margin-top:4px; font:13px inherit; padding:3px 5px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--fg); }
tr.flagged td { background:color-mix(in srgb, var(--warn) 12%, transparent); }
.bar { position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line); padding:10px 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
button { font:inherit; padding:6px 14px; border-radius:6px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; }
textarea { width:100%; min-height:110px; font:13px Consolas, monospace; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px; }
@media (max-width:760px) { .t th:last-child, td.flag { width:7em; } .t th:first-child, .t td.n { width:3.4em; font-size:12px; } }
"""

JS = """
const KEY = __KEY__;
const SECTIONS = __SECTIONS__;
function load() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } }
function save(s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} }
const state = load();
const rowsEl = [...document.querySelectorAll("tr[data-id]")];
for (const tr of rowsEl) {
  const id = tr.dataset.id, cb = tr.querySelector(".rej"), nt = tr.querySelector(".note");
  if (state[id]) { cb.checked = !!state[id].r; nt.value = state[id].n || ""; }
  const upd = () => { state[id] = { r: cb.checked, n: nt.value }; tr.classList.toggle("flagged", cb.checked); save(state); render(); };
  cb.addEventListener("change", upd); nt.addEventListener("input", upd); tr.classList.toggle("flagged", cb.checked);
}
for (const q of document.querySelectorAll(".q")) {
  const k = q.dataset.q, nt = q.querySelector(".qnote");
  if (state[k]) { const r = q.querySelector(`input[value="${state[k].a}"]`); if (r) r.checked = true; if (nt) nt.value = state[k].n || ""; }
  const upd = () => { const sel = q.querySelector("input[type=radio]:checked"); state[k] = { a: sel ? sel.value : "", n: nt ? nt.value : "" }; save(state); render(); };
  q.querySelectorAll("input[type=radio]").forEach(r => r.addEventListener("change", upd)); if (nt) nt.addEventListener("input", upd);
}
function answer(k) {
  const q = document.querySelector(`.q[data-q="${k}"]`), s = state[k] || {};
  if (!s.a) return "not answered" + (s.n ? " - " + s.n : "");
  const lab = q.querySelector(`input[value="${s.a}"]`).closest("label").textContent.trim();
  return lab + (s.n ? " - " + s.n : "");
}
function render() {
  const parts = SECTIONS.map(sec => {
    const qs = sec.qs.map(k => answer(k)).join("; ");
    const flagged = rowsEl.filter(tr => tr.dataset.sec === sec.key && tr.querySelector(".rej").checked)
      .map(tr => tr.dataset.id + (tr.querySelector(".note").value ? " (" + tr.querySelector(".note").value + ")" : ""));
    return `${sec.key} ${sec.short}: ${qs}; technical faults ticked: ${flagged.length ? flagged.join(", ") : "none"}`;
  });
  document.getElementById("reply").value = "G4 read (" + __SHEET__ + "). " + parts.join(". ") + ". Gate 4: " + answer("qG4") + ".";
  const n = rowsEl.filter(tr => tr.querySelector(".rej").checked).length;
  const answered = [...document.querySelectorAll(".q")].filter(q => (state[q.dataset.q] || {}).a).length;
  document.getElementById("count").textContent = `questions answered: ${answered} of ${document.querySelectorAll(".q").length}; rows ticked: ${n}`;
}
render();
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("reply"); t.select();
  try { await navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); }
});
"""


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def highlight(text: str, lang: str) -> str:
    out, last = [], 0
    for m in HL[lang].finditer(text):
        out.append(html.escape(text[last:m.start()]))
        cls = "lat" if m.lastgroup == "lat" else "frn"
        out.append(f'<mark class="{cls}">{html.escape(m.group(0))}</mark>')
        last = m.end()
    out.append(html.escape(text[last:]))
    return "".join(out)


def rep4(text: str) -> float:
    return repeat_4gram_rate([w.lower() for w in words(text)])


def pick(sec: dict, g0: list[dict], g6: list[dict]) -> list[int]:
    lang = sec["lang"]
    if sec["select"] == "foreign":
        cand = [i for i, d in enumerate(g6) if FOREIGN[lang].search(d["text"] or "")]
    elif sec["select"] == "latin":
        cand = [i for i, d in enumerate(g6) if LATIN.search(d["text"] or "")]
    else:
        cand = [i for i, d in enumerate(g6) if rep4(d["text"] or "") >= 0.2]
    chosen = sorted(random.Random(f"{SEED}-{sec['key']}").sample(cand, min(N_ROWS, len(cand))))
    return chosen, len(cand)


def num_table(sec: dict, met: dict, scr: dict) -> str:
    head = "<tr><th>measure (over 2,000 sampled documents per model)</th>" + "".join(f"<th>{html.escape(lbl)}</th>" for _, _, lbl in sec["cols"]) + "</tr>"
    body = []
    for key, label, nd in sec["nums"]:
        cells = []
        for chain, g, _ in sec["cols"]:
            v = scr.get((chain, g, key), met.get((chain, g, key)))
            cells.append(f'<td class="v">{"–" if v is None else f"{v:.{nd}f}"}</td>')
        body.append(f"<tr><td>{html.escape(label)}</td>{''.join(cells)}</tr>")
    return f'<div class="wrap"><table class="m"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>'


def q_block(qkey: str, text: str, opts: list[tuple[str, str]]) -> str:
    radios = "".join(f'<label><input type="radio" name="{qkey}" value="{v}"> {html.escape(lbl)}</label>' for v, lbl in opts)
    return (f'<div class="q" data-q="{qkey}"><b>{html.escape(text)}</b><div class="opts">{radios}</div>'
            f'<input type="text" class="qnote" placeholder="short note (optional)"></div>')


def section(sec: dict, met: dict, scr: dict) -> tuple[str, list[str]]:
    lang, chain = sec["lang"], sec["chain"]
    p0, p6 = RES / "samples" / f"GEN0-{lang}_gen0_50.jsonl", RES / "samples" / f"{chain}_gen6_50.jsonl"
    g0, g6 = rows(p0), rows(p6)
    assert len(g0) == len(g6) == 50 and all(a["prefix_id"] == b["prefix_id"] for a, b in zip(g0, g6)), f"{p6.name}: samples must share the 50 prompts"
    chosen, n_cand = pick(sec, g0, g6)
    body = []
    for j, i in enumerate(chosen, 1):
        a, b = g0[i], g6[i]
        rid = f"{sec['key']}{j:02d}"
        if sec["select"] == "repeat":
            info0, info6 = f"own 4-gram repetition {rep4(a['text']):.2f}", f"own 4-gram repetition {rep4(b['text']):.2f}"
        else:
            cnt = (lambda t: len(LATIN.findall(t))) if sec["select"] == "latin" else (lambda t: len(FOREIGN[lang].findall(t)))
            what = "Latin letters" if sec["select"] == "latin" else "letters of another script"
            info0, info6 = f"{cnt(a['text'])} {what}", f"{cnt(b['text'])} {what}"
        body.append(f"""<tr data-id="{rid}" data-sec="{sec['key']}"><td class="n">{rid}</td>
<td><div class="pre">{html.escape(a["prefix"])}</div><div class="g0">{highlight(a["text"], lang)}</div><div class="info">{html.escape(info0)}</div></td>
<td><div class="pre">{html.escape(b["prefix"])}</div><div class="g1">{highlight(b["text"], lang)}</div><div class="info">{html.escape(info6 + "; prompt " + b["prefix_id"])}</div></td>
<td class="flag"><label><input type="checkbox" class="rej"> technical fault</label><input type="text" class="note" placeholder="what (optional)"></td></tr>""")
    lang_attr = "bn" if lang == "BN" else "en"
    picked = (f"{len(chosen)} rows drawn with a fixed seed from the {n_cand} of these 50 samples that show the pattern"
              if sec["select"] != "repeat" else f"{len(chosen)} rows drawn with a fixed seed from the {n_cand} of these 50 samples whose own 4-gram repetition is at least 0.2")
    table = (f'<p class="sub">{html.escape(picked)}.</p><table class="t" lang="{lang_attr}"><thead><tr><th>#</th><th>generation 0 (prompt in grey)</th>'
             f'<th>{html.escape(chain)}, generation 6 (same prompt)</th><th>tick only a fault</th></tr></thead><tbody>{"".join(body)}</tbody></table>')
    qs = "".join(q_block(k, t, o) for k, t, o in sec["qs"])
    part = f'<h2 id="{sec["key"]}">{html.escape(sec["title"])}</h2><p>{html.escape(sec["what"])}</p>{num_table(sec, met, scr)}{qs}{table}'
    hashes = [f"{p.name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()[:16]}…" for p in (p0, p6)]
    return part, hashes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default="cg4-g4-read-v1", help="browser storage key; change it for a new read so old ticks do not carry over")
    a = ap.parse_args()
    met = {(r["chain_id"], r["generation"], r["metric"]): r["value"] for r in rows(RES / "metrics.jsonl")}
    scr = {(r["chain_id"], r["generation"], r["metric"]): r["value"] for r in rows(RES / "screening_metrics.jsonl")}
    parts, hashes = [], []
    for sec in SECTIONS:
        p, h = section(sec, met, scr)
        parts.append(p); hashes += h
    out = Path(a.out) if Path(a.out).is_absolute() else PKG / a.out
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    shorts = {"A": "English other-script letters", "B": "Bangla Latin letters", "C": "English top-p 0.95 repetition", "D": "Bangla top-p 0.95 repetition"}
    js_secs = [{"key": s["key"], "short": shorts[s["key"]], "qs": [k for k, _, _ in s["qs"]]} for s in SECTIONS]
    js = (JS.replace("__KEY__", json.dumps(a.key)).replace("__SECTIONS__", json.dumps(js_secs))
          .replace("__SHEET__", json.dumps(out.name)))
    hashes_html = html.escape("; ".join(dict.fromkeys(hashes)))
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CG4 Gate 4 Read</title>
<style>{CSS}</style></head>
<body><main>
<h1>CG4 Gate 4: read of two patterns</h1>
<p class="sub">Generated {html.escape(generated)} from <code>results/</code> on the VPS (REQ-021). It contains unscreened model output: a local file only, do not upload or share it.</p>
<div class="card"><b>What this page is.</b> The full run is complete, and every automatic Gate 4 check passed (<code>signoffs/G4_chains.md</code>).
Two patterns in the measurements need human eyes before you decide the gate, and this page shows the text behind them:
<ul>
<li><a href="#A">A</a> and <a href="#B">B</a>: under REPLACE, more documents contain letters of other scripts in every generation (English: other scripts; Bangla: Latin letters).</li>
<li><a href="#C">C</a> and <a href="#D">D</a>: the top-p 0.95 chains write more and more documents that repeat themselves.</li>
</ul>
In every row the <span class="g0">left column</span> is generation 0 (trained on real text) and the <span class="g1">right column</span> is generation 6 after the same real prompt (grey).
<mark class="frn">This colour</mark> marks letters of another script; in Bangla, <mark class="lat">this colour</mark> marks Latin letters. The automatic numbers sit above each section.</div>
<div class="card"><b>What to do</b> (about 30–45 minutes; sections B and D need a Bangla reader):
<ol>
<li>Read the rows of a section. You do not need to grade each sample.</li>
<li>Answer the section's question(s). Section B and D also ask whether the Bangla is still readable Bangla: only you can judge that.</li>
<li>Tick <i>technical fault</i> on a row only if it looks like something broke in the software: broken or unreadable characters, symbols that are not letters of any language, the same text pasted twice, or empty text. Write what in the box.
Mixed languages, repetition and clumsy or invented sentences are what the study measures. Do not tick them.</li>
<li>At the bottom, choose <b>G4 passed</b> or <b>G4 not passed</b>, press <b>Copy reply</b> and paste the text into the Claude Code chat.</li>
</ol>
Your ticks and answers stay in this browser only, so you can stop and come back later. This read is not the Gate 5 read: G5 comes later, with the rubric, for generations 3 and 6 of the six main chains.</div>
<div class="card"><b>Where the numbers come from.</b> <code>results/metrics.jsonl</code> (registered measures) and <code>results/screening_metrics.jsonl</code> (exploratory screening, REQ-019), each over the 2,000 documents sampled from a model.
The highlighted letters use the screening's own definitions (<code>harness/tools/screening_check.py</code>). Sample files: {hashes_html}.</div>
{"".join(parts)}
<h2>Gate 4</h2>
{q_block(*GATE_Q)}
<h2>Your reply</h2>
<textarea id="reply" readonly></textarea>
</main>
<div class="bar"><button id="copy">Copy reply</button><span id="count" class="sub" style="margin:0"></span></div>
<script>{js}</script>
</body></html>"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
