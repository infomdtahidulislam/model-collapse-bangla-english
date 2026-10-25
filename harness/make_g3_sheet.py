#!/usr/bin/env python3
"""
Self-contained HTML reading sheet for the Gate 3 pilot read (06_HUMAN_TASKS.md: read 50 generation-1 samples per language,
confirm the metrics match the text, confirm the duplicate and empty checks). Shows, for the same 50 prompts, the generation-0
continuation next to the REPLACE generation-1 continuation, with the automatic numbers on top. The authors tick rows with a
problem, answer one question per language, press "Copy reply" and paste the text into the Claude Code chat.

The page holds unscreened synthetic text, so it is written inside results/ (results/human_read/) and must not be shared.

  python harness/make_g3_sheet.py --out results/human_read/G3_pilot_read_2026-10-14.html
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
NUMS = [("log_ppl_heldout", "held-out log-perplexity (lower is better)", 3), ("tail_fact_recall_ALL", "fact recall, all strata", 3),
        ("script_docs_ge95", "documents in the right script", 3), ("repeat_4gram_rate", "4-gram repetition", 4),
        ("distinct_2", "distinct word pairs", 3), ("mean_length_words", "mean length (words)", 1), ("cap_hit_rate", "share cut at the length cap", 3)]


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def metric_table(lang: str, metrics: dict) -> str:
    head = "<tr><th>measure</th><th>generation 0</th><th>generation 1 (REPLACE)</th></tr>"
    body = []
    for key, label, nd in NUMS:
        a, b = metrics.get((f"GEN0-{lang}", 0, key)), metrics.get((f"{lang}-REPLACE", 1, key))
        fmt = lambda v: "–" if v is None else f"{v:.{nd}f}"
        body.append(f"<tr><td>{html.escape(label)}</td><td>{fmt(a)}</td><td>{fmt(b)}</td></tr>")
    step = json.load(open(RES / "chains" / f"{lang}-REPLACE" / "gen_1" / "step.json", encoding="utf-8"))
    g = step.get("generate") or {}
    extra = (f"Generation-1 training text (written by generation 0): {g.get('docs', 0):,} documents, {g.get('tokens', 0):,} tokens; "
             f"exact duplicates {100 * (g.get('exact_duplicate_rate') or 0):.2f}%, empty {100 * (g.get('empty_rate') or 0):.2f}% (limit 5% each).")
    return f'<table class="m"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table><p class="sub">{html.escape(extra)}</p>'


def sample_table(lang: str) -> tuple[str, list[str]]:
    p0, p1 = RES / "samples" / f"GEN0-{lang}_gen0_50.jsonl", RES / "samples" / f"{lang}-REPLACE_gen1_50.jsonl"
    a, b = rows(p0), rows(p1)
    assert len(a) == len(b) == 50 and all(x["prefix_ids"] == y["prefix_ids"] for x, y in zip(a, b)), "samples must share their 50 prompts"
    body = []
    for i, (x, y) in enumerate(zip(a, b), 1):
        rid = f"{lang}-S{i:02d}"
        body.append(f"""<tr data-id="{rid}"><td class="n">{i}</td>
<td><div class="pre">{html.escape(x["prefix"])}</div><div class="g0">{html.escape(x["text"])}</div></td>
<td><div class="pre">{html.escape(y["prefix"])}</div><div class="g1">{html.escape(y["text"])}</div></td>
<td class="v"><label><input type="checkbox" class="rej"> problem</label><input type="text" class="note" placeholder="what (optional)"></td></tr>""")
    hashes = [f"{p.name} sha256 {hashlib.sha256(p.read_bytes()).hexdigest()[:16]}…" for p in (p0, p1)]
    lang_attr = "bn" if lang == "BN" else "en"
    table = (f'<table class="t" lang="{lang_attr}"><thead><tr><th>#</th><th>generation 0 (prompt in grey)</th><th>generation 1, REPLACE (same prompt)</th>'
             f'<th>flag</th></tr></thead><tbody>{"".join(body)}</tbody></table>')
    return table, hashes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default="cg4-g3-pilot-read-v1", help="browser storage key; change it for a new read so old ticks do not carry over")
    ap.add_argument("--note", default="", help="highlighted note shown first (e.g. what changed since the last read)")
    a = ap.parse_args()
    metrics = {(r["chain_id"], r["generation"], r["metric"]): r["value"] for r in rows(RES / "metrics.jsonl")}
    parts, hashes = [], []
    for lang, name in (("EN", "English"), ("BN", "Bangla")):
        t, h = sample_table(lang)
        hashes += h
        parts.append(f"""<h2>{name}</h2>{metric_table(lang, metrics)}
<div class="q" data-lang="{lang}"><b>Does the generation-1 text match these numbers?</b>
<label><input type="radio" name="q{lang}" value="yes"> yes</label> <label><input type="radio" name="q{lang}" value="no"> no</label>
<input type="text" class="qnote" placeholder="short note (optional)"></div>{t}""")
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    key = a.key
    note = f'<div class="card" style="border-left-color:var(--warn)"><b>Please read first.</b> {html.escape(a.note)}</div>' if a.note else ""
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CG4 Gate 3 Pilot</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1d1b; --muted:#6a675f; --line:#dedbd2; --card:#ffffff; --accent:#1f5f8b; --g0:#244b6b; --g1:#6b2f12; --warn:#8a3b12; --chip:#eef3f7; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --g0:#9cc3e6; --g1:#f0b38c; --warn:#f0a67a; --chip:#26303a; }} }}
:root[data-theme="dark"] {{ --bg:#17181a; --fg:#e8e6e1; --muted:#a6a39b; --line:#34363a; --card:#1f2124; --accent:#7fb4dc; --g0:#9cc3e6; --g1:#f0b38c; --warn:#f0a67a; --chip:#26303a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 "Segoe UI", "Nirmala UI", "Noto Sans Bengali", system-ui, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:24px 16px 80px; }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:19px; margin:36px 0 8px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
.sub {{ color:var(--muted); margin:6px 0 14px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent); border-radius:8px; padding:14px 16px; margin:12px 0; }}
.card ol, .card ul {{ margin:6px 0 4px 20px; padding:0; }} .card li {{ margin:3px 0; }}
table.m {{ border-collapse:collapse; background:var(--card); border:1px solid var(--line); margin:8px 0; }}
.m th, .m td {{ border-bottom:1px solid var(--line); padding:5px 10px; text-align:left; }}
.q {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:10px 14px; margin:10px 0; display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
.q .qnote {{ flex:1; min-width:200px; }}
table.t {{ width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); table-layout:fixed; }}
.t th, .t td {{ border-bottom:1px solid var(--line); padding:8px 10px; vertical-align:top; text-align:left; overflow-wrap:anywhere; }}
.t th {{ font-size:13px; color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--card); }}
.t th:first-child, .t td.n {{ width:2.6em; color:var(--muted); }} .t th:last-child, td.v {{ width:10.5em; }}
.pre {{ color:var(--muted); font-size:13px; margin-bottom:3px; }}
.g0 {{ color:var(--g0); white-space:pre-wrap; }} .g1 {{ color:var(--g1); white-space:pre-wrap; }}
input[type=text] {{ width:100%; margin-top:4px; font:13px inherit; padding:3px 5px; border:1px solid var(--line); border-radius:4px; background:var(--bg); color:var(--fg); }}
tr.flagged td {{ background:color-mix(in srgb, var(--warn) 12%, transparent); }}
.bar {{ position:sticky; bottom:0; background:var(--card); border-top:1px solid var(--line); padding:10px 16px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }}
button {{ font:inherit; padding:6px 14px; border-radius:6px; border:1px solid var(--accent); background:var(--accent); color:#fff; cursor:pointer; }}
textarea {{ width:100%; min-height:90px; font:13px Consolas, monospace; background:var(--bg); color:var(--fg); border:1px solid var(--line); border-radius:6px; padding:8px; }}
@media (max-width:760px) {{ .t th:last-child, td.v {{ width:7em; }} }}
</style></head>
<body><main>
<h1>CG4 Gate 3: pilot read</h1>
<p class="sub">Generated {html.escape(generated)} from <code>results/</code> on the VPS. It contains unscreened model output: a local file only, do not upload or share it.</p>
{note}
<div class="card"><b>What this page is.</b> The pilot ran one round of the main experiment in each language. Generation 0 is the model trained on real text. It wrote 10 million tokens of new text, and generation 1 was trained on that text only, with no real text.
For each language below there are 50 rows. Every row starts from the same real prompt (grey: the first words of a real document). The <span class="g0">left column</span> is what generation 0 wrote after it, and the <span class="g1">right column</span> is what generation 1 wrote after the same prompt. The automatic numbers for both models sit above each language's rows.</div>
<div class="card"><b>What to do</b> (06_HUMAN_TASKS.md, Gate 3; about 1–2 hours; both authors, together or one language each):
<ol>
<li>Look at the numbers table of the language (their meaning is below).</li>
<li>Read the 50 rows. You do not need to grade each sample. Ask yourself whether the right-hand text (generation 1) is worse, better or about the same as the left-hand text, in the way the numbers say.</li>
<li>Tick <i>problem</i> on a row only when it shows something the automatic checks should have caught, and write what in the box next to it:
the same text twice (duplicate), empty or almost empty text, text in the wrong script or language, one phrase repeated over and over, or broken characters.
Ordinary bad writing (invented facts, odd or clumsy sentences) is expected from a 270-million-parameter model, and it is what the study measures. Do not tick it.</li>
<li>For each language, answer <b>"Does the generation-1 text match these numbers?"</b> with yes or no, and add a short note if you like.</li>
<li>Press <b>Copy reply</b> at the bottom of the page and paste the text into the Claude Code chat. That is your Gate 3 read. The budget question (REQ-017) is answered separately in the chat.</li>
</ol>
Your ticks and answers stay in this browser only, so you can stop and come back later. The page contains unscreened model output: keep it on the VPS and do not share it.</div>
<div class="card"><b>What the numbers mean.</b>
<ul>
<li><i>Held-out log-perplexity:</i> how surprised the model is by real text it never trained on. Lower is better.</li>
<li><i>Fact recall:</i> the share of fact questions (capital, country, birthplace, occupation) where the model prefers the true answer over three wrong ones. Chance is 0.25.</li>
<li><i>Documents in the right script:</i> the share of documents that are at least 95% Latin script (English) or Bengali script (Bangla).</li>
<li><i>4-gram repetition:</i> how often four-word sequences repeat inside a document. Above 0.2 would be a problem.</li>
<li><i>Distinct word pairs:</i> the variety of word pairs. Lower means more repetitive text.</li>
<li><i>Mean length</i> and <i>share cut at the length cap:</i> how long the documents are, and how many stopped at the maximum length instead of ending by themselves.</li>
</ul>
Sample files: {html.escape("; ".join(hashes))}.</div>
{"".join(parts)}
<h2>Your reply</h2>
<textarea id="reply" readonly></textarea>
</main>
<div class="bar"><button id="copy">Copy reply</button><span id="count" class="sub" style="margin:0"></span></div>
<script>
const KEY = {json.dumps(key)};
function load() {{ try {{ return JSON.parse(localStorage.getItem(KEY) || "{{}}"); }} catch (e) {{ return {{}}; }} }}
function save(s) {{ try {{ localStorage.setItem(KEY, JSON.stringify(s)); }} catch (e) {{}} }}
const state = load();
const rowsEl = [...document.querySelectorAll("tr[data-id]")];
for (const tr of rowsEl) {{
  const id = tr.dataset.id, cb = tr.querySelector(".rej"), nt = tr.querySelector(".note");
  if (state[id]) {{ cb.checked = !!state[id].r; nt.value = state[id].n || ""; }}
  const upd = () => {{ state[id] = {{ r: cb.checked, n: nt.value }}; tr.classList.toggle("flagged", cb.checked); save(state); render(); }};
  cb.addEventListener("change", upd); nt.addEventListener("input", upd); tr.classList.toggle("flagged", cb.checked);
}}
for (const q of document.querySelectorAll(".q")) {{
  const lang = q.dataset.lang, k = "q" + lang, nt = q.querySelector(".qnote");
  if (state[k]) {{ const r = q.querySelector(`input[value="${{state[k].a}}"]`); if (r) r.checked = true; nt.value = state[k].n || ""; }}
  const upd = () => {{ const sel = q.querySelector("input[type=radio]:checked"); state[k] = {{ a: sel ? sel.value : "", n: nt.value }}; save(state); render(); }};
  q.querySelectorAll("input[type=radio]").forEach(r => r.addEventListener("change", upd)); nt.addEventListener("input", upd);
}}
function render() {{
  const part = lang => {{
    const q = state["q" + lang] || {{}};
    const flagged = rowsEl.filter(tr => tr.dataset.id.startsWith(lang) && tr.querySelector(".rej").checked)
      .map(tr => tr.dataset.id + (tr.querySelector(".note").value ? " (" + tr.querySelector(".note").value + ")" : ""));
    return `${{lang === "EN" ? "English" : "Bangla"}}: text matches the numbers: ${{q.a || "not answered"}}${{q.n ? " - " + q.n : ""}}; flagged rows: ${{flagged.length ? flagged.join(", ") : "none"}}`;
  }};
  document.getElementById("reply").value = "G3 pilot read. " + part("EN") + ". " + part("BN") + ".";
  const n = l => rowsEl.filter(tr => tr.dataset.id.startsWith(l) && tr.querySelector(".rej").checked).length;
  document.getElementById("count").textContent = `flagged: English ${{n("EN")}} of 50, Bangla ${{n("BN")}} of 50`;
}}
render();
document.getElementById("copy").addEventListener("click", async () => {{
  const t = document.getElementById("reply"); t.select();
  try {{ await navigator.clipboard.writeText(t.value); }} catch (e) {{ document.execCommand("copy"); }}
}});
</script>
</body></html>"""
    out = Path(a.out) if Path(a.out).is_absolute() else PKG / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
