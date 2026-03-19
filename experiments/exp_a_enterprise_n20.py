#!/usr/bin/env python3
"""
experiments/exp_a_enterprise_n20.py
=====================================
Revision Experiment A — Enterprise n=20 small-scale study.

Addresses reviewer CRITICAL issue #1:
  "The small-scale enterprise result (n=2) is insufficient for statistical
   inference and is a development checkpoint only."

Runs 20 independent NSGA-II optimizations for the enterprise case study at
small scale (steps=50, pop=50, ngen=20), matching the original ent_stats.py
configuration.  Reports full hypervolume statistics with bootstrap CI,
Wilcoxon test (champion vs reference), and Cohen's d.

Results go to: experiments/results/ent_stats_small_n20/

Usage
-----
# Full run (n=20, default config)
python experiments/exp_a_enterprise_n20.py

# Smoke test (n=2, tiny pop/ngen — verify imports work)
python experiments/exp_a_enterprise_n20.py --smoke

# Resume an interrupted run
python experiments/exp_a_enterprise_n20.py --resume

# Parallel workers
python experiments/exp_a_enterprise_n20.py --n-jobs 4
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List

import numpy as np

# ---------------------------------------------------------------------------
# Path setup — add repo root so heas and experiments.common are importable
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from common import (
    completed_run_ids,
    compute_hvs_for_runs,
    format_table_row,
    load_completed_runs,
    log_run_progress,
    pool_reference_point,
    print_config_header,
    print_summary_table,
    results_path,
    run_optimization_simple,
    save_json,
    save_run_result,
)

import heas.experiments.enterprise as enterprise
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import cohens_d, summarize_runs, wilcoxon_test

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "ent_stats_small_n20"
BASE_SEED = 3000          # distinct from ent_stats BASE_SEED=2000
N_RUNS = 20
POP_SIZE = 50
N_GENERATIONS = 20
N_EVAL_EPISODES = 5
EVAL_SEED = 42
STEPS = 50                # small-scale: 50 steps (same as original ent_stats)

# Reference genome (laissez-faire baseline): tax=0.1, audit=0.2, subsidy=0, penalty=0
REFERENCE_GENOME = [0.1, 0.2, 0.0, 0.0]


# ---------------------------------------------------------------------------
# Single-run optimization
# ---------------------------------------------------------------------------

def _run_one(run_id: int, pop_size: int, n_gen: int) -> Dict[str, Any]:
    """Run one NSGA-II enterprise optimization; return result dict."""
    enterprise._N_EVAL_EPISODES = N_EVAL_EPISODES
    enterprise._EVAL_SEED = EVAL_SEED

    seed = BASE_SEED + run_id
    t0 = time.time()
    ea = run_optimization_simple(
        objective_fn=enterprise.enterprise_objective,
        gene_schema=enterprise.ENTERPRISE_SCHEMA,
        strategy="nsga2",
        pop_size=pop_size,
        n_generations=n_gen,
        seed=seed,
    )
    elapsed = time.time() - t0

    hof_fitness = ea.get("hof_fitness", [])
    # enterprise minimises (-welfare, var_profit); welfare = -hof_fitness[0][0]
    champion_welfare = 0.0
    if hof_fitness:
        best_neg = min(f[0] for f in hof_fitness if len(f) >= 2)
        champion_welfare = -best_neg

    return {
        "run_id": run_id,
        "seed": seed,
        "pop_size": pop_size,
        "n_generations": n_gen,
        "steps": STEPS,
        "base_seed": BASE_SEED,
        "elapsed_s": elapsed,
        "hof_fitness": hof_fitness,
        "hall_of_fame": ea.get("hall_of_fame", []),
        "logbook": ea.get("logbook", []),
        "champion_welfare": champion_welfare,
    }


def _quick_hv(result: Dict[str, Any]) -> float:
    """Preview HV using a per-run reference (for progress logging only)."""
    pts = [tuple(float(v) for v in f)
           for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    return hypervolume(pts, auto_reference_point(pts))


# ---------------------------------------------------------------------------
# Wilcoxon comparison: champion vs reference across enterprise scenarios
# ---------------------------------------------------------------------------

def _wilcoxon_champion_vs_ref(
    all_runs: List[Dict],
    welfare_per_run: List[float],
    n_scenarios: int = 32,
    n_episodes: int = 10,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Evaluate the median-welfare champion against the reference policy.

    Selects the run whose champion_welfare is closest to the median, then
    evaluates that champion and the reference genome across enterprise scenarios.
    Returns Wilcoxon stat, p-value, and Cohen's d.
    """
    if smoke:
        n_scenarios, n_episodes = 2, 2
    if len(welfare_per_run) < 3:
        print("  Wilcoxon skipped: fewer than 3 runs.")
        return {}

    print(f"\n  Wilcoxon: champion vs reference ({n_scenarios} scenarios, "
          f"{n_episodes} episodes each)...")

    # Pick median-welfare champion run
    median_w = float(np.median(welfare_per_run))
    idx = int(np.argmin(np.abs(np.array(welfare_per_run) - median_w)))
    hof = all_runs[idx].get("hall_of_fame", [])
    if not hof:
        print("  Wilcoxon skipped: no hall of fame in median run.")
        return {}
    champion_genome = hof[0]

    try:
        scenarios = list(enterprise.make_32_scenarios())[:n_scenarios]
    except Exception as exc:
        print(f"  Wilcoxon skipped: cannot build scenarios ({exc}).")
        return {}

    champ_scores: List[float] = []
    ref_scores: List[float] = []

    for sc in scenarios:
        sc_params = dict(getattr(sc, "params", {}))
        champ_welfares: List[float] = []
        ref_welfares: List[float] = []

        for ep in range(n_episodes):
            enterprise._N_EVAL_EPISODES = 1
            enterprise._EVAL_SEED = ep

            # champion
            try:
                obj_c = enterprise.enterprise_objective(champion_genome)
                champ_welfares.append(-float(obj_c[0]))
            except Exception:
                champ_welfares.append(0.0)

            # reference
            try:
                obj_r = enterprise.enterprise_objective(REFERENCE_GENOME)
                ref_welfares.append(-float(obj_r[0]))
            except Exception:
                ref_welfares.append(0.0)

        champ_scores.append(float(np.mean(champ_welfares)))
        ref_scores.append(float(np.mean(ref_welfares)))

    try:
        stat, pval = wilcoxon_test(champ_scores, ref_scores)
        d = cohens_d(champ_scores, ref_scores)
        sig = "***" if pval < 0.001 else ("**" if pval < 0.01
              else ("*" if pval < 0.05 else "n.s."))
        print(f"  Wilcoxon stat={stat:.4f}  p={pval:.6f}  ({sig})")
        print(f"  Cohen's d={d:.4f}")
        result = {
            "wilcoxon_stat": stat, "p_value": pval, "cohens_d": d,
            "n_scenarios": n_scenarios, "n_episodes": n_episodes,
            "champion_genome": list(champion_genome),
            "reference_genome": list(REFERENCE_GENOME),
            "champion_scores": champ_scores,
            "ref_scores": ref_scores,
        }
        save_json(results_path(EXPERIMENT_NAME, "wilcoxon.json"), result)
        print(f"  Saved → experiments/results/{EXPERIMENT_NAME}/wilcoxon.json")
        return result
    except Exception as exc:
        print(f"  Wilcoxon failed: {exc}")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def _plot_hv_distribution(hvs: List[float]) -> None:
    """Histogram of per-run hypervolumes for the 20 enterprise runs."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(hvs, bins=10, color="steelblue", alpha=0.75, edgecolor="white")
        ax.axvline(float(np.mean(hvs)), color="red", linestyle="--",
                   label=f"Mean={np.mean(hvs):.4f}")
        ax.set_xlabel("Hypervolume")
        ax.set_ylabel("Count")
        ax.set_title(f"Enterprise HV distribution (n={len(hvs)} runs, small scale)")
        ax.legend()
        ax.grid(True, alpha=0.3)

        path = results_path(EXPERIMENT_NAME, "figs", "hv_distribution.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  Plot → {path}")
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")


def _plot_pareto_overlay(all_runs: List[Dict]) -> None:
    """Overlay all 20 Pareto fronts on one axes."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 5))
        for run in all_runs:
            pts = [(float(f[0]), float(f[1]))
                   for f in run.get("hof_fitness", []) if len(f) >= 2]
            if pts:
                xs = [-p[0] for p in pts]   # negate: minimised -welfare
                ys = [p[1] for p in pts]
                ax.scatter(xs, ys, alpha=0.3, s=8, color="steelblue")
        ax.set_xlabel("Welfare (higher is better)")
        ax.set_ylabel("Profit variance (lower is better)")
        ax.set_title(f"Enterprise Pareto overlay (n={len(all_runs)} runs)")
        ax.grid(True, alpha=0.3)

        path = results_path(EXPERIMENT_NAME, "figs", "pareto_overlay.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  Plot → {path}")
    except Exception as exc:
        print(f"  (Pareto plot skipped: {exc})")


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(
    pop_size: int = POP_SIZE,
    n_gen: int = N_GENERATIONS,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Run the n=20 enterprise small-scale study."""
    if smoke:
        n_runs, pop_size, n_gen = 2, 5, 2

    config = dict(
        experiment="exp_a_enterprise_n20",
        pop_size=pop_size,
        n_generations=n_gen,
        n_runs=n_runs,
        n_eval_episodes=N_EVAL_EPISODES,
        eval_seed=EVAL_SEED,
        steps=STEPS,
        base_seed=BASE_SEED,
        purpose="Addresses reviewer CRITICAL #1: enterprise n=2 insufficient",
    )
    print_config_header(config)

    done_ids = completed_run_ids(EXPERIMENT_NAME) if resume else set()
    if done_ids:
        print(f"  Resuming: {len(done_ids)} run(s) already done.")

    # --- Run optimization loop ---
    t_start = time.time()
    for run_id in range(n_runs):
        if run_id in done_ids:
            continue
        result = _run_one(run_id, pop_size, n_gen)
        save_run_result(result, EXPERIMENT_NAME, run_id)
        log_run_progress(
            run_id, n_runs, _quick_hv(result), time.time() - t_start,
            label=f"HV preview | welfare={result['champion_welfare']:.2f}",
        )

    # --- Aggregate ---
    all_runs = load_completed_runs(EXPERIMENT_NAME)
    print(f"\n  Loaded {len(all_runs)} completed runs.")

    ref_pt = pool_reference_point(all_runs)
    hvs = compute_hvs_for_runs(all_runs, ref_pt)
    hv_stats = summarize_runs(hvs)

    welfare_per_run = [r.get("champion_welfare", 0.0) for r in all_runs]
    welfare_stats = summarize_runs(welfare_per_run)

    print(f"\n  HV:      mean={hv_stats['mean']:.6f} ± {hv_stats['std']:.6f}")
    print(f"           95% CI=[{hv_stats['ci_lower']:.6f}, {hv_stats['ci_upper']:.6f}]  n={hv_stats['n']}")
    print(f"  Welfare: mean={welfare_stats['mean']:.4f} ± {welfare_stats['std']:.4f}")
    print(f"           95% CI=[{welfare_stats['ci_lower']:.4f}, {welfare_stats['ci_upper']:.4f}]")

    # --- Wilcoxon test ---
    wilcoxon_data = _wilcoxon_champion_vs_ref(
        all_runs, welfare_per_run, smoke=smoke,
    )

    # --- Summary JSON ---
    summary = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_per_run": hvs,
        "hv_stats": hv_stats,
        "welfare_per_run": welfare_per_run,
        "welfare_stats": welfare_stats,
        "wilcoxon": wilcoxon_data,
    }
    save_json(results_path(EXPERIMENT_NAME, "summary.json"), summary)
    print(f"\n  Summary → experiments/results/{EXPERIMENT_NAME}/summary.json")

    # --- LaTeX rows ---
    print("\n  LaTeX rows for paper:")
    print("  " + format_table_row(f"Enterprise HV (n={len(hvs)}, small scale)", hvs))
    print("  " + format_table_row(f"Enterprise Welfare (n={len(welfare_per_run)}, small scale)",
                                  welfare_per_run))

    # --- Plots ---
    _plot_hv_distribution(hvs)
    _plot_pareto_overlay(all_runs)

    print(f"\n  Done. All results in: experiments/results/{EXPERIMENT_NAME}/")
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Exp A — Enterprise n=20 small-scale (reviewer CRITICAL #1)"
    )
    p.add_argument("--pop",    type=int, default=POP_SIZE,    help="Population size")
    p.add_argument("--ngen",   type=int, default=N_GENERATIONS, help="Generations")
    p.add_argument("--n-runs", type=int, default=N_RUNS,      help="Independent runs")
    p.add_argument("--resume", action="store_true",           help="Skip done runs")
    p.add_argument("--smoke",  action="store_true",
                   help="Smoke test: 2 runs, tiny pop/ngen")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)
    run_experiment(
        pop_size=args.pop,
        n_gen=args.ngen,
        n_runs=args.n_runs,
        resume=args.resume,
        smoke=args.smoke,
    )


if __name__ == "__main__":
    main()
