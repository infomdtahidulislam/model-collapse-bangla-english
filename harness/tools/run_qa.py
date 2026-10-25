"""Run audit (2026-10-14): is every registered statistic being produced, complete and sane? Run on the host:

  python harness/tools/run_qa.py

For every finished step (base, generation 0, every chain generation) it checks:
  - the metric rows in results/metrics.jsonl: the same metric names as generation 0 of that language (chains also carry the
    sample-under-reference measure), no NaN values, held-out n = 2,000 (fresh 500/499), recall n = 200 per stratum and 600 in all;
  - step.json: present, no NaN loss, target tokens per regime (REPLACE ~10 M synthetic and 0 real; ACCUMULATE real + all
    synthetic so far; REAL-REPEAT real only), the training text's duplicate and empty rates <= 5%, the 2,000-document
    sample's duplicate and empty rates <= 5%.
Prints a one-line summary per step and a list of anomalies. Read-only; diagnostic only."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parents[2]
RES = PKG / "results"
rows = [json.loads(l) for l in open(RES / "metrics.jsonl", encoding="utf-8") if l.strip()]
by = defaultdict(dict)
for r in rows:
    by[(r["chain_id"], r["generation"])][r["metric"]] = r
anom = []
ref = {lang: set(by[(f"GEN0-{lang}", 0)].keys()) for lang in ("EN", "BN")}
for (cid, g), ms in sorted(by.items(), key=lambda x: (x[0][0], x[0][1])):
    lang = next(iter(ms.values()))["language"]
    missing = sorted(ref[lang] - set(ms)) if not cid.startswith("BASE-") else []
    nan = sorted(k for k, r in ms.items() if isinstance(r.get("value"), float) and math.isnan(r["value"]))
    hn = ms.get("log_ppl_heldout", {}).get("n")
    rn = [ms.get(f"tail_fact_recall_{s}", {}).get("n") for s in ("HEAD", "MID", "TAIL", "ALL")]
    issues = []
    if missing: issues.append(f"missing metrics {missing[:6]}")
    if nan: issues.append(f"NaN in {nan[:6]}")
    if hn != 2000: issues.append(f"held-out n={hn}")
    if rn != [200, 200, 200, 600]: issues.append(f"recall n={rn}")
    # step record
    if cid.startswith("BASE-"):
        sp = RES / "chains" / cid / "base" / "step.json"
    elif cid.startswith("GEN0-"):
        sp = RES / "chains" / cid / "step.json"
    else:
        sp = RES / "chains" / cid / f"gen_{g}" / "step.json"
    info = ""
    if not sp.exists():
        issues.append("no step.json")
    else:
        st = json.load(open(sp, encoding="utf-8"))
        t, gen, smp = st.get("train") or {}, st.get("generate") or {}, st.get("sample") or {}
        if t.get("nan"): issues.append("NaN loss")
        ts = st.get("training_set") or {}
        real, syn = ts.get("real_target_tokens", t.get("real_target_tokens")), ts.get("synthetic_target_tokens", t.get("synthetic_target_tokens"))
        reg = st.get("regime", "")
        if reg == "REPLACE" and real not in (0, None): issues.append(f"REPLACE trained on {real} real tokens")
        for k, v in (("training-text duplicates", gen.get("exact_duplicate_rate")), ("training-text empty", gen.get("empty_rate")),
                     ("sample duplicates", smp.get("exact_duplicate_rate")), ("sample empty", smp.get("empty_rate"))):
            if v is not None and v > 0.05: issues.append(f"{k} {v:.3f} > 0.05")
        info = (f"loss {t.get('loss_first', float('nan')):.3f}->{t.get('final_loss', float('nan')):.3f} " if t else "") + \
               (f"real {real or 0:,} syn {syn or 0:,} " if t else "") + \
               (f"gen dup {gen.get('exact_duplicate_rate', 0):.4f} " if gen else "") + \
               (f"sample dup {smp.get('exact_duplicate_rate', 0):.4f} empty {smp.get('empty_rate', 0):.4f}" if smp else "")
    lp = ms.get("log_ppl_heldout", {}).get("value")
    print(f"{cid:22s} g{g:>2}  metrics {len(ms):>2}  log_ppl {lp if lp is None else round(lp, 3)}  {info}  {'OK' if not issues else 'CHECK: ' + '; '.join(issues)}")
    if issues:
        anom.append((cid, g, issues))
print(f"\nsteps audited: {len(by)}; with anomalies: {len(anom)}")
for a in anom:
    print("  ", a)
