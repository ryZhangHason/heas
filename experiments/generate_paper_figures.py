#!/usr/bin/env python3
"""
experiments/generate_paper_figures.py
======================================
Generate paper-optimized figures for HEAS draft V3.

WSC 2026 requirement: all text in figures ≥ 9pt in final print.
Strategy: set figsize = intended display width in paper (inches),
so the scale factor is 1.0 and fonts appear at exactly the specified size.

WSC single-column text width = 6.5 inches.
We display figures at:
  - full column  → figsize_width = 6.5 in, \includegraphics[width=\columnwidth]
  - 85% column   → figsize_width = 5.5 in, \includegraphics[width=0.85\columnwidth]

All body-text fonts in figures ≥ 9pt.

Outputs → HEAS draft V3/figs/  (overwrites the exploration figures)
"""
import os, json, sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import csv

# ── paths ────────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.abspath(__file__))
RESULTS   = os.path.join(_HERE, "results")
OUTDIR    = os.path.join(os.path.dirname(_HERE), "HEAS draft V3", "figs")
os.makedirs(OUTDIR, exist_ok=True)

# ── global style ─────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":      "DejaVu Sans",   # closest available; WSC allows Arial
    "font.size":        9,
    "axes.titlesize":   9,
    "axes.labelsize":   9,
    "xtick.labelsize":  8.5,
    "ytick.labelsize":  8.5,
    "legend.fontsize":  8.5,
    "figure.dpi":       200,
})

C = {"nsga2": "#2196F3", "random": "#9E9E9E", "eco": "#4CAF50",
     "ci": "#F44336", "champion": "#2196F3"}

def _load(path):
    with open(path) as f:
        return json.load(f)

def _save(fig, name):
    p = os.path.join(OUTDIR, name)
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    print(f"  → {name}")


# ── Fig A: Large-scale algorithm showdown ────────────────────────────────────
# One panel (bar + strip), full column width.
# Display at width=\columnwidth → figsize_w = 6.5 in
def fig_a_showdown():
    d    = _load(os.path.join(RESULTS, "large_scale_comparison", "p1_summary.json"))
    hvs  = d["hv_by_strategy"]
    sts  = d["stats_by_strategy"]
    cfg  = d["config"]
    test = d["statistical_tests"]["nsga2_vs_random"]

    fig, ax = plt.subplots(figsize=(6.5, 3.6))

    x      = np.array([0, 1])
    labels = ["NSGA-II", "Random"]
    means  = [sts[s]["mean"]  for s in ["nsga2", "random"]]
    stds   = [sts[s]["std"]   for s in ["nsga2", "random"]]
    ci_lo  = [sts[s]["mean"] - sts[s]["ci_lower"] for s in ["nsga2", "random"]]
    ci_hi  = [sts[s]["ci_upper"] - sts[s]["mean"] for s in ["nsga2", "random"]]
    colors = [C["nsga2"], C["random"]]

    bars = ax.bar(x, means, width=0.45, alpha=0.72, color=colors,
                  yerr=stds, capsize=7, error_kw=dict(linewidth=1.5))
    ax.errorbar(x, means, yerr=[ci_lo, ci_hi],
                fmt="none", color=C["ci"], capsize=11, linewidth=2,
                label="95% CI", zorder=5)

    # per-run scatter
    for i, s in enumerate(["nsga2", "random"]):
        jit = np.random.RandomState(i).uniform(-0.16, 0.16, len(hvs[s]))
        ax.scatter(x[i] + jit, hvs[s], color=colors[i], alpha=0.45, s=18, zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Hypervolume")
    ax.set_xlabel(f"Strategy  (steps={cfg['steps']:,}, episodes={cfg['n_eval']}, "
                  f"pop={cfg['pop_size']}, ngen={cfg['n_generations']}, n={cfg['n_runs']})")
    ax.legend(loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)

    sig = "***" if test["p_value"] < 0.001 else "**" if test["p_value"] < 0.01 else "*"
    ax.text(0.5, 0.97,
            f"Wilcoxon p = {test['p_value']:.2e} {sig},  Cohen's d = {test['cohens_d']:.2f}",
            transform=ax.transAxes, ha="center", va="top", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF9C4", alpha=0.85))

    fig.tight_layout()
    _save(fig, "fig4_large_scale_showdown.pdf")


# ── Fig B: Tournament noise stability ────────────────────────────────────────
# Single panel, 85% column.
# Display at width=0.85\columnwidth → figsize_w = 5.5 in
def fig_b_noise():
    d       = _load(os.path.join(RESULTS, "tournament_stress", "noise_stability.json"))
    by_sig  = d.get("results_by_sigma", d.get("by_sigma", {}))
    keys    = list(by_sig.keys())
    sigmas  = [float(k) for k in keys]
    means   = [by_sig[k].get("mean", by_sig[k].get("mean_tau", 0)) for k in keys]
    ci_lo   = [by_sig[k]["ci_lower"] for k in keys]
    ci_hi   = [by_sig[k]["ci_upper"] for k in keys]

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    ax.plot(sigmas, means, "o-", color=C["eco"], linewidth=2, markersize=6,
            label="Mean Kendall \u03c4")
    ax.fill_between(sigmas, ci_lo, ci_hi, alpha=0.2, color=C["eco"], label="95% CI")
    ax.axhline(1.0, linestyle=":", color="black", linewidth=0.8, alpha=0.6)

    # annotate key points
    for s, t in zip(sigmas, means):
        if s in (0.0, 10.0, 50.0, 200.0):
            ax.annotate(f"\u03c4={t:.3f}", (s, t),
                        textcoords="offset points", xytext=(5, 5), fontsize=8)

    ax.set_xlabel("Noise \u03c3 (injected into episode scores)")
    ax.set_ylabel("Kendall \u03c4")
    ax.set_ylim(0.42, 1.08)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save(fig, "fig8_noise_stability.pdf")


# ── Fig C: Champion vs Reference — 32 scenarios ──────────────────────────────
# Bar chart (Δ biomass), full column.
# Display at width=\columnwidth → figsize_w = 6.5 in
def fig_c_champion32():
    rows = []
    with open(os.path.join(RESULTS, "large_scale_comparison",
                            "p3_champion_vs_ref_32.csv")) as f:
        for row in csv.DictReader(f):
            rows.append(row)
    d   = _load(os.path.join(RESULTS, "large_scale_comparison", "p3_summary.json"))
    agg = d["aggregate"]
    tst = d["statistical_tests"]
    cfg = d["config"]

    delta = [float(r["delta"]) for r in rows]
    ids   = list(range(len(delta)))
    colors = [C["champion"] if v >= 0 else "#EF5350" for v in delta]

    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    ax.bar(ids, delta, color=colors, alpha=0.82, width=0.85)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axhline(agg["mean_delta"], linestyle="--", color=C["champion"],
               linewidth=1.8, label=f"Mean \u0394 = +{agg['mean_delta']:.1f} "
                                     f"(+{agg['pct_gain']:.1f}%)")

    ax.set_xlabel("Held-out scenario index (0\u201331)")
    ax.set_ylabel("\u0394 prey biomass  (champion \u2212 reference)")
    ax.set_title(f"Champion vs. Reference: {agg['n_wins']}/{agg['n_scenarios']} wins  "
                 f"(steps={cfg['steps']}, n\u2091\u2093={cfg['n_eval']})")
    ax.legend(loc="upper left")
    ax.grid(True, axis="y", alpha=0.3)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    sig = "***" if tst["p_value"] < 0.001 else "**" if tst["p_value"] < 0.01 else "*"
    ax.text(0.99, 0.04,
            f"Wilcoxon p = {tst['p_value']:.2e} {sig},  d = {tst['cohens_d']:.2f}",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#FFF9C4", alpha=0.85))

    fig.tight_layout()
    _save(fig, "fig7_champion_32scenarios.pdf")


# ── Fig D: Scale sensitivity heatmap ─────────────────────────────────────────
# 3×3 heatmap, 85% column (square-ish aspect).
# Display at width=0.85\columnwidth → figsize_w = 5.5 in
def fig_d_heatmap():
    d = _load(os.path.join(RESULTS, "baseline_comparison", "scale_grid.json"))
    steps_list  = [140, 300, 500]
    n_eval_list = [5, 10, 20]

    matrix = np.array([
        [d["grid_results"][f"steps{s}_ep{e}"]["stats"]["mean"] for e in n_eval_list]
        for s in steps_list
    ])
    matrix_std = np.array([
        [d["grid_results"][f"steps{s}_ep{e}"]["stats"]["std"] for e in n_eval_list]
        for s in steps_list
    ])

    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto",
                   vmin=matrix.min() - 0.5, vmax=matrix.max() + 0.5)

    ax.set_xticks(range(len(n_eval_list)))
    ax.set_yticks(range(len(steps_list)))
    ax.set_xticklabels([f"ep = {e}" for e in n_eval_list])
    ax.set_yticklabels([f"steps = {s}" for s in steps_list])
    ax.set_xlabel("Episodes per genome evaluation")
    ax.set_ylabel("Steps per episode")

    threshold = matrix.mean()
    for i in range(len(steps_list)):
        for j in range(len(n_eval_list)):
            txt_color = "white" if matrix[i, j] > threshold else "black"
            ax.text(j, i,
                    f"{matrix[i,j]:.2f}\n\u00b1{matrix_std[i,j]:.2f}",
                    ha="center", va="center", fontsize=9, color=txt_color)

    cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label("Mean Hypervolume", fontsize=9)
    cbar.ax.tick_params(labelsize=8.5)

    fig.tight_layout()
    _save(fig, "fig3_scale_heatmap.pdf")


# ── main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Generating paper-optimized figures → {OUTDIR}\n")
    np.random.seed(42)
    fig_a_showdown()
    fig_b_noise()
    fig_c_champion32()
    fig_d_heatmap()
    print("\nDone. All 4 figures regenerated at paper scale.")
    print("Font baseline: 9pt body text, 8.5pt ticks/legend.")
    print("Figures designed at target display width — scale factor = 1.0 in paper.")
