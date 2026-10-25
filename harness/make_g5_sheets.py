#!/usr/bin/env python3
"""
Self-contained HTML reading sheets for the Gate 5 human read (06_HUMAN_TASKS.md, pre-specified rubric).

  - one page per confirmatory chain (6 pages): the 50 fixed prompts of `results/samples/<chain>_gen3_50.jsonl` and
    `<chain>_gen6_50.jsonl`, generation 3 next to generation 6 for the same prompt, with the rubric controls under each sample;
  - two optional pages for the generation-0 part of the optional fluency rating (20 samples per language);
  - an index page.

Rubric columns (06_HUMAN_TASKS.md): sample_id, script_error (0/1), english_intrusion (BN only, 0/1), nonwords (count),
repetition_loop (0/1), topic_drift (0/1), fluency_1to5 (optional), note. sample_id is the prompt id (e.g. EN-P00012), the same
for both generations. A sample counts as coded once its nonword count is filled in; uncoded samples are exported with empty
fields, never as 0. The pages show no automatic numbers and no highlighting, so the coding stays independent of the measures it
checks. Answers are stored in the browser under the reader's name, so both authors can use one browser. "Copy reply" gives
the CSV text to paste into the Claude Code chat; "Download CSV" saves the same rows as a file. "Export progress" saves the
reader's answers for the page as a JSON file (format cg4-g5-progress-v1, with the sample file hashes); "Import progress" loads
such a file back into the page (after a browser clean-up, on another computer, or after the page is regenerated), after
checking that it belongs to this page and asking before it replaces answers already in the browser. The browser storage key of
a page does not change when the page is regenerated, so answers already entered are kept.

The pages hold unscreened synthetic text, so they are written inside results/ (results/human_read/) and must not be shared.

  python harness/make_g5_sheets.py --stamp 2026-10-17
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
RES = PKG / "results"
OUTDIR = RES / "human_read"
CHAINS = [f"{lang}-{reg}" for lang in ("EN", "BN") for reg in ("REPLACE", "ACCUMULATE", "ACCUMULATE-FILTER")]
GENS = (3, 6)
FLUENCY_SUBSET = 20          # the first 20 prompts of every file: the shared subset of the optional fluency rating

CSS = """
:root { --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6a675f; --line:#dedbd2; --card:#ffffff; --accent:#1f5f8b; --g3:#244b6b; --g6:#6b2f12;
        --done:#2f6b3a; --warn:#8a3b12; --badge:#eef3f7; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a;
        --card:#1f2124; --accent:#7fb4dc; --g3:#9cc3e6; --g6:#f0b38c; --done:#8fd19e; --warn:#f0a67a; --badge:#26303a; } }
:root[data-theme="dark"] { --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --g3:#9cc3e6;
        --g6:#f0b38c; --done:#8fd19e; --warn:#f0a67a; --badge:#26303a; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:15px/1.55 "Segoe UI", "Nirmala UI", "Noto Sans Bengali", system-ui, sans-serif; }
main { max-width:1240px; margin:0 auto; padding:24px 16px 96px; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:19px; margin:32px 0 8px; }
.sub { color:var(--muted); margin:6px 0 14px; }
.card { background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:14px 16px; margin:12px 0; }
.card ol, .card ul { margin:6px 0 4px 20px; padding:0; } .card li { margin:3px 0; }
.who { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
.who input { max-width:260px; }
fieldset { border:0; margin:0; padding:0; min-width:0; } fieldset:disabled .p { opacity:.55; }
.p { background:var(--card); border:1px solid var(--line); border-radius:8px; margin:14px 0; overflow:hidden; }
.ph { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; padding:8px 12px; border-bottom:1px solid var(--line); }
.ph .id { font-weight:600; } .ph .pre { color:var(--muted); font-size:13px; flex:1; min-width:200px; }
.badge { font-size:12px; background:var(--badge); border-radius:10px; padding:1px 8px; color:var(--muted); }
.pair { display:grid; grid-template-columns:1fr 1fr; }
.s { padding:10px 12px; border-right:1px solid var(--line); min-width:0; } .s:last-child { border-right:0; }
.s .lab { font-size:12px; font-weight:600; letter-spacing:.02em; margin-bottom:4px; }
.s[data-g="3"] .lab { color:var(--g3); } .s[data-g="6"] .lab { color:var(--g6); }
.txt { white-space:pre-wrap; overflow-wrap:anywhere; }
.ctl { margin-top:10px; padding-top:8px; border-top:1px dashed var(--line); display:flex; gap:6px 14px; flex-wrap:wrap; align-items:center; font-size:13px; }
.ctl label { white-space:nowrap; } .ctl .nw { width:5em; } .ctl .nt { flex:1 1 100%; }
.s.done .lab::after { content:"  ✓ coded"; color:var(--done); }
input[type=text], input[type=number], select { font:13px inherit; padding:3px 5px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--fg); }
input[type=text] { width:100%; }
.bar { position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line); padding:10px 16px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
button { font:inherit; padding:6px 14px; border-radius:6px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; }
button.sec { background:transparent; color:var(--accent); }
label.btn { font:inherit; padding:6px 14px; border-radius:6px; border:1px solid var(--accent); color:var(--accent); cursor:pointer; display:inline-block; }
textarea { width:100%; min-height:120px; font:12px Consolas, monospace; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px; }
table.idx { border-collapse:collapse; background:var(--card); border:1px solid var(--line); width:100%; }
.idx th, .idx td { border-bottom:1px solid var(--line); padding:7px 10px; text-align:left; vertical-align:top; }
code { font-size:13px; }
@media (max-width:860px) { .pair { grid-template-columns:1fr; } .s { border-right:0; border-bottom:1px solid var(--line); } .s:last-child { border-bottom:0; } }
"""

JS = """
const KEYBASE = __KEYBASE__, PAGE = __PAGE__;
const blocks = [...document.querySelectorAll(".s")];
const nameEl = document.getElementById("reader"), all = document.getElementById("all");
let reader = "", state = {};
const key = () => KEYBASE + "|" + reader.trim().toLowerCase();
function load() { try { return JSON.parse(localStorage.getItem(key()) || "{}"); } catch (e) { return {}; } }
function save() { try { localStorage.setItem(key(), JSON.stringify(state)); localStorage.setItem(KEYBASE + "|last", reader); } catch (e) {} }
function fields(b) { const q = c => b.querySelector(c); return { se: q(".se"), ei: q(".ei"), nw: q(".nw"), rl: q(".rl"), td: q(".td"), fl: q(".fl"), nt: q(".nt") }; }
function sid(b) { return b.dataset.g + "|" + b.dataset.sid; }
function isDone(b, v) { return PAGE.mode === "fluency" ? (v.fl || "") !== "" : (v.nw ?? "") !== ""; }
function apply() {
  for (const b of blocks) {
    const f = fields(b), v = state[sid(b)] || {};
    for (const k of ["se", "ei", "rl", "td"]) if (f[k]) f[k].checked = !!v[k];
    if (f.nw) f.nw.value = v.nw ?? ""; if (f.fl) f.fl.value = v.fl ?? ""; if (f.nt) f.nt.value = v.nt ?? "";
    b.classList.toggle("done", isDone(b, v));
  }
  render();
}
function read(b) {
  const f = fields(b), v = {};
  for (const k of ["se", "ei", "rl", "td"]) if (f[k]) v[k] = f[k].checked;
  if (f.nw) v.nw = f.nw.value.trim(); if (f.fl) v.fl = f.fl.value; if (f.nt) v.nt = f.nt.value;
  return v;
}
for (const b of blocks) {
  const upd = () => { if (!reader.trim()) return; const v = read(b); state[sid(b)] = v; b.classList.toggle("done", isDone(b, v)); save(); render(); };
  b.querySelectorAll("input, select").forEach(el => { el.addEventListener("change", upd); el.addEventListener("input", upd); });
}
function setReader(v) { reader = v; all.disabled = !reader.trim(); state = reader.trim() ? load() : {}; apply(); }
nameEl.addEventListener("input", () => setReader(nameEl.value));
try { const last = localStorage.getItem(KEYBASE + "|last"); if (last) nameEl.value = last; } catch (e) {}
const q = s => /[",\\n\\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
const b01 = x => x ? "1" : "0";
function csv(g) {
  const rows = blocks.filter(b => b.dataset.g === String(g));
  const out = [PAGE.mode === "fluency" ? "sample_id,fluency_1to5,note" : "sample_id,script_error,english_intrusion,nonwords,repetition_loop,topic_drift,fluency_1to5,note"];
  let done = 0;
  for (const b of rows) {
    const v = state[sid(b)] || {}, d = isDone(b, v); if (d) done++;
    if (PAGE.mode === "fluency") { out.push([b.dataset.sid, d ? v.fl : "", q(v.nt || "")].join(",")); continue; }
    out.push(d ? [b.dataset.sid, b01(v.se), PAGE.lang === "BN" ? b01(v.ei) : "", v.nw, b01(v.rl), b01(v.td), v.fl || "", q(v.nt || "")].join(",")
               : [b.dataset.sid, "", "", "", "", "", "", q(v.nt || "")].join(","));
  }
  return { text: out.join("\\n"), done, n: rows.length };
}
function render() {
  const parts = [`G5 read, ${PAGE.title} (${PAGE.sheet}), reader: ${reader.trim() || "(no name)"}, ${new Date().toISOString().slice(0, 16)}Z`];
  const counts = [];
  for (const f of PAGE.files) {
    const c = csv(f.g); counts.push(`gen ${f.g}: ${c.done} of ${c.n}`);
    parts.push(`## ${f.label} | ${f.path} sha256 ${f.sha} | coded ${c.done} of ${c.n}`, c.text);
  }
  document.getElementById("reply").value = parts.join("\\n");
  document.getElementById("count").textContent = reader.trim() ? `${reader.trim()}: coded ${counts.join(", ")}` : "enter your name at the top to start";
}
function download(g) {
  const f = PAGE.files.find(x => x.g === g), c = csv(g);
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([c.text + "\\n"], { type: "text/csv;charset=utf-8" }));
  a.download = `${f.label}_${(reader.trim() || "reader").replace(/[^A-Za-z0-9]+/g, "_")}.csv`; a.click();
}
const safe = s => (s || "reader").trim().replace(/[^A-Za-z0-9]+/g, "_");
function exportData() {
  const coded = {};
  for (const f of PAGE.files) { const c = csv(f.g); coded["gen" + f.g] = `${c.done} of ${c.n}`; }
  return { format: "cg4-g5-progress-v1", sheet: PAGE.sheet, keybase: KEYBASE, title: PAGE.title, reader: reader.trim(),
           saved_at: new Date().toISOString(), files: PAGE.files, coded, answers: state };
}
function applyImport(d) {
  if (!d || d.format !== "cg4-g5-progress-v1") return "This is not a G5 progress file.";
  if (d.keybase !== KEYBASE) return `This progress file belongs to ${d.title || d.sheet || "another page"}, not to ${PAGE.title}. Open that page and import it there.`;
  if (!d.reader || !String(d.reader).trim()) return "The file has no reader name.";
  const changed = PAGE.files.filter(f => !(d.files || []).some(x => x.g === f.g && x.sha === f.sha));
  if (changed.length && !confirm("The sample files of this page differ from the ones in the progress file. Import anyway?")) return "Import cancelled.";
  const known = new Set(blocks.map(sid)), answers = {};
  let n = 0;
  for (const [k, v] of Object.entries(d.answers || {})) if (known.has(k) && v && typeof v === "object") { answers[k] = v; n++; }
  reader = String(d.reader).trim(); nameEl.value = reader;
  const existing = load();
  if (Object.keys(existing).length && JSON.stringify(existing) !== JSON.stringify(answers) &&
      !confirm(`${reader} already has answers for this page in this browser. Replace them with the ${n} answers from the file (saved ${d.saved_at || "?"})?`)) {
    setReader(reader); return "Import cancelled; the answers already in this browser were kept.";
  }
  state = answers; all.disabled = false; save(); apply();
  return `Imported ${n} answers for ${reader} (saved ${d.saved_at || "?"}).`;
}
document.getElementById("copy").addEventListener("click", async () => {
  const t = document.getElementById("reply"); t.select();
  try { await navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand("copy"); }
});
document.querySelectorAll("button[data-dl]").forEach(btn => btn.addEventListener("click", () => download(Number(btn.dataset.dl))));
document.getElementById("export").addEventListener("click", () => {
  if (!reader.trim()) { alert("Enter your name at the top first."); return; }
  const a = document.createElement("a"), stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
  a.href = URL.createObjectURL(new Blob([JSON.stringify(exportData(), null, 1)], { type: "application/json" }));
  a.download = `${PAGE.sheet.replace(/\\.html$/, "")}_${safe(reader)}_progress_${stamp}.json`; a.click();
  document.getElementById("saved").textContent = "exported at " + new Date().toLocaleTimeString();
});
document.getElementById("import").addEventListener("change", ev => {
  const file = ev.target.files[0]; if (!file) return;
  const r = new FileReader();
  r.onload = () => { let d; try { d = JSON.parse(r.result); } catch (e) { alert("This file is not a JSON file."); ev.target.value = ""; return; }
                     alert(applyImport(d)); ev.target.value = ""; };
  r.readAsText(file);
});
setReader(nameEl.value);
"""


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def controls(lang: str, mode: str) -> str:
    fl = ('<label>fluency <select class="fl"><option value="">–</option>' + "".join(f'<option value="{i}">{i}</option>' for i in range(1, 6)) + "</select></label>")
    if mode == "fluency":
        return f'<div class="ctl">{fl}<input type="text" class="nt" placeholder="note (optional)"></div>'
    ei = '<label><input type="checkbox" class="ei"> English intrusion</label>' if lang == "BN" else ""
    return (f'<div class="ctl"><label>nonwords <input type="number" class="nw" min="0" step="1" placeholder="count"></label>'
            f'<label><input type="checkbox" class="se"> script error</label>{ei}'
            f'<label><input type="checkbox" class="rl"> repetition loop</label><label><input type="checkbox" class="td"> topic drift</label>'
            f'{fl}<input type="text" class="nt" placeholder="note (optional)"></div>')


def coding_card(lang: str) -> str:
    se = ("<i>script error</i> (0/1): letters of a script other than Latin (Cyrillic, Arabic, Thai…), or garbage characters (broken symbols, "
          "boxes, strings of symbols that are not text)." if lang == "EN" else
          "<i>script error</i> (0/1): letters of a third script (neither Bengali nor Latin: Devanagari, Cyrillic…), or garbage characters "
          "(broken symbols, boxes, strings of symbols that are not text).")
    ei = ("" if lang == "EN" else
          "<li><i>English intrusion</i> (0/1, Bangla only): English words or any Latin-letter string inside the Bangla text.</li>")
    return f"""<div class="card"><b>How to code each sample</b> (the pre-specified rubric, <code>06_HUMAN_TASKS.md</code>). Code generation 3 and generation 6 separately; each has its own controls.
<ul>
<li><i>nonwords</i> (count): morphologically broken or invented words. Count them; 0 if there are none. If a text is too broken to count exactly, give your best count and write "approximate" in the note. <b>A sample counts as coded once this number is filled in.</b></li>
<li>{se}</li>
{ei}
<li><i>repetition loop</i> (0/1): the text repeats a word, phrase, sentence or symbol pattern over and over.</li>
<li><i>topic drift</i> (0/1): the continuation is unrelated to the prompt (grey).</li>
<li><i>fluency</i> (1–5, optional): 1 = not readable as language, 3 = readable but clumsy or partly broken, 5 = fluent. The optional fluency rating covers the
20 prompts marked <span class="badge">fluency subset</span>; both of you rate those, so that agreement can be reported.</li>
<li><i>note</i>: anything worth saying, in a few words.</li>
</ul>
Ordinary invented facts and clumsy writing are expected from a 270-million-parameter model. Code what the rubric asks, nothing more.</div>"""


def chain_page(chain: str, stamp: str) -> tuple[str, str, list[dict]]:
    lang = chain[:2]
    files = []
    data = {}
    for g in GENS:
        p = RES / "samples" / f"{chain}_gen{g}_50.jsonl"
        data[g] = rows(p)
        files.append({"g": g, "label": f"{chain}_gen{g}", "path": f"results/samples/{p.name}", "sha": sha16(p)})
    assert len(data[3]) == len(data[6]) == 50 and [d["prefix_id"] for d in data[3]] == [d["prefix_id"] for d in data[6]], f"{chain}: generations must share the 50 prompts"
    cards = []
    for i, (a, b) in enumerate(zip(data[3], data[6]), 1):
        badge = '<span class="badge">fluency subset</span>' if i <= FLUENCY_SUBSET else ""
        cards.append(f"""<div class="p"><div class="ph"><span class="id">#{i} · {html.escape(a["prefix_id"])}</span>{badge}<span class="pre">prompt: {html.escape(a["prefix"])}</span></div>
<div class="pair"><div class="s" data-g="3" data-sid="{html.escape(a["prefix_id"])}"><div class="lab">GENERATION 3</div><div class="txt">{html.escape(a["text"])}</div>{controls(lang, "rubric")}</div>
<div class="s" data-g="6" data-sid="{html.escape(b["prefix_id"])}"><div class="lab">GENERATION 6</div><div class="txt">{html.escape(b["text"])}</div>{controls(lang, "rubric")}</div></div></div>""")
    name = f"G5_{chain}_{stamp}.html"
    page_js = {"title": chain, "sheet": name, "lang": lang, "mode": "rubric", "files": files}
    body = f"""<h1>CG4 Gate 5 read: {html.escape(chain)}</h1>
<p class="sub">Generated {{generated}} from <code>results/samples/</code> on the VPS. Unscreened model output: a local file only, do not upload or share it. <a href="G5_index_{stamp}.html">All G5 pages</a></p>
<div class="card who"><b>Your name:</b> <input type="text" id="reader" placeholder="e.g. Maksuda Akter"> <span class="sub" style="margin:0">Answers are saved in this browser under your name, so you can stop and come back, and both of you can use this browser.</span></div>
<div class="card"><b>What to do</b> (about 2–3 hours for this page): read the 50 prompts below. Each shows <span style="color:var(--g3)">generation 3</span> and <span style="color:var(--g6)">generation 6</span> after the same real prompt (grey).
Code each of the 100 samples with the rubric below. When you are done, press <b>Copy reply</b> and paste the text into the Claude Code chat. <b>Download CSV</b> saves the same rows as files for your own records.<br>
<b>Export progress</b> saves your answers on this page to a JSON file (in Downloads). <b>Import progress</b> loads such a file back and you continue where you left off, for example after the browser was cleaned, on another computer, or after the page was regenerated. Export at the end of each session as a safety copy. You can also give the agent your exported file instead of pasting the reply.</div>
{coding_card(lang)}
<fieldset id="all" disabled>{"".join(cards)}</fieldset>
<h2>Your reply</h2><textarea id="reply" readonly></textarea>"""
    bar = ('<button id="copy">Copy reply</button><button class="sec" id="export">Export progress</button>'
           '<label class="btn">Import progress<input type="file" id="import" accept=".json,application/json" hidden></label>'
           '<button class="sec" data-dl="3">Download CSV gen 3</button><button class="sec" data-dl="6">Download CSV gen 6</button>'
           '<span id="saved" class="sub" style="margin:0"></span>')
    return name, page(f"G5 Read {chain}", body, bar, f"cg4-g5-{chain}-v1", page_js, lang), files


def fluency_page(lang: str, stamp: str) -> tuple[str, str, list[dict]]:
    p = RES / "samples" / f"GEN0-{lang}_gen0_50.jsonl"
    data = rows(p)[:FLUENCY_SUBSET]
    files = [{"g": 0, "label": f"GEN0-{lang}_gen0_fluency", "path": f"results/samples/{p.name}", "sha": sha16(p)}]
    cards = []
    for i, a in enumerate(data, 1):
        cards.append(f"""<div class="p"><div class="ph"><span class="id">#{i} · {html.escape(a["prefix_id"])}</span><span class="pre">prompt: {html.escape(a["prefix"])}</span></div>
<div class="pair" style="grid-template-columns:1fr"><div class="s" data-g="0" data-sid="{html.escape(a["prefix_id"])}"><div class="lab">GENERATION 0</div><div class="txt">{html.escape(a["text"])}</div>{controls(lang, "fluency")}</div></div></div>""")
    name = f"G5_fluency_gen0_{lang}_{stamp}.html"
    page_js = {"title": f"GEN0-{lang} fluency (optional)", "sheet": name, "lang": lang, "mode": "fluency", "files": files}
    language = "English" if lang == "EN" else "Bangla"
    body = f"""<h1>CG4 Gate 5, optional: fluency of generation 0 ({language})</h1>
<p class="sub">Generated {{generated}} from <code>results/samples/</code> on the VPS. Unscreened model output: a local file only, do not upload or share it. <a href="G5_index_{stamp}.html">All G5 pages</a></p>
<div class="card who"><b>Your name:</b> <input type="text" id="reader" placeholder="e.g. Md Tahidul Islam"> <span class="sub" style="margin:0">Answers are saved in this browser under your name.</span></div>
<div class="card"><b>Only if you do the optional fluency rating.</b> The registered rating covers 20 samples per chain at generations 0, 3 and 6, rated by both of you on a 1–5 scale.
Generations 3 and 6 are rated on the chain pages (the prompts marked <span class="badge">fluency subset</span>). Generation 0 is shared by the three {language} chains, so it is rated once, here: the same 20 prompts.
1 = not readable as language, 3 = readable but clumsy or partly broken, 5 = fluent. Press <b>Copy reply</b> when done.
<b>Export progress</b> and <b>Import progress</b> save your answers to a JSON file and load them back.</div>
<fieldset id="all" disabled>{"".join(cards)}</fieldset>
<h2>Your reply</h2><textarea id="reply" readonly></textarea>"""
    bar = ('<button id="copy">Copy reply</button><button class="sec" id="export">Export progress</button>'
           '<label class="btn">Import progress<input type="file" id="import" accept=".json,application/json" hidden></label>'
           '<button class="sec" data-dl="0">Download CSV</button><span id="saved" class="sub" style="margin:0"></span>')
    return name, page(f"G5 Fluency {lang}", body, bar, f"cg4-g5-fluency-gen0-{lang}-v1", page_js, lang), files


def second_rater(chain: str) -> str:
    """The author who did not code this chain's rubric page (from the G5 manifest), or a generic label."""
    man = OUTDIR / "G5_read_manifest.json"
    if not man.exists():
        return "the author who did not code this chain"
    entries = json.loads(man.read_text(encoding="utf-8"))["entries"]
    readers = {e["reader"] for e in entries}
    coder = {e["reader"] for e in entries if e["chain"] == chain and e.get("kind", "rubric") == "rubric"}
    other = sorted(readers - coder)
    return other[0] if len(other) == 1 and len(coder) == 1 else "the author who did not code this chain"


def fluency_chain_page(chain: str, stamp: str) -> tuple[str, str, list[dict]]:
    """Optional fluency rating by the second author: the 20 subset prompts of generations 3 and 6, fluency and note only."""
    lang = chain[:2]
    files, data = [], {}
    for g in GENS:
        p = RES / "samples" / f"{chain}_gen{g}_50.jsonl"
        data[g] = rows(p)[:FLUENCY_SUBSET]
        files.append({"g": g, "label": f"{chain}_gen{g}_fluency", "path": f"results/samples/{p.name}", "sha": sha16(p)})
    cards = []
    for i, (a, b) in enumerate(zip(data[3], data[6]), 1):
        cards.append(f"""<div class="p"><div class="ph"><span class="id">#{i} · {html.escape(a["prefix_id"])}</span><span class="pre">prompt: {html.escape(a["prefix"])}</span></div>
<div class="pair"><div class="s" data-g="3" data-sid="{html.escape(a["prefix_id"])}"><div class="lab">GENERATION 3</div><div class="txt">{html.escape(a["text"])}</div>{controls(lang, "fluency")}</div>
<div class="s" data-g="6" data-sid="{html.escape(b["prefix_id"])}"><div class="lab">GENERATION 6</div><div class="txt">{html.escape(b["text"])}</div>{controls(lang, "fluency")}</div></div></div>""")
    name = f"G5_fluency_{chain}_{stamp}.html"
    page_js = {"title": f"{chain} fluency (optional)", "sheet": name, "lang": lang, "mode": "fluency", "files": files}
    who = second_rater(chain)
    body = f"""<h1>CG4 Gate 5, optional: fluency of {html.escape(chain)} (second rater)</h1>
<p class="sub">Generated {{generated}} from <code>results/samples/</code> on the VPS. Unscreened model output: a local file only, do not upload or share it. <a href="G5_index_{stamp}.html">All G5 pages</a></p>
<div class="card who"><b>Your name:</b> <input type="text" id="reader" placeholder="{html.escape(who)}"> <span class="sub" style="margin:0">Answers are saved in this browser under your name.</span></div>
<div class="card"><b>For: {html.escape(who)}.</b> These are the 20 prompts marked <span class="badge">fluency subset</span> on the {html.escape(chain)} page, generation 3 next to generation 6. The other author rated them while coding that page; you rate them here without seeing those ratings, so that agreement between you can be reported (<code>06_HUMAN_TASKS.md</code>).
Rate only <b>fluency</b>: 1 = not readable as language, 3 = readable but clumsy or partly broken, 5 = fluent. The note is optional. About 15–20 minutes. Press <b>Copy reply</b> (or <b>Export progress</b>) when done.</div>
<fieldset id="all" disabled>{"".join(cards)}</fieldset>
<h2>Your reply</h2><textarea id="reply" readonly></textarea>"""
    bar = ('<button id="copy">Copy reply</button><button class="sec" id="export">Export progress</button>'
           '<label class="btn">Import progress<input type="file" id="import" accept=".json,application/json" hidden></label>'
           '<button class="sec" data-dl="3">Download CSV gen 3</button><button class="sec" data-dl="6">Download CSV gen 6</button>'
           '<span id="saved" class="sub" style="margin:0"></span>')
    return name, page(f"G5 Fluency {chain}", body, bar, f"cg4-g5-fluency-{chain}-v1", page_js, lang), files


def page(title: str, body: str, bar: str, keybase: str, page_js: dict, lang: str) -> str:
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    js = JS.replace("__KEYBASE__", json.dumps(keybase)).replace("__PAGE__", json.dumps(page_js))
    return f"""<!doctype html>
<html lang="{'bn' if lang == 'BN' else 'en'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><main>{body.replace("{generated}", html.escape(generated))}</main>
<div class="bar">{bar}<span id="count" class="sub" style="margin:0"></span></div>
<script>{js}</script></body></html>"""


def index_page(stamp: str, entries: list[tuple[str, str, list[dict]]]) -> str:
    rows_html = []
    for name, what, files in entries:
        hashes = "<br>".join(f"<code>{html.escape(f['path'])}</code> sha256 {f['sha']}…" for f in files)
        rows_html.append(f'<tr><td><a href="{html.escape(name)}">{html.escape(what)}</a></td><td>{hashes}</td></tr>')
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CG4 G5 Read</title><style>{CSS}</style></head>
<body><main>
<h1>CG4 Gate 5: human read</h1>
<p class="sub">Generated {html.escape(generated)} from <code>results/samples/</code> on the VPS. The pages hold unscreened model output: local files only, do not upload or share them.</p>
<div class="card"><b>What Gate 5 is</b> (<code>06_HUMAN_TASKS.md</code>, <code>08_GATES_AND_CHECKLISTS.md</code>): a qualitative read of generations 3 and 6 for each of the six confirmatory chains,
50 samples each (12 files), coded with the pre-specified rubric. It checks that the automatic measures match the text, and it feeds the paper's qualitative section.
The gate passes when both of you have read and recorded the rubric, and any mismatch between the numbers and the text has been investigated.
<ul>
<li><b>Split by chain</b>: each page is one chain, with generations 3 and 6 side by side (100 samples, about 2–3 hours). Split the six pages between you, for example three each.</li>
<li><b>Optional fluency rating</b>: both of you rate the same 20 prompts per page (marked <span class="badge">fluency subset</span>) plus generation 0 on the two optional pages, 1–5, so that agreement can be reported. The author who coded a chain page rated its 20 prompts there; the other author rates the same prompts on that chain's own <i>fluency</i> page below (fluency only, without seeing the first ratings). Both authors rate the two generation-0 pages.</li>
<li>On each page, enter your name first, code the samples, then press <b>Copy reply</b> and paste the text into the Claude Code chat, one page at a time. The agent writes <code>results/human_read/&lt;chain&gt;_gen&lt;g&gt;.csv</code> with the sample file hashes,
counts the codes per chain and generation, and places them next to the automatic measures. Disagreements between readers are reported, not resolved.</li>
<li>The pages show no automatic numbers and no highlighting, so that your coding is independent of the measures it checks.</li>
<li><b>Export progress</b> on a page saves your answers to a JSON file; <b>Import progress</b> loads it back on the same page, so you can always continue where you left off (another browser or computer, a cleaned browser, or a regenerated page). Export after each session as a safety copy.</li>
</ul></div>
<table class="idx"><thead><tr><th>Page</th><th>Sample files (SHA-256)</th></tr></thead><tbody>{"".join(rows_html)}</tbody></table>
</main></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for chain in CHAINS:
        name, text, files = chain_page(chain, a.stamp)
        (OUTDIR / name).write_text(text, encoding="utf-8")
        entries.append((name, f"{chain}: generations 3 and 6 (100 samples)", files))
        print(f"wrote {OUTDIR / name} ({len(text) // 1024} KB)")
    for lang in ("EN", "BN"):
        name, text, files = fluency_page(lang, a.stamp)
        (OUTDIR / name).write_text(text, encoding="utf-8")
        entries.append((name, f"Optional: fluency of GEN0-{lang}, 20 samples (both authors)", files))
        print(f"wrote {OUTDIR / name} ({len(text) // 1024} KB)")
    for chain in CHAINS:
        name, text, files = fluency_chain_page(chain, a.stamp)
        (OUTDIR / name).write_text(text, encoding="utf-8")
        entries.append((name, f"Optional: fluency of {chain}, 20 prompts × generations 3 and 6, second rater: {second_rater(chain)}", files))
        print(f"wrote {OUTDIR / name} ({len(text) // 1024} KB)")
    idx = OUTDIR / f"G5_index_{a.stamp}.html"
    idx.write_text(index_page(a.stamp, entries), encoding="utf-8")
    print(f"wrote {idx}")


if __name__ == "__main__":
    main()
