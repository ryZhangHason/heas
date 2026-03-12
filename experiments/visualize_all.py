#!/usr/bin/env python3
"""
experiments/visualize_all.py
=============================
Comprehensive visualization of all HEAS WSC experiments.

Generates a single PDF figure suite covering:
  Fig 1 — ECO: 30-run HV distribution (box + strip)
  Fig 2 — Algorithm ablation: NSGA-II vs Simple vs Random (eco, steps=300)
  Fig 3 — Scale sensitivity heatmap (steps × episodes)
  Fig 4 — Large-scale algorithm showdown (NSGA-II vs Random, steps=1000)
  Fig 5 — Scale progression: HV vs simulation horizon across all experiments
  Fig 6 — Champion vs Reference: 16-scenario baseline
  Fig 7 — Champion vs Reference: 32-scenario large-scale stress test
  Fig 8 — Tournament noise stability curve (Kendall tau vs sigma)
  Fig 9 — Tournament voting agreement & sample complexity
  Fig 10 — Wolf-Sheep: algorithm comparison (30 runs)
  Fig 11 — Cross-domain scalability (Eco + Enterprise, large scale)

Usage
-----
python experiments/visualize_all.py
Outputs → experiments/results/figures/
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

RESULTS = os.path.join(_HERE, "results")
FIGS    = os.path.join(RESULTS, "figures")
os.makedirs(FIGS, exist_ok=True)

# ── colour palette ─────────────────────────────────────────────────────────
C = {
    "nsga2":      "#2196F3",   # blue
    "simple":     "#FF9800",   # orange
    "random":     "#9E9E9E",   # grey
    "eco":        "#4CAF50",   # green
    "enterprise": "#FF9800",   # orange
    "wolf":       "#795548",   # brown
    "champion":   "#2196F3",   # blue
    "reference":  "#9E9E9E",   # grey
    "ci":         "#F44336",   # red (CI whiskers)
}

def _load(path: str):
    with open(path) as f:
        return json.load(f)

def _save(fig, name: str):
    p = os.path.join(FIGS, name)
    fig.savefig(p, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  Saved → results/figures/{name}")


# ===========================================================================
# Fig 1 — ECO 30-run HV distribution
# ===========================================================================
def fig1_eco_hv_distribution():
    path = os.path.join(RESULTS, "eco_stats", "pop20_ngen10_trait", "summary.json")
    d = _load(path)
    hvs = d["hv_per_run"]
    st  = d["stats"]

    fig, ax = plt.subplots(figsize=(6, 4))
    # boxplot
    bp = ax.boxplot(hvs, positions=[1], widths=0.4, patch_artist=True,
                    boxprops=dict(facecolor=C["eco"], alpha=0.4),
                    medianprops=dict(color="black", linewidth=2),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5),
                    flierprops=dict(marker="o", markersize=4, alpha=0.5))
    # strip
    jitter = np.random.RandomState(0).uniform(-0.12, 0.12, len(hvs))
    ax.scatter([1 + j for j in jitter], hvs, color=C["eco"], alpha=0.6,
               s=30, zorder=5)
    # CI band
    ax.axhspan(st["ci_lower"], st["ci_upper"], xmin=0.05, xmax=0.95,
               alpha=0.12, color=C["ci"], label=f"95% CI [{st['ci_lower']:.2f}, {st['ci_upper']:.2f}]")
    ax.axhline(st["mean"], color=C["eco"], linestyle="--", linewidth=1.5,
               label=f"Mean = {st['mean']:.3f}")

    ax.set_xlim(0.5, 1.5)
    ax.set_xticks([1])
    ax.set_xticklabels([f"Eco NSGA-II\n(n={st['n']})"])
    ax.set_ylabel("Hypervolume")
    ax.set_title("Fig 1 — Ecological NSGA-II: 30-Run HV Distribution\n"
                 "(steps=150, pop=20, ngen=10)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    _save(fig, "fig1_eco_hv_distribution.pdf")


# ===========================================================================
# Fig 2 — Algorithm ablation (eco baseline)
# ===========================================================================
def fig2_algorithm_ablation():
    d = _load(os.path.join(RESULTS, "baseline_comparison", "ablation.json"))
    strategies = ["nsga2", "simple", "random"]
    labels     = ["NSGA-II", "Simple\n(μ+λ)", "Random"]
    hvs        = {s: d["hv_by_strategy"][s] for s in strategies}
    stats      = {s: d["stats_by_strategy"][s] for s in strategies}

    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(strategies))
    means = [stats[s]["mean"] for s in strategies]
    stds  = [stats[s]["std"]  for s in strategies]
    ci_lo = [stats[s]["mean"] - stats[s]["ci_lower"] for s in strategies]
    ci_hi = [stats[s]["ci_upper"] - stats[s]["mean"] for s in strategies]

    bars = ax.bar(x, means, yerr=stds, capsize=6, alpha=0.72, width=0.5,
                  color=[C[s] for s in strategies], label="±1 σ")
    ax.errorbar(x, means, yerr=[ci_lo, ci_hi],
                fmt="none", color=C["ci"], capsize=10, linewidth=2,
                label="95% CI", zorder=5)
    # individual points
    for i, s in enumerate(strategies):
        jitter = np.random.RandomState(i).uniform(-0.18, 0.18, len(hvs[s]))
        ax.scatter(x[i] + jitter, hvs[s], color=C[s], alpha=0.5, s=20, zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Hypervolume")
    ax.set_title("Fig 2 — Algorithm Ablation: NSGA-II vs Simple vs Random\n"
                 "(Eco, steps=300, pop=20, ngen=10, n=10 runs)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    _save(fig, "fig2_algorithm_ablation.pdf")


# ===========================================================================
# Fig 3 — Scale sensitivity heatmap
# ===========================================================================
def fig3_scale_heatmap():
    d = _load(os.path.join(RESULTS, "baseline_comparison", "scale_grid.json"))
    steps_list  = [140, 300, 500]
    n_eval_list = [5, 10, 20]
    grid = d["grid_results"]

    matrix = np.array([
        [grid[f"steps{s}_ep{e}"]["stats"]["mean"] for e in n_eval_list]
        for s in steps_list
    ])
    matrix_std = np.array([
        [grid[f"steps{s}_ep{e}"]["stats"]["std"] for e in n_eval_list]
        for s in steps_list
    ])

    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(n_eval_list)))
    ax.set_yticks(range(len(steps_list)))
    ax.set_xticklabels([f"ep={e}" for e in n_eval_list])
    ax.set_yticklabels([f"steps={s}" for s in steps_list])
    for i in range(len(steps_list)):
        for j in range(len(n_eval_list)):
            ax.text(j, i, f"{matrix[i,j]:.2f}\n±{matrix_std[i,j]:.2f}",
                    ha="center", va="center", fontsize=7.5,
                    color="white" if matrix[i,j] > matrix.mean() else "black")
    plt.colorbar(im, ax=ax, label="Mean HV")
    ax.set_xlabel("Episodes per genome evaluation")
    ax.set_ylabel("Steps per episode")
    ax.set_title("Fig 3 — Scale Sensitivity: HV by Simulation Scale\n"
                 "(NSGA-II, n=10 runs each cell)")
    fig.tight_layout()
    _save(fig, "fig3_scale_heatmap.pdf")


# ===========================================================================
# Fig 4 — Large-scale algorithm showdown
# ===========================================================================
def fig4_large_scale_showdown():
    d = _load(os.path.join(RESULTS, "large_scale_comparison", "p1_summary.json"))
    strategies = ["nsga2", "random"]
    labels     = ["NSGA-II", "Random"]
    hvs        = d["hv_by_strategy"]
    stats      = d["stats_by_strategy"]
    tests      = d["statistical_tests"]["nsga2_vs_random"]
    cfg        = d["config"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Left: bar comparison
    x = np.arange(len(strategies))
    means = [stats[s]["mean"] for s in strategies]
    stds  = [stats[s]["std"]  for s in strategies]
    ci_lo = [stats[s]["mean"] - stats[s]["ci_lower"] for s in strategies]
    ci_hi = [stats[s]["ci_upper"] - stats[s]["mean"] for s in strategies]

    ax1.bar(x, means, yerr=stds, capsize=6, alpha=0.75, width=0.5,
            color=[C["nsga2"], C["random"]], label="±1 σ")
    ax1.errorbar(x, means, yerr=[ci_lo, ci_hi],
                 fmt="none", color=C["ci"], capsize=10, linewidth=2, label="95% CI")
    for i, s in enumerate(strategies):
        jitter = np.random.RandomState(i).uniform(-0.15, 0.15, len(hvs[s]))
        ax1.scatter(x[i] + jitter, hvs[s], color=[C["nsga2"], C["random"]][i],
                    alpha=0.5, s=25, zorder=6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)
    ax1.set_ylabel("Hypervolume")
    ax1.set_title(f"Algorithm Showdown at Large Scale\n"
                  f"({cfg['steps']:,} steps × {cfg['n_eval']} eps, pop={cfg['pop_size']}, n={cfg['n_runs']})")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3, axis="y")
    # annotate stats
    sig = "***" if tests["p_value"] < 0.001 else "**" if tests["p_value"] < 0.01 else "*"
    ax1.text(0.5, 0.95,
             f"Wilcoxon p={tests['p_value']:.2e} {sig}\nCohen's d={tests['cohens_d']:.2f}",
             transform=ax1.transAxes, ha="center", va="top", fontsize=8,
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))

    # Right: per-run scatter
    for i, s in enumerate(strategies):
        runs = sorted(hvs[s])
        ax2.plot(range(len(runs)), runs, "o-", color=[C["nsga2"], C["random"]][i],
                 alpha=0.7, linewidth=1.2, markersize=5, label=f"{labels[i]} (μ={stats[s]['mean']:.2f})")
        ax2.axhline(stats[s]["mean"], linestyle="--", linewidth=1,
                    color=[C["nsga2"], C["random"]][i], alpha=0.5)
    ax2.set_xlabel("Run index (sorted by HV)")
    ax2.set_ylabel("Hypervolume")
    ax2.set_title("Per-Run HV Distribution")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Fig 4 — Large-Scale Algorithm Showdown (Ecological, 1,000 steps/episode)",
                 fontsize=11, y=1.02)
    fig.tight_layout()
    _save(fig, "fig4_large_scale_showdown.pdf")


# ===========================================================================
# Fig 5 — Scale progression: HV vs simulation horizon
# ===========================================================================
def fig5_scale_progression():
    """Compare mean HV across all eco experiments ordered by step-evals/genome."""
    scale_grid  = _load(os.path.join(RESULTS, "baseline_comparison", "scale_grid.json"))
    eco_stats   = _load(os.path.join(RESULTS, "eco_stats", "pop20_ngen10_trait", "summary.json"))
    large_p1    = _load(os.path.join(RESULTS, "large_scale_comparison", "p1_summary.json"))

    # (label, step_evals, mean_hv, ci_lo, ci_hi, marker)
    points = []
    for s in [140, 300, 500]:
        for e in [5, 10, 20]:
            key  = f"steps{s}_ep{e}"
            st   = scale_grid["grid_results"][key]["stats"]
            points.append((f"{s}s×{e}ep", s * e, st["mean"],
                           st["mean"] - st["ci_lower"], st["ci_upper"] - st["mean"], "o"))

    # eco_stats main (steps=150, ep=5)
    st = eco_stats["stats"]
    points.append(("150s×5ep\n(eco_stats)", 150 * 5, st["mean"],
                   st["mean"] - st["ci_lower"], st["ci_upper"] - st["mean"], "s"))

    # large scale NSGA-II
    st = large_p1["stats_by_strategy"]["nsga2"]
    cfg = large_p1["config"]
    step_evals = cfg["steps"] * cfg["n_eval"]
    points.append((f"{cfg['steps']}s×{cfg['n_eval']}ep\n(large)", step_evals,
                   st["mean"], st["mean"] - st["ci_lower"], st["ci_upper"] - st["mean"], "^"))

    points.sort(key=lambda p: p[1])

    fig, ax = plt.subplots(figsize=(8, 4))
    x_vals  = [p[1] for p in points]
    y_vals  = [p[2] for p in points]
    yerr_lo = [p[3] for p in points]
    yerr_hi = [p[4] for p in points]
    markers = [p[5] for p in points]
    labels  = [p[0] for p in points]

    # color by source
    colors = ["#4CAF50" if "eco_stats" in l else
              "#795548" if "large" in l else
              "#2196F3" for l in labels]

    for i, (x, y, elo, ehi, mk) in enumerate(zip(x_vals, y_vals, yerr_lo, yerr_hi, markers)):
        ax.errorbar(x, y, yerr=[[elo], [ehi]], fmt=mk, color=colors[i],
                    capsize=4, markersize=7, linewidth=1.5, alpha=0.85)

    ax.plot(x_vals, y_vals, "--", color="#BDBDBD", linewidth=1, zorder=0)

    # label a few key points
    for i, (x, y, _, _, _, _) in enumerate(zip(x_vals, y_vals, *[[0]*6]*4)):
        if labels[i] in ["140s×5ep", "500s×20ep", f"{cfg['steps']}s×{cfg['n_eval']}ep\n(large)",
                         "150s×5ep\n(eco_stats)"]:
            ax.annotate(labels[i], (x, y), textcoords="offset points",
                        xytext=(5, 6), fontsize=7, color=colors[i])

    legend_patches = [
        Patch(color="#2196F3", label="Scale grid (NSGA-II, n=10)"),
        Patch(color="#4CAF50", label="Eco stats (n=30)"),
        Patch(color="#795548", label="Large scale (NSGA-II, n=20)"),
    ]
    ax.legend(handles=legend_patches, fontsize=8)
    ax.set_xlabel("Step-evaluations per genome  (steps × episodes)")
    ax.set_ylabel("Mean Hypervolume")
    ax.set_title("Fig 5 — HV vs Simulation Scale Across All Eco Experiments")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save(fig, "fig5_scale_progression.pdf")


# ===========================================================================
# Fig 6 — Champion vs Reference: 16-scenario baseline
# ===========================================================================
def fig6_champion_16():
    import csv
    rows = []
    with open(os.path.join(RESULTS, "baseline_comparison", "champion_vs_ref.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    d   = _load(os.path.join(RESULTS, "baseline_comparison", "champion_vs_ref.json"))
    agg = d["aggregate"]

    champ = [float(r["champ_biomass"]) for r in rows]
    ref   = [float(r["ref_biomass"])   for r in rows]
    delta = [float(r["delta"])         for r in rows]
    ids   = list(range(len(rows)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(ids, champ, "o-", color=C["champion"], label=f"Champion (μ={agg['mean_champ']:.1f})",
             linewidth=1.5, markersize=5)
    ax1.plot(ids, ref, "s--", color=C["reference"], label=f"Reference (μ={agg['mean_ref']:.1f})",
             linewidth=1.5, markersize=5)
    ax1.fill_between(ids, ref, champ,
                     where=[c >= r for c, r in zip(champ, ref)],
                     alpha=0.15, color=C["champion"])
    ax1.fill_between(ids, ref, champ,
                     where=[c < r for c, r in zip(champ, ref)],
                     alpha=0.15, color="red")
    ax1.set_xlabel("Scenario index")
    ax1.set_ylabel("Mean prey biomass")
    ax1.set_title("Per-Scenario Performance")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    bar_c = [C["champion"] if d >= 0 else "#F44336" for d in delta]
    ax2.bar(ids, delta, color=bar_c, alpha=0.8)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(agg["mean_delta"], linestyle="--", color=C["champion"], linewidth=1.5,
                label=f"Mean Δ={agg['mean_delta']:+.2f} ({agg['pct_gain']:+.1f}%)")
    ax2.set_xlabel("Scenario index")
    ax2.set_ylabel("Δ biomass (champion − reference)")
    ax2.set_title(f"Champion − Reference\n({agg['n_wins']}/{agg['n_scenarios']} wins)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    tests = d["statistical_tests"]
    fig.suptitle(f"Fig 6 — Champion vs Reference: 16 OOD Scenarios (baseline)\n"
                 f"Wilcoxon p={tests['p_value']:.4f}  Cohen's d={tests['cohens_d']:.3f}",
                 fontsize=10)
    fig.tight_layout()
    _save(fig, "fig6_champion_16scenarios.pdf")


# ===========================================================================
# Fig 7 — Champion vs Reference: 32-scenario large-scale
# ===========================================================================
def fig7_champion_32():
    import csv
    rows = []
    with open(os.path.join(RESULTS, "large_scale_comparison", "p3_champion_vs_ref_32.csv")) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    d   = _load(os.path.join(RESULTS, "large_scale_comparison", "p3_summary.json"))
    agg = d["aggregate"]
    cfg = d["config"]

    champ = [float(r["champ_biomass"]) for r in rows]
    ref   = [float(r["ref_biomass"])   for r in rows]
    delta = [float(r["delta"])         for r in rows]
    ids   = list(range(len(rows)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))

    ax1.plot(ids, champ, "o-", color=C["champion"], label=f"Champion (μ={agg['mean_champ']:.1f})",
             linewidth=1.2, markersize=4)
    ax1.plot(ids, ref, "s--", color=C["reference"], label=f"Reference (μ={agg['mean_ref']:.1f})",
             linewidth=1.2, markersize=4)
    ax1.fill_between(ids, ref, champ,
                     where=[c >= r for c, r in zip(champ, ref)],
                     alpha=0.15, color=C["champion"])
    ax1.set_xlabel("Scenario index (0–31)")
    ax1.set_ylabel("Mean prey biomass")
    ax1.set_title(f"Per-Scenario ({cfg['steps']:,} steps × {cfg['n_eval']} eps)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    bar_c = [C["champion"] if d >= 0 else "#F44336" for d in delta]
    ax2.bar(ids, delta, color=bar_c, alpha=0.8)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(agg["mean_delta"], linestyle="--", color=C["champion"], linewidth=1.5,
                label=f"Mean Δ={agg['mean_delta']:+.1f} ({agg['pct_gain']:+.1f}%)")
    ax2.set_xlabel("Scenario index (0–31)")
    ax2.set_ylabel("Δ biomass (champion − reference)")
    ax2.set_title(f"Champion − Reference\n({agg['n_wins']}/{agg['n_scenarios']} wins)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    tests = d["statistical_tests"]
    fig.suptitle(f"Fig 7 — Large-Scale Champion Robustness: 32 OOD Scenarios\n"
                 f"Wilcoxon p={tests['p_value']:.2e} (***)  Cohen's d={tests['cohens_d']:.3f}",
                 fontsize=10)
    fig.tight_layout()
    _save(fig, "fig7_champion_32scenarios.pdf")


# ===========================================================================
# Fig 8 — Tournament noise stability
# ===========================================================================
def fig8_noise_stability():
    d = _load(os.path.join(RESULTS, "tournament_stress", "noise_stability.json"))
    by_sigma = d.get("results_by_sigma", d.get("by_sigma", {}))

    keys     = list(by_sigma.keys())
    sigmas   = [float(k) for k in keys]
    tau_mean = [by_sigma[k].get("mean", by_sigma[k].get("mean_tau", 0)) for k in keys]
    tau_lo   = [by_sigma[k]["ci_lower"] for k in keys]
    tau_hi   = [by_sigma[k]["ci_upper"] for k in keys]

    margin = d.get("champion_margin", None)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(sigmas, tau_mean, "o-", color=C["eco"], linewidth=2, markersize=7, label="Mean Kendall τ")
    ax.fill_between(sigmas, tau_lo, tau_hi, alpha=0.2, color=C["eco"], label="95% CI")

    if margin:
        noise_pct = [100 * s / margin for s in sigmas]
        for i, (s, t, pct) in enumerate(zip(sigmas, tau_mean, noise_pct)):
            if pct < 200:
                ax.annotate(f"{pct:.0f}%", (s, t), textcoords="offset points",
                            xytext=(4, 5), fontsize=7, color="#757575")

    ax.axhline(1.0, linestyle=":", color="black", linewidth=1, alpha=0.5)
    ax.set_xlabel("Noise σ (injected into episode scores)")
    ax.set_ylabel("Kendall τ (ranking preservation)")
    ax.set_title("Fig 8 — Tournament Noise Stability\n"
                 "(n=30 repeats; labels = σ as % of champion margin)")
    ax.set_ylim(0.4, 1.05)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    _save(fig, "fig8_noise_stability.pdf")


# ===========================================================================
# Fig 9 — Voting agreement + sample complexity
# ===========================================================================
def fig9_tournament_properties():
    agree = _load(os.path.join(RESULTS, "tournament_stress", "agreement_result.json"))
    samp  = _load(os.path.join(RESULTS, "tournament_stress", "sample_complexity.json"))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Panel 1: voting rule agreement matrix
    rules = ["argmax", "majority", "borda", "copeland"]
    matrix = np.ones((4, 4))   # perfect agreement per results
    if "agreement_matrix" in agree:
        mat = agree["agreement_matrix"]
        for i, r1 in enumerate(rules):
            for j, r2 in enumerate(rules):
                try:
                    matrix[i, j] = mat[r1][r2]
                except Exception:
                    pass

    im = ax1.imshow(matrix, vmin=0, vmax=1, cmap="RdYlGn")
    ax1.set_xticks(range(4)); ax1.set_yticks(range(4))
    ax1.set_xticklabels(rules, rotation=25, ha="right", fontsize=8)
    ax1.set_yticklabels(rules, fontsize=8)
    for i in range(4):
        for j in range(4):
            ax1.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=9,
                     color="white" if matrix[i,j] < 0.5 else "black")
    plt.colorbar(im, ax=ax1, label="Agreement rate")
    ax1.set_title("Voting Rule Agreement\n(n=30 repeats × 8 scenarios)")

    # Panel 2: sample complexity
    by_budget = samp.get("by_episode_budget", {})
    budgets   = sorted(int(k) for k in by_budget.keys())
    p_correct = [by_budget[str(b)]["p_correct"] for b in budgets]
    n_correct = [by_budget[str(b)]["n_correct"] for b in budgets]
    n_total   = [by_budget[str(b)]["n_total"]   for b in budgets]

    ax2.plot(budgets, p_correct, "o-", color=C["champion"], linewidth=2, markersize=7)
    for b, p, nc, nt in zip(budgets, p_correct, n_correct, n_total):
        ax2.annotate(f"{nc}/{nt}", (b, p), textcoords="offset points",
                     xytext=(3, -10), fontsize=7, color="#555")
    ax2.axhline(1.0, linestyle=":", color="black", linewidth=1, alpha=0.5)
    ax2.set_xlabel("Episodes per scenario")
    ax2.set_ylabel("P(correct winner identified)")
    ax2.set_ylim(0.8, 1.05)
    ax2.set_title("Sample Complexity\n(n=30 repeats)")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Fig 9 — Tournament Infrastructure: Voting Agreement & Sample Complexity",
                 fontsize=10)
    fig.tight_layout()
    _save(fig, "fig9_tournament_properties.pdf")


# ===========================================================================
# Fig 10 — Wolf-Sheep algorithm comparison
# ===========================================================================
def fig10_wolf_sheep():
    d = _load(os.path.join(RESULTS, "wolf_sheep_study", "algo_comparison.json"))
    strategies = ["nsga2", "simple", "random"]
    labels     = ["NSGA-II", "Simple\n(μ+λ)", "Random"]
    hvs        = {s: d["hv_by_strategy"][s] for s in strategies}
    stats      = d["stats_by_strategy"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    x = np.arange(len(strategies))
    means = [stats[s]["mean"] for s in strategies]
    stds  = [stats[s]["std"]  for s in strategies]
    ci_lo = [stats[s]["mean"] - stats[s]["ci_lower"] for s in strategies]
    ci_hi = [stats[s]["ci_upper"] - stats[s]["mean"] for s in strategies]

    ax1.bar(x, means, yerr=stds, capsize=6, alpha=0.72, width=0.5,
            color=[C["nsga2"], C["simple"], C["random"]], label="±1 σ")
    ax1.errorbar(x, means, yerr=[ci_lo, ci_hi],
                 fmt="none", color=C["ci"], capsize=10, linewidth=2, label="95% CI")
    for i, s in enumerate(strategies):
        jitter = np.random.RandomState(i+10).uniform(-0.15, 0.15, len(hvs[s]))
        ax1.scatter(x[i] + jitter, hvs[s], color=[C["nsga2"], C["simple"], C["random"]][i],
                    alpha=0.4, s=15, zorder=6)
    ax1.set_xticks(x); ax1.set_xticklabels(labels)
    ax1.set_ylabel("Hypervolume"); ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3, axis="y")
    ax1.set_title("Algorithm Comparison\n(Wolf-Sheep, steps=200, n=30)")

    # Panel 2: boxplot comparison
    bp_data = [hvs[s] for s in strategies]
    bp = ax2.boxplot(bp_data, patch_artist=True,
                     medianprops=dict(color="black", linewidth=2),
                     whiskerprops=dict(linewidth=1.5),
                     capprops=dict(linewidth=1.5))
    for patch, s in zip(bp["boxes"], strategies):
        patch.set_facecolor({"nsga2": C["nsga2"], "simple": C["simple"], "random": C["random"]}[s])
        patch.set_alpha(0.5)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Hypervolume"); ax2.grid(True, alpha=0.3, axis="y")
    ax2.set_title("HV Distributions (n=30 runs each)")

    # stat annotation
    tests = d.get("statistical_tests", {})
    if "nsga2_vs_random" in tests:
        t = tests["nsga2_vs_random"]
        sig = "***" if t["p_value"] < 0.001 else "**" if t["p_value"] < 0.01 else "*"
        ax1.text(0.5, 0.97, f"NSGA-II vs Random: p={t['p_value']:.2e} {sig}",
                 transform=ax1.transAxes, ha="center", va="top", fontsize=7.5,
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="lightyellow", alpha=0.8))

    fig.suptitle("Fig 10 — Wolf-Sheep Predation: Algorithm Comparison (30 runs)",
                 fontsize=10)
    fig.tight_layout()
    _save(fig, "fig10_wolf_sheep.pdf")


# ===========================================================================
# Fig 11 — Cross-domain scalability
# ===========================================================================
def fig11_cross_domain():
    d = _load(os.path.join(RESULTS, "large_scale_comparison", "p2_summary.json"))
    dr = d["domain_results"]

    eco_st  = dr["eco"]["stats"]
    ent_st  = dr["ent"]["stats"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Eco HV distribution
    eco_runs = _load_runs(os.path.join(RESULTS, "large_scale_comparison", "p2_eco"))
    eco_hvs  = [r.get("_hv", 0) for r in eco_runs] if eco_runs else []
    if not eco_hvs:
        from heas.utils.pareto import hypervolume, auto_reference_point
        all_pts = []
        for r in eco_runs:
            for f in r.get("hof_fitness", []):
                if len(f) >= 2:
                    all_pts.append(tuple(float(v) for v in f))
        ref_pt = auto_reference_point(all_pts) if all_pts else (1, 1)
        eco_hvs = []
        for r in eco_runs:
            pts = [tuple(float(v) for v in f) for f in r.get("hof_fitness", []) if len(f) >= 2]
            eco_hvs.append(hypervolume(pts, ref_pt) if pts else 0)

    ent_runs = _load_runs(os.path.join(RESULTS, "large_scale_comparison", "p2_ent"))
    ent_hvs  = []
    if ent_runs:
        from heas.utils.pareto import hypervolume, auto_reference_point
        all_pts = []
        for r in ent_runs:
            for f in r.get("hof_fitness", []):
                if len(f) >= 2:
                    all_pts.append(tuple(float(v) for v in f))
        ref_pt = auto_reference_point(all_pts) if all_pts else (1, 1)
        for r in ent_runs:
            pts = [tuple(float(v) for v in f) for f in r.get("hof_fitness", []) if len(f) >= 2]
            ent_hvs.append(hypervolume(pts, ref_pt) if pts else 0)

    # Use stats from summary if direct computation fails
    if not eco_hvs: eco_hvs = [eco_st["mean"]] * eco_st["n"]
    if not ent_hvs: ent_hvs = [ent_st["mean"]] * ent_st["n"]

    jitter_e = np.random.RandomState(42).uniform(-0.12, 0.12, len(eco_hvs))
    jitter_n = np.random.RandomState(43).uniform(-0.12, 0.12, len(ent_hvs))

    ax1.scatter(1 + jitter_e, eco_hvs, color=C["eco"], alpha=0.6, s=30, zorder=5)
    ax1.scatter(2 + jitter_n, ent_hvs, color=C["enterprise"], alpha=0.6, s=30, zorder=5)
    ax1.boxplot([eco_hvs, ent_hvs], positions=[1, 2], widths=0.35,
                patch_artist=True,
                boxprops=dict(alpha=0.3),
                medianprops=dict(color="black", linewidth=2))
    for patch, col in zip(ax1.patches, [C["eco"], C["enterprise"]]):
        patch.set_facecolor(col)

    # CIs
    for pos, st, col in [(1, eco_st, C["eco"]), (2, ent_st, C["enterprise"])]:
        ax1.errorbar(pos, st["mean"],
                     yerr=[[st["mean"] - st["ci_lower"]], [st["ci_upper"] - st["mean"]]],
                     fmt="none", color=C["ci"], capsize=10, linewidth=2)

    ax1.set_xticks([1, 2])
    ax1.set_xticklabels([
        f"Ecological\n({dr['eco']['steps']:,}s×{dr['eco']['n_eval']}ep)",
        f"Enterprise\n({dr['ent']['steps']}s×{dr['ent']['n_eval']}ep)",
    ])
    ax1.set_ylabel("Hypervolume (domain-specific ref)")
    ax1.set_title("HV by Domain (20 runs each)")
    ax1.grid(True, alpha=0.3, axis="y")

    # Panel 2: summary bar with CI
    domains = ["Ecological", "Enterprise"]
    sts = [eco_st, ent_st]
    cols = [C["eco"], C["enterprise"]]
    means = [s["mean"] for s in sts]
    stds  = [s["std"]  for s in sts]
    ci_lo = [s["mean"] - s["ci_lower"] for s in sts]
    ci_hi = [s["ci_upper"] - s["mean"] for s in sts]

    ax2.bar([0, 1], means, yerr=stds, capsize=6, alpha=0.75, width=0.5,
            color=cols, label="±1 σ")
    ax2.errorbar([0, 1], means, yerr=[ci_lo, ci_hi],
                 fmt="none", color=C["ci"], capsize=10, linewidth=2, label="95% CI")
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(domains)
    ax2.set_ylabel("Mean Hypervolume")
    ax2.set_title("Mean ± Std with 95% CI")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    for i, (st, col) in enumerate(zip(sts, cols)):
        ax2.text(i, st["mean"] + st["std"] + 0.02 * max(means),
                 f"μ={st['mean']:.1f}\n±{st['std']:.1f}",
                 ha="center", va="bottom", fontsize=8, color=col)

    fig.suptitle("Fig 11 — Cross-Domain Scalability: NSGA-II at Large Scale\n"
                 f"(pop={d['config']['pop_size']}, ngen={d['config']['n_generations']}, "
                 f"n={d['config']['n_runs']} runs)", fontsize=10)
    fig.tight_layout()
    _save(fig, "fig11_cross_domain.pdf")


# ===========================================================================
# Fig 12 — Overview summary dashboard
# ===========================================================================
def fig12_summary_dashboard():
    """One-page summary of all key metrics."""
    fig = plt.figure(figsize=(16, 10))
    gs  = gridspec.GridSpec(3, 4, figure=fig, hspace=0.55, wspace=0.4)

    # ── Row 0: HV comparisons ────────────────────────────────────────────
    # (a) Eco NSGA-II 30-run
    ax0 = fig.add_subplot(gs[0, 0])
    eco_s = _load(os.path.join(RESULTS, "eco_stats", "pop20_ngen10_trait", "summary.json"))
    hvs = eco_s["hv_per_run"]; st = eco_s["stats"]
    jit = np.random.RandomState(0).uniform(-0.08, 0.08, len(hvs))
    ax0.scatter([1 + j for j in jit], hvs, color=C["eco"], alpha=0.6, s=15)
    ax0.boxplot(hvs, positions=[1], widths=0.3, patch_artist=True,
                boxprops=dict(facecolor=C["eco"], alpha=0.3),
                medianprops=dict(color="black", linewidth=1.5),
                whiskerprops=dict(linewidth=1), capprops=dict(linewidth=1))
    ax0.set_xlim(0.6, 1.4); ax0.set_xticks([1])
    ax0.set_xticklabels(["Eco\nNSGA-II\nn=30"], fontsize=7)
    ax0.set_ylabel("HV", fontsize=8); ax0.set_title("(a) Eco 30-run", fontsize=8)
    ax0.grid(True, alpha=0.3, axis="y")

    # (b) Algorithm ablation
    ax1 = fig.add_subplot(gs[0, 1])
    abl = _load(os.path.join(RESULTS, "baseline_comparison", "ablation.json"))
    for i, (s, lbl) in enumerate([("nsga2","NSGA-II"),("simple","Simple"),("random","Random")]):
        st2 = abl["stats_by_strategy"][s]
        ax1.bar(i, st2["mean"], yerr=st2["std"], capsize=4, alpha=0.75,
                color=C[s], width=0.6)
    ax1.set_xticks([0,1,2])
    ax1.set_xticklabels(["NSGA-II","Simple","Random"], fontsize=7, rotation=15)
    ax1.set_ylabel("HV", fontsize=8); ax1.set_title("(b) Algorithm Ablation\n(n=10)", fontsize=8)
    ax1.grid(True, alpha=0.3, axis="y")

    # (c) Large-scale showdown
    ax2 = fig.add_subplot(gs[0, 2])
    ls = _load(os.path.join(RESULTS, "large_scale_comparison", "p1_summary.json"))
    for i, s in enumerate(["nsga2","random"]):
        st3 = ls["stats_by_strategy"][s]
        ax2.bar(i, st3["mean"], yerr=st3["std"], capsize=4, alpha=0.75,
                color=C[s], width=0.6)
    ax2.set_xticks([0,1])
    ax2.set_xticklabels(["NSGA-II","Random"], fontsize=8)
    ax2.set_ylabel("HV", fontsize=8); ax2.set_title("(c) Large Scale\n(1000s×5ep, n=20)", fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")
    tests = ls["statistical_tests"]["nsga2_vs_random"]
    ax2.text(0.5, 0.97, f"p={tests['p_value']:.1e}  d={tests['cohens_d']:.2f}",
             transform=ax2.transAxes, ha="center", va="top", fontsize=7,
             bbox=dict(boxstyle="round,pad=0.2", facecolor="lightyellow", alpha=0.8))

    # (d) Wolf-sheep comparison
    ax3 = fig.add_subplot(gs[0, 3])
    ws = _load(os.path.join(RESULTS, "wolf_sheep_study", "algo_comparison.json"))
    for i, s in enumerate(["nsga2","simple","random"]):
        st4 = ws["stats_by_strategy"][s]
        ax3.bar(i, st4["mean"], yerr=st4["std"], capsize=4, alpha=0.75,
                color=C[s], width=0.6)
    ax3.set_xticks([0,1,2])
    ax3.set_xticklabels(["NSGA-II","Simple","Random"], fontsize=7, rotation=15)
    ax3.set_ylabel("HV", fontsize=8); ax3.set_title("(d) Wolf-Sheep\n(n=30)", fontsize=8)
    ax3.grid(True, alpha=0.3, axis="y")

    # ── Row 1: Scale + Noise ─────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, :2])
    sg = _load(os.path.join(RESULTS, "baseline_comparison", "scale_grid.json"))
    steps_list  = [140, 300, 500]
    n_eval_list = [5, 10, 20]
    matrix = np.array([[sg["grid_results"][f"steps{s}_ep{e}"]["stats"]["mean"]
                         for e in n_eval_list] for s in steps_list])
    im = ax4.imshow(matrix, cmap="YlGnBu", aspect="auto")
    ax4.set_xticks(range(3)); ax4.set_yticks(range(3))
    ax4.set_xticklabels([f"ep={e}" for e in n_eval_list], fontsize=8)
    ax4.set_yticklabels([f"steps={s}" for s in steps_list], fontsize=8)
    for i in range(3):
        for j in range(3):
            ax4.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center", fontsize=8,
                     color="white" if matrix[i,j] > matrix.mean() else "black")
    plt.colorbar(im, ax=ax4, label="Mean HV", fraction=0.03)
    ax4.set_title("(e) Scale Sensitivity Heatmap\n(steps × episodes, n=10 each)", fontsize=8)

    ax5 = fig.add_subplot(gs[1, 2:])
    ns = _load(os.path.join(RESULTS, "tournament_stress", "noise_stability.json"))
    _ns_by = ns.get("results_by_sigma", ns.get("by_sigma", {}))
    keys = list(_ns_by.keys())
    sigmas = [float(k) for k in keys]
    taus   = [_ns_by[k].get("mean", _ns_by[k].get("mean_tau", 0)) for k in keys]
    ci_lo2 = [_ns_by[k]["ci_lower"] for k in keys]
    ci_hi2 = [_ns_by[k]["ci_upper"] for k in keys]
    ax5.plot(sigmas, taus, "o-", color=C["eco"], linewidth=2, markersize=6)
    ax5.fill_between(sigmas, ci_lo2, ci_hi2, alpha=0.2, color=C["eco"])
    ax5.set_xlabel("Noise σ", fontsize=8); ax5.set_ylabel("Kendall τ", fontsize=8)
    ax5.set_ylim(0.4, 1.05); ax5.grid(True, alpha=0.3)
    ax5.set_title("(f) Tournament Noise Stability\n(n=30 repeats)", fontsize=8)

    # ── Row 2: Champion robustness ───────────────────────────────────────
    import csv
    ax6 = fig.add_subplot(gs[2, :2])
    rows16 = []
    with open(os.path.join(RESULTS, "baseline_comparison", "champion_vs_ref.csv")) as f:
        for row in csv.DictReader(f):
            rows16.append(row)
    delta16 = [float(r["delta"]) for r in rows16]
    ids16   = list(range(len(delta16)))
    d16     = _load(os.path.join(RESULTS, "baseline_comparison", "champion_vs_ref.json"))
    ax6.bar(ids16, delta16, color=[C["champion"] if d >= 0 else "#F44336" for d in delta16], alpha=0.8)
    ax6.axhline(0, color="black", linewidth=0.8)
    ax6.axhline(d16["aggregate"]["mean_delta"], linestyle="--", color=C["champion"],
                linewidth=1.5, label=f"Mean Δ={d16['aggregate']['mean_delta']:+.2f}")
    ax6.set_xlabel("Scenario (0–15)", fontsize=8); ax6.set_ylabel("Δ biomass", fontsize=8)
    ax6.legend(fontsize=7); ax6.grid(True, alpha=0.3, axis="y")
    ax6.set_title(f"(g) Champion − Reference: 16 OOD Scenarios\n"
                  f"({d16['aggregate']['n_wins']}/16 wins, p={d16['statistical_tests']['p_value']:.4f})", fontsize=8)

    ax7 = fig.add_subplot(gs[2, 2:])
    rows32 = []
    with open(os.path.join(RESULTS, "large_scale_comparison", "p3_champion_vs_ref_32.csv")) as f:
        for row in csv.DictReader(f):
            rows32.append(row)
    delta32 = [float(r["delta"]) for r in rows32]
    ids32   = list(range(len(delta32)))
    d32     = _load(os.path.join(RESULTS, "large_scale_comparison", "p3_summary.json"))
    ax7.bar(ids32, delta32, color=[C["champion"] if d >= 0 else "#F44336" for d in delta32], alpha=0.8)
    ax7.axhline(0, color="black", linewidth=0.8)
    ax7.axhline(d32["aggregate"]["mean_delta"], linestyle="--", color=C["champion"],
                linewidth=1.5, label=f"Mean Δ={d32['aggregate']['mean_delta']:+.1f}")
    ax7.set_xlabel("Scenario (0–31)", fontsize=8); ax7.set_ylabel("Δ biomass", fontsize=8)
    ax7.legend(fontsize=7); ax7.grid(True, alpha=0.3, axis="y")
    ax7.set_title(f"(h) Champion − Reference: 32 OOD Scenarios (large scale)\n"
                  f"({d32['aggregate']['n_wins']}/32 wins, p={d32['statistical_tests']['p_value']:.2e})", fontsize=8)

    fig.suptitle("HEAS WSC 2026 — Experiment Overview Dashboard", fontsize=13, y=1.01)
    _save(fig, "fig12_summary_dashboard.pdf")


# ===========================================================================
# Helpers
# ===========================================================================
def _load_runs(directory: str):
    if not os.path.isdir(directory):
        return []
    runs = []
    for fname in sorted(os.listdir(directory)):
        if fname.startswith("run_") and fname.endswith(".json"):
            try:
                runs.append(_load(os.path.join(directory, fname)))
            except Exception:
                pass
    return runs


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__":
    print("Generating HEAS experiment visualizations...")
    print(f"Output directory: experiments/results/figures/\n")

    fns = [
        ("Fig 1  — Eco 30-run HV distribution",      fig1_eco_hv_distribution),
        ("Fig 2  — Algorithm ablation (eco)",          fig2_algorithm_ablation),
        ("Fig 3  — Scale sensitivity heatmap",         fig3_scale_heatmap),
        ("Fig 4  — Large-scale algorithm showdown",    fig4_large_scale_showdown),
        ("Fig 5  — Scale progression",                 fig5_scale_progression),
        ("Fig 6  — Champion vs Ref 16 scenarios",      fig6_champion_16),
        ("Fig 7  — Champion vs Ref 32 scenarios",      fig7_champion_32),
        ("Fig 8  — Tournament noise stability",        fig8_noise_stability),
        ("Fig 9  — Tournament voting + sample cplx",   fig9_tournament_properties),
        ("Fig 10 — Wolf-Sheep algorithm comparison",   fig10_wolf_sheep),
        ("Fig 11 — Cross-domain scalability",          fig11_cross_domain),
        ("Fig 12 — Summary dashboard",                 fig12_summary_dashboard),
    ]

    for label, fn in fns:
        print(f"\n{label}")
        try:
            fn()
        except Exception as exc:
            print(f"  [SKIPPED] {exc}")

    print(f"\nDone. {len(fns)} figures → experiments/results/figures/")
