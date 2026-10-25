#!/usr/bin/env python3
"""REQ-034: item-paired bootstrap sensitivity check (post-hoc, 2026-10-20).
Resamples the SAME evaluation items jointly across checkpoints and arms within
each language — held-out documents for log-perplexity, probes for recall — and
re-derives the key registered contrasts, the H0 attenuation ratio and the
REAL-REPEAT nets. Point estimates are asserted equal to the released values
(H0_anchor.csv, H_tests.csv, controls.csv) before any resampling is trusted.
Inputs: the released per-item sidecar bundle. CPU-only. B=10,000, seed 20261020.
"""
import json, os, math, csv
import numpy as np

ROOT = "cg4_sidecars_bundle/results/chains"
GENS = list(range(7))
B, SEED = 10000, 20261020
rng = np.random.default_rng(SEED)

def step_dir(chain, g):
    return os.path.join(ROOT, chain) if g == 0 else os.path.join(ROOT, chain, f"gen_{g}")

def heldout_vec(chain, g):
    d = {}
    for line in open(os.path.join(step_dir(chain, g), "heldout_nll.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        if r["set"] == "heldout":
            d[r["doc_id"]] = r["nll_total"] / r["n_tokens"]
    return d

def recall_vec(chain, g):
    by = {}
    for line in open(os.path.join(step_dir(chain, g), "probe_scores.jsonl"), encoding="utf-8"):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        by.setdefault(r["probe_id"], []).append(r)
    return {pid: (1.0 if min(cand, key=lambda r: r["nll_total"])["is_gold"] else 0.0) for pid, cand in by.items()}

def build(lang):
    traj = {"REPL": [(f"GEN0-{lang}", 0)] + [(f"{lang}-REPLACE", g) for g in range(1, 7)],
            "ACC":  [(f"GEN0-{lang}", 0)] + [(f"{lang}-ACCUMULATE", g) for g in range(1, 7)],
            "RR":   [(f"GEN0-{lang}", 0)] + [(f"{lang}-REAL-REPEAT", g) for g in range(1, 7)]}
    cols = sorted({cg for arm in traj.values() for cg in arm})
    colix = {cg: i for i, cg in enumerate(cols)}
    hv = {cg: heldout_vec(*cg) for cg in cols}
    ids = sorted(hv[cols[0]])
    for cg in cols:
        assert sorted(hv[cg]) == ids, f"held-out id mismatch {cg}"
    D = np.array([[hv[cg][i] for cg in cols] for i in ids])            # docs x ckpts
    rv = {cg: recall_vec(*cg) for cg in cols}
    pids = sorted(rv[cols[0]])
    for cg in cols:
        assert sorted(rv[cg]) == pids, f"probe id mismatch {cg}"
    C = np.array([[rv[cg][p] for cg in cols] for p in pids])           # probes x ckpts
    arm_ix = {a: np.array([colix[cg] for cg in traj[a]]) for a in traj}
    return D, C, arm_ix

X = np.arange(7, dtype=float); XC = X - X.mean(); XV = (XC**2).sum()
def slope(Y):          # Y: ... x 7
    return (Y * XC).sum(-1) / XV

def stats_from(meanD, meanC, arm_ix):
    """meanD/meanC: ... x n_ckpts arrays of per-checkpoint values."""
    out = {}
    s_ppl = {a: slope(meanD[..., arm_ix[a]]) for a in arm_ix}
    rec = {a: meanC[..., arm_ix[a]] for a in arm_ix}
    s_rec = {a: slope(np.log(rec[a] / rec[a][..., :1])) for a in arm_ix}
    out["slope_ppl"] = s_ppl; out["slope_rec"] = s_rec
    return out

def derive(en, bn):
    q = {}
    q["h0_ratio"] = abs(en["slope_ppl"]["ACC"]) / abs(en["slope_ppl"]["REPL"])
    q["h1_ppl"] = bn["slope_ppl"]["REPL"] - en["slope_ppl"]["REPL"]
    q["h1_recall"] = bn["slope_rec"]["REPL"] - en["slope_rec"]["REPL"]
    dppl_en = en["slope_ppl"]["REPL"] - en["slope_ppl"]["ACC"]
    dppl_bn = bn["slope_ppl"]["REPL"] - bn["slope_ppl"]["ACC"]
    q["h2_ppl_contrast"] = dppl_bn / np.abs(bn["slope_ppl"]["REPL"]) - dppl_en / np.abs(en["slope_ppl"]["REPL"])
    q["h2_ppl_abs"] = dppl_bn - dppl_en
    drec_en = en["slope_rec"]["REPL"] - en["slope_rec"]["ACC"]
    drec_bn = bn["slope_rec"]["REPL"] - bn["slope_rec"]["ACC"]
    q["h2_recall_contrast"] = drec_bn / np.abs(bn["slope_rec"]["REPL"]) - drec_en / np.abs(en["slope_rec"]["REPL"])
    q["h2_recall_abs"] = drec_bn - drec_en
    q["rr_net_en"] = en["slope_ppl"]["REPL"] - en["slope_ppl"]["RR"]
    q["rr_net_bn"] = bn["slope_ppl"]["REPL"] - bn["slope_ppl"]["RR"]
    return q

print("building matrices...", flush=True)
D_en, C_en, ix_en = build("EN"); D_bn, C_bn, ix_bn = build("BN")
print(f"EN: docs {D_en.shape} probes {C_en.shape} | BN: docs {D_bn.shape} probes {C_bn.shape}", flush=True)

# ---- point estimates + tie-in assertions against the released analysis ----
en0 = stats_from(D_en.mean(0), C_en.mean(0), ix_en)
bn0 = stats_from(D_bn.mean(0), C_bn.mean(0), ix_bn)
q0 = derive(en0, bn0)
REG = {  # value, lo, hi, p (from released H0_anchor.csv / H_tests.csv / controls.csv)
 "h0_ratio":         (0.6045608036302673, 0.5625780204544464, 0.6491266418141031, None),
 "h1_ppl":           (-0.0457845116863176, -0.0559687854116843, -0.03579042356880189, 0.0),
 "h1_recall":        (0.0040876776538668145, -0.017790163027066836, 0.02848632684183875, 0.706),
 "h2_ppl_contrast":  (0.6517245344128825, 0.5355018195198026, 0.766828239514759, 0.0),
 "h2_ppl_abs":       (0.03678252270444361, 0.02536629221501828, 0.048062920150938104, None),
 "h2_recall_contrast": (-2.4160845714988737, -34.60384683793371, -0.4073959966055024, 0.032),
 "h2_recall_abs":    (-0.028612837572480024, -0.05323079359569015, -0.0025517279453800877, None),
 "rr_net_en":        (7.734048982427355e-05, -0.007144999266186382, 0.006750011561350918, 0.948),
 "rr_net_bn":        (0.06685021340502618, 0.056145450497702164, 0.07649764778043631, 0.0),
}
checks = {"EN_REPL": (en0["slope_ppl"]["REPL"], 0.13000339606713665),
          "EN_ACC": (en0["slope_ppl"]["ACC"], 0.07859495760101207),
          "BN_REPL": (bn0["slope_ppl"]["REPL"], 0.08421888438081905),
          "EN_RR": (en0["slope_ppl"]["RR"], 0.12992605557731238),
          "BN_RR": (bn0["slope_ppl"]["RR"], 0.017368670975792866),
          "EN_rec_REPL": (en0["slope_rec"]["REPL"], -0.014867908812776885),
          "BN_rec_REPL": (bn0["slope_rec"]["REPL"], -0.01078023115891007)}
for k, (got, want) in checks.items():
    assert abs(got - want) < 1e-9, (k, got, want)
for k, (want, *_rest) in REG.items():
    assert abs(q0[k] - want) < 1e-9, (k, q0[k], want)
print("tie-in: all point estimates equal the released values (<1e-9)", flush=True)

# ---- paired bootstrap ----
nd_en, np_en = D_en.shape[0], C_en.shape[0]
nd_bn, np_bn = D_bn.shape[0], C_bn.shape[0]
acc = {k: [] for k in REG}
CH = 250
for start in range(0, B, CH):
    b = min(CH, B - start)
    ide = rng.integers(0, nd_en, (b, nd_en)); ipe = rng.integers(0, np_en, (b, np_en))
    idb = rng.integers(0, nd_bn, (b, nd_bn)); ipb = rng.integers(0, np_bn, (b, np_bn))
    en = stats_from(D_en[ide].mean(1), C_en[ipe].mean(1), ix_en)
    bn = stats_from(D_bn[idb].mean(1), C_bn[ipb].mean(1), ix_bn)
    q = derive(en, bn)
    for k in REG: acc[k].append(q[k])
res = {k: np.concatenate(acc[k]) for k in REG}
def pval(a):
    return min(1.0, 2 * min((a <= 0).mean(), (a >= 0).mean()))
rows = []
for k, (rv, rlo, rhi, rp) in REG.items():
    a = res[k]
    lo, hi = np.percentile(a, [2.5, 97.5])
    p = None if rp is None else pval(a)
    rows.append({"quantity": k, "point_estimate": q0[k],
                 "registered_lo": rlo, "registered_hi": rhi, "registered_p": rp,
                 "paired_lo": lo, "paired_hi": hi, "paired_p": p,
                 "B": B, "seed": SEED})
    w_r = rhi - rlo; w_p = hi - lo
    print(f"{k:20s} est {q0[k]:+.4f} | registered [{rlo:+.4f},{rhi:+.4f}] p={rp} "
          f"| paired [{lo:+.4f},{hi:+.4f}] p={p} | width ratio {w_p/w_r:.2f}", flush=True)
with open("req034_paired_bootstrap.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("written: req034_paired_bootstrap.csv", flush=True)
