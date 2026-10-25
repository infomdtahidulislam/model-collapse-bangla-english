"""Figure for the 2026-10-22 revision: registered controls and the registered decoding pair, drawn from T1_metrics.csv.
Panels per language: (1) held-out log-perplexity relative to generation 0 for REPLACE, REAL-REPEAT and ACCUMULATE;
(2) raw distinct-2 and (3) mean sample NLL under the generation-0 model for REPLACE under top-p 1.0 (registered) and
top-p 0.95 (registered robustness pair). Generation 0 of the top-p 0.95 chain is the shared generation-0 model sampled at
top-p 1.0, drawn as a separate open marker. Usage: python plot_controls_decoder.py <T1_metrics.csv> <out_stem>"""
import sys
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
d = pd.read_csv(sys.argv[1]); stem = sys.argv[2]
plt.rcParams.update({"font.size": 7.5, "axes.titlesize": 7.5, "axes.labelsize": 7.5, "legend.fontsize": 6.8,
                     "xtick.labelsize": 6.8, "ytick.labelsize": 6.8, "axes.linewidth": 0.6, "font.family": "DejaVu Sans"})
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
S = {"REPLACE": dict(c="#2a78d6", ls="-", m="o", lab="REPLACE (top-p 1.0)"),
     "REAL-REPEAT": dict(c="#eb6834", ls="--", m="s", lab="REAL-REPEAT"),
     "ACCUMULATE": dict(c="#1baf7a", ls=":", m="^", lab="ACCUMULATE"),
     "REPLACE-topp95": dict(c="#e34948", ls="-.", m="D", lab="REPLACE (top-p 0.95)")}
def series(chain, metric):
    s = d[(d.chain_id == chain) & (d.metric == metric) & (d.generation.between(0, 6))].sort_values("generation")
    return s.generation.values, s.value.values, s.ci_lo.values, s.ci_hi.values
def draw(ax, L, arm, metric, start=0):
    g, v, lo, hi = series(f"{L}-{arm}", metric); k = g >= start; st = S[arm]
    ax.fill_between(g[k], lo[k], hi[k], color=st["c"], alpha=0.15, lw=0)
    ax.plot(g[k], v[k], color=st["c"], ls=st["ls"], lw=1.4, marker=st["m"], ms=3.2, mec="#fcfcfb", mew=0.6, label=st["lab"])
    return g, v
fig, axes = plt.subplots(2, 3, figsize=(6.6, 4.3), constrained_layout=True)
for r, (L, name) in enumerate([("EN", "English"), ("BN", "Bangla")]):
    ax = axes[r, 0]
    for arm in ["REPLACE", "REAL-REPEAT", "ACCUMULATE"]:
        draw(ax, L, arm, "log_ppl_heldout_rel0")
    ax.set_ylabel("Held-out log-perplexity\nminus generation 0 (nats)")
    ax.set_title(f"({'ad'[r]}) {name}: held-out loss", loc="left", color=INK)
    for j, (arm, metric, yl, tt) in enumerate([("distinct_2", "distinct_2", "distinct-2 (raw, 50,000-word window)", "distinct-2"),
                                                ("sample_nll", "sample_nll_ref_mean", "Sample NLL under\ngeneration-0 model (nats/token)", "sample NLL")], start=1):
        ax = axes[r, j]
        g, v = draw(ax, L, "REPLACE", metric)
        draw(ax, L, "REPLACE-topp95", metric, start=1)
        ax.plot([0], [v[0]], ls="none", marker="o", ms=4.2, mfc="white", mec=INK, mew=0.8, label="shared gen. 0 (top-p 1.0)", zorder=5)
        ax.set_ylabel(yl); ax.set_title(f"({'bcef'[2 * r + j - 1]}) {name}: {tt}", loc="left", color=INK)
for ax in axes.flat:
    ax.set_xticks(range(7)); ax.set_xlabel("Generation", color=MUTED)
    ax.grid(True, color=GRID, lw=0.5); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"): ax.spines[sp].set_color(MUTED)
    ax.tick_params(colors=MUTED, width=0.5, length=2.5)
axes[0, 0].legend(frameon=False, loc="upper left", handlelength=2.6)
axes[1, 1].legend(frameon=False, loc="lower left", handlelength=2.6)
fig.savefig(stem + ".png", dpi=300); fig.savefig(stem + ".svg")
print("written", stem)
