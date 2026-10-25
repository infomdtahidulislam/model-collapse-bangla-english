#!/usr/bin/env python
"""Offline test of harness/analyze.py on synthetic metrics with known trends; no real result is read.

Builds a metrics.jsonl for every chain of configs/chains.yaml (and the generation-0 and base models), with linear trends for
log-scale metrics and exponential trends for positive metrics (so that their log ratio to generation 0 is linear) and narrow
CIs, runs `analyze.py --robustness --no-log` into a temporary folder, and checks the slopes, the H0/H1/H2 estimates, the Holm
adjustment, the floor rule, the three outputs of the decision rule, the controls and the reproducibility of the bootstrap.

usage: python harness/tests/test_analyze.py
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

HARNESS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HARNESS))
from common import chain_meta, load_chains_cfg  # noqa: E402

LOGSCALE = {"log_ppl_heldout": 3.0, "bpb_heldout": 1.2, "log_ppl_fresh": 3.2, "bpb_fresh": 1.3, "sample_nll_ref_mean": 4.0}
POSITIVE = {"distinct_2": 0.8, "tail_fact_recall_ALL": 0.6, "tail_fact_recall_HEAD": 0.7, "tail_fact_recall_MID": 0.6,
            "tail_fact_recall_TAIL": 0.5, "tail_fact_recall_norm_ALL": 0.6, "distinct_char5": 0.5, "mtld": 80.0,
            "stereotype_preference": 0.55, "fertility_tokens_per_word": 1.5, "sample_nll_ref_sd": 0.8, "sample_nll_ref_p5": 3.0,
            "sample_nll_ref_p95": 5.0, "mean_length_words": 160.0}
# log-scale slope per generation by (language, regime); positive metrics get minus half of it as their log slope
K_LOG = {("EN", "REPLACE"): 0.10, ("EN", "ACCUMULATE"): 0.02, ("EN", "ACCUMULATE-FILTER"): 0.03, ("EN", "REAL-REPEAT"): 0.01,
         ("EN", "ACCUMULATE-SUBSAMPLE"): 0.04, ("BN", "REPLACE"): 0.20, ("BN", "ACCUMULATE"): 0.08, ("BN", "ACCUMULATE-FILTER"): 0.09,
         ("BN", "REAL-REPEAT"): 0.02, ("BN", "ACCUMULATE-SUBSAMPLE"): 0.10}
GEN0 = ["GEN0-EN", "GEN0-BN", "GEN0-EN-s2", "GEN0-BN-s2", "GEN0-EN-s3", "GEN0-BN-s3", "GEN0-EN-WM"]
FAILS: list[str] = []


def check(cond: bool, what: str) -> None:
    print(("ok    " if cond else "FAIL  ") + what)
    if not cond:
        FAILS.append(what)


def default_k() -> tuple[dict, dict]:
    meta = chain_meta(load_chains_cfg())
    kl = {cid: K_LOG[(m["language"], m["regime"])] for cid, m in meta.items()}
    return kl, {cid: -v / 2 for cid, v in kl.items()}


def build(path: Path, kl: dict, kp: dict, gen0_override: dict | None = None) -> None:
    meta = chain_meta(load_chains_cfg())
    recs = []

    def rec(cid, g, m, v, lo, hi):
        recs.append({"chain_id": cid, "generation": g, "metric": m, "value": v, "ci_lo": lo, "ci_hi": hi, "n": 2000,
                     "checkpoint": "synthetic", "computed_at": "synthetic", "language": cid.split("-")[1] if cid.startswith(("GEN0-", "BASE-")) else cid[:2]})

    for g0 in GEN0 + ["BASE-EN", "BASE-BN"]:
        g = -1 if g0.startswith("BASE") else 0
        for m, b in LOGSCALE.items():
            rec(g0, g, m, b, b - 0.001, b + 0.001)
        for m, b in POSITIVE.items():
            v, lo, hi = (gen0_override or {}).get((g0, m), (b, b * 0.999, b * 1.001))
            rec(g0, g, m, v, lo, hi)
    for cid, m in meta.items():
        top = 10 if cid in ("EN-REPLACE", "BN-REPLACE") else 6
        g0 = m.get("gen0") or f"GEN0-{m['language']}"
        for g in range(1, top + 1):
            for met, b in LOGSCALE.items():
                v = b + kl[cid] * g
                rec(cid, g, met, v, v - 0.001, v + 0.001)
            for met, b in POSITIVE.items():
                b0 = (gen0_override or {}).get((g0, met), (b,))[0]
                v = b0 * math.exp(kp[cid] * g)
                rec(cid, g, met, v, v * 0.999, v * 1.001)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def run(tmp: Path, name: str, kl: dict, kp: dict, gen0_override: dict | None = None) -> Path:
    d = tmp / name
    d.mkdir()
    build(d / "metrics.jsonl", kl, kp, gen0_override)
    out = d / "analysis"
    r = subprocess.run([sys.executable, str(HARNESS / "analyze.py"), "--robustness", "--no-log", "--metrics", str(d / "metrics.jsonl"),
                        "--screening", str(d / "none.jsonl"), "--extract", str(d / "no_extract"), "--novelty", str(d / "none.jsonl"),
                        "--extra", "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-4000:])
        raise SystemExit(f"analyze.py failed in scenario {name}")
    return out


def get(df: pd.DataFrame, **kw) -> pd.Series:
    sub = df
    for k, v in kw.items():
        sub = sub[sub[k] == v]
    assert len(sub) == 1, (kw, len(sub))
    return sub.iloc[0]


def main() -> None:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        kl, kp = default_k()

        # 1. all registered predictions hold -> H0 PASS, H1 and H2 supported
        out = run(tmp, "main", kl, kp)
        rep = (out / "analysis_report.md").read_text(encoding="utf-8")
        t2 = pd.read_csv(out / "T2_slopes.csv")
        check(abs(get(t2, chain_id="EN-REPLACE", metric="log_ppl_heldout", generations="0..6")["slope"] - 0.10) < 1e-9, "T2 slope EN-REPLACE log ppl = 0.10")
        check(abs(get(t2, chain_id="BN-REPLACE", metric="distinct_2_logratio0", generations="0..6")["slope"] + 0.10) < 1e-9, "T2 slope BN-REPLACE log d2 ratio = -0.10")
        check(abs(get(t2, chain_id="EN-REPLACE", metric="log_ppl_heldout", generations="0..10")["slope"] - 0.10) < 1e-9, "T2 extension slope 0..10")
        h0 = pd.read_csv(out / "H0_anchor.csv")
        check(bool(h0["sign_ok"].all()) and bool((abs(h0["ratio_abs"] - 0.2) < 1e-9).all()), "H0 signs ok and ratios 0.2")
        check("H0 rule output: PASS" in rep, "H0 rule output PASS")
        ht = pd.read_csv(out / "H_tests.csv")
        h1 = ht[(ht["hypothesis"] == "H1") & ht["role"].isna()] if "role" in ht else ht[ht["hypothesis"] == "H1"]
        exp1 = {"log_ppl_heldout": 0.10, "distinct_2_logratio0": -0.05, "tail_fact_recall_ALL_logratio0": -0.05}
        for m, e in exp1.items():
            r = get(h1, metric=m)
            check(abs(r["estimate"] - e) < 1e-9 and r["sign_ok"] and r["p_holm"] < 0.05, f"H1 {m} = {e:+.2f}, predicted sign, Holm p < 0.05")
        h2 = ht[(ht["hypothesis"] == "H2") & ht["role"].isna()]
        exp2 = {"log_ppl_heldout": 0.6 - 0.8, "distinct_2_logratio0": -0.6 + 0.8, "tail_fact_recall_ALL_logratio0": -0.6 + 0.8}
        for m, e in exp2.items():
            r = get(h2, metric=m)
            check(abs(r["estimate"] - e) < 1e-9 and r["sign_ok"], f"H2 {m} = {e:+.2f} with the predicted sign")
        r = get(h2, metric="log_ppl_heldout")
        check(abs(r["abs_secondary"] - ((0.20 - 0.08) - (0.10 - 0.02))) < 1e-9, "H2 secondary absolute difference = +0.04")
        dec = pd.read_csv(out / "H_decision.csv")
        check(set(dec[dec["hypothesis"] == "H1"]["rule_output"]) == {"supported"}, "H1 rule output supported")
        check(set(dec[dec["hypothesis"] == "H2"]["rule_output"]) == {"supported"}, "H2 rule output supported")
        sr = pd.read_csv(out / "H1_seed_replicates.csv")
        check(bool((sr["n_seeds"] == 3).all()) and bool(sr["all_predicted_sign"].all()), "seed replicates: 3 seeds, all with the predicted sign")
        ctl = pd.read_csv(out / "controls.csv")
        r = get(ctl, control="REPLACE net of REAL-REPEAT", language="EN", metric="log_ppl_heldout")
        check(abs(r["estimate"] - 0.09) < 1e-9, "control: EN REPLACE net of REAL-REPEAT = 0.09")
        r = get(ctl, control="slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English)", metric="log_ppl_heldout")
        check(abs(r["estimate"] - 0.10) < 1e-9, "control: BN-REPLACE vs EN-REPLACE-WM = 0.10")
        rob = pd.read_csv(out / "robustness.csv")
        check({i.split(" ")[0] for i in rob["item"]} >= {"(i)", "(ii)", "(iii)", "(iv)", "(v)", "(vi)"}, "robustness items (i)-(vi) present")
        q = pd.read_csv(out / "robustness_quadratic.csv")
        check(abs(get(q, chain_id="EN-REPLACE", metric="log_ppl_heldout")["quadratic_coef"]) < 1e-9, "quadratic term of a linear series = 0")
        for f in ("F1_primary.png", "F2_contrasts.png", "F3_recall_strata.png", "F5_length_check.png", "F6_nll_under_gen0.png", "T1_metrics.csv"):
            check((out / f).exists(), f"output {f} written")
        out2 = run(tmp, "main_again", kl, kp)
        check((out / "H_tests.csv").read_bytes() == (out2 / "H_tests.csv").read_bytes(), "bootstrap reproducible (identical H_tests.csv)")

        # 2. H0 ratio 0.8 -> FAIL; Bangla generation-0 recall at chance -> H1(iii) excluded; H2(i) wrong sign -> inconclusive
        kl2 = dict(kl, **{"EN-ACCUMULATE": 0.08})
        out = run(tmp, "h0fail_floor", kl2, kp, {("GEN0-BN", "tail_fact_recall_ALL"): (0.27, 0.24, 0.30)})
        rep = (out / "analysis_report.md").read_text(encoding="utf-8")
        check("H0 rule output: FAIL" in rep, "H0 FAIL when |ACC|/|REP| = 0.8")
        ht = pd.read_csv(out / "H_tests.csv")
        r = ht[(ht["hypothesis"] == "H1") & (ht["metric"] == "tail_fact_recall_ALL_logratio0")].iloc[0]
        check(bool(r["excluded"]), "floor rule: H1(iii) excluded")
        dec = pd.read_csv(out / "H_decision.csv")
        d1 = dec[dec["hypothesis"] == "H1"]
        check(len(d1) == 2 and set(d1["rule_output"]) == {"supported"}, "H1 decided on (i) and (ii) only: supported")
        check(set(dec[dec["hypothesis"] == "H2"]["rule_output"]) == {"inconclusive"}, "H2 inconclusive when one contrast has the wrong sign")

        # 3. Bangla degrades less than English -> H1 not supported
        kl3, kp3 = dict(kl), dict(kp)
        for s in ("", "-s2", "-s3"):
            kl3[f"EN-REPLACE{s}"], kl3[f"BN-REPLACE{s}"] = kl[f"BN-REPLACE{s}"], kl[f"EN-REPLACE{s}"]
            kp3[f"EN-REPLACE{s}"], kp3[f"BN-REPLACE{s}"] = kp[f"BN-REPLACE{s}"], kp[f"EN-REPLACE{s}"]
        out = run(tmp, "h1_not", kl3, kp3)
        dec = pd.read_csv(out / "H_decision.csv")
        check(set(dec[dec["hypothesis"] == "H1"]["rule_output"]) == {"not supported"}, "H1 not supported when every contrast has the wrong sign")
    print(f"\n{'RESULT: PASS' if not FAILS else f'RESULT: FAIL ({len(FAILS)} checks)'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
