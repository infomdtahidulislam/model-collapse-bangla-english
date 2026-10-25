#!/usr/bin/env python
"""CG4 analysis as pre-specified in 07_ANALYSIS_PLAN.md (with 01_PREREGISTRATION.md and 05_METRICS.md).

Reads results/metrics.jsonl and results/screening_metrics.jsonl; writes tables (CSV), figures (PNG, SVG) and
analysis_report.md to results/analysis/. Numbers and descriptions only: the interpretation is written by the authors.

Rewritten at G6 (2026-10-18), before any result was read, so that the code carries out the registered analysis
(logs/decisions.md 2026-10-18; REQ-025; results/deviations.md): the registered metric versions for H0-H2, H2 as the
registered ratio, H0 decided as REQ-025 option A, the registered decision rule, the seed replicates and controls (07 §4),
robustness (i)-(vi) (07 §5), the exploratory items (01, "Exploratory") and the screening tables (07 §5b). Robustness
(vii)-(ix), table T3 and figure F4 need the archived corpora and step records; they are listed as pending until computed.
The version before the rewrite is in the G4b archive and in results/packs/verify_20261016-232223/harness/analyze.py.

Uncertainty is measurement uncertainty only: a parametric bootstrap from each point's CI (1,000 draws) in which every
measurement (metric x checkpoint x generation) gets one fixed set of normal draws, so a generation-0 point shared by
several chains moves together in every test. Run-to-run variance comes only from the seed replicates (descriptive).

usage: python harness/analyze.py [--robustness] [--metrics FILE] [--screening FILE] [--out DIR] [--no-log]
"""
from __future__ import annotations

import argparse
import math
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import RESULTS, chain_meta, load_chains_cfg, log_decision, read_jsonl, utf8_stdout  # noqa: E402

utf8_stdout()
B_DRAWS = 1000
ALPHA = 0.05
CHANCE = 0.25
H_METRICS = ["log_ppl_heldout", "distinct_2_logratio0", "tail_fact_recall_ALL_logratio0"]  # H1/H2 (i)-(iii): 01 Hypotheses, 07 §3
COPRIMARY = "bpb_heldout"                                                                  # H1(i) must agree in direction in bytes
H0_METRICS = ["log_ppl_heldout", "distinct_2_logratio0"]                                   # REQ-025, option A
RAW_METRICS = ["log_ppl_heldout", "distinct_2", "tail_fact_recall_ALL"]                    # robustness (i)
LABEL = {"log_ppl_heldout": "(i) log held-out perplexity", "bpb_heldout": "(i) bits per byte (co-primary unit)",
         "distinct_2_logratio0": "(ii) log(distinct-2 / gen 0)", "tail_fact_recall_ALL_logratio0": "(iii) log(tail-fact recall / gen 0)"}
LOWER_IS_BETTER = {"log_ppl": True, "bpb": True, "bpc": True, "distinct": False, "ttr_window": False, "mtld": False,
                   "entropy": False, "tail_mass": False, "tail_fact_recall": False, "semantic_dispersion": False}
LOG_SCALE = ("log_ppl", "bpb", "bpc", "sample_nll")     # differences from generation 0 (*_rel0); other positive metrics: log ratio


def base_name(m: str) -> str:
    return m.replace("_logratio0", "").replace("_rel0", "")


def better_down(m: str) -> bool:
    b = base_name(m)
    for k, v in LOWER_IS_BETTER.items():
        if b.startswith(k):
            return v
    raise KeyError(f"no direction defined for {m}")


def fmt(x, nd: int = 4) -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "n/a"
    return f"{x:+.{nd}f}"


# ---------------------------------------------------------------- data (07 §1)

def load(cfg: dict, path: Path, extra: list[Path] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict, list[str]]:
    """results/metrics.jsonl plus the G6 robustness files in the same schema (results/tokenizer_metrics.jsonl for (vii),
    results/semantic_dispersion.jsonl for (ix)), when present."""
    recs = list(read_jsonl(path))
    for p in extra or []:
        recs += list(read_jsonl(p))
    raw = pd.DataFrame(recs)
    if raw.empty:
        raise SystemExit(f"{path} is empty")
    raw = raw.drop_duplicates(subset=["chain_id", "generation", "metric"], keep="last")
    for c in ("value", "ci_lo", "ci_hi"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["generation"] = raw["generation"].astype(int)
    base = raw[raw["chain_id"].str.startswith("BASE-")].copy()
    meta = chain_meta(cfg)
    parts, missing0 = [], []
    for cid, m in meta.items():
        g0 = m.get("gen0") or f"GEN0-{m['language']}"
        p0 = raw[(raw["chain_id"] == g0) & (raw["generation"] == 0)].copy()
        if p0.empty:
            missing0.append(cid)
        p0["source"] = g0
        p0["chain_id"] = cid
        own = raw[raw["chain_id"] == cid].copy()
        own["source"] = cid
        parts += [p0, own]
    df = pd.concat(parts, ignore_index=True)
    df["language"] = df["chain_id"].map(lambda c: meta[c]["language"])
    df["regime"] = df["chain_id"].map(lambda c: meta[c]["regime"])
    df["variant"] = df["chain_id"].map(lambda c: meta[c].get("variant") or "main")
    df["seed_offset"] = df["chain_id"].map(lambda c: int(meta[c].get("seed_offset") or 0))
    df["priority"] = df["chain_id"].map(lambda c: int(meta[c].get("priority") or 0))
    return df, base, meta, missing0


def add_normalised(df: pd.DataFrame) -> pd.DataFrame:
    """Difference from generation 0 for log-scale metrics (*_rel0), log ratio to generation 0 for positive metrics
    (*_logratio0); CIs are shifted or transformed the same way. The slope of a normalised series equals the slope of the
    series itself (log-scale) or of its logarithm (log ratio)."""
    out = [df]
    for (cid, m), pts in df.groupby(["chain_id", "metric"]):
        p0 = pts[pts["generation"] == 0]
        if p0.empty:
            continue
        v0 = float(p0["value"].iloc[0])
        r = pts.copy()
        if m.startswith(LOG_SCALE):
            for c in ("value", "ci_lo", "ci_hi"):
                r[c] = pts[c] - v0
            r["metric"] = m + "_rel0"
        elif v0 > 0 and (pts["value"] > 0).all():
            r["value"] = np.log(pts["value"] / v0)
            r["ci_lo"] = np.log(np.maximum(pts["ci_lo"].to_numpy(float), 1e-12) / v0)
            r["ci_hi"] = np.log(np.maximum(pts["ci_hi"].to_numpy(float), 1e-12) / v0)
            r["metric"] = m + "_logratio0"
        else:
            continue
        out.append(r)
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- bootstrap

@dataclass
class Fit:
    est: float
    draws: np.ndarray
    n: int
    miss: int

    def ci(self) -> tuple[float, float]:
        return ci(self.draws)


def ci(d: np.ndarray) -> tuple[float, float]:
    d = d[np.isfinite(d)]
    if not len(d):
        return (float("nan"), float("nan"))
    return (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def p_two(d: np.ndarray) -> float:
    """Two-sided bootstrap p-value of 'the quantity is 0' (measurement uncertainty only)."""
    d = d[np.isfinite(d)]
    if not len(d):
        return float("nan")
    return float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean())))


class Boot:
    """Parametric bootstrap from the per-point CIs (sd = CI width / 3.92). Each measurement (metric, source checkpoint,
    generation) has one fixed set of B standard-normal draws, seeded from the config seed and the measurement's key, so
    shared generation-0 points move together and every test is reproducible regardless of the order of computation."""

    def __init__(self, df: pd.DataFrame, seed: int, B: int = B_DRAWS):
        self.seed, self.B = int(seed), B
        self._z: dict[tuple, np.ndarray] = {}
        self.idx = {k: g.sort_values("generation") for k, g in df.groupby(["chain_id", "metric"])}

    def z(self, metric: str, source: str, gen: int) -> np.ndarray:
        k = (metric, source, int(gen))
        if k not in self._z:
            self._z[k] = np.random.default_rng([self.seed, zlib.crc32(repr(k).encode())]).standard_normal(self.B)
        return self._z[k]

    def points(self, chain: str, metric: str, gens) -> pd.DataFrame | None:
        p = self.idx.get((chain, metric))
        if p is None:
            return None
        p = p[p["generation"].isin(list(gens))]
        return p if len(p) else None

    def _noisy(self, p: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray, int]:
        y = p["value"].to_numpy(float)
        sd = ((p["ci_hi"] - p["ci_lo"]) / 3.92).to_numpy(float)
        miss = int(np.isnan(sd).sum())
        sd = np.nan_to_num(sd, nan=0.0)
        Z = np.stack([self.z(metric, s, g) for s, g in zip(p["source"], p["generation"])], axis=1)
        return y, y[None, :] + Z * sd[None, :], miss

    def fit(self, chain: str, metric: str, gens, deg: int = 1) -> Fit | None:
        """OLS over the given generations; deg 1 returns the slope, deg 2 the quadratic coefficient."""
        p = self.points(chain, metric, gens)
        if p is None or len(p) < (2 if deg == 1 else deg + 2):     # a quadratic needs a residual degree of freedom
            return None
        x = p["generation"].to_numpy(float)
        y, Y, miss = self._noisy(p, metric)
        X = np.vander(x, deg + 1)
        est = float(np.linalg.lstsq(X, y, rcond=None)[0][0])
        draws = np.linalg.lstsq(X, Y.T, rcond=None)[0][0]
        return Fit(est, draws, len(p), miss)

    def endpoint(self, chain: str, metric: str, g_end: int) -> Fit | None:
        """Value at g_end minus value at generation 0 (robustness vi)."""
        p = self.points(chain, metric, [0, g_end])
        if p is None or len(p) < 2:
            return None
        y, Y, miss = self._noisy(p, metric)
        return Fit(float(y[-1] - y[0]), Y[:, -1] - Y[:, 0], 2, miss)


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj, run = np.empty(m), 0.0
    for rank, idx in enumerate(order):
        run = max(run, (m - rank) * pvals[idx])
        adj[idx] = min(1.0, run)
    return list(adj)


# ---------------------------------------------------------------- tests (07 §3)

def h0_anchor(boot: Boot, gens, metrics=H0_METRICS, seeds=("EN-REPLACE-s2", "EN-REPLACE-s3"), rep: str = "EN-REPLACE",
              acc: str = "EN-ACCUMULATE") -> tuple[list[dict], bool | None]:
    """REQ-025 option A: pass/fail on the point estimates as registered; CIs reported and flagged, not deciding."""
    rows = []
    for m in metrics:
        fr, fa = boot.fit(rep, m, gens), boot.fit(acc, m, gens)
        if fr is None or fa is None:
            rows.append({"metric": m, "computed": False})
            continue
        want = 1 if better_down(m) else -1
        ratio = abs(fa.est) / abs(fr.est) if fr.est != 0 else math.inf
        with np.errstate(divide="ignore", invalid="ignore"):
            rdraws = np.abs(fa.draws) / np.abs(fr.draws)
        (r_lo, r_hi), (s_lo, s_hi), (a_lo, a_hi) = ci(rdraws), fr.ci(), fa.ci()
        flags = []
        if s_lo <= 0 <= s_hi:
            flags.append(f"{rep} slope CI crosses 0")
        if r_lo <= 0.5 <= r_hi:
            flags.append("ratio CI crosses 0.5")
        seed_txt = []
        for sc in seeds:
            f = boot.fit(sc, m, gens)
            seed_txt.append(f"{sc} {fmt(f.est)} ({'published sign' if np.sign(f.est) == want else 'NOT the published sign'})" if f else f"{sc} n/a")
        rows.append({"metric": m, "computed": True, "slope_REPLACE": fr.est, "slope_REPLACE_lo": s_lo, "slope_REPLACE_hi": s_hi,
                     "slope_ACCUMULATE": fa.est, "slope_ACCUMULATE_lo": a_lo, "slope_ACCUMULATE_hi": a_hi,
                     "published_sign": "+" if want > 0 else "-", "sign_ok": bool(np.sign(fr.est) == want),
                     "ratio_abs": ratio, "ratio_lo": r_lo, "ratio_hi": r_hi, "ratio_ok": bool(ratio <= 0.5),
                     "flags": "; ".join(flags) or "none", "seed_replicates": "; ".join(seed_txt),
                     "points_without_ci": fr.miss + fa.miss})
    if not all(r["computed"] for r in rows):
        return rows, None
    return rows, all(r["sign_ok"] and r["ratio_ok"] for r in rows)


def h1_contrast(boot: Boot, m: str, gens, bn: str = "BN-REPLACE", en: str = "EN-REPLACE") -> dict | None:
    """slope(BN) - slope(EN); predicted: BN worse (positive for lower-is-better metrics, negative otherwise)."""
    fb, fe = boot.fit(bn, m, gens), boot.fit(en, m, gens)
    if fb is None or fe is None:
        return None
    want = 1 if better_down(m) else -1
    d, dd = fb.est - fe.est, fb.draws - fe.draws
    lo, hi = ci(dd)
    (b_lo, b_hi), (e_lo, e_hi) = fb.ci(), fe.ci()
    return {"metric": m, "contrast": f"slope({bn}) - slope({en})", "estimate": d, "lo": lo, "hi": hi, "p_boot": p_two(dd),
            "predicted_sign": "+" if want > 0 else "-", "sign_ok": bool(np.sign(d) == want),
            "slope_a": fb.est, "slope_a_lo": b_lo, "slope_a_hi": b_hi, "slope_b": fe.est, "slope_b_lo": e_lo, "slope_b_hi": e_hi,
            "points_without_ci": fb.miss + fe.miss}


def h2_contrast(boot: Boot, m: str, gens, acc: str = "ACCUMULATE") -> dict | None:
    """Delta_L = (slope_REPLACE - slope_ACC) / |slope_REPLACE| per language (as registered); contrast Delta_BN - Delta_EN.
    Predicted: smaller relative benefit for BN. Delta_L is positive when accumulation helps a lower-is-better metric and
    negative when it helps a higher-is-better one, so the predicted sign is negative for the former and positive for the
    latter. Secondary: the absolute difference of the slope differences."""
    f = {(L, R): boot.fit(f"{L}-{R}", m, gens) for L in ("BN", "EN") for R in ("REPLACE", acc)}
    if any(v is None for v in f.values()):
        return None
    with np.errstate(divide="ignore", invalid="ignore"):
        dl = {L: ((f[(L, "REPLACE")].est - f[(L, acc)].est) / abs(f[(L, "REPLACE")].est),
                  (f[(L, "REPLACE")].draws - f[(L, acc)].draws) / np.abs(f[(L, "REPLACE")].draws)) for L in ("BN", "EN")}
    want = -1 if better_down(m) else 1
    est, dd = dl["BN"][0] - dl["EN"][0], dl["BN"][1] - dl["EN"][1]
    lo, hi = ci(dd)
    a_est = (f[("BN", "REPLACE")].est - f[("BN", acc)].est) - (f[("EN", "REPLACE")].est - f[("EN", acc)].est)
    a_d = (f[("BN", "REPLACE")].draws - f[("BN", acc)].draws) - (f[("EN", "REPLACE")].draws - f[("EN", acc)].draws)
    a_lo, a_hi = ci(a_d)
    flags = [f"{L}-REPLACE slope CI includes 0 (ratio unstable)" for L in ("BN", "EN") if (lambda c: c[0] <= 0 <= c[1])(f[(L, "REPLACE")].ci())]
    return {"metric": m, "contrast": f"Delta_BN - Delta_EN (accumulation arm {acc})", "estimate": est, "lo": lo, "hi": hi,
            "p_boot": p_two(dd), "predicted_sign": "+" if want > 0 else "-", "sign_ok": bool(np.sign(est) == want),
            "Delta_BN": dl["BN"][0], "Delta_EN": dl["EN"][0], "abs_secondary": a_est, "abs_secondary_lo": a_lo, "abs_secondary_hi": a_hi,
            "flags": "; ".join(flags) or "none", "points_without_ci": sum(v.miss for v in f.values())}


def decide(rows: list[dict], extra: dict[str, bool] | None = None) -> tuple[str, list[dict]]:
    """01_PREREGISTRATION.md decision rule: 'supported' if every included contrast has the predicted sign with Holm-adjusted
    bootstrap p < 0.05 and meets its extra conditions (H1(i): bytes agree; seed replicates: every per-seed contrast has the
    predicted sign); 'not supported' if no contrast has the predicted sign; 'inconclusive' otherwise."""
    extra = extra or {}
    inc = [r for r in rows if not r.get("excluded")]
    cond = []
    for r in inc:
        ok = r["sign_ok"] and r["p_holm"] < ALPHA and extra.get(r["metric"], True)
        cond.append({"metric": r["metric"], "sign_ok": r["sign_ok"], "p_holm": r["p_holm"], "p_holm_lt_0.05": r["p_holm"] < ALPHA,
                     "extra_conditions_ok": extra.get(r["metric"], True), "all_conditions": ok})
    if inc and all(c["all_conditions"] for c in cond):
        return "supported", cond
    if not any(r["sign_ok"] for r in inc):
        return "not supported", cond
    return "inconclusive", cond


def seed_chains(meta: dict) -> dict[int, dict[str, str]]:
    """REPLACE chains per seed offset and language: offset 0 the confirmatory pair, 1000 / 2000 the re-seeded pairs."""
    out: dict[int, dict[str, str]] = {}
    for cid, m in meta.items():
        if m["regime"] == "REPLACE" and (m.get("variant") or "main") in ("main", "seed2", "seed3"):
            out.setdefault(int(m.get("seed_offset") or 0), {})[m["language"]] = cid
    return {s: v for s, v in sorted(out.items()) if {"EN", "BN"} <= set(v)}


def floor_check(df: pd.DataFrame, gen0_ids: dict[str, str], metric: str) -> dict[str, dict]:
    """Floor rule (01, 05 §4): a language or stratum whose generation-0 recall CI includes chance (0.25) is excluded."""
    out = {}
    for lang, src in gen0_ids.items():
        r = df[(df["source"] == src) & (df["generation"] == 0) & (df["metric"] == metric)]
        if r.empty:
            out[lang] = {"value": float("nan"), "ci_lo": float("nan"), "ci_hi": float("nan"), "at_chance": None}
            continue
        r = r.iloc[0]
        out[lang] = {"value": float(r["value"]), "ci_lo": float(r["ci_lo"]), "ci_hi": float(r["ci_hi"]),
                     "at_chance": bool(r["ci_lo"] <= CHANCE <= r["ci_hi"])}
    return out


# ---------------------------------------------------------------- figures

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def fig_series(df: pd.DataFrame, metrics: list[str], out: Path, name: str, G: int, chains: list[str] | None = None) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, len(metrics), figsize=(4.2 * len(metrics), 3.6))
    axes = np.atleast_1d(axes)
    for ax, m in zip(axes, metrics):
        sub = df[df["metric"] == m]
        if chains:
            sub = sub[sub["chain_id"].isin(chains)]
        for cid, s in sub.groupby("chain_id"):
            s = s.sort_values("generation")
            conf = int(s["priority"].iloc[0]) == 0
            ax.plot(s["generation"], s["value"], "-" if s["language"].iloc[0] == "EN" else "--", marker="o", ms=3,
                    lw=1.8 if conf else 0.8, label=cid)
            if conf and s["ci_lo"].notna().any():
                ax.fill_between(s["generation"], s["ci_lo"], s["ci_hi"], alpha=0.12)
        ax.axvline(G, color="grey", lw=0.6, ls=":")
        ax.set_title(m, fontsize=8)
        ax.set_xlabel("generation")
    axes[-1].legend(fontsize=4.5)
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=160)
    fig.savefig(out / f"{name}.svg")
    plt.close(fig)


def fig_contrasts(rows: list[dict], out: Path) -> None:
    plt = _plt()
    rows = [r for r in rows if r and np.isfinite(r["estimate"])]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(6.5, 0.45 * len(rows) + 1.2))
    ys = np.arange(len(rows))[::-1]
    for y, r in zip(ys, rows):
        ax.errorbar(r["estimate"], y, xerr=[[r["estimate"] - r["lo"]], [r["hi"] - r["estimate"]]], fmt="o", ms=4, capsize=3)
    ax.axvline(0, color="grey", lw=0.6)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{r['hypothesis']} {r['metric']}" for r in rows], fontsize=6)
    ax.set_xlabel("estimate with 95% measurement CI")
    fig.tight_layout()
    fig.savefig(out / "F2_contrasts.png", dpi=160)
    fig.savefig(out / "F2_contrasts.svg")
    plt.close(fig)


def fig_length(df: pd.DataFrame, out: Path) -> None:
    plt = _plt()
    d2 = df[df["metric"] == "distinct_2"][["chain_id", "generation", "value"]].rename(columns={"value": "distinct_2"})
    ln = df[df["metric"] == "mean_length_words"][["chain_id", "generation", "value"]].rename(columns={"value": "mean_length_words"})
    j = d2.merge(ln, on=["chain_id", "generation"])
    if j.empty:
        return
    fig, ax = plt.subplots(figsize=(4.8, 3.8))
    for cid, s in j.groupby("chain_id"):
        ax.scatter(s["mean_length_words"], s["distinct_2"], s=12, label=cid)
    ax.set_xlabel("mean generated length (words)")
    ax.set_ylabel("distinct-2 (fixed window)")
    ax.legend(fontsize=4.5)
    fig.tight_layout()
    fig.savefig(out / "F5_length_check.png", dpi=160)
    plt.close(fig)


def fig_nll(df: pd.DataFrame, chains: list[str], out: Path) -> None:
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=False)
    for ax, lang in zip(axes, ("EN", "BN")):
        for cid in [c for c in chains if c.startswith(lang + "-")]:
            s = df[df["chain_id"] == cid].pivot_table(index="generation", columns="metric", values="value")
            if not {"sample_nll_ref_mean", "sample_nll_ref_p5", "sample_nll_ref_p95"} <= set(s.columns):
                continue
            ax.plot(s.index, s["sample_nll_ref_mean"], marker="o", ms=3, label=cid)
            ax.fill_between(s.index, s["sample_nll_ref_p5"], s["sample_nll_ref_p95"], alpha=0.1)
        ax.set_title(f"{lang}: NLL of the sample under the generation-0 model (mean, 5th-95th pct)", fontsize=7)
        ax.set_xlabel("generation")
        ax.legend(fontsize=5)
    fig.tight_layout()
    fig.savefig(out / "F6_nll_under_gen0.png", dpi=160)
    plt.close(fig)


def novelty_table(path: Path, out: Path) -> list[str]:
    """Robustness (viii) and the exploratory n-gram novelty (REQ-027): one row per synthetic training corpus, descriptive."""
    if not path.exists():
        return ["- (viii) n-gram novelty and exact/near-duplicate rates of every synthetic corpus against the seed: PENDING "
                "(`harness/tools/novelty_duplicates.py`)."]
    t = pd.DataFrame(list(read_jsonl(path))).sort_values(["chain_id", "generation"])
    t.to_csv(out / "robustness_viii_novelty_duplicates.csv", index=False)
    lines = [f"- (viii) n-gram novelty and duplicates against the seed (REQ-027; descriptive): `robustness_viii_novelty_duplicates.csv`, "
             f"{len(t)} synthetic training corpora, {int(t['docs'].sum()):,} documents. novelty_1..4 = share of word n-gram occurrences never "
             f"found in the seed. Near-duplicates of seed documents by the pipeline's MinHash test against the seed signatures: "
             f"{int(t['near_dup_docs'].sum())} documents in total (largest rate in one corpus {t['near_dup_rate'].max():.2e}); exact duplicates of "
             f"seed documents (first 400 words): {int(t['exact_dup_docs'].sum())} documents in total. Figure `F8_novelty`."]
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
    for ax, n in zip(axes, (2, 4)):
        for cid, s in t.groupby("chain_id"):
            ax.plot(s["generation"], s[f"novelty_{n}"], "-" if cid.startswith("EN") else "--", marker="o", ms=3, lw=0.9, label=cid)
        ax.set_title(f"novelty_{n}: share of word {n}-grams not in the seed (training corpus of each generation)", fontsize=6)
        ax.set_xlabel("generation")
    axes[-1].legend(fontsize=4)
    fig.tight_layout()
    fig.savefig(out / "F8_novelty.png", dpi=160)
    plt.close(fig)
    return lines


def t3_f4(root: Path, out: Path) -> list[str]:
    """T3 and F4 (07 §2) from the step records extracted from the G4b archive: the generation record of every generating step
    (generate.json: documents, tokens, exact-duplicate, empty and cap-hit rates, mean lengths) and the filter record of every
    ACCUMULATE-FILTER step (filter.json: criteria applied in the order script, repetition, perplexity band, near-duplicate; each
    rejected document is counted under the first criterion it fails; top-up rounds, kept tokens, shortfall)."""
    import json as _json
    if not root.exists():
        return ["- T3 (filter pass rates, top-up, shortfall; duplicate rates) and F4 (filter statistics): PENDING (the step records are "
                f"extracted from the G4b archive into {root})."]
    gen, flt = [], []
    for p in sorted(root.glob("*/gen_*/generate.json")):
        j = _json.load(open(p, encoding="utf-8"))
        gen.append({"chain_id": p.parts[-3], "generation": int(p.parts[-2].split("_")[1]), **{k: j.get(k) for k in (
            "engine", "docs", "tokens", "exact_duplicate_rate", "empty_rate", "cap_hit_rate", "mean_tokens", "mean_words", "mean_chars", "mean_bytes")},
            "temperature": (j.get("sampling") or {}).get("temperature"), "top_p": (j.get("sampling") or {}).get("top_p")})
    for p in sorted(root.glob("*/gen_*/filter.json")):
        j = _json.load(open(p, encoding="utf-8"))
        n = max(1, int(j.get("input") or 0))
        flt.append({"chain_id": p.parts[-3], "generation": int(p.parts[-2].split("_")[1]), "input": j.get("input"),
                    **{f"fail_{c}": j.get(f"fail_{c}") for c in ("script", "repeat", "ppl", "dup")},
                    **{f"share_fail_{c}": (j.get(f"fail_{c}") or 0) / n for c in ("script", "repeat", "ppl", "dup")},
                    "kept": j.get("kept"), "pass_rate": j.get("pass_rate"), "topup_rounds": j.get("topup_rounds"),
                    "generated_tokens_total": j.get("generated_tokens_total"), "budget_tokens": j.get("budget_tokens"),
                    "kept_tokens_available": j.get("kept_tokens_available"), "kept_tokens_used": j.get("kept_tokens_used"),
                    "shortfall_tokens": j.get("shortfall_tokens")})
    G3, F3 = pd.DataFrame(gen), pd.DataFrame(flt)
    G3.sort_values(["chain_id", "generation"]).to_csv(out / "T3_generation.csv", index=False)
    F3.sort_values(["chain_id", "generation"]).to_csv(out / "T3_filter.csv", index=False)
    lines = [f"- T3: `T3_generation.csv` ({len(G3)} generating steps: documents, tokens, exact-duplicate, empty and cap-hit rates, mean "
             f"lengths; largest exact-duplicate rate {G3['exact_duplicate_rate'].max():.4f}, largest empty rate {G3['empty_rate'].max():.4f}) "
             f"and `T3_filter.csv` ({len(F3)} ACCUMULATE-FILTER steps: rejections by criterion, applied in the order script, repetition, "
             "perplexity band, near-duplicate; top-up rounds; kept tokens; shortfall). Sample length, script fidelity and fertility per "
             "step are in `T1_metrics.csv`."]
    if not F3.empty:
        lines.append(f"- Filter: pass rate {F3['pass_rate'].min():.3f} to {F3['pass_rate'].max():.3f}; top-up rounds up to "
                     f"{int(F3['topup_rounds'].max())}; shortfall tokens {int(F3['shortfall_tokens'].sum())} in total. Figure `F4_filter`.")
        plt = _plt()
        fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
        for ax, lang in zip(axes, ("EN", "BN")):
            s = F3[F3["chain_id"] == f"{lang}-ACCUMULATE-FILTER"].sort_values("generation")
            bottom = np.zeros(len(s))
            for c in ("script", "repeat", "ppl", "dup"):
                ax.bar(s["generation"], s[f"share_fail_{c}"], bottom=bottom, label=f"rejected: {c}")
                bottom += s[f"share_fail_{c}"].to_numpy(float)
            ax.set_title(f"{lang}-ACCUMULATE-FILTER: share of generated documents rejected", fontsize=7)
            ax.set_xlabel("generation")
        axes[-1].legend(fontsize=6)
        fig.tight_layout()
        fig.savefig(out / "F4_filter.png", dpi=160)
        fig.savefig(out / "F4_filter.svg")
        plt.close(fig)
    return lines


# ---------------------------------------------------------------- main

def rows_to_csv(rows: list[dict], path: Path) -> None:
    pd.DataFrame([r for r in rows if r]).to_csv(path, index=False)


def run(a: argparse.Namespace) -> list[str]:
    cfg = load_chains_cfg()
    G = int(cfg["generations"])
    GENS = list(range(0, G + 1))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    extra = [Path(p) for p in a.extra] if a.extra is not None else \
        [p for p in (RESULTS / "tokenizer_metrics.jsonl", RESULTS / "semantic_dispersion.jsonl") if p.exists()]
    df, base, meta, missing0 = load(cfg, Path(a.metrics), extra)
    df = add_normalised(df)
    boot = Boot(df, cfg["seed"])
    conf_ids = [c for c, m in meta.items() if int(m.get("priority") or 0) == 0]
    gen0_ids = {L: f"GEN0-{L}" for L in ("EN", "BN")}
    R = ["# Analysis report (numbers only; the interpretation is written by the authors)", "",
         f"Pre-registration: {cfg['prereg_tag']} (`01_PREREGISTRATION.md`); analysis plan `07_ANALYSIS_PLAN.md`; confirmatory generations 0..{G}; "
         f"bootstrap: {B_DRAWS} draws, seed {cfg['seed']}. Inference statement (07 §3): one chain per cell; the bootstrap quantifies "
         "measurement uncertainty only, never run-to-run variance; the seed replicates give the run-to-run spread (descriptive).",
         f"Inputs: `{Path(a.metrics).name}`" + "".join(f", `{p.name}`" for p in extra) + ".", ""]
    if missing0:
        R.append(f"- WARNING: no generation-0 rows for {missing0}")

    # ---- descriptives (07 §2)
    if not base.empty:
        base.pivot_table(index="language", columns="metric", values="value").to_csv(out / "T0_base_model.csv")
    cols = ["chain_id", "language", "regime", "variant", "seed_offset", "priority", "generation", "metric", "value", "ci_lo", "ci_hi", "n", "source"]
    df.sort_values(["chain_id", "metric", "generation"])[[c for c in cols if c in df.columns]].to_csv(out / "T1_metrics.csv", index=False)
    t2 = []
    for (cid, m), _ in df.groupby(["chain_id", "metric"]):
        f = boot.fit(cid, m, GENS)
        if f is None:
            continue
        lo, hi = f.ci()
        t2.append({"chain_id": cid, "language": meta[cid]["language"], "regime": meta[cid]["regime"],
                   "variant": meta[cid].get("variant") or "main", "metric": m, "generations": f"0..{G}", "slope": f.est, "lo": lo, "hi": hi,
                   "n_points": f.n, "points_without_ci": f.miss})
    ext = [c for c, m in meta.items() if m["regime"] == "REPLACE" and (m.get("variant") or "main") == "main"]
    for cid in ext:
        for m in H_METRICS + [COPRIMARY]:
            for gens, lab in ((range(0, 11), "0..10"), (range(G, 11), f"{G}..10")):
                f = boot.fit(cid, m, gens)
                if f is not None and f.n >= 3:
                    lo, hi = f.ci()
                    t2.append({"chain_id": cid, "language": meta[cid]["language"], "regime": "REPLACE", "variant": "extension", "metric": m,
                               "generations": lab, "slope": f.est, "lo": lo, "hi": hi, "n_points": f.n, "points_without_ci": f.miss})
    t2 = pd.DataFrame(t2)
    t2.to_csv(out / "T2_slopes.csv", index=False)
    n_miss = int((t2["points_without_ci"] > 0).sum()) if not t2.empty else 0
    R += ["## Descriptives (07 §2)",
          f"- T0 base-model metrics (generation -1): `T0_base_model.csv`; T1 every metric by chain x generation with CI (incl. normalised "
          f"versions): `T1_metrics.csv` ({len(df)} rows); T2 per-chain OLS slopes over 0..{G} with bootstrap CIs, plus the REPLACE "
          f"extension over 0..10 and {G}..10: `T2_slopes.csv` ({len(t2)} rows; {n_miss} with points lacking a CI)."]
    R += t3_f4(Path(a.extract), out) + [""]

    # ---- H0 (REQ-025 option A)
    h0_rows, h0_pass = h0_anchor(boot, GENS)
    rows_to_csv(h0_rows, out / "H0_anchor.csv")
    R += ["## H0, the anchor (01 Hypotheses; decided as REQ-025 option A, 2026-10-18)",
          "Rule: on log held-out perplexity and log(distinct-2 / gen 0), seed-0 chains, generations 0..6: the EN-REPLACE slope has the "
          "published sign (+ for perplexity, - for distinct-2) and |slope EN-ACCUMULATE| <= 0.5 x |slope EN-REPLACE| for both. "
          "Point estimates decide; 95% measurement CIs are reported and flagged. File: `H0_anchor.csv`."]
    for r in h0_rows:
        if not r["computed"]:
            R.append(f"- {r['metric']}: not computed (missing points)")
            continue
        R.append(f"- {LABEL.get(r['metric'], r['metric'])}: EN-REPLACE slope {fmt(r['slope_REPLACE'])} [{fmt(r['slope_REPLACE_lo'])}, "
                 f"{fmt(r['slope_REPLACE_hi'])}] (published sign {r['published_sign']}: {'yes' if r['sign_ok'] else 'NO'}); EN-ACCUMULATE "
                 f"slope {fmt(r['slope_ACCUMULATE'])} [{fmt(r['slope_ACCUMULATE_lo'])}, {fmt(r['slope_ACCUMULATE_hi'])}]; ratio "
                 f"|ACC|/|REP| {r['ratio_abs']:.3f} [{r['ratio_lo']:.3f}, {r['ratio_hi']:.3f}] (<= 0.5: {'yes' if r['ratio_ok'] else 'NO'}); "
                 f"flags: {r['flags']}; seed replicates (descriptive): {r['seed_replicates']}")
    R.append(f"- **H0 rule output: {'PASS' if h0_pass else ('FAIL' if h0_pass is False else 'NOT COMPUTED')}**"
             + ("" if h0_pass else ". By the registered rule, if the anchor fails, no other hypothesis is interpreted (the numbers are still reported)."))
    R.append("")

    # ---- H1, H2 (07 §3)
    fl = floor_check(df, gen0_ids, "tail_fact_recall_ALL")
    floor_out = any(v["at_chance"] for v in fl.values())
    h1 = []
    for m in H_METRICS:
        r = h1_contrast(boot, m, GENS)
        if r:
            r["hypothesis"] = "H1"
            r["excluded"] = bool(m.startswith("tail_fact_recall") and floor_out)
            h1.append(r)
    inc = [r for r in h1 if not r["excluded"]]
    for r, p in zip(inc, holm([r["p_boot"] for r in inc]) if inc else []):
        r["p_holm"] = p
    for r in h1:
        r.setdefault("p_holm", float("nan"))
    bpb = h1_contrast(boot, COPRIMARY, GENS)
    if bpb:
        bpb.update({"hypothesis": "H1", "excluded": False, "p_holm": float("nan"), "role": "co-primary unit for H1(i) (direction only)"})
    seeds = seed_chains(meta)
    srows = []
    for m in H_METRICS + [COPRIMARY]:
        per = []
        for s, ch in seeds.items():
            r = h1_contrast(boot, m, GENS, bn=ch["BN"], en=ch["EN"])
            if r:
                per.append((s, r["estimate"]))
        if per:
            vals = np.array([v for _, v in per])
            want = 1 if better_down(m) else -1
            srows.append({"metric": m, "seed_offsets": [s for s, _ in per], "H1_per_seed": [float(v) for v in vals], "n_seeds": len(per),
                          "mean": float(vals.mean()), "sd": float(vals.std(ddof=1)) if len(vals) > 1 else float("nan"),
                          "same_sign": bool(np.all(np.sign(vals) == np.sign(vals[0]))), "all_predicted_sign": bool(np.all(np.sign(vals) == want))})
    pd.DataFrame(srows).to_csv(out / "H1_seed_replicates.csv", index=False)
    seed_ok = {r["metric"]: r["all_predicted_sign"] for r in srows}
    extra1 = {m: seed_ok.get(m, True) for m in H_METRICS}
    if bpb:
        extra1["log_ppl_heldout"] = extra1["log_ppl_heldout"] and bpb["sign_ok"]
    lab1, cond1 = decide(h1, extra1)
    h2 = []
    for m in H_METRICS:
        r = h2_contrast(boot, m, GENS)
        if r:
            r["hypothesis"] = "H2"
            r["excluded"] = False
            h2.append(r)
    for r, p in zip(h2, holm([r["p_boot"] for r in h2]) if h2 else []):
        r["p_holm"] = p
    h2b = h2_contrast(boot, COPRIMARY, GENS)
    if h2b:
        h2b.update({"hypothesis": "H2", "excluded": False, "p_holm": float("nan"), "role": "bits per byte, reported (not in the Holm family)"})
    lab2, cond2 = decide(h2)
    allh = h1 + ([bpb] if bpb else []) + h2 + ([h2b] if h2b else [])
    rows_to_csv(allh, out / "H_tests.csv")
    dec = [{"hypothesis": "H1", "rule_output": lab1, **c} for c in cond1] + [{"hypothesis": "H2", "rule_output": lab2, **c} for c in cond2]
    pd.DataFrame(dec).to_csv(out / "H_decision.csv", index=False)
    R += ["## H1 and H2 (07 §3; decision rule of 01, 'Analysis plan and inference')",
          f"Floor rule (05 §4): generation-0 recall (ALL) and 95% CI: " + "; ".join(
              f"{L} {v['value']:.3f} [{v['ci_lo']:.3f}, {v['ci_hi']:.3f}] (includes 0.25: {v['at_chance']})" for L, v in fl.items())
          + (" -> H1(iii) excluded." if floor_out else " -> H1(iii) included.")]
    for r in allh:
        tag = "" if r.get("role") is None else f" [{r['role']}]"
        ph = "n/a" if not np.isfinite(r["p_holm"]) else f"{r['p_holm']:.4f}"
        extra = f"; Delta_BN {fmt(r['Delta_BN'])}, Delta_EN {fmt(r['Delta_EN'])}; secondary absolute difference {fmt(r['abs_secondary'])} [{fmt(r['abs_secondary_lo'])}, {fmt(r['abs_secondary_hi'])}]; flags: {r['flags']}" if r["hypothesis"] == "H2" else \
            f"; slope BN {fmt(r['slope_a'])} [{fmt(r['slope_a_lo'])}, {fmt(r['slope_a_hi'])}], slope EN {fmt(r['slope_b'])} [{fmt(r['slope_b_lo'])}, {fmt(r['slope_b_hi'])}]"
        R.append(f"- {r['hypothesis']} {LABEL.get(r['metric'], r['metric'])}{tag}: estimate {fmt(r['estimate'])} [{fmt(r['lo'])}, {fmt(r['hi'])}], "
                 f"p_boot {r['p_boot']:.4f}, p_holm {ph}, predicted sign "
                 f"{r['predicted_sign']} ({'yes' if r['sign_ok'] else 'no'}){' EXCLUDED (floor rule)' if r.get('excluded') else ''}{extra}")
    for r in srows:
        R.append(f"- H1 seed replicates {r['metric']}: per seed offset {r['seed_offsets']}: {[fmt(v) for v in r['H1_per_seed']]}, mean "
                 f"{fmt(r['mean'])}, SD {r['sd']:.4f}, same sign {r['same_sign']}, all with the predicted sign {r['all_predicted_sign']}")
    R += [f"- **H1 rule output: {lab1}**; **H2 rule output: {lab2}** (conditions per contrast: `H_decision.csv`; tests: `H_tests.csv`; "
          "seed replicates: `H1_seed_replicates.csv`). Mechanical output of the registered rule; the authors write the interpretation.", ""]

    # ---- seed replicates and controls (07 §4)
    ctl = []
    for L in ("EN", "BN"):
        for m in H_METRICS + [COPRIMARY]:
            fr, fq = boot.fit(f"{L}-REPLACE", m, GENS), boot.fit(f"{L}-REAL-REPEAT", m, GENS)
            if fr and fq:
                lo, hi = ci(fr.draws - fq.draws)
                ctl.append({"control": "REPLACE net of REAL-REPEAT", "language": L, "metric": m, "slope_REAL_REPEAT": fq.est,
                            "estimate": fr.est - fq.est, "lo": lo, "hi": hi, "p_boot": p_two(fr.draws - fq.draws)})
            fa, fs = boot.fit(f"{L}-ACCUMULATE", m, GENS), boot.fit(f"{L}-ACCUMULATE-SUBSAMPLE", m, GENS)
            if fa and fs:
                lo, hi = ci(fs.draws - fa.draws)
                ctl.append({"control": "ACCUMULATE-SUBSAMPLE minus ACCUMULATE (slopes)", "language": L, "metric": m, "slope_SUBSAMPLE": fs.est,
                            "slope_ACCUMULATE": fa.est, "estimate": fs.est - fa.est, "lo": lo, "hi": hi, "p_boot": p_two(fs.draws - fa.draws)})
    for m in H_METRICS + [COPRIMARY]:
        r = h1_contrast(boot, m, GENS, bn="BN-REPLACE", en="EN-REPLACE-WM")
        if r:
            ctl.append({"control": "slope(BN-REPLACE) - slope(EN-REPLACE-WM) (word-matched English)", "language": "BN vs EN-WM", "metric": m,
                        "slope_BN": r["slope_a"], "slope_EN_WM": r["slope_b"], "estimate": r["estimate"], "lo": r["lo"], "hi": r["hi"], "p_boot": r["p_boot"]})
        r = h2_contrast(boot, m, GENS, acc="ACCUMULATE-SUBSAMPLE")
        if r:
            ctl.append({"control": "H2 contrast with ACCUMULATE-SUBSAMPLE as the accumulation arm (compute-matched)", "language": "BN vs EN", "metric": m,
                        "estimate": r["estimate"], "lo": r["lo"], "hi": r["hi"], "p_boot": r["p_boot"], "Delta_BN": r["Delta_BN"], "Delta_EN": r["Delta_EN"]})
    rows_to_csv(ctl, out / "controls.csv")
    R += ["## Seed replicates and controls (07 §4)", "- Seed replicates: `H1_seed_replicates.csv` (above). Controls: `controls.csv`:"]
    for r in ctl:
        R.append(f"  - {r['control']} | {r['language']} | {r['metric']}: {fmt(r['estimate'])} [{fmt(r['lo'])}, {fmt(r['hi'])}], p_boot {r['p_boot']:.4f}")
    R += ["- REPLACE extension 7..10 and the top-p 0.95 pair: descriptive series in `T1_metrics.csv`, slopes in `T2_slopes.csv`, figure `F1_all_chains`.", ""]

    # ---- robustness (07 §5)
    if a.robustness:
        rob = []

        def add(item: str, rows: list):
            for r in rows:
                if r:
                    rob.append({"item": item, "hypothesis": r.get("hypothesis"), "metric": r["metric"], "estimate": r["estimate"], "lo": r["lo"],
                                "hi": r["hi"], "p_boot": r["p_boot"], "predicted_sign": r["predicted_sign"], "sign_ok": r["sign_ok"],
                                "flags": r.get("flags", "")})

        def h12(metrics, gens):
            res = []
            for m in metrics:
                for fn, h in ((h1_contrast, "H1"), (h2_contrast, "H2")):
                    r = fn(boot, m, gens)
                    if r:
                        r["hypothesis"] = h
                        res.append(r)
            return res

        add("(i) raw (non-normalised) metrics", h12(RAW_METRICS, GENS))
        h0r, h0r_pass = h0_anchor(boot, GENS, metrics=["log_ppl_heldout", "distinct_2"])
        for r in h0r:
            if r["computed"]:
                rob.append({"item": "(i) raw metrics: H0", "hypothesis": "H0", "metric": r["metric"], "estimate": r["slope_REPLACE"],
                            "lo": r["slope_REPLACE_lo"], "hi": r["slope_REPLACE_hi"], "p_boot": float("nan"), "predicted_sign": r["published_sign"],
                            "sign_ok": r["sign_ok"], "flags": f"ratio {r['ratio_abs']:.3f} [{r['ratio_lo']:.3f}, {r['ratio_hi']:.3f}]; {r['flags']}"})
        add("(ii) generation 0 excluded (1..6)", h12(H_METRICS, range(1, G + 1)))
        h0x, _ = h0_anchor(boot, range(1, G + 1))
        for r in h0x:
            if r["computed"]:
                rob.append({"item": "(ii) generation 0 excluded: H0", "hypothesis": "H0", "metric": r["metric"], "estimate": r["slope_REPLACE"],
                            "lo": r["slope_REPLACE_lo"], "hi": r["slope_REPLACE_hi"], "p_boot": float("nan"), "predicted_sign": r["published_sign"],
                            "sign_ok": r["sign_ok"], "flags": f"ratio {r['ratio_abs']:.3f} [{r['ratio_lo']:.3f}, {r['ratio_hi']:.3f}]; {r['flags']}"})
        add("(iii) fresh slice", h12(["log_ppl_fresh", "bpb_fresh"], GENS))
        flt = floor_check(df, gen0_ids, "tail_fact_recall_TAIL")
        add("(iv) rule-B recall and the TAIL stratum (TAIL at chance in: "
            + (", ".join(L for L, v in flt.items() if v["at_chance"]) or "none") + ")",
            h12(["tail_fact_recall_norm_ALL_logratio0", "tail_fact_recall_TAIL_logratio0"], GENS))
        add("(v) character-5-gram distinctness and MTLD", h12(["distinct_char5_logratio0", "mtld_logratio0"], GENS))
        endp = []
        for m in H_METRICS + [COPRIMARY]:
            fb, fe = boot.endpoint("BN-REPLACE", m, G), boot.endpoint("EN-REPLACE", m, G)
            if fb and fe:
                want = 1 if better_down(m) else -1
                d = fb.draws - fe.draws
                lo, hi = ci(d)
                endp.append({"hypothesis": "H1", "metric": m, "estimate": fb.est - fe.est, "lo": lo, "hi": hi, "p_boot": p_two(d),
                             "predicted_sign": "+" if want > 0 else "-", "sign_ok": bool(np.sign(fb.est - fe.est) == want)})
            f = {(L, Rg): boot.endpoint(f"{L}-{Rg}", m, G) for L in ("BN", "EN") for Rg in ("REPLACE", "ACCUMULATE")}
            if all(f.values()):
                with np.errstate(divide="ignore", invalid="ignore"):
                    dl = {L: ((f[(L, "REPLACE")].est - f[(L, "ACCUMULATE")].est) / abs(f[(L, "REPLACE")].est),
                              (f[(L, "REPLACE")].draws - f[(L, "ACCUMULATE")].draws) / np.abs(f[(L, "REPLACE")].draws)) for L in ("BN", "EN")}
                want = -1 if better_down(m) else 1
                d = dl["BN"][1] - dl["EN"][1]
                lo, hi = ci(d)
                endp.append({"hypothesis": "H2", "metric": m, "estimate": dl["BN"][0] - dl["EN"][0], "lo": lo, "hi": hi, "p_boot": p_two(d),
                             "predicted_sign": "+" if want > 0 else "-", "sign_ok": bool(np.sign(dl["BN"][0] - dl["EN"][0]) == want)})
        add(f"(vi) endpoint contrast at generation {G} (change from generation 0)", endp)
        if (df["metric"] == "distinct_2_tok_logratio0").any():
            add("(vii) base-tokenizer metrics (REQ-027): log(token distinct-2 / gen 0)", h12(["distinct_2_tok_logratio0"], GENS))
        if (df["metric"] == "semantic_dispersion_labse_logratio0").any():
            add("(ix) semantic dispersion under LaBSE (REQ-026): log(dispersion / gen 0)", h12(["semantic_dispersion_labse_logratio0"], GENS))
        quad = []
        for cid in conf_ids:
            for m in H_METRICS + [COPRIMARY]:
                f = boot.fit(cid, m, GENS, deg=2)
                if f:
                    lo, hi = f.ci()
                    quad.append({"chain_id": cid, "metric": m, "quadratic_coef": f.est, "lo": lo, "hi": hi, "ci_excludes_0": bool(not (lo <= 0 <= hi))})
        pd.DataFrame(quad).to_csv(out / "robustness_quadratic.csv", index=False)
        rows_to_csv(rob, out / "robustness.csv")
        R += ["## Robustness (07 §5; reported, no decision rule)", "File: `robustness.csv`; quadratic-term check per chain: `robustness_quadratic.csv`."]
        for r in rob:
            R.append(f"- {r['item']} | {r['hypothesis']} {r['metric']}: {fmt(r['estimate'])} [{fmt(r['lo'])}, {fmt(r['hi'])}]"
                     + (f", p_boot {r['p_boot']:.4f}" if np.isfinite(r["p_boot"]) else "") + f", predicted sign {r['predicted_sign']} "
                     f"({'yes' if r['sign_ok'] else 'no'})" + (f"; {r['flags']}" if r.get("flags") and r["flags"] != "none" else ""))
        nq = sum(1 for q in quad if q["ci_excludes_0"])
        R += [f"- (vi) quadratic term: {nq} of {len(quad)} chain x metric fits have a 95% CI excluding 0 (`robustness_quadratic.csv`)."]
        R.append("- (vii) base-tokenizer metrics (REQ-027): contrasts above; distinct-1..4 and TTR on token ids for every step in `T1_metrics.csv` / "
                 "`T2_slopes.csv` (`*_tok`); input `results/tokenizer_metrics.jsonl`." if (df["metric"] == "distinct_2_tok").any() else
                 "- (vii) metrics with the base tokenizer instead of word splits: PENDING (`harness/tools/token_metrics.py`).")
        R += novelty_table(Path(a.novelty), out)
        R.append("- (ix) semantic dispersion (REQ-026): contrasts above; values for every step in `T1_metrics.csv` (`semantic_dispersion_labse`); "
                 "input `results/semantic_dispersion.jsonl`." if (df["metric"] == "semantic_dispersion_labse").any() else
                 "- (ix) semantic diversity (multilingual sentence-embedding dispersion): PENDING (`harness/tools/semantic_dispersion.py`).")
        R.append("")

    # ---- exploratory (01 "Exploratory (reported, not tested)")
    exp = []
    for cid in [c for c in conf_ids] + [c for c in meta if c not in conf_ids]:
        for m in ["tail_fact_recall_HEAD_logratio0", "tail_fact_recall_MID_logratio0", "tail_fact_recall_TAIL_logratio0", "stereotype_preference",
                  "fertility_tokens_per_word", "sample_nll_ref_sd", "sample_nll_ref_mean_rel0"]:
            f = boot.fit(cid, m, GENS)
            if f:
                lo, hi = f.ci()
                exp.append({"chain_id": cid, "metric": m, "slope": f.est, "lo": lo, "hi": hi, "n_points": f.n})
    rows_to_csv(exp, out / "exploratory_slopes.csv")
    strata = {f"{L} {s}": v for s in ("HEAD", "MID", "TAIL") for L, v in floor_check(df, gen0_ids, f"tail_fact_recall_{s}").items()}
    first = []
    for cid in [c for c in meta if meta[c]["language"] == "BN" and meta[c]["regime"] != "REAL-REPEAT"]:
        rec = {"chain_id": cid}
        for m in ("stereotype_preference", "log_ppl_heldout"):
            s = df[(df["chain_id"] == cid) & (df["metric"] == m)].sort_values("generation")
            s0 = s[s["generation"] == 0]
            g_first = None
            if not s0.empty:
                lo0, hi0 = float(s0["ci_lo"].iloc[0]), float(s0["ci_hi"].iloc[0])
                for _, r in s[s["generation"] > 0].iterrows():
                    if r["ci_lo"] > hi0 or r["ci_hi"] < lo0:
                        g_first = int(r["generation"])
                        break
            rec[f"first_generation_CI_apart_from_gen0_{m}"] = g_first
        first.append(rec)
    rows_to_csv(first, out / "exploratory_fairness_before_perplexity_BN.csv")
    R += ["## Exploratory (01: reported, not tested)",
          "- Per-stratum recall, bias-probe drift (within language), fertility of generated text and the NLL of the sample under the "
          "generation-0 model: slopes in `exploratory_slopes.csv`, series in `T1_metrics.csv`, figures `F3_recall_strata` and `F6_nll_under_gen0`.",
          "- Generation-0 recall per stratum and 95% CI (floor rule; at chance = CI includes 0.25): " + "; ".join(
              f"{k} {v['value']:.3f} [{v['ci_lo']:.3f}, {v['ci_hi']:.3f}]{' AT CHANCE' if v['at_chance'] else ''}" for k, v in strata.items()),
          "- 'Fairness before perplexity' (BN): first generation whose 95% CI no longer overlaps the generation-0 CI, per metric: "
          "`exploratory_fairness_before_perplexity_BN.csv` (descriptive operationalisation by the agent; not pre-specified).",
          "- n-gram novelty of each synthetic corpus against the seed: with robustness (viii) (`robustness_viii_novelty_duplicates.csv`).", ""]

    # ---- screening (07 §5b)
    if Path(a.screening).exists():
        sc = pd.DataFrame(list(read_jsonl(Path(a.screening))))
        sc.sort_values(["chain_id", "metric", "generation"]).to_csv(out / "S1_screening.csv", index=False)
        R += ["## Screening measures (07 §5b; EXPLORATORY, never used for a test)",
              f"- `S1_screening.csv`: {len(sc)} rows (share of documents, Wilson 95% CI), for each generation's sample (`screen_*`) and every "
              "model-written training text (`screen_train_*`); references: held-out real text and the base model. Figure `F7_screening`.", ""]
        try:
            plt = _plt()
            fig, axes = plt.subplots(1, 2, figsize=(9, 3.6))
            for ax, (lang, m) in zip(axes, (("EN", "screen_foreign_letter"), ("BN", "screen_latin_letter"))):
                for cid in [c for c in conf_ids if c.startswith(lang + "-")]:
                    s = sc[(sc["chain_id"].isin([cid, f"GEN0-{lang}"])) & (sc["metric"] == m)].sort_values("generation")
                    ax.plot(s["generation"], s["value"], marker="o", ms=3, label=cid)
                ax.set_title(f"{lang}: {m} (exploratory)", fontsize=7)
                ax.set_xlabel("generation")
                ax.legend(fontsize=5)
            fig.tight_layout()
            fig.savefig(out / "F7_screening.png", dpi=160)
            plt.close(fig)
        except Exception as e:  # noqa: BLE001
            R.append(f"- F7 not drawn ({type(e).__name__}: {e})")

    # ---- figures (07 §2)
    fig_series(df, ["log_ppl_heldout", "bpb_heldout", "distinct_2_logratio0", "tail_fact_recall_ALL_logratio0"], out, "F1_primary", G, conf_ids)
    fig_series(df, ["log_ppl_heldout", "bpb_heldout", "distinct_2_logratio0", "tail_fact_recall_ALL_logratio0"], out, "F1_all_chains", G)
    fig_contrasts(allh, out)
    fig_series(df, ["tail_fact_recall_HEAD", "tail_fact_recall_MID", "tail_fact_recall_TAIL"], out, "F3_recall_strata", G, conf_ids)
    fig_length(df, out)
    fig_nll(df, conf_ids, out)
    R += ["## Figures", "- F1_primary (confirmatory chains, CI bands), F1_all_chains (every chain incl. extension, seeds, controls), F2_contrasts "
          "(H1/H2 with CIs), F3_recall_strata, F4_filter (filter statistics, when the extracted step records are present), "
          "F5_length_check (shortcut check), F6_nll_under_gen0, F7_screening (exploratory), F8_novelty (robustness viii, when computed).", ""]
    return R


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--robustness", action="store_true")
    ap.add_argument("--metrics", default=str(RESULTS / "metrics.jsonl"))
    ap.add_argument("--screening", default=str(RESULTS / "screening_metrics.jsonl"))
    ap.add_argument("--out", default=str(RESULTS / "analysis"))
    ap.add_argument("--extract", default=str(RESULTS / "g6_extract" / "results" / "chains"),
                    help="step records extracted from the G4b archive (harness/tools/g6_extract.py), for T3 and F4")
    ap.add_argument("--extra", nargs="*", default=None,
                    help="extra metric files in the metrics.jsonl schema; default: results/tokenizer_metrics.jsonl and "
                         "results/semantic_dispersion.jsonl when present; give the flag alone for none")
    ap.add_argument("--novelty", default=str(RESULTS / "novelty_duplicates.jsonl"), help="robustness (viii) table")
    ap.add_argument("--no-log", action="store_true", help="do not write a decisions.md line (tests)")
    a = ap.parse_args()
    report = run(a)
    (Path(a.out) / "analysis_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"wrote {Path(a.out) / 'analysis_report.md'} ({len(report)} lines) and the tables and figures beside it")
    if not a.no_log:
        log_decision(f"regenerated analysis outputs in {a.out} (analyze.py{' --robustness' if a.robustness else ''})")


if __name__ == "__main__":
    main()
