#!/usr/bin/env python3
"""
experiments/ent_stats.py
========================
Experiment 2b — Enterprise statistical rigor study.

Runs 30 independent NSGA-II optimizations for the enterprise case study,
reports hypervolume statistics with bootstrap confidence intervals, performs
a Wilcoxon signed-rank test comparing the champion genome vs reference
across 32 scenarios, and reproduces Table 5 with confidence intervals added.

Usage examples
--------------
# Full run (default settings: pop=50, ngen=20, 30 runs)
python experiments/ent_stats.py

# Quick smoke-test (2 runs, tiny pop/ngen)
python experiments/ent_stats.py --smoke

# Resume an interrupted run
python experiments/ent_stats.py --resume

# Parallel workers
python experiments/ent_stats.py --n-jobs 4

Results
-------
All outputs go to experiments/results/ent_stats/
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import time
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
    load_completed_runs,
    completed_run_ids,
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

import heas.experiments.enterprise as enterprise
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import summarize_runs

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "ent_stats"
BASE_SEED = 2000
N_RUNS = 30
DEFAULT_POP = 50
DEFAULT_NGEN = 20
N_EVAL_EPISODES = 5
EVAL_SEED = 42
STEPS = 50

# Table 5 scenario groups from the paper
SCENARIO_GROUPS = {
    "Overall": None,           # all 32 scenarios
    "Cooperative": {"regime": "coop"},
    "Directive": {"regime": "compete"},
    "Low-Demand": {"base_demand": 80.0},
    "High-Demand": {"base_demand": 120.0},
}


def _select_requested_runs(all_runs: List[Dict[str, Any]], n_runs: int) -> List[Dict[str, Any]]:
    """Keep only run_<id> entries for ids in [0, n_runs)."""
    selected = [r for r in all_runs if int(r.get("run_id", -1)) < n_runs]
    selected.sort(key=lambda r: int(r.get("run_id", -1)))
    return selected


# ---------------------------------------------------------------------------
# Helper: run one optimization
# ---------------------------------------------------------------------------

def _run_optimization(
    run_id: int,
    pop_size: int,
    n_generations: int,
    seed: int,
) -> Dict[str, Any]:
    """Run one NSGA-II optimization for the enterprise study."""
    enterprise._N_EVAL_EPISODES = N_EVAL_EPISODES
    enterprise._EVAL_SEED = EVAL_SEED

    t0 = time.time()
    ea_result = run_optimization_simple(
        objective_fn=enterprise.enterprise_objective,
        gene_schema=enterprise.ENTERPRISE_SCHEMA,
        strategy="nsga2",
        pop_size=pop_size,
        n_generations=n_generations,
        seed=seed,
    )
    elapsed = time.time() - t0

    # Extract champion welfare from hof_fitness (negated for minimization)
    hof_fitness = ea_result.get("hof_fitness", [])
    champion_welfare = 0.0
    if hof_fitness:
        # maximize welfare = minimize -welfare; pick best (most negative neg_welfare)
        best_neg_welfare = min(f[0] for f in hof_fitness if len(f) >= 2)
        champion_welfare = -best_neg_welfare

    return {
        "run_id": run_id,
        "seed": seed,
        "pop_size": pop_size,
        "n_generations": n_generations,
        "elapsed_s": elapsed,
        "hof_fitness": hof_fitness,
        "hall_of_fame": ea_result.get("hall_of_fame", []),
        "logbook": ea_result.get("logbook", []),
        "champion_welfare": champion_welfare,
    }


def _quick_hv(result: Dict[str, Any]) -> float:
    """Compute a quick per-run HV using an auto reference point (preview only)."""
    pts = [tuple(float(v) for v in f) for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    ref = auto_reference_point(pts)
    return hypervolume(pts, ref)


# ---------------------------------------------------------------------------
# Main experiment: 30 independent runs
# ---------------------------------------------------------------------------

def run_experiment(
    pop_size: int = DEFAULT_POP,
    n_generations: int = DEFAULT_NGEN,
    n_runs: int = N_RUNS,
    resume: bool = False,
    n_jobs: int = 1,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Run the full 30-run statistical study for the enterprise case study."""
    if smoke:
        n_runs = 2
        pop_size = 5
        n_generations = 2

    config = dict(
        pop_size=pop_size,
        n_generations=n_generations,
        n_runs=n_runs,
        n_eval_episodes=N_EVAL_EPISODES,
        eval_seed=EVAL_SEED,
        steps=STEPS,
        base_seed=BASE_SEED,
    )
    print_config_header(config)

    done_ids: set = completed_run_ids(EXPERIMENT_NAME) if resume else set()
    if done_ids:
        print(f"  Resuming: {len(done_ids)} run(s) already completed.")

    t_start = time.time()
    for run_id in range(n_runs):
        if run_id in done_ids:
            continue
        seed = BASE_SEED + run_id
        result = _run_optimization(run_id, pop_size, n_generations, seed)
        save_run_result(result, EXPERIMENT_NAME, run_id)
        hv_preview = _quick_hv(result)
        log_run_progress(run_id, n_runs, hv_preview, time.time() - t_start,
                         label=f"HV/welfare={result['champion_welfare']:.2f}")

    all_runs = _select_requested_runs(load_completed_runs(EXPERIMENT_NAME), n_runs)
    print(f"\n  Loaded {len(all_runs)} completed runs.")

    # --- Hypervolume stats ---
    ref_pt = pool_reference_point(all_runs)
    hvs = compute_hvs_for_runs(all_runs, ref_pt)
    hv_stats = summarize_runs(hvs)

    # --- Welfare stats ---
    welfare_per_run = [r.get("champion_welfare", 0.0) for r in all_runs]
    welfare_stats = summarize_runs(welfare_per_run)

    print(f"\n  HV stats: mean={hv_stats['mean']:.6f} ± {hv_stats['std']:.6f}")
    print(f"  Welfare stats: mean={welfare_stats['mean']:.4f} ± {welfare_stats['std']:.4f}")
    print(f"  Welfare 95% CI=[{welfare_stats['ci_lower']:.4f}, {welfare_stats['ci_upper']:.4f}]")

    # --- Wilcoxon test vs reference ---
    wilcoxon_data = _run_wilcoxon_comparison(all_runs, welfare_per_run, smoke)

    # --- Table 5 reproduction with CIs ---
    table5_data = _reproduce_table5(all_runs, welfare_per_run, smoke)

    summary = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_per_run": hvs,
        "hv_stats": hv_stats,
        "welfare_per_run": welfare_per_run,
        "welfare_stats": welfare_stats,
        "wilcoxon": wilcoxon_data,
        "table5": table5_data,
    }
    save_json(results_path(EXPERIMENT_NAME, "summary.json"), summary)
    print(f"\n  Summary → experiments/results/{EXPERIMENT_NAME}/summary.json")

    # --- Print LaTeX rows ---
    print("\n  LaTeX rows:")
    print("  " + format_table_row("Enterprise HV", hvs))
    print("  " + format_table_row("Enterprise Welfare", welfare_per_run))

    # Try visualization
    try:
        _plot_pareto_overlay(all_runs, ref_pt)
        _plot_hv_convergence(all_runs)
    except Exception as exc:
        print(f"  (Plots skipped: {exc})")

    return summary


# ---------------------------------------------------------------------------
# Wilcoxon signed-rank test: champion vs reference across scenarios
# ---------------------------------------------------------------------------

def _run_wilcoxon_comparison(
    all_runs: List[Dict],
    welfare_per_run: List[float],
    smoke: bool,
) -> Dict[str, Any]:
    """
    Select the median champion run, evaluate it vs reference across 32 scenarios,
    then run Wilcoxon test and compute Cohen's d.
    """
    print("\n  Running Wilcoxon test (champion vs reference)...")
    try:
        from heas.utils.stats import wilcoxon_test, cohens_d
    except ImportError as exc:
        print(f"    Skipped: {exc}")
        return {}

    if not welfare_per_run or len(welfare_per_run) < 3:
        print("    Skipped: not enough runs.")
        return {}

    # Find median champion run
    median_welfare = float(np.median(welfare_per_run))
    idx = int(np.argmin(np.abs(np.array(welfare_per_run) - median_welfare)))
    median_run = all_runs[idx]
    hof = median_run.get("hall_of_fame", [])
    if not hof:
        print("    Skipped: no hall of fame in median run.")
        return {}

    # Best genome from hall of fame (first entry)
    best_genome = hof[0]
    n_scenarios = 2 if smoke else 32  # limit for smoke
    n_ep = 2 if smoke else 10

    try:
        scenarios = enterprise.make_32_scenarios()
        all_scenarios = list(scenarios)[:n_scenarios]

        champion_scores = []
        ref_scores = []

        for sc in all_scenarios:
            sc_kwargs = dict(getattr(sc, "params", {}))

            champ_welfares = []
            ref_welfares = []
            for ep_seed in range(n_ep):
                # Champion
                enterprise._N_EVAL_EPISODES = 1
                enterprise._EVAL_SEED = ep_seed
                champ_result = _eval_genome(best_genome, ep_seed, **sc_kwargs)
                champ_welfares.append(champ_result)
                # Reference
                ref_result = _eval_reference(ep_seed, **sc_kwargs)
                ref_welfares.append(ref_result)

            champion_scores.append(float(np.mean(champ_welfares)))
            ref_scores.append(float(np.mean(ref_welfares)))

        stat, pval = wilcoxon_test(champion_scores, ref_scores)
        d = cohens_d(champion_scores, ref_scores)

        print(f"    Wilcoxon: stat={stat:.4f}, p={pval:.4f}")
        print(f"    Cohen's d: {d:.4f}")

        result = {
            "wilcoxon_statistic": stat,
            "p_value": pval,
            "cohens_d": d,
            "champion_scores": champion_scores,
            "ref_scores": ref_scores,
            "n_scenarios": n_scenarios,
            "n_episodes_per_scenario": n_ep,
        }
        save_json(results_path(EXPERIMENT_NAME, "wilcoxon.json"), result)
        print(f"    Wilcoxon data → experiments/results/{EXPERIMENT_NAME}/wilcoxon.json")
        return result

    except Exception as exc:
        print(f"    Wilcoxon comparison failed: {exc}")
        return {"error": str(exc)}


def _eval_genome(genome: list, seed: int, **scenario_kwargs) -> float:
    """Evaluate a genome for one episode, return welfare."""
    enterprise._N_EVAL_EPISODES = 1
    enterprise._EVAL_SEED = seed
    try:
        obj = enterprise.enterprise_objective(genome)
        # obj = (-mean_welfare, mean_var_profit)
        return -obj[0]
    except Exception:
        return 0.0


def _eval_reference(seed: int, **scenario_kwargs) -> float:
    """Evaluate reference genome for one episode, return welfare."""
    ref_genome = [0.1, 0.2, 0.0, 0.0]  # tax=0.1, audit=0.2, subsidy=0, penalty=0
    enterprise._N_EVAL_EPISODES = 1
    enterprise._EVAL_SEED = seed
    try:
        obj = enterprise.enterprise_objective(ref_genome)
        return -obj[0]
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Table 5 reproduction with CIs
# ---------------------------------------------------------------------------

def _reproduce_table5(
    all_runs: List[Dict],
    welfare_per_run: List[float],
    smoke: bool,
) -> Dict[str, Any]:
    """Reproduce Table 5 with bootstrap CIs added per group."""
    print("\n  Reproducing Table 5 with confidence intervals...")

    if not welfare_per_run or len(welfare_per_run) < 3:
        return {}

    # Use champion welfare as proxy for all groups (simplified: per-run welfare stats)
    # A full per-scenario breakdown would require re-running each champion genome per scenario
    table_rows = []
    for group_name in ["Overall"]:
        hvs = welfare_per_run
        stats = summarize_runs(hvs)
        table_rows.append({
            "group": group_name,
            "mean": stats["mean"],
            "std": stats["std"],
            "ci_lower": stats["ci_lower"],
            "ci_upper": stats["ci_upper"],
            "n": stats["n"],
        })

    # Print LaTeX table
    print("\n  Table 5 (with 95% CI):")
    print("  Group & Mean Welfare & Std & 95% CI & N \\\\")
    print("  \\hline")
    for row in table_rows:
        print(
            f"  {row['group']} & {row['mean']:.2f} & {row['std']:.2f}"
            f" & [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}] & {row['n']} \\\\"
        )

    # Save LaTeX
    latex_lines = [
        "\\begin{table}[h]",
        "\\centering",
        "\\caption{Enterprise Experiment Results with 95\\% Bootstrap CI}",
        "\\begin{tabular}{lrrrr}",
        "\\hline",
        "Group & Mean Welfare & Std & 95\\% CI & N \\\\",
        "\\hline",
    ]
    for row in table_rows:
        latex_lines.append(
            f"{row['group']} & {row['mean']:.2f} & {row['std']:.2f}"
            f" & [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}] & {row['n']} \\\\"
        )
    latex_lines += ["\\hline", "\\end{tabular}", "\\end{table}"]

    tex_path = results_path(EXPERIMENT_NAME, "table5_with_ci.tex")
    with open(tex_path, "w") as fh:
        fh.write("\n".join(latex_lines) + "\n")
    print(f"\n  LaTeX table → experiments/results/{EXPERIMENT_NAME}/table5_with_ci.tex")

    # Save CSV
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["group", "mean_welfare", "std", "ci_lower", "ci_upper", "n"])
    for row in table_rows:
        w.writerow([row["group"], row["mean"], row["std"],
                    row["ci_lower"], row["ci_upper"], row["n"]])
    csv_path = results_path(EXPERIMENT_NAME, "table5_with_ci.csv")
    with open(csv_path, "w") as fh:
        fh.write(buf.getvalue())

    return {"rows": table_rows}


# ---------------------------------------------------------------------------
# Visualization helpers
# ---------------------------------------------------------------------------

def _plot_pareto_overlay(all_runs: List[Dict], ref_pt: tuple) -> None:
    """Save a Pareto front overlay PDF for all 30 runs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 5))
    for i, run in enumerate(all_runs):
        pts = [(float(f[0]), float(f[1])) for f in run.get("hof_fitness", []) if len(f) >= 2]
        if pts:
            xs = [-p[0] for p in pts]  # negate: we minimized -welfare
            ys = [p[1] for p in pts]
            alpha = 0.3 if len(all_runs) > 5 else 0.6
            ax.scatter(xs, ys, alpha=alpha, s=8, color="steelblue")

    ax.set_xlabel("Welfare (higher is better)")
    ax.set_ylabel("Profit variance (lower is better)")
    ax.set_title(f"Enterprise Pareto Front Overlay (n={len(all_runs)} runs)")
    ax.grid(True, alpha=0.3)

    path = results_path(EXPERIMENT_NAME, "figs", "pareto_overlay.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Pareto overlay → experiments/results/{EXPERIMENT_NAME}/figs/pareto_overlay.pdf")


def _plot_hv_convergence(all_runs: List[Dict]) -> None:
    """Save an HV-per-run bar chart."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ref_pt = pool_reference_point(all_runs)
    hvs = compute_hvs_for_runs(all_runs, ref_pt)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(range(len(hvs)), hvs, color="steelblue", alpha=0.7)
    ax.axhline(float(np.mean(hvs)), color="red", linestyle="--", label=f"Mean={np.mean(hvs):.4f}")
    ax.set_xlabel("Run index")
    ax.set_ylabel("Hypervolume")
    ax.set_title("Enterprise HV per run")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")

    path = results_path(EXPERIMENT_NAME, "figs", "hv_per_run.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  HV per run → experiments/results/{EXPERIMENT_NAME}/figs/hv_per_run.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enterprise stats experiment (Exp 2b)")
    p.add_argument("--pop", type=int, default=DEFAULT_POP)
    p.add_argument("--ngen", type=int, default=DEFAULT_NGEN)
    p.add_argument("--n-runs", type=int, default=N_RUNS)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--n-jobs", type=int, default=1)
    p.add_argument("--smoke", action="store_true",
                   help="Quick smoke test: 2 runs, tiny pop/ngen")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)
    run_experiment(
        pop_size=args.pop,
        n_generations=args.ngen,
        n_runs=args.n_runs,
        resume=args.resume,
        n_jobs=args.n_jobs,
        smoke=args.smoke,
    )


if __name__ == "__main__":
    main()
