#!/usr/bin/env python3
"""
experiments/noise_aware.py
===========================
Experiment 5 — Noise-aware optimization.

Compares three evaluation budgets:
  - 1-seed  (single episode per genome evaluation)
  - 5-seed  (5 episodes, mean fitness)
  - 10-seed (10 episodes, mean fitness)

For each budget, 30 independent NSGA-II runs are executed.
Reports hypervolume statistics with bootstrap CIs and Wilcoxon tests
comparing budgets pairwise.

Usage
-----
python experiments/noise_aware.py          # all 3 budgets
python experiments/noise_aware.py --smoke  # quick test
python experiments/noise_aware.py --seeds 1 5 10  # explicit budget list

Results
-------
All outputs go to experiments/results/noise_aware/
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from functools import partial
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from common import (
    compute_hvs_for_runs,
    completed_run_ids,
    load_completed_runs,
    log_run_progress,
    pool_reference_point,
    print_config_header,
    print_summary_table,
    results_path,
    run_optimization_simple,
    save_json,
    save_run_result,
    format_table_row,
)

import heas.experiments.eco as eco
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import bootstrap_ci, cohens_d, summarize_runs, wilcoxon_test

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "noise_aware"
BASE_SEED = 4000
N_RUNS = 30
DEFAULT_POP = 50
DEFAULT_NGEN = 25
EVAL_SEED_BASE = 42
STEPS = 140

SEED_BUDGETS = [1, 5, 10]  # number of evaluation episodes per genome


def _select_requested_runs(all_runs: List[Dict[str, Any]], n_runs: int) -> List[Dict[str, Any]]:
    """Keep only run_<id> entries for ids in [0, n_runs)."""
    selected = [r for r in all_runs if int(r.get("run_id", -1)) < n_runs]
    selected.sort(key=lambda r: int(r.get("run_id", -1)))
    return selected


# ---------------------------------------------------------------------------
# Per-budget objective factory
# ---------------------------------------------------------------------------

def _make_noise_aware_objective(n_eval_seeds: int, run_seed: int):
    """
    Return a trait-based ecological objective that averages over n_eval_seeds.
    We need a module-level function for pickling — the partial is created here
    but the actual computation is in _trait_objective_with_n_seeds.
    """
    # Use run-specific RNG so each objective call sees fresh evaluation noise.
    # This makes seed-budget averaging meaningful while remaining reproducible per run.
    seed_rng = np.random.default_rng(run_seed + 10_007)

    def objective(genome) -> tuple:
        """Mean-of-n fitness: average (-mean_biomass, cv) over n_eval_seeds."""
        results = []
        eval_seeds = seed_rng.integers(0, 2**31 - 1, size=n_eval_seeds, dtype=np.int64)
        for seed_offset, eval_seed in enumerate(eval_seeds):
            eco._N_EVAL_EPISODES = 1
            eco._EVAL_SEED = int(eval_seed + EVAL_SEED_BASE + seed_offset)
            try:
                obj = eco.trait_objective(genome)
                results.append(obj)
            except Exception:
                # Worst-case fallback for minimization objective.
                results.append((0.0, 1.0))
        # Mean across seeds
        mean_neg_prey = float(np.mean([r[0] for r in results]))
        mean_ext_rate = float(np.mean([r[1] for r in results]))
        return (mean_neg_prey, mean_ext_rate)

    objective.__name__ = f"noise_aware_{n_eval_seeds}seed"
    return objective


# ---------------------------------------------------------------------------
# Run one optimization with given n_eval_seeds budget
# ---------------------------------------------------------------------------

def _run_optimization(
    run_id: int,
    pop_size: int,
    n_generations: int,
    seed: int,
    n_eval_seeds: int,
) -> Dict[str, Any]:
    """Run one NSGA-II optimization with given evaluation budget."""
    objective_fn = _make_noise_aware_objective(n_eval_seeds, run_seed=seed)
    schema = eco.TRAIT_SCHEMA

    t0 = time.time()
    ea_result = run_optimization_simple(
        objective_fn=objective_fn,
        gene_schema=schema,
        strategy="nsga2",
        pop_size=pop_size,
        n_generations=n_generations,
        seed=seed,
    )
    elapsed = time.time() - t0

    return {
        "run_id": run_id,
        "seed": seed,
        "n_eval_seeds": n_eval_seeds,
        "pop_size": pop_size,
        "n_generations": n_generations,
        "elapsed_s": elapsed,
        "hof_fitness": ea_result.get("hof_fitness", []),
        "hall_of_fame": ea_result.get("hall_of_fame", []),
        "logbook": ea_result.get("logbook", []),
    }


def _quick_hv(result: Dict[str, Any]) -> float:
    pts = [tuple(float(v) for v in f) for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    ref = auto_reference_point(pts)
    return hypervolume(pts, ref)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(
    seed_budgets: Optional[List[int]] = None,
    pop_size: int = DEFAULT_POP,
    n_generations: int = DEFAULT_NGEN,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Run 30-run study for each evaluation budget in seed_budgets."""
    if smoke:
        n_runs = 2
        pop_size = 5
        n_generations = 2

    if seed_budgets is None:
        seed_budgets = SEED_BUDGETS

    config = dict(
        seed_budgets=seed_budgets,
        pop_size=pop_size,
        n_generations=n_generations,
        n_runs=n_runs,
        base_seed=BASE_SEED,
    )
    print_config_header(config)

    all_runs_by_budget: Dict[int, List[Dict]] = {}

    for n_seeds in seed_budgets:
        sub_experiment = f"{EXPERIMENT_NAME}/{n_seeds}seed"
        done_ids: set = completed_run_ids(sub_experiment) if resume else set()

        print(f"\n--- Budget: {n_seeds} eval seed(s) per genome ---")
        if done_ids:
            print(f"  Resuming: {len(done_ids)} run(s) already completed.")

        t_start = time.time()
        for run_id in range(n_runs):
            if run_id in done_ids:
                continue
            seed = BASE_SEED + run_id
            result = _run_optimization(run_id, pop_size, n_generations, seed, n_seeds)
            save_run_result(result, sub_experiment, run_id)
            hv_preview = _quick_hv(result)
            log_run_progress(run_id, n_runs, hv_preview, time.time() - t_start)

        all_runs = _select_requested_runs(load_completed_runs(sub_experiment), n_runs)
        all_runs_by_budget[n_seeds] = all_runs

    # Pool reference across ALL budgets for fair HV comparison
    all_runs_flat = [r for runs in all_runs_by_budget.values() for r in runs]
    ref_pt = pool_reference_point(all_runs_flat)

    hvs_by_budget: Dict[int, List[float]] = {}
    for n_seeds in seed_budgets:
        hvs = compute_hvs_for_runs(all_runs_by_budget[n_seeds], ref_pt)
        hvs_by_budget[n_seeds] = hvs

    # Print summary table
    print("\n=== Noise-Aware Optimization Results ===")
    rows = [(f"Eco trait — {n}-seed eval", hvs_by_budget[n]) for n in seed_budgets]
    print_summary_table(rows)

    # Pairwise Wilcoxon tests
    wilcoxon_results = {}
    if len(seed_budgets) >= 2:
        print("\n  Pairwise Wilcoxon tests:")
        for i in range(len(seed_budgets)):
            for j in range(i + 1, len(seed_budgets)):
                n1, n2 = seed_budgets[i], seed_budgets[j]
                hvs1, hvs2 = hvs_by_budget[n1], hvs_by_budget[n2]
                if len(hvs1) >= 5 and len(hvs2) >= 5:
                    try:
                        stat, pval = wilcoxon_test(hvs1, hvs2)
                        d = cohens_d(hvs1, hvs2)
                        key = f"{n1}seed_vs_{n2}seed"
                        wilcoxon_results[key] = {
                            "statistic": stat, "p_value": pval, "cohens_d": d
                        }
                        print(f"    {n1}-seed vs {n2}-seed: "
                              f"stat={stat:.4f}, p={pval:.4f}, d={d:.4f}")
                    except Exception as exc:
                        print(f"    {n1}-seed vs {n2}-seed: skipped ({exc})")

    # Save CSV summary
    csv_path = results_path(EXPERIMENT_NAME, "summary_table.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["budget_seeds", "mean_hv", "std_hv", "ci_lower", "ci_upper", "n"])
        for n_seeds in seed_budgets:
            s = summarize_runs(hvs_by_budget[n_seeds])
            w.writerow([n_seeds, s["mean"], s["std"], s["ci_lower"], s["ci_upper"], s["n"]])
    print(f"\n  CSV → experiments/results/{EXPERIMENT_NAME}/summary_table.csv")

    # Save full results
    full_result = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_by_budget": {str(n): hvs_by_budget[n] for n in seed_budgets},
        "stats_by_budget": {
            str(n): summarize_runs(hvs_by_budget[n]) for n in seed_budgets
        },
        "wilcoxon": wilcoxon_results,
    }
    save_json(results_path(EXPERIMENT_NAME, "summary.json"), full_result)
    print(f"  Summary → experiments/results/{EXPERIMENT_NAME}/summary.json")

    # LaTeX rows
    print("\n  LaTeX rows:")
    for n_seeds in seed_budgets:
        print("  " + format_table_row(f"Eco trait {n_seeds}-seed", hvs_by_budget[n_seeds]))

    # Visualization
    try:
        _plot_hv_by_budget(seed_budgets, hvs_by_budget)
        _plot_runtime_comparison(seed_budgets, all_runs_by_budget)
    except Exception as exc:
        print(f"  (Plots skipped: {exc})")

    return full_result


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def _plot_hv_by_budget(
    seed_budgets: List[int],
    hvs_by_budget: Dict[int, List[float]],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    means = [float(np.mean(hvs_by_budget[n])) for n in seed_budgets]
    stds = [float(np.std(hvs_by_budget[n])) for n in seed_budgets]
    ci_lo = [bootstrap_ci(hvs_by_budget[n])[0] if len(hvs_by_budget[n]) >= 2 else means[i]
             for i, n in enumerate(seed_budgets)]
    ci_hi = [bootstrap_ci(hvs_by_budget[n])[1] if len(hvs_by_budget[n]) >= 2 else means[i]
             for i, n in enumerate(seed_budgets)]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(seed_budgets))
    ax.bar(x, means, yerr=stds, capsize=5, color="steelblue", alpha=0.7, label="±1 std")
    ax.errorbar(x, means, yerr=[
        [m - lo for m, lo in zip(means, ci_lo)],
        [hi - m for m, hi in zip(means, ci_hi)],
    ], fmt="none", color="red", capsize=8, linewidth=2, label="95% CI")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{n}-seed" for n in seed_budgets])
    ax.set_xlabel("Evaluation budget (seeds per genome)")
    ax.set_ylabel("Hypervolume (pooled reference)")
    ax.set_title("Noise-Aware Optimization: HV vs Evaluation Budget")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    path = results_path(EXPERIMENT_NAME, "figs", "hv_by_budget.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  HV plot → experiments/results/{EXPERIMENT_NAME}/figs/hv_by_budget.pdf")


def _plot_runtime_comparison(
    seed_budgets: List[int],
    all_runs_by_budget: Dict[int, List[Dict]],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mean_runtimes = []
    for n in seed_budgets:
        rts = [r.get("elapsed_s", 0.0) for r in all_runs_by_budget.get(n, [])]
        mean_runtimes.append(float(np.mean(rts)) if rts else 0.0)

    fig, ax = plt.subplots(figsize=(5, 3))
    x = range(len(seed_budgets))
    ax.bar(x, mean_runtimes, color="darkorange", alpha=0.7)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{n}-seed" for n in seed_budgets])
    ax.set_xlabel("Evaluation budget")
    ax.set_ylabel("Mean runtime (s)")
    ax.set_title("Runtime vs Evaluation Budget")
    ax.grid(True, alpha=0.3, axis="y")

    path = results_path(EXPERIMENT_NAME, "figs", "runtime_by_budget.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Runtime plot → experiments/results/{EXPERIMENT_NAME}/figs/runtime_by_budget.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Noise-aware optimization study (Exp 5)")
    p.add_argument("--seeds", type=int, nargs="+", default=None,
                   help="Evaluation seed budgets (default: 1 5 10)")
    p.add_argument("--pop", type=int, default=DEFAULT_POP)
    p.add_argument("--ngen", type=int, default=DEFAULT_NGEN)
    p.add_argument("--n-runs", type=int, default=N_RUNS)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--smoke", action="store_true",
                   help="Quick smoke test: 2 runs, tiny pop/ngen, budgets=[1,5]")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    seed_budgets = args.seeds
    if args.smoke and seed_budgets is None:
        seed_budgets = [1, 5]

    run_experiment(
        seed_budgets=seed_budgets,
        pop_size=args.pop,
        n_generations=args.ngen,
        n_runs=args.n_runs,
        resume=args.resume,
        smoke=args.smoke,
    )


if __name__ == "__main__":
    main()
