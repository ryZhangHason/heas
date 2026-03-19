#!/usr/bin/env python3
"""
experiments/exp_b_bimodal_ablation.py
=======================================
Revision Experiment B — Bimodal convergence investigation.

Addresses reviewer CRITICAL issue #2:
  "The distribution is bimodal — runs settle near local optima (HV ≈ 4–6.5)
   or reach the global Pareto front (HV ≈ 11.7–11.8).  This is *acknowledged*
   but NOT explained mechanistically."

Two sub-tasks:

  1. VISUALISE — Load the existing 30-run eco_stats data (pop=20, ngen=10,
     steps=150) and produce a histogram that clearly shows the bimodal HV
     distribution.  Identify the escape threshold separating the two modes.

  2. ABLATE — Run NSGA-II on the same ecological setup across a population-
     budget grid:
         pop ∈ {10, 20, 30, 50}  ×  ngen ∈ {5, 10, 15, 25}
     with n=20 independent runs per cell.  For each cell, record the
     *escape rate* = fraction of runs whose HV > ESCAPE_THRESHOLD.
     This reveals whether bimodality is budget-dependent (mechanistic
     explanation: insufficient budget → initialization-dependent trap).

Results go to: experiments/results/bimodal_ablation/

Usage
-----
# Full run (all 4×4 = 16 budget cells, n=20 each)
python experiments/exp_b_bimodal_ablation.py

# Only produce the histogram from existing eco_stats data (no new runs)
python experiments/exp_b_bimodal_ablation.py --visualize-only

# Smoke test (2×2 grid, n=2 each)
python experiments/exp_b_bimodal_ablation.py --smoke

# Resume an interrupted ablation
python experiments/exp_b_bimodal_ablation.py --resume

# Choose a custom escape threshold (default: 9.0)
python experiments/exp_b_bimodal_ablation.py --escape-threshold 9.0
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from common import (
    completed_run_ids,
    compute_hvs_for_runs,
    load_completed_runs,
    log_run_progress,
    pool_reference_point,
    print_config_header,
    results_path,
    run_optimization_simple,
    save_json,
    save_run_result,
)

import heas.experiments.eco as eco
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import summarize_runs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "bimodal_ablation"
BASE_SEED = 7000

# Ablation grid
POP_SIZES  = [10, 20, 30, 50]
NGEN_LIST  = [5, 10, 15, 25]
N_RUNS_PER_CELL = 20

# Ecological simulation config (matches original eco_stats study)
STEPS = 150
N_EVAL_EPISODES = 5
EVAL_SEED = 42

# HV threshold separating "trapped in local basin" from "reached global front".
# Derived from inspection of eco_stats/pop20_ngen10_trait/summary.json:
#   low cluster:  HV ∈ [3.6, 7.4]
#   high cluster: HV ∈ [8.6, 11.8]
# A value of 9.0 cleanly separates the two modes.
DEFAULT_ESCAPE_THRESHOLD = 9.0

# Path to pre-existing eco_stats 30-run data (used for the histogram)
ECO_STATS_EXPERIMENT = "eco_stats/pop20_ngen10_trait"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_eco(steps: int, n_eval: int, seed: int) -> None:
    eco._STEPS = steps
    eco._N_EVAL_EPISODES = n_eval
    eco._EVAL_SEED = seed


def _quick_hv(result: Dict[str, Any]) -> float:
    pts = [tuple(float(v) for v in f)
           for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    return hypervolume(pts, auto_reference_point(pts))


# ---------------------------------------------------------------------------
# Sub-task 1: Visualise existing bimodal distribution
# ---------------------------------------------------------------------------

def visualize_existing_bimodal(
    escape_threshold: float = DEFAULT_ESCAPE_THRESHOLD,
) -> Dict[str, Any]:
    """Load existing 30-run eco_stats data and produce a bimodal histogram.

    Returns a dict with the hv_per_run values and escape statistics.
    """
    print("\n" + "=" * 70)
    print("Sub-task 1 — Visualise existing bimodal distribution")
    print(f"  Source: experiments/results/{ECO_STATS_EXPERIMENT}/")
    print(f"  Escape threshold: HV > {escape_threshold}")

    existing_runs = load_completed_runs(ECO_STATS_EXPERIMENT)
    if not existing_runs:
        # Also try loading from the summary JSON directly
        import json
        summary_path = results_path(ECO_STATS_EXPERIMENT, "summary.json")
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                summary = json.load(f)
            hvs = summary.get("hv_per_run", [])
            ref_pt = tuple(summary.get("reference_point", [0.0, 0.0]))
        else:
            print(f"  WARNING: No eco_stats data found at {ECO_STATS_EXPERIMENT}.")
            print("  Run eco_stats.py first, or run this script with --ablation-only.")
            return {}
    else:
        ref_pt = pool_reference_point(existing_runs)
        hvs = compute_hvs_for_runs(existing_runs, ref_pt)

    n_total = len(hvs)
    n_escaped = sum(1 for h in hvs if h > escape_threshold)
    n_trapped  = n_total - n_escaped
    escape_rate = n_escaped / max(n_total, 1)

    print(f"\n  n={n_total} runs  |  escaped (HV>{escape_threshold}): {n_escaped}  "
          f"|  trapped: {n_trapped}  |  escape rate: {escape_rate:.1%}")

    low_mode  = [h for h in hvs if h <= escape_threshold]
    high_mode = [h for h in hvs if h >  escape_threshold]
    if low_mode:
        print(f"  Low mode  (trapped):  mean={np.mean(low_mode):.2f}  "
              f"range=[{min(low_mode):.2f}, {max(low_mode):.2f}]  n={len(low_mode)}")
    if high_mode:
        print(f"  High mode (escaped):  mean={np.mean(high_mode):.2f}  "
              f"range=[{min(high_mode):.2f}, {max(high_mode):.2f}]  n={len(high_mode)}")

    result = {
        "source_experiment": ECO_STATS_EXPERIMENT,
        "escape_threshold": escape_threshold,
        "hv_per_run": list(hvs),
        "n_runs": n_total,
        "n_escaped": n_escaped,
        "n_trapped": n_trapped,
        "escape_rate": escape_rate,
        "low_mode_stats": summarize_runs(low_mode) if low_mode else {},
        "high_mode_stats": summarize_runs(high_mode) if high_mode else {},
    }
    save_json(results_path(EXPERIMENT_NAME, "existing_bimodal.json"), result)
    print(f"  Saved → experiments/results/{EXPERIMENT_NAME}/existing_bimodal.json")

    _plot_bimodal_histogram(hvs, escape_threshold, n_escaped, n_total)
    return result


def _plot_bimodal_histogram(
    hvs: List[float],
    escape_threshold: float,
    n_escaped: int,
    n_total: int,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 4))

        # Two colours: trapped (red) vs escaped (blue)
        trapped = [h for h in hvs if h <= escape_threshold]
        escaped = [h for h in hvs if h >  escape_threshold]

        bins = np.linspace(min(hvs) - 0.5, max(hvs) + 0.5, 22)
        ax.hist(trapped, bins=bins, color="salmon",    alpha=0.75,
                edgecolor="white", label=f"Trapped (HV≤{escape_threshold})  n={len(trapped)}")
        ax.hist(escaped, bins=bins, color="steelblue", alpha=0.75,
                edgecolor="white", label=f"Escaped  (HV>{escape_threshold})  n={len(escaped)}")
        ax.axvline(escape_threshold, color="black", linestyle="--", linewidth=1.2,
                   label=f"Threshold = {escape_threshold}")
        ax.set_xlabel("Hypervolume per run")
        ax.set_ylabel("Count")
        ax.set_title(
            f"Bimodal HV distribution — ecological study\n"
            f"(n={n_total} runs, pop=20, ngen=10, steps=150)\n"
            f"Escape rate: {n_escaped}/{n_total} = {n_escaped/max(n_total,1):.1%}"
        )
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        path = results_path(EXPERIMENT_NAME, "figs", "bimodal_histogram.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  Histogram → {path}")
    except Exception as exc:
        print(f"  (Histogram plot skipped: {exc})")


# ---------------------------------------------------------------------------
# Sub-task 2: Population budget ablation
# ---------------------------------------------------------------------------

def run_budget_ablation(
    pop_sizes: List[int] = POP_SIZES,
    ngen_list: List[int] = NGEN_LIST,
    n_runs: int = N_RUNS_PER_CELL,
    escape_threshold: float = DEFAULT_ESCAPE_THRESHOLD,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Run NSGA-II across a (pop × ngen) budget grid; compute escape rate per cell."""
    if smoke:
        pop_sizes = [10, 20]
        ngen_list  = [5, 10]
        n_runs     = 2

    config = dict(
        experiment=EXPERIMENT_NAME,
        pop_sizes=pop_sizes,
        ngen_list=ngen_list,
        n_runs_per_cell=n_runs,
        steps=STEPS,
        n_eval_episodes=N_EVAL_EPISODES,
        eval_seed=EVAL_SEED,
        escape_threshold=escape_threshold,
        base_seed=BASE_SEED,
        purpose="Budget ablation to explain bimodal convergence (reviewer CRITICAL #2)",
    )
    print("\n" + "=" * 70)
    print("Sub-task 2 — Budget ablation across pop × ngen grid")
    print_config_header(config)

    # Collect all runs across every cell so we can pool a global reference point
    all_cell_runs: Dict[str, List[Dict]] = {}

    for pop in pop_sizes:
        for ngen in ngen_list:
            cell_key = f"pop{pop}_ngen{ngen}"
            sub = f"{EXPERIMENT_NAME}/{cell_key}"
            done = completed_run_ids(sub) if resume else set()

            print(f"\n  --- Cell: pop={pop}, ngen={ngen} ---")
            t0 = time.time()
            for run_id in range(n_runs):
                if run_id in done:
                    continue
                seed = BASE_SEED + pop * 1000 + ngen * 100 + run_id
                # Use slightly different eval seed per run to avoid correlation
                _set_eco(STEPS, N_EVAL_EPISODES, EVAL_SEED + run_id * 13)
                t_run = time.time()
                ea = run_optimization_simple(
                    objective_fn=eco.trait_objective,
                    gene_schema=eco.TRAIT_SCHEMA,
                    strategy="nsga2",
                    pop_size=pop,
                    n_generations=ngen,
                    seed=seed,
                )
                result = {
                    "run_id":  run_id,
                    "seed":    seed,
                    "pop":     pop,
                    "ngen":    ngen,
                    "steps":   STEPS,
                    "base_seed": BASE_SEED,
                    "elapsed_s": time.time() - t_run,
                    "hof_fitness":  ea.get("hof_fitness", []),
                    "hall_of_fame": ea.get("hall_of_fame", []),
                }
                save_run_result(result, sub, run_id)
                log_run_progress(run_id, n_runs, _quick_hv(result),
                                 time.time() - t0)
            all_cell_runs[cell_key] = load_completed_runs(sub)

    # Pool a single reference point across ALL cells for fair HV comparison
    combined_runs = [r for runs in all_cell_runs.values() for r in runs]
    global_ref = pool_reference_point(combined_runs)
    print(f"\n  Global reference point: {global_ref}")

    # --- Compute escape rates ---
    escape_matrix: Dict[str, Dict[str, float]] = {}
    mean_hv_matrix: Dict[str, Dict[str, float]] = {}

    for pop in pop_sizes:
        escape_matrix[str(pop)] = {}
        mean_hv_matrix[str(pop)] = {}
        for ngen in ngen_list:
            cell_key = f"pop{pop}_ngen{ngen}"
            runs = all_cell_runs.get(cell_key, [])
            hvs = compute_hvs_for_runs(runs, global_ref)
            n_esc = sum(1 for h in hvs if h > escape_threshold)
            esc_rate = n_esc / max(len(hvs), 1)
            escape_matrix[str(pop)][str(ngen)] = esc_rate
            mean_hv_matrix[str(pop)][str(ngen)] = float(np.mean(hvs)) if hvs else 0.0

    # --- Print ASCII escape rate table ---
    print(f"\n  Escape Rate (HV > {escape_threshold}) by budget cell:")
    header = "         " + "".join(f"  ngen={n:>2}" for n in ngen_list)
    print(header)
    for pop in pop_sizes:
        row = f"  pop={pop:<3}"
        for ngen in ngen_list:
            esc = escape_matrix[str(pop)][str(ngen)]
            row += f"     {esc:.0%}  "
        print(row)

    print(f"\n  Mean HV by budget cell:")
    print(header)
    for pop in pop_sizes:
        row = f"  pop={pop:<3}"
        for ngen in ngen_list:
            mhv = mean_hv_matrix[str(pop)][str(ngen)]
            row += f"  {mhv:6.2f}  "
        print(row)

    # --- Save summary ---
    ablation_summary = {
        "config": config,
        "global_reference_point": list(global_ref),
        "escape_threshold": escape_threshold,
        "escape_rate_matrix": escape_matrix,
        "mean_hv_matrix": mean_hv_matrix,
        "cells": {
            f"pop{pop}_ngen{ngen}": {
                "hv_per_run": compute_hvs_for_runs(
                    all_cell_runs.get(f"pop{pop}_ngen{ngen}", []), global_ref),
                "stats": summarize_runs(
                    compute_hvs_for_runs(
                        all_cell_runs.get(f"pop{pop}_ngen{ngen}", []), global_ref)
                    or [0.0]),
            }
            for pop in pop_sizes for ngen in ngen_list
        },
    }
    save_json(results_path(EXPERIMENT_NAME, "ablation_summary.json"), ablation_summary)
    print(f"\n  Ablation summary → experiments/results/{EXPERIMENT_NAME}/ablation_summary.json")

    _plot_escape_rate_heatmap(pop_sizes, ngen_list, escape_matrix, escape_threshold)
    _plot_mean_hv_heatmap(pop_sizes, ngen_list, mean_hv_matrix)

    return ablation_summary


def _plot_escape_rate_heatmap(
    pop_sizes: List[int],
    ngen_list: List[int],
    escape_matrix: Dict[str, Dict[str, float]],
    escape_threshold: float,
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        matrix = np.array([
            [escape_matrix[str(pop)][str(ngen)] for ngen in ngen_list]
            for pop in pop_sizes
        ])
        fig, ax = plt.subplots(figsize=(6, 4))
        im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn",
                       vmin=0.0, vmax=1.0)
        ax.set_xticks(range(len(ngen_list)))
        ax.set_yticks(range(len(pop_sizes)))
        ax.set_xticklabels([f"ngen={n}" for n in ngen_list])
        ax.set_yticklabels([f"pop={p}" for p in pop_sizes])
        for i, pop in enumerate(pop_sizes):
            for j, ngen in enumerate(ngen_list):
                ax.text(j, i, f"{matrix[i,j]:.0%}",
                        ha="center", va="center", fontsize=10, fontweight="bold")
        plt.colorbar(im, ax=ax, label=f"Escape rate (HV > {escape_threshold})")
        ax.set_xlabel("Generations (ngen)")
        ax.set_ylabel("Population size")
        ax.set_title(
            f"Escape rate heatmap\n"
            f"(escape = HV > {escape_threshold}, n={N_RUNS_PER_CELL} runs/cell)"
        )
        fig.tight_layout()

        path = results_path(EXPERIMENT_NAME, "figs", "escape_rate_heatmap.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  Escape rate heatmap → {path}")
    except Exception as exc:
        print(f"  (Escape rate heatmap skipped: {exc})")


def _plot_mean_hv_heatmap(
    pop_sizes: List[int],
    ngen_list: List[int],
    mean_hv_matrix: Dict[str, Dict[str, float]],
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        matrix = np.array([
            [mean_hv_matrix[str(pop)][str(ngen)] for ngen in ngen_list]
            for pop in pop_sizes
        ])
        fig, ax = plt.subplots(figsize=(6, 4))
        im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
        ax.set_xticks(range(len(ngen_list)))
        ax.set_yticks(range(len(pop_sizes)))
        ax.set_xticklabels([f"ngen={n}" for n in ngen_list])
        ax.set_yticklabels([f"pop={p}" for p in pop_sizes])
        for i in range(len(pop_sizes)):
            for j in range(len(ngen_list)):
                ax.text(j, i, f"{matrix[i,j]:.2f}",
                        ha="center", va="center", fontsize=9)
        plt.colorbar(im, ax=ax, label="Mean HV")
        ax.set_xlabel("Generations (ngen)")
        ax.set_ylabel("Population size")
        ax.set_title("Mean hypervolume by budget cell")
        fig.tight_layout()

        path = results_path(EXPERIMENT_NAME, "figs", "mean_hv_heatmap.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  Mean HV heatmap → {path}")
    except Exception as exc:
        print(f"  (Mean HV heatmap skipped: {exc})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Exp B — Bimodal convergence investigation (reviewer CRITICAL #2)"
    )
    p.add_argument("--visualize-only", action="store_true",
                   help="Only produce histogram from existing eco_stats data; no new runs")
    p.add_argument("--ablation-only", action="store_true",
                   help="Skip histogram; only run budget ablation")
    p.add_argument("--smoke",  action="store_true",
                   help="Smoke test: 2×2 grid, n=2 each")
    p.add_argument("--resume", action="store_true",
                   help="Skip already-completed cells")
    p.add_argument("--escape-threshold", type=float, default=DEFAULT_ESCAPE_THRESHOLD,
                   help=f"HV threshold for 'escaped' (default: {DEFAULT_ESCAPE_THRESHOLD})")
    p.add_argument("--n-runs", type=int, default=N_RUNS_PER_CELL,
                   help="Independent runs per budget cell")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    if not args.ablation_only:
        visualize_existing_bimodal(escape_threshold=args.escape_threshold)

    if not args.visualize_only:
        run_budget_ablation(
            escape_threshold=args.escape_threshold,
            n_runs=args.n_runs,
            resume=args.resume,
            smoke=args.smoke,
        )

    print(f"\n  All outputs in: experiments/results/{EXPERIMENT_NAME}/")


if __name__ == "__main__":
    main()
