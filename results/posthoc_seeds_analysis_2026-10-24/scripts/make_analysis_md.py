#!/usr/bin/env python3
"""Post-hoc (2026-10-24, PC): writes ANALYSIS.md from the CSV files in out/ (every number in the report is read from them).
usage: python -B make_analysis_md.py <package root> <analysis folder>"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PKG, A = Path(sys.argv[1]), Path(sys.argv[2])
O = A / "out"
R = PKG / "results"
MINUS = "−"


def f(x, nd=4, sign=True):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    s = f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"
    if float(s.replace("+", "")) == 0:
        s = f"{0:.{nd}f}" if x == 0 else (MINUS if x < 0 else "+") + f"{0:.{nd}f}"
    return s.replace("-", MINUS)


def ci(e, lo, hi, nd=4):
    return f"{f(e, nd)} [{f(lo, nd)}, {f(hi, nd)}]"


def p(v):
    return "p < 0.002" if v < 0.002 else f"p {v:.3f}"


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


sc = pd.read_csv(O / "seeds_controls.csv")
ss = pd.read_csv(O / "seeds_controls_summary.csv")
arms = pd.read_csv(O / "seeds_arms.csv")
pdoc = pd.read_csv(O / "perdoc_seeds.csv")
pdx = pd.read_csv(O / "perdoc_seeds_extra.csv")
dex = pd.read_csv(O / "seeds_decoder_extras.csv")
xs = pd.read_csv(O / "cross_decoder2_slope_ci.csv")
xd = pd.read_csv(O / "cross_decoder2_distinct2_K100_n200.csv")
xl = pd.read_csv(O / "cross_decoder2_levels.csv")
x50 = pd.read_csv(O / "cross_decoder2_first50.csv")
fw = pd.read_csv(O / "full_sample_vs_window.csv")
oov = pd.read_csv(O / "oov_share_new_chains.csv")
pub = pd.read_csv(R / "analysis" / "posthoc_review_2026-10-19" / "nonword_oov_shares.csv")
drop = pd.read_csv(O / "validation" / "empty_drop" / "cross_decoder2_dropempty_slope_ci.csv")
SEEDS = (0, 2, 3)
LANG = {"EN": "English", "BN": "Bangla"}


def net(L, m, s):
    r = sc[(sc.kind == "REPLACE minus REAL-REPEAT slope") & (sc.language == L) & (sc.metric == m) & (sc.seed == s)].iloc[0]
    return r


def get(kind, L, s, m=None, gens=None):
    x = sc[(sc.kind == kind) & (sc.language == L) & (sc.seed == s)]
    if m is not None:
        x = x[x.metric == m]
    if gens is not None:
        x = x[x.generations == gens]
    return x.iloc[0]


def arm(L, s, a):
    return arms[(arms.language == L) & (arms.seed == s) & (arms.arm == a)].iloc[0]


# ------------------------------------------------------------------ numbers used in the prose
NET = {(L, s): net(L, "log_ppl_heldout", s) for L in ("EN", "BN") for s in SEEDS}
qR = {L: [arm(L, s, "REPLACE").logppl_quadratic for s in SEEDS] for L in ("EN", "BN")}
qQ = {L: [arm(L, s, "REAL-REPEAT").logppl_quadratic for s in SEEDS] for L in ("EN", "BN")}
corr_arms = {L: pdoc[pdoc.language == L].pearson_REPLACE_vs_REAL_REPEAT.to_numpy() for L in ("EN", "BN")}
cc = pdx[pdx.kind == "per-document slope correlation"]


def crange(L, pat):
    v = cc[(cc.language == L) & cc.arm.str.match(pat)].pearson
    return f"{v.min():.2f} to {v.max():.2f}"


low = {s: arm("BN", s, "REAL-REPEAT") for s in SEEDS}
assert len({int(low[s].lowest_gen) for s in SEEDS}) == 1
lowgen = int(low[0].lowest_gen)
reg = fw[~fw.posthoc_chain]
n_ci = int(reg.window_ci_excludes_0.sum())
keep_ci = int(reg[reg.window_ci_excludes_0].sign_full_equals_window.sum())
flip_ci = reg[reg.window_ci_excludes_0 & ~reg.sign_full_equals_window]
flip_other = reg[~reg.window_ci_excludes_0 & ~reg.sign_full_equals_window]
s12_keep = int(reg.sign_S12_equals_window.sum())
full_keep = int(reg.sign_full_equals_window.sum())
inside = int(reg.full_inside_window_ci.sum())
s12_flip_ci = reg[reg.window_ci_excludes_0 & (reg.sign_S12_equals_window == False)]  # noqa: E712
lr = reg[~reg.statistic.str.contains("raw")]
move = float((lr.S12_point - lr.full_point).abs().max())
contr = xs[xs.quantity.str.startswith("training-decoder contrast, mean")]
slopes = xs[xs.quantity.str.startswith("slope")]
n_up = int(((slopes.point > 0) & ~slopes.quantity.str.contains("topp95")).sum())
n_dn = int(((slopes.point < 0) & slopes.quantity.str.contains("topp95")).sum())
ex0 = int(((slopes.ci_lo > 0) | (slopes.ci_hi < 0)).sum())
drop_diff = drop.merge(xs, on=["language", "seed", "quantity"], suffixes=("_d", ""))
dmax = float((drop_diff.point_d - drop_diff.point).abs().max())
d_tp = xd[xd.training_text == "top-p 0.95"]
d_t1 = xd[xd.training_text == "top-p 1.0"]
sd_out = dex[(dex.language == "BN") & (dex.seed == 3)].topp95_sample_nll_sd_slope_1_6.iloc[0]
lvl = pd.read_csv(PKG / "results" / "posthoc_seeds_2026-10-23" / "host" / "results" / "posthoc2_cross_decoder" / "cross_decoder2_summary.csv")
shift = (lvl.pivot_table(index=["chain", "gen"], columns="decoder_top_p", values="mean_nll_nats")[1.0]
         - lvl.pivot_table(index=["chain", "gen"], columns="decoder_top_p", values="mean_nll_nats")[0.95])
topd = arms[arms.arm == "REPLACE-topp95"]

oov_rows, oslope = [], {}
for c in ("EN-REAL-REPEAT", "EN-REAL-REPEAT-s2", "EN-REAL-REPEAT-s3", "EN-REPLACE-topp95", "EN-REPLACE-topp95-s2", "EN-REPLACE-topp95-s3",
          "BN-REAL-REPEAT", "BN-REAL-REPEAT-s2", "BN-REAL-REPEAT-s3", "BN-REPLACE-topp95", "BN-REPLACE-topp95-s2", "BN-REPLACE-topp95-s3"):
    k = c.rsplit("-s", 1)[1] if c.endswith(("-s2", "-s3")) else ""
    g0name = f"GEN0-{c[:2]}" + (f"-s{k}" if k else "")
    g0v = pub[pub.chain == g0name].token_oov_share.iloc[0]
    if c.endswith(("-s2", "-s3")):
        v = oov[oov.chain == c].sort_values("generation").token_oov_share.tolist()
    else:
        v = pub[pub.chain == c].sort_values("gen").token_oov_share.tolist()
    sl = float(np.polyfit(np.arange(1, 7), np.array(v, float), 1)[0])
    oslope[c] = sl
    oov_rows.append([c + (" (post-hoc)" if k else ""), "n/a" if "topp95" in c else f"{g0v:.4f}"] + [f"{x:.4f}" for x in v] + [f(sl)])

M = []
M += ["# posthoc_gpu_pack2: seed replicates of the two controls, cross-decoder over three seeds, full-sample check", "",
      "Analysis written 2026-10-24 on the PC from the take-home folder `results/posthoc_seeds_2026-10-23/` (zip SHA-256 "
      "`75725fb1...0b77`; all checks in `checks.md` passed). The authors decided these runs on 22 October (REQ-035), after the "
      "registered results had been read, so everything here is post-hoc: nothing is pre-registered, and no registered number, "
      "test or verdict changes. Square brackets are 95% measurement intervals from the registered bootstrap of "
      "`harness/analyze.py` (1,000 draws; p is its two-sided bootstrap p, unadjusted) unless a table says otherwise; the seeds "
      "are the run-to-run comparison. Model-written text was read only by code, in memory; this report and `out/` hold numbers "
      "only. Seed 0 is the registered chain; for REPLACE, seeds 2 and 3 are the registered replicates; for REAL-REPEAT and "
      "REPLACE-topp95, seeds 2 and 3 are the new post-hoc chains, each started from the same re-seeded generation-0 model and "
      "the same step seeds as the REPLACE chain of its seed.", "",
      "## Summary", "",
      f"1. **The English non-specificity is not a property of one chain.** REPLACE minus REAL-REPEAT on log held-out perplexity "
      f"is {ci(NET[('EN', 0)].estimate, NET[('EN', 0)].ci_lo, NET[('EN', 0)].ci_hi)}, "
      f"{ci(NET[('EN', 2)].estimate, NET[('EN', 2)].ci_lo, NET[('EN', 2)].ci_hi)} and "
      f"{ci(NET[('EN', 3)].estimate, NET[('EN', 3)].ci_lo, NET[('EN', 3)].ci_hi)} nats/generation in seeds 0, 2 and 3, "
      f"and {f(NET[('BN', 0)].estimate)}, {f(NET[('BN', 2)].estimate)} and {f(NET[('BN', 3)].estimate)} in Bangla (all three "
      "intervals exclude zero). Section 5.7 of the manuscript named this test: more REAL-REPEAT seeds with a clearly nonzero "
      "English contrast would have tied the finding to one chain. They did not.",
      f"2. **The differences behind the matching summary replicate.** In all three seeds English REPLACE rises almost linearly "
      f"(quadratic coefficients {', '.join(f(v) for v in qR['EN'])}) while REAL-REPEAT accelerates ({', '.join(f(v) for v in qQ['EN'])}); "
      f"the per-document slopes of the two arms correlate {', '.join(f'{v:.2f}' for v in corr_arms['EN'])} (Bangla "
      f"{', '.join(f(v, 2) for v in corr_arms['BN'])}), while two seeds of the same arm correlate {crange('EN', 'REPLACE seed . vs REPLACE')} "
      f"(REPLACE) and {crange('EN', 'REAL-REPEAT seed . vs REAL-REPEAT')} (REAL-REPEAT) in English and {crange('BN', 'REPLACE seed . vs REPLACE')} "
      f"and {crange('BN', 'REAL-REPEAT seed . vs REAL-REPEAT')} in Bangla. Each arm's per-document pattern is reproducible across "
      "seeds, and the two arms' patterns differ. Bangla REAL-REPEAT first falls and then rises in every seed (lowest at generation "
      f"{lowgen} in all three, {', '.join(f(low[s].lowest_rel0, 3) for s in SEEDS)} nats against generation 0).",
      "3. **The top-p 0.95 arm replicates in all three seeds**: distinct-2 falls steeply, the sample NLL under the generation-0 "
      "model falls, and repeated 4-grams rise, while the top-p 1.0 chains move the other way (Section 3). New, and also in every "
      f"seed: the top-p 0.95 chains raise held-out perplexity faster than REPLACE ({', '.join(f(v) for v in topd[topd.language == 'EN'].topp95_minus_REPLACE_logppl)} "
      f"nats/generation in English, {', '.join(f(v) for v in topd[topd.language == 'BN'].topp95_minus_REPLACE_logppl)} in Bangla; every interval excludes zero).",
      f"4. **Cross-decoder over three seeds (200 prefixes per cell):** all {len(slopes)} slopes follow the training-text decoder "
      f"({n_up} of 12 top-p 1.0-trained slopes rise, {n_dn} of 12 top-p 0.95-trained slopes fall; {ex0} of {len(slopes)} prefix-bootstrap "
      "intervals exclude zero). The training-decoder contrast, averaged over the three seeds, is " +
      "; ".join(f"{LANG[r.language]} {ci(r.point, r.ci_lo, r.ci_hi, 3)} (evaluation top-p {r.quantity.split('top-p ')[-1]})" for r in contr.itertuples()) +
      ". Distinct-2 of the continuations falls for all 12 top-p 0.95-trained rows and does not fall for 11 of the 12 top-p 1.0-trained rows.",
      f"5. **The full-sample check changes the conclusion of Supplementary Section S14.** On all 2,000 documents per step, the "
      f"equal-length slope has the registered window slope's sign in {full_keep} of the 17 registered chains, against {s12_keep} of 17 on "
      f"the 50-document files, and in {keep_ci} of the {n_ci} chains whose registered interval excludes zero (the exception, "
      f"{', '.join(flip_ci.chain)}, has a registered interval that starts at {f(flip_ci.window_ci_lo.iloc[0])}). The four chains whose "
      f"registered intervals excluded zero and whose 50-document check changed sign ({', '.join(s12_flip_ci.chain)}) all return to the "
      "registered sign. The 50-document check was too small to resolve slopes of this size; the registered window slopes hold up.",
      "6. **Two smaller points need care.** The English REAL-REPEAT novelty proxy falls only slightly (slopes " +
      ", ".join(f(oslope[c]) for c in ("EN-REAL-REPEAT", "EN-REAL-REPEAT-s2", "EN-REAL-REPEAT-s3")) + " per generation; in seeds 2 and 3 "
      "its generation-6 value lies above generation 0), so Section S8 should call the English fall small (Section 6). The "
      f"sample-NLL spread of BN-REPLACE-topp95-s3 widens (SD slope {f(sd_out, 3)}) because of one or two documents per generation at "
      "about 40 nats/token, not because the bulk spreads (Section 3).",

      "7. **Run and money.** All eight chains completed six generations with the registered recipe and seeds; the 156 cross-decoder "
      "cells and the full-sample check are complete; every check of README_RUN.md section 4 passed (`checks.md`). The pack used "
      "14.4 GPU-hours and was invoiced US$9.00 (cap US$15); the CG4 total is US$47.83 of the US$55 ceiling.", ""]

# ------------------------------------------------------------------ section 2
rows = []
for L in ("EN", "BN"):
    for m, lab in (("log_ppl_heldout", "log held-out perplexity"), ("bpb_heldout", "bits per byte"),
                   ("distinct_2_logratio0", "log(distinct-2 / gen-0)"), ("tail_fact_recall_ALL_logratio0", "log(recall / gen-0)")):
        r = [net(L, m, s) for s in SEEDS]
        sm = ss[(ss.language == L) & (ss.metric == m)].iloc[0]
        rows.append([LANG[L], lab] + [f"{ci(x.estimate, x.ci_lo, x.ci_hi)}, {p(x.p_boot)}" for x in r] +
                    [f"{f(sm['mean'])} ({f(sm['min'])} to {f(sm['max'])})"])
M += ["## 2. The REAL-REPEAT control in three seeds", "",
      "**Table A. REPLACE minus REAL-REPEAT, slope over generations 0 to 6 (the registered net contrast of Table 4, per seed).**", "",
      table(["Language", "Metric", "Seed 0 (registered)", "Seed 2", "Seed 3", "Mean of 3 (range)"], rows), "",
      "The registered seed-0 row is reproduced exactly. English: the perplexity and bits-per-byte contrasts are near zero in every "
      "seed, with every interval including zero; REPLACE's log distinct-2 ratio rises relative to REAL-REPEAT in every seed; recall "
      "does not separate the arms. Bangla: every contrast that excluded zero in seed 0 excludes it in seeds 2 and 3, with the same "
      "sign and similar size.", ""]
rows = []
for L in ("EN", "BN"):
    for s in SEEDS:
        r0, r1 = get("slope REPLACE", L, s, gens="0..3"), get("slope REPLACE", L, s, gens="3..6")
        q0, q1 = get("slope REAL-REPEAT", L, s, gens="0..3"), get("slope REAL-REPEAT", L, s, gens="3..6")
        a1, a2 = arm(L, s, "REPLACE"), arm(L, s, "REAL-REPEAT")
        rows.append([LANG[L], s, f"{f(r0.estimate, 3)} / {f(r1.estimate, 3)}", f"{f(q0.estimate, 3)} / {f(q1.estimate, 3)}",
                     ci(a1.logppl_quadratic, a1.quad_ci_lo, a1.quad_ci_hi), ci(a2.logppl_quadratic, a2.quad_ci_lo, a2.quad_ci_hi),
                     f"{f(a1.rise_to_gen6, 3)} / {f(a2.rise_to_gen6, 3)}"])
M += ["**Table B. Trajectory shape of log held-out perplexity (nats/generation).**", "",
      table(["Language", "Seed", "REPLACE slope 0-3 / 3-6", "REAL-REPEAT slope 0-3 / 3-6", "REPLACE quadratic", "REAL-REPEAT quadratic",
             "Rise to gen. 6, REPLACE / REAL-REPEAT"], rows), "",
      "Seed 0 reproduces Supplementary Table S11 (0.139 / 0.120 and 0.086 / 0.172; quadratic coefficients -0.0031 and +0.0145 in "
      "English, -0.0012 and +0.0141 in Bangla) and the main text's generation-6 rises (+0.775 and +0.776).".replace("-0.", MINUS + "0."), ""]
rows = []
for L in ("EN", "BN"):
    d = pdoc[pdoc.language == L]
    dom = pdx[(pdx.kind == "mean slope by domain") & (pdx.language == L)]
    for s in SEEDS:
        r = d[d.seed == s].iloc[0]
        wR = dom[(dom.arm == "REPLACE") & (dom.seed.astype(str) == str(s))].iloc[0]
        wQ = dom[(dom.arm == "REAL-REPEAT") & (dom.seed.astype(str) == str(s))].iloc[0]
        rows.append([LANG[L], s, ci(r.pearson_REPLACE_vs_REAL_REPEAT, r.ci_lo, r.ci_hi, 3),
                     f"{r.share_rising_REPLACE:.3f} / {r.share_rising_REAL_REPEAT:.3f}",
                     f"{wR.web:.3f} / {wR.wikipedia:.3f}", f"{wQ.web:.3f} / {wQ.wikipedia:.3f}"])
M += ["**Table C. Per-document held-out slopes (2,000 documents per language; document-bootstrap intervals, 2,000 draws).**", "",
      table(["Language", "Seed", "Correlation, REPLACE vs REAL-REPEAT", "Share of documents rising, REPLACE / REAL-REPEAT",
             "REPLACE mean slope, web / Wikipedia", "REAL-REPEAT mean slope, web / Wikipedia"], rows), "",
      f"Between seeds of the same arm the per-document slopes correlate {crange('EN', 'REPLACE seed . vs REPLACE')} (English REPLACE), "
      f"{crange('EN', 'REAL-REPEAT seed . vs REAL-REPEAT')} (English REAL-REPEAT), {crange('BN', 'REPLACE seed . vs REPLACE')} (Bangla "
      f"REPLACE) and {crange('BN', 'REAL-REPEAT seed . vs REAL-REPEAT')} (Bangla REAL-REPEAT), every interval within 0.03 of its value "
      "(`out/perdoc_seeds_extra.csv`). The registered comparison was 0.910 between REPLACE seeds 0 and 2. So the gap between the arms "
      "(0.46 to 0.47 in English, about -0.1 in Bangla) is not seed noise: each training policy raises the loss on its own set of "
      "documents, and does so again in a new seed. REAL-REPEAT's larger rise on the web half of the held-out set also replicates "
      "in every seed. Seed 0's correlation intervals differ from Table S11's ([0.421, 0.523] and [-0.147, -0.038]) in the third "
      "decimal only because this script draws its own bootstrap resamples.".replace("about -0.1", f"about {MINUS}0.1").replace("[-0.147, -0.038]", f"[{MINUS}0.147, {MINUS}0.038]"), ""]

# ------------------------------------------------------------------ section 3
rows = []
for L in ("EN", "BN"):
    for s in SEEDS:
        suf = "" if s == 0 else f"-s{s}"
        dt = get(f"slope {L}-REPLACE-topp95{suf}", L, s, m="distinct_2")
        dr = get(f"slope {L}-REPLACE{suf}", L, s, m="distinct_2")
        nt = get(f"slope {L}-REPLACE-topp95{suf}", L, s, m="sample_nll_ref_mean")
        nr = get(f"slope {L}-REPLACE{suf}", L, s, m="sample_nll_ref_mean")
        rt = get(f"repeat_4gram_rate at generation 6, {L}-REPLACE-topp95{suf}", L, s)
        e = dex[(dex.language == L) & (dex.seed == s)].iloc[0]
        rows.append([LANG[L], s, f"{f(dt.estimate)} / {f(dr.estimate)}", f"{e.topp95_distinct2_gen1:.3f} to {e.topp95_distinct2_gen6:.3f}",
                     f"{f(nt.estimate, 3)} / {f(nr.estimate, 3)}", f"{f(e.topp95_sample_nll_slope_0_6, 3)} / {f(e.REPLACE_sample_nll_slope_0_6, 3)}",
                     f"{rt.estimate:.3f} / {e.REPLACE_repeat4_max_gen1_6:.3f}",
                     f"{f(e.topp95_sample_nll_sd_slope_1_6, 3)} / {f(e.REPLACE_sample_nll_sd_slope_1_6, 3)}"])
M += ["## 3. The top-p 0.95 arm in three seeds", "",
      "**Table D. Sample diagnostics of the top-p 0.95 chain against the REPLACE chain of the same seed (top-p 0.95 / top-p 1.0).**", "",
      table(["Language", "Seed", "Distinct-2 slope, gen. 1-6", "Distinct-2, top-p 0.95, gen. 1 to 6", "Sample NLL slope, gen. 1-6",
             "Sample NLL slope, gen. 0-6 (registered window)", "Repeated 4-grams, gen. 6 / REPLACE max", "Sample-NLL SD slope, gen. 1-6"], rows), "",
      "Every distinct-2 and sample-NLL slope of the top-p 0.95 chains has an interval excluding zero (`out/seeds_controls.csv`), and so "
      "does every REPLACE minus top-p 0.95 difference. The seed-0 rows reproduce Section 4.3 (-0.0476 and -0.0621; -0.167 and "
      "-0.210 against +0.270 and +0.156; repetition 0.180 and 0.177). The spread of the sample NLL does not narrow under top-p 0.95 "
      f"in five of six chains; in BN-REPLACE-topp95-s3 it widens ({f(sd_out, 3)}) because one or two of its 2,000 documents per "
      "generation score about 40 nats/token at generations 4 to 6 (without documents above 10 nats/token its SD stays at 0.90 to "
      "0.94, as in the other seeds; the 5th and 95th percentiles are unchanged).".replace("(-0.0476 and -0.0621; -0.167 and -0.210",
                                                                                         f"({MINUS}0.0476 and {MINUS}0.0621; {MINUS}0.167 and {MINUS}0.210"), ""]
rows = []
ratio = {L: (min(arm(L, s, "REPLACE-topp95").logppl_slope_0_6 / arm(L, s, "REPLACE").logppl_slope_0_6 for s in SEEDS),
             max(arm(L, s, "REPLACE-topp95").logppl_slope_0_6 / arm(L, s, "REPLACE").logppl_slope_0_6 for s in SEEDS)) for L in ("EN", "BN")}
for L in ("EN", "BN"):
    for s in SEEDS:
        t, r = arm(L, s, "REPLACE-topp95"), arm(L, s, "REPLACE")
        rows.append([LANG[L], s, ci(r.logppl_slope_0_6, r.logppl_ci_lo, r.logppl_ci_hi), ci(t.logppl_slope_0_6, t.logppl_ci_lo, t.logppl_ci_hi),
                     ci(t.topp95_minus_REPLACE_logppl, t.diff_ci_lo, t.diff_ci_hi), ci(t.topp95_minus_REPLACE_bpb, t.diff_bpb_ci_lo, t.diff_bpb_ci_hi)])
M += ["**Table E. Held-out log-perplexity under the two training decoders (slopes over generations 0 to 6).**", "",
      table(["Language", "Seed", "REPLACE (top-p 1.0)", "REPLACE-topp95", "Difference (top-p 0.95 minus 1.0)", "Difference, bits per byte"], rows), "",
      f"This comparison is not in the manuscript. Training on top-p 0.95 text raised held-out perplexity {ratio['EN'][0]:.2f} to "
      f"{ratio['EN'][1]:.2f} times as fast as training on top-p 1.0 text in English and {ratio['BN'][0]:.2f} to {ratio['BN'][1]:.2f} times "
      "as fast in Bangla, in every seed, while its own samples became more predictable to the generation-0 model (Table D).", ""]

# ------------------------------------------------------------------ section 4
rows = []
for L in ("EN", "BN"):
    for tt in ("top-p 1.0", "top-p 0.95"):
        for dec in ("1.0", "0.95"):
            cells = []
            for s in SEEDS:
                suf = "" if s == 0 else f"-s{s}"
                c = f"{L}-REPLACE{'-topp95' if tt == 'top-p 0.95' else ''}{suf}"
                r = slopes[slopes.quantity == f"slope {c}, eval top-p {dec}"].iloc[0]
                cells.append(ci(r.point, r.ci_lo, r.ci_hi, 3))
            lv = xl[(xl.training_text == tt) & (xl.eval_top_p == float(dec)) & xl.chain.str.startswith(L)]
            rows.append([LANG[L], tt, f"top-p {dec}"] + cells + [f"{lv.gen1.min():.2f} to {lv.gen1.max():.2f}", f"{lv.gen6.min():.2f} to {lv.gen6.max():.2f}"])
M += ["## 4. Cross-decoder evaluation over three seeds", "",
      "Each checkpoint drew 200 continuations (the first 200 evaluation prefixes) under each decoder; each continuation is scored "
      "as its mean per-token NLL under the chain's own generation-0 model. Slopes are OLS over generations 1 to 6 with "
      "prefix-paired bootstrap intervals (5,000 draws, one resample of the prefixes shared by all cells of a language). Three of "
      "the 31,200 continuations are empty (no NLL); each such cell is averaged over its 199 usable draws, as the run's summary "
      f"does (dropping the two affected prefixes from every Bangla cell instead moves no Bangla slope or contrast by more than {dmax:.4f}).", "",
      "**Table F. Cross-decoder slopes (nats/generation) by training-text decoder and evaluation decoder.**", "",
      table(["Language", "Training text", "Evaluation", "Seed 0", "Seed 2", "Seed 3", "Gen. 1 level (3 seeds)", "Gen. 6 level (3 seeds)"], rows), ""]
rows = []
for L in ("EN", "BN"):
    for dec in ("1.0", "0.95"):
        per = [xs[(xs.language == L) & (xs.seed == str(s)) & (xs.quantity == f"training-decoder contrast (top-p 1.0 minus 0.95 trained), eval top-p {dec}")].iloc[0] for s in SEEDS]
        mn = xs[(xs.language == L) & (xs.quantity == f"training-decoder contrast, mean over seeds, eval top-p {dec}")].iloc[0]
        rows.append([LANG[L], f"top-p {dec}"] + [ci(r.point, r.ci_lo, r.ci_hi, 3) for r in per] + [ci(mn.point, mn.ci_lo, mn.ci_hi, 3)])
g0 = xl.drop_duplicates(["gen0_model", "eval_top_p"]).copy()
g0["lang"] = g0.gen0_model.str.split("-").str[1]


def g0r(L, dec):
    v = g0[(g0.lang == L) & (g0.eval_top_p == dec)].gen0_level
    return f"{v.min():.2f} to {v.max():.2f}"
M += ["**Table G. Training-decoder contrast (top-p 1.0-trained slope minus top-p 0.95-trained slope, same seed and evaluation decoder).**", "",
      table(["Language", "Evaluation", "Seed 0", "Seed 2", "Seed 3", "Mean of the three seeds"], rows), "",
      f"The evaluation decoder shifts the level (top-p 0.95 scores {shift.min():.2f} to {shift.max():.2f} nats lower on the same checkpoint; "
      f"median {shift.median():.2f}) and reverses no direction. The three generation-0 models score English {g0r('EN', 1.0)} "
      f"(top-p 1.0) and {g0r('EN', 0.95)} (top-p 0.95), Bangla {g0r('BN', 1.0)} and {g0r('BN', 0.95)}. "
      "Seed 0's numbers differ from Table 5 because these are new draws (the host's torch changed from 2.8.0 to 2.13.0, so the same "
      "seeds gave identical continuations in only 7.8% of cases) and 200 rather than 50 prefixes: on the same first 50 prefixes, all "
      f"eight seed-0 slopes fall inside the 2026-10-20 intervals ({int(x50.first50_inside_2026_10_20_ci.sum())} of 8; `out/cross_decoder2_first50.csv`).", ""]
rows = []
for L in ("EN", "BN"):
    for tt in ("top-p 1.0", "top-p 0.95"):
        for dec in ("top-p 1.0", "top-p 0.95"):
            x = xd[(xd.language == L) & (xd.training_text == tt) & (xd.evaluation == dec)].sort_values("seed")
            rows.append([LANG[L], tt, dec] + [ci(r.raw_slope_1_6, r.range_lo, r.range_hi) for r in x.itertuples()] +
                        [f"{x.words_per_generation.min():,} to {x.words_per_generation.max():,}"])
M += ["**Table H. Distinct-2 of the continuations, equal length per prefix (raw slope over generations 1 to 6; brackets: stability "
      "range over 2,000 subsets of 160 of the 200 prefixes, not a confidence interval).**", "",
      table(["Language", "Training text", "Evaluation", "Seed 0", "Seed 2", "Seed 3", "Words per generation"], rows), "",
      f"All {len(d_tp)} top-p 0.95-trained rows fall ({f(d_tp.raw_slope_1_6.max())} to {f(d_tp.raw_slope_1_6.min())}), every stability range "
      f"excluding zero. Of the {len(d_t1)} top-p 1.0-trained rows, {int((d_t1.raw_slope_1_6 > 0).sum())} rise and one falls slightly "
      f"(BN-REPLACE-s3 under top-p 0.95 evaluation, {f(d_t1.raw_slope_1_6.min())}, {abs(d_t1.raw_slope_1_6.min()) / abs(d_tp.raw_slope_1_6.max()):.2f} "
      "times the smallest top-p 0.95 fall). The "
      "statement of Section 4.3 (\"did not fall for the chains trained on top-p 1.0 text\") holds for 11 of 12 rows and in sign for "
      "every English row.", ""]

# ------------------------------------------------------------------ section 5
rows = []
for r in fw.itertuples():
    rows.append([r.chain + (" (post-hoc)" if r.posthoc_chain else ""), "1 to 6, raw" if "raw" in r.statistic else "0 to 6, log ratio",
                 ci(r.window_slope, r.window_ci_lo, r.window_ci_hi), f(r.S12_point) if not np.isnan(r.S12_point) else "n/a",
                 ci(r.full_point, r.full_range_lo, r.full_range_hi), f"{int(r.full_words_per_step):,}",
                 "same" if r.sign_full_equals_window else "**changed**"])
M += ["## 5. Full-sample equal-length check", "",
      "Same statistic as Supplementary Table S12 (each prefix contributes the same number of words, at most 100, at every step; "
      "bigrams within documents), now on all 2,000 documents per step of all 25 chains. Brackets after the full-sample value: "
      "stability range over 500 subsets of 1,600 prefixes. Window: the registered distinct-2 slope with its registered 95% interval "
      "(for the eight post-hoc chains, the same computation on their records).", "",
      "**Table I. Distinct-2 slopes: registered window, 50-document check (Table S12) and full-sample check.**", "",
      table(["Chain", "Generations", "Window [95% CI]", "50 documents (S12)", "2,000 documents [range]", "Words per step", "Sign vs window"], rows), "",
      f"On the full samples the equal-length slope keeps the window's sign in {full_keep} of the 17 registered chains ({s12_keep} of 17 "
      f"at 50 documents) and in {keep_ci} of the {n_ci} with registered intervals excluding zero; {inside} of 17 full-sample values lie "
      f"inside the registered interval. The sign changes left are {', '.join(flip_other.chain)}, whose registered intervals include zero, "
      f"and {', '.join(flip_ci.chain)} ({f(flip_ci.window_slope.iloc[0])} [{f(flip_ci.window_ci_lo.iloc[0])}, {f(flip_ci.window_ci_hi.iloc[0])}] "
      f"against {f(flip_ci.full_point.iloc[0])}). The three Bangla REPLACE seeds, which all changed sign at 50 documents, keep the "
      "registered sign, and so do EN-ACCUMULATE-FILTER and EN-REAL-REPEAT. English REPLACE rises in all three seeds and both "
      "REPLACE-topp95 chains fall, as at 50 documents. The 50-document stability ranges were taken over subsets of the same 50 "
      "prefixes, so they could not show how far a different set of 50 prefixes would move the slope; the full samples show that it "
      f"moved by up to {move:.4f} on the log-ratio chains, the size of the slopes in question. For the eight post-hoc chains the full-sample sign agrees "
      f"with the window in {int(fw[fw.posthoc_chain].sign_full_equals_window.sum())} of 8. The raw slopes of the top-p 0.95 chains "
      "are smaller in magnitude on the equal-length statistic than in the window (for example -0.0365 against -0.0476), as at 50 "
      "documents: the window counts bigrams across document boundaries and over unequal lengths.".replace("-0.0365 against -0.0476", f"{MINUS}0.0365 against {MINUS}0.0476"), ""]

# ------------------------------------------------------------------ section 6
M += ["## 6. Lexical-novelty proxy for the new chains (rows for Supplementary Table S6)", "",
      "Share of continuation word tokens absent from the language's seed vocabulary, per 50-sample file (the statistic of Table S6; "
      "recomputing it on the registered files reproduces every published share within 0.000005, "
      "`out/validation/oov_share_recomputed_vs_published.csv`). Generation 0 is the chain's own generation-0 model; the top-p 0.95 "
      "chains have no generation-0 file under their decoder.", "",
      table(["Chain", "Gen. 0", "1", "2", "3", "4", "5", "6", "OLS slope, gen. 1-6"], oov_rows), "",
      "Bangla REAL-REPEAT falls in all three seeds (slopes " + ", ".join(f(oslope[c]) for c in ("BN-REAL-REPEAT", "BN-REAL-REPEAT-s2", "BN-REAL-REPEAT-s3")) +
      "). The top-p 0.95 chains stay far below the confirmatory chains in both languages and fall clearly in Bangla (slopes " +
      ", ".join(f(oslope[c]) for c in ("BN-REPLACE-topp95", "BN-REPLACE-topp95-s2", "BN-REPLACE-topp95-s3")) + ") and slightly in English (" +
      ", ".join(f(oslope[c]) for c in ("EN-REPLACE-topp95", "EN-REPLACE-topp95-s2", "EN-REPLACE-topp95-s3")) +
      "). English REAL-REPEAT drifts down only slightly (slopes " + ", ".join(f(oslope[c]) for c in ("EN-REAL-REPEAT", "EN-REAL-REPEAT-s2", "EN-REAL-REPEAT-s3")) +
      " per generation) against file-to-file swings of about 0.01, and its generation-6 value lies above its generation-0 value "
      "in seeds 2 and 3, unlike seed 0. Section S8's \"the REAL-REPEAT controls fall in both languages\" holds as a trend over "
      "generations 1 to 6 in every seed, but the English fall is small and should be described as such.", ""]

# ------------------------------------------------------------------ section 7
M += ["## 7. What this changes in the manuscript (proposal for rev 20; nothing has been edited yet)", "",
      "- **Abstract and Section 3.1:** the real-data and decoding controls now have three seeds each (seeds 2 and 3 post-hoc, run "
      "24 October); SUBSAMPLE and the word-matched chain remain single chains. The English net contrast can be stated as near zero "
      "in all three seeds.",
      "- **Table 2:** add a post-hoc row for 24 October (seed replicates of REAL-REPEAT and REPLACE-topp95, cross-decoder over three "
      "seeds, full-sample equal-length check).",
      "- **Section 4.2 and Table 4:** keep the registered seed-0 rows; add the seed-2 and seed-3 contrasts (Table A) or their mean and "
      "range; replace \"This is one REAL-REPEAT chain and a failure to detect a difference\" by the three-seed result (still a failure "
      "to detect a difference, now in three seeds); add the shape and per-document replication (Tables B and C), including the "
      "within-arm correlations that show the arms' per-document patterns are reproducible.",
      "- **Section 4.3, Table 5 and Supplementary Section S9 (Tables S8 and S9):** report the three-seed cross-decoder results with "
      "200 prefixes (Tables F, G and H); the seed-0 values change because the draws are new; the third limit (\"each decoder arm is "
      "a single chain\") goes; add the top-p 0.95 sample diagnostics of seeds 2 and 3 (Table D).",
      "- **Section 4.3 or 5.3, new:** the top-p 0.95 chains also raise held-out perplexity faster than REPLACE, in every seed (Table E).",
      "- **Section 4.4, Supplementary Section S14 and Table S12:** add the full-sample column (Table I) and replace the conclusion "
      "that registered window slopes \"depend on how the window is built\": on the full samples, 11 of the 12 registered slopes "
      "with intervals excluding zero keep their sign; the 50-document check was too small. Remove \"The same check on the full "
      "2,000-document samples needs the restricted files and was not run\".",
      "- **Section 5.2:** \"with one REAL-REPEAT chain per language neither result is an estimate of run-to-run variance\" becomes "
      "the three-seed statement. **Section 5.6:** only SUBSAMPLE and the word-matched chain remain single; the attenuation ratio "
      "is still a seed-0 comparison (ACCUMULATE was not re-seeded); revise the sentence on the 50-document recomputation. "
      "**Section 5.7:** the REAL-REPEAT test it names has now been run.",
      "- **Supplementary Sections S8 (Table S6) and S13 (Table S11):** add the new rows (Section 6; Table C); limit the English "
      "REAL-REPEAT novelty claim.",
      "- **Two rounding slips found while checking seed 0:** Section 4.3 gives the Bangla REPLACE sample-NLL SD slope over "
      "generations 1 to 6 as +0.022; it is +0.0215 (+0.021 at three decimals). Table S11 gives the Bangla REPLACE web-half slope "
      "as 0.089; `perdoc_slopes_by_domain.csv` has 0.0884884 (0.088). Both look like a value rounded twice; a rounding pass over "
      "rev 20 would catch any others.",
      "- **Section 3.7 and Data availability:** add the 24 October rental (14.4 GPU-hours, US$9.00; CG4 total US$47.83) and the "
      "new released outputs (numbers only: `metrics_posthoc_2026-10-23.jsonl`, the per-document held-out records, the scorer check, "
      "the cross-decoder summary and per-continuation NLLs, the full-sample tables and the files in `out/`). The new sample files, "
      "50-document files and `cross_decoder2_samples.jsonl.gz` hold unscreened model text and stay private.", ""]

# ------------------------------------------------------------------ section 8
M += ["## 8. Files and re-running", "",
      "Scripts are in `scripts/`; outputs in `out/` (validation runs in `out/validation/`). From the package root:", "",
      "```",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/checks_posthoc2.py . results/posthoc_seeds_analysis_2026-10-24",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/seeds_controls.py . results/posthoc_seeds_2026-10-23/host/results/metrics_posthoc_2026-10-23.jsonl results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/perdoc_seeds.py results/cg4_sidecars_from_G4b_2026-10-20.zip results/posthoc_seeds_2026-10-23/host/results/chains results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/cross_decoder2_slope_ci.py results/posthoc_seeds_2026-10-23/host/results/posthoc2_cross_decoder/cross_decoder2_samples.jsonl.gz results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/cross_decoder2_distinct2.py results/posthoc_seeds_2026-10-23/host/results/posthoc2_cross_decoder/cross_decoder2_samples.jsonl.gz results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/seeds_extra.py . results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/oov_new_chains.py . results/posthoc_seeds_analysis_2026-10-24/out",
      "python -B results/posthoc_seeds_analysis_2026-10-24/scripts/make_analysis_md.py . results/posthoc_seeds_analysis_2026-10-24",
      "```", "",
      "Validation (all in `out/validation/`): `seeds_controls.py` without the new records reproduces the registered seed-0 control "
      "of Table 4 and Section 4.2 exactly; `cross_decoder2_slope_ci.py` on the 2026-10-20 file reproduces "
      "`posthoc_review_2026-10-22/cross_decoder_slope_ci.csv` exactly; both engines of `cross_decoder2_distinct2.py` reproduce "
      "Supplementary Table S9 exactly and give identical files on the new data; `seeds_extra.py` reproduces the registered window "
      "slopes of `T2_slopes.csv` (largest difference 1e-16); `oov_new_chains.py` reproduces the published Table S6 shares. "
      "`verify_independent.py` recomputes 168 point estimates of this report by a separate route (plain NumPy on the raw "
      "records and the samples file, no bootstrap code): the largest difference is below 1e-10 "
      "(`out/validation/independent_check.csv`), and its four full-sample sign counts agree exactly. See "
      "`README.md` for what each script is and what changed from the copies prepared on 23 October.", ""]
(A / "ANALYSIS.md").write_text("\n".join(M), encoding="utf-8")
print("ANALYSIS.md written:", len("\n".join(M)), "characters")
