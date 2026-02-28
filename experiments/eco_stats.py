#!/usr/bin/env python3
"""
experiments/eco_stats.py
========================
Experiment 2a + Experiment 4 — Ecological statistical rigor study.

Runs 30 independent NSGA-II optimizations for the ecological case study
and reports hypervolume statistics with bootstrap confidence intervals.
Also reconciles the ecological inconsistency (Exp 4) by labeling trait-
based and MLP-weight evolution results clearly as distinct setups.

Usage examples
--------------
# Full run, default settings (pop=50, ngen=25, mode=trait, 30 runs)
python experiments/eco_stats.py

# Quick smoke-test (2 runs, tiny pop/ngen)
python experiments/eco_stats.py --smoke

# Specify grid point
python experiments/eco_stats.py --pop 100 --ngen 50 --mode mlp

# Resume an interrupted run
python experiments/eco_stats.py --resume

# Parallel (4 workers for NSGA-II objective evaluation)
python experiments/eco_stats.py --n-jobs 4

# Reconcile trait vs MLP setups side-by-side (Exp 4 fix)
python experiments/eco_stats.py --reconcile

# Ablation: compare NSGA-II vs simple vs random (pop=50, ngen=25, trait)
python experiments/eco_stats.py --ablation

# Convergence sweep across ngen values
python experiments/eco_stats.py --convergence

Results
-------
All outputs go to experiments/results/eco_stats/
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Path setup — add repo root so we can import heas and experiments.common
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from common import (  # experiments/common.py
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
)

import heas.experiments.eco as eco
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import summarize_runs

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "eco_stats"
BASE_SEED = 1000
N_RUNS = 30
DEFAULT_POP = 50
DEFAULT_NGEN = 25
DEFAULT_MODE = "trait"
N_EVAL_EPISODES = 5
EVAL_SEED = 42
STEPS = 140  # simulation steps per episode

CONVERGENCE_NGENS = [5, 10, 15, 20, 25, 50]
ABLATION_STRATEGIES = ["nsga2", "simple", "random"]


# ---------------------------------------------------------------------------
# Helper: run one optimization and return the full result dict
# ---------------------------------------------------------------------------

def _run_optimization(
    run_id: int,
    pop_size: int,
    n_generations: int,
    mode: str,
    seed: int,
    n_jobs: int = 1,
) -> Dict[str, Any]:
    """Run one NSGA-II optimization for the ecological study."""
    eco._N_EVAL_EPISODES = N_EVAL_EPISODES
    eco._STEPS = STEPS
    # Use a run-specific EVAL_SEED so each of the 30 seeds sees different episodes
    # → produces genuine variance in the bootstrap CI (not std=0).
    eco._EVAL_SEED = EVAL_SEED + run_id * 17

    if mode == "trait":
        objective_fn = eco.trait_objective
        schema = eco.TRAIT_SCHEMA
    elif mode == "mlp":
        objective_fn = eco.mlp_objective
        schema = eco.get_mlp_schema()
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

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
        "pop_size": pop_size,
        "n_generations": n_generations,
        "mode": mode,
        "elapsed_s": elapsed,
        "hof_fitness": ea_result.get("hof_fitness", []),
        "hall_of_fame": ea_result.get("hall_of_fame", []),
        "logbook": ea_result.get("logbook", []),
    }


# ---------------------------------------------------------------------------
# Main experiment: 30 independent runs for a given config
# ---------------------------------------------------------------------------

def run_experiment(
    pop_size: int = DEFAULT_POP,
    n_generations: int = DEFAULT_NGEN,
    mode: str = DEFAULT_MODE,
    n_runs: int = N_RUNS,
    resume: bool = False,
    n_jobs: int = 1,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Run the full 30-run statistical study for one (pop, ngen, mode) config."""
    if smoke:
        n_runs = 2
        pop_size = 5
        n_generations = 2

    config_key = f"pop{pop_size}_ngen{n_generations}_{mode}"
    sub_experiment = f"{EXPERIMENT_NAME}/{config_key}"

    config = dict(
        pop_size=pop_size,
        n_generations=n_generations,
        mode=mode,
        n_runs=n_runs,
        n_eval_episodes=N_EVAL_EPISODES,
        eval_seed=EVAL_SEED,
        steps=STEPS,
        base_seed=BASE_SEED,
    )
    print_config_header(config)

    # Determine which runs to skip (checkpoint resume)
    done_ids: set = completed_run_ids(sub_experiment) if resume else set()
    if done_ids:
        print(f"  Resuming: {len(done_ids)} run(s) already completed, skipping.")

    # Execute runs
    t_start = time.time()
    for run_id in range(n_runs):
        if run_id in done_ids:
            continue
        seed = BASE_SEED + run_id
        result = _run_optimization(run_id, pop_size, n_generations, mode, seed, n_jobs)
        save_run_result(result, sub_experiment, run_id)
        hv_preview = _quick_hv(result)
        log_run_progress(run_id, n_runs, hv_preview, time.time() - t_start)

    # Load all completed runs
    all_runs = load_completed_runs(sub_experiment)
    print(f"\n  Loaded {len(all_runs)} completed runs.")

    # Compute pooled reference point then per-run HVs
    ref_pt = pool_reference_point(all_runs)
    hvs = compute_hvs_for_runs(all_runs, ref_pt)
    stats = summarize_runs(hvs)

    print(f"\n  Results for config: {config_key}")
    print(f"  HV mean={stats['mean']:.6f} ± std={stats['std']:.6f}")
    print(f"  95% CI=[{stats['ci_lower']:.6f}, {stats['ci_upper']:.6f}]  n={stats['n']}")

    # Save summary
    summary = {
        "config": config,
        "config_key": config_key,
        "reference_point": list(ref_pt),
        "hv_per_run": hvs,
        "stats": stats,
    }
    save_json(results_path(sub_experiment, "summary.json"), summary)
    print(f"  Summary saved → experiments/results/{sub_experiment}/summary.json")

    # Print LaTeX-ready row
    mode_label = {
        "trait": "Trait-based (tournament narrative)",
        "mlp": "MLP weight evolution (Table 3)",
    }.get(mode, mode)
    print(f"\n  LaTeX row:")
    from common import format_table_row
    print("  " + format_table_row(f"Eco {mode_label} p={pop_size} g={n_generations}", hvs))

    return summary


def _quick_hv(result: Dict[str, Any]) -> float:
    """Compute a quick per-run HV using an auto reference point (preview only)."""
    pts = [tuple(float(v) for v in f) for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    ref = auto_reference_point(pts)
    return hypervolume(pts, ref)


# ---------------------------------------------------------------------------
# Ablation study: NSGA-II vs simple vs random
# ---------------------------------------------------------------------------

def run_ablation(
    pop_size: int = 50,
    n_generations: int = 25,
    mode: str = "trait",
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> None:
    """Compare NSGA-II, simple (mu+lambda), and random search."""
    if smoke:
        n_runs = 2
        pop_size = 5
        n_generations = 2

    eco._N_EVAL_EPISODES = N_EVAL_EPISODES
    eco._EVAL_SEED = EVAL_SEED

    if mode == "trait":
        objective_fn = eco.trait_objective
        schema = eco.TRAIT_SCHEMA
    else:
        objective_fn = eco.mlp_objective
        schema = eco.get_mlp_schema()

    all_hvs: Dict[str, List[float]] = {}
    all_runs_by_strategy: Dict[str, List[Dict]] = {}

    for strategy in ABLATION_STRATEGIES:
        sub_experiment = f"{EXPERIMENT_NAME}/ablation_{strategy}_{mode}"
        done_ids = completed_run_ids(sub_experiment) if resume else set()

        print(f"\n--- Ablation: strategy={strategy}, mode={mode} ---")
        t_start = time.time()
        for run_id in range(n_runs):
            if run_id in done_ids:
                continue
            seed = BASE_SEED + run_id
            eco._N_EVAL_EPISODES = N_EVAL_EPISODES
            eco._EVAL_SEED = EVAL_SEED
            t0 = time.time()
            ea_result = run_optimization_simple(
                objective_fn=objective_fn,
                gene_schema=schema,
                strategy=strategy,
                pop_size=pop_size,
                n_generations=n_generations,
                seed=seed,
            )
            elapsed = time.time() - t0
            result = {
                "run_id": run_id,
                "seed": seed,
                "strategy": strategy,
                "pop_size": pop_size,
                "n_generations": n_generations,
                "mode": mode,
                "elapsed_s": elapsed,
                "hof_fitness": ea_result.get("hof_fitness", []),
            }
            save_run_result(result, sub_experiment, run_id)
            hv_preview = _quick_hv(result)
            log_run_progress(run_id, n_runs, hv_preview, time.time() - t_start)

        all_runs = load_completed_runs(sub_experiment)
        all_runs_by_strategy[strategy] = all_runs

    # Pool reference across ALL strategies for fair comparison
    combined = []
    for runs in all_runs_by_strategy.values():
        combined.extend(runs)
    ref_pt = pool_reference_point(combined)

    rows = []
    for strategy in ABLATION_STRATEGIES:
        runs = all_runs_by_strategy[strategy]
        hvs = compute_hvs_for_runs(runs, ref_pt)
        all_hvs[strategy] = hvs
        rows.append((f"Eco-{mode} {strategy}", hvs))

    print("\n=== Ablation Summary ===")
    print_summary_table(rows)

    ablation_summary = {
        "mode": mode,
        "pop_size": pop_size,
        "n_generations": n_generations,
        "reference_point": list(ref_pt),
        "results": {s: {"hv_per_run": hvs, "stats": summarize_runs(hvs)}
                    for s, hvs in all_hvs.items()},
    }
    save_json(results_path(EXPERIMENT_NAME, "ablation_summary.json"), ablation_summary)
    print(f"\nAblation summary → experiments/results/{EXPERIMENT_NAME}/ablation_summary.json")


# ---------------------------------------------------------------------------
# Convergence study: HV vs ngen across multiple seeds
# ---------------------------------------------------------------------------

def run_convergence(
    pop_size: int = DEFAULT_POP,
    mode: str = DEFAULT_MODE,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> None:
    """Run convergence sweep: HV mean ± CI vs ngen for [5,10,15,20,25,50]."""
    ngen_list = [2, 4] if smoke else CONVERGENCE_NGENS
    if smoke:
        n_runs = 2
        pop_size = 5

    eco._N_EVAL_EPISODES = N_EVAL_EPISODES
    eco._EVAL_SEED = EVAL_SEED

    if mode == "trait":
        objective_fn = eco.trait_objective
        schema = eco.TRAIT_SCHEMA
    else:
        objective_fn = eco.mlp_objective
        schema = eco.get_mlp_schema()

    # Pool reference across everything for fair comparison
    all_runs_flat: List[Dict] = []

    runs_by_ngen: Dict[int, List[Dict]] = {}
    for ngen in ngen_list:
        sub_experiment = f"{EXPERIMENT_NAME}/conv_{mode}_ngen{ngen}"
        done_ids = completed_run_ids(sub_experiment) if resume else set()
        print(f"\n--- Convergence: ngen={ngen}, mode={mode} ---")
        t_start = time.time()
        for run_id in range(n_runs):
            if run_id in done_ids:
                continue
            seed = BASE_SEED + run_id
            eco._N_EVAL_EPISODES = N_EVAL_EPISODES
            eco._EVAL_SEED = EVAL_SEED
            t0 = time.time()
            ea_result = run_optimization_simple(
                objective_fn=objective_fn,
                gene_schema=schema,
                strategy="nsga2",
                pop_size=pop_size,
                n_generations=ngen,
                seed=seed,
            )
            elapsed = time.time() - t0
            result = {
                "run_id": run_id,
                "seed": seed,
                "ngen": ngen,
                "pop_size": pop_size,
                "mode": mode,
                "elapsed_s": elapsed,
                "hof_fitness": ea_result.get("hof_fitness", []),
            }
            save_run_result(result, sub_experiment, run_id)
            hv_preview = _quick_hv(result)
            log_run_progress(run_id, n_runs, hv_preview, time.time() - t_start)

        runs = load_completed_runs(sub_experiment)
        runs_by_ngen[ngen] = runs
        all_runs_flat.extend(runs)

    # Compute shared reference point
    ref_pt = pool_reference_point(all_runs_flat)

    convergence_data = {}
    for ngen in ngen_list:
        runs = runs_by_ngen[ngen]
        hvs = compute_hvs_for_runs(runs, ref_pt)
        stats = summarize_runs(hvs)
        convergence_data[ngen] = {"hv_per_run": hvs, "stats": stats}
        print(f"  ngen={ngen:3d}  HV={stats['mean']:.6f} ± {stats['std']:.6f}"
              f"  95% CI=[{stats['ci_lower']:.6f}, {stats['ci_upper']:.6f}]")

    conv_summary = {
        "mode": mode,
        "pop_size": pop_size,
        "reference_point": list(ref_pt),
        "convergence": convergence_data,
    }
    save_json(results_path(EXPERIMENT_NAME, f"convergence_{mode}.json"), conv_summary)
    print(f"\nConvergence data → experiments/results/{EXPERIMENT_NAME}/convergence_{mode}.json")

    # Try to produce a text-based plot as fallback
    _print_convergence_chart(convergence_data, mode)

    # Try matplotlib
    try:
        _plot_convergence(convergence_data, mode)
    except Exception as exc:
        print(f"  (Matplotlib plot skipped: {exc})")


def _print_convergence_chart(convergence_data: Dict, mode: str) -> None:
    """Print a simple ASCII convergence chart to stdout."""
    print(f"\n  Convergence chart ({mode}):")
    ngens = sorted(convergence_data)
    max_hv = max(convergence_data[n]["stats"]["mean"] for n in ngens) or 1.0
    for ngen in ngens:
        st = convergence_data[ngen]["stats"]
        bar_len = int(40 * st["mean"] / max_hv)
        bar = "#" * bar_len
        print(f"  ngen={ngen:3d} [{bar:<40}] {st['mean']:.4f} ± {st['std']:.4f}")


def _plot_convergence(convergence_data: Dict, mode: str) -> None:
    """Save a convergence plot as PDF."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ngens = sorted(convergence_data)
    means = [convergence_data[n]["stats"]["mean"] for n in ngens]
    ci_lo = [convergence_data[n]["stats"]["ci_lower"] for n in ngens]
    ci_hi = [convergence_data[n]["stats"]["ci_upper"] for n in ngens]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(ngens, means, "o-", label=mode)
    ax.fill_between(ngens, ci_lo, ci_hi, alpha=0.3)
    ax.set_xlabel("Generations")
    ax.set_ylabel("Hypervolume")
    ax.set_title(f"Convergence — {mode}")
    ax.legend()
    ax.grid(True, alpha=0.3)

    path = results_path(EXPERIMENT_NAME, "figs", f"convergence_{mode}.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved → experiments/results/{EXPERIMENT_NAME}/figs/convergence_{mode}.pdf")


# ---------------------------------------------------------------------------
# Reconciliation table (Exp 4 fix): trait vs MLP side-by-side
# ---------------------------------------------------------------------------

def run_reconcile(
    pop_size: int = DEFAULT_POP,
    n_generations: int = DEFAULT_NGEN,
    n_runs: int = N_RUNS,
    resume: bool = False,
    n_jobs: int = 1,
    smoke: bool = False,
) -> None:
    """
    Exp 4 — Reconcile ecological inconsistency.

    Runs trait-based and MLP-weight evolution side-by-side and prints an
    explicit comparison table that distinguishes the two experimental setups.
    """
    print("\n" + "=" * 70)
    print("Exp 4 — Reconciling ecological inconsistency")
    print("  'trait' mode  = trait-based policies (Section 4.1 tournament narrative)")
    print("  'mlp' mode    = MLP weight evolution (Table 3 in paper)")
    print("=" * 70)

    # Run both modes
    summary_trait = run_experiment(
        pop_size=pop_size, n_generations=n_generations, mode="trait",
        n_runs=n_runs, resume=resume, n_jobs=n_jobs, smoke=smoke,
    )
    summary_mlp = run_experiment(
        pop_size=pop_size, n_generations=n_generations, mode="mlp",
        n_runs=n_runs, resume=resume, n_jobs=n_jobs, smoke=smoke,
    )

    # Pool reference points across BOTH modes for the comparison table
    all_runs_t = load_completed_runs(f"{EXPERIMENT_NAME}/pop{pop_size}_ngen{n_generations}_trait")
    all_runs_m = load_completed_runs(f"{EXPERIMENT_NAME}/pop{pop_size}_ngen{n_generations}_mlp")
    combined_ref = pool_reference_point(all_runs_t + all_runs_m)
    hvs_t = compute_hvs_for_runs(all_runs_t, combined_ref)
    hvs_m = compute_hvs_for_runs(all_runs_m, combined_ref)

    print("\n=== Reconciliation Table (shared reference point) ===")
    rows = [
        ("Trait-based evolution (tournament narrative)", hvs_t),
        ("MLP weight evolution (Table 3)", hvs_m),
    ]
    print_summary_table(rows)

    try:
        from heas.utils.stats import wilcoxon_test, cohens_d
        if len(hvs_t) >= 10 and len(hvs_m) >= 10:
            stat, pval = wilcoxon_test(hvs_t, hvs_m)
            d = cohens_d(hvs_t, hvs_m)
            print(f"\n  Wilcoxon test (trait vs MLP): stat={stat:.4f}, p={pval:.4f}")
            print(f"  Cohen's d: {d:.4f}")
    except Exception as exc:
        print(f"  (Statistical comparison skipped: {exc})")

    recon_summary = {
        "combined_reference_point": list(combined_ref),
        "trait": {"hv_per_run": hvs_t, "stats": summarize_runs(hvs_t)},
        "mlp": {"hv_per_run": hvs_m, "stats": summarize_runs(hvs_m)},
    }
    save_json(results_path(EXPERIMENT_NAME, "reconciliation.json"), recon_summary)
    print(f"\nReconciliation data → experiments/results/{EXPERIMENT_NAME}/reconciliation.json")


# ---------------------------------------------------------------------------
# Full grid sweep
# ---------------------------------------------------------------------------

def run_grid(
    pop_sizes: Optional[List[int]] = None,
    ngens: Optional[List[int]] = None,
    modes: Optional[List[str]] = None,
    n_runs: int = N_RUNS,
    resume: bool = False,
    n_jobs: int = 1,
    smoke: bool = False,
) -> None:
    """Run all (pop, ngen, mode) combinations and print summary table."""
    pop_sizes = pop_sizes or [20, 50, 100]
    ngens = ngens or [10, 25, 50]
    modes = modes or ["trait"]

    rows = []
    for mode in modes:
        for pop in pop_sizes:
            for ngen in ngens:
                summary = run_experiment(
                    pop_size=pop, n_generations=ngen, mode=mode,
                    n_runs=n_runs, resume=resume, n_jobs=n_jobs, smoke=smoke,
                )
                label = f"Eco-{mode} p={pop} g={ngen}"
                hvs = summary["hv_per_run"]
                rows.append((label, hvs))

    print("\n\n=== FULL GRID SUMMARY TABLE ===")
    print_summary_table(rows)

    # Save CSV
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["config", "mean_hv", "std_hv", "ci_lower", "ci_upper", "n"])
    for label, hvs in rows:
        s = summarize_runs(hvs)
        w.writerow([label, s["mean"], s["std"], s["ci_lower"], s["ci_upper"], s["n"]])
    csv_path = results_path(EXPERIMENT_NAME, "summary_table.csv")
    with open(csv_path, "w") as fh:
        fh.write(buf.getvalue())
    print(f"\nCSV table → experiments/results/{EXPERIMENT_NAME}/summary_table.csv")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Eco stats experiment (Exp 2a + Exp 4)"
    )
    p.add_argument("--pop", type=int, default=DEFAULT_POP, help="Population size")
    p.add_argument("--ngen", type=int, default=DEFAULT_NGEN, help="Number of generations")
    p.add_argument("--mode", choices=["trait", "mlp"], default=DEFAULT_MODE,
                   help="Optimization mode: 'trait' (2 genes) or 'mlp' (weight vector)")
    p.add_argument("--n-runs", type=int, default=N_RUNS, help="Number of independent runs")
    p.add_argument("--resume", action="store_true", help="Skip already-completed runs")
    p.add_argument("--n-jobs", type=int, default=1,
                   help="Parallel workers for runner.run_many (-1=all CPUs)")
    p.add_argument("--smoke", action="store_true",
                   help="Quick smoke test: 2 runs, tiny pop/ngen")
    p.add_argument("--reconcile", action="store_true",
                   help="Run trait vs MLP side-by-side (Exp 4 fix)")
    p.add_argument("--ablation", action="store_true",
                   help="Ablation: NSGA-II vs simple vs random")
    p.add_argument("--convergence", action="store_true",
                   help="Convergence sweep across ngen values")
    p.add_argument("--grid", action="store_true",
                   help="Full grid: all (pop, ngen, mode) combinations")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    if args.reconcile:
        run_reconcile(
            pop_size=args.pop, n_generations=args.ngen,
            n_runs=args.n_runs, resume=args.resume,
            n_jobs=args.n_jobs, smoke=args.smoke,
        )
    elif args.ablation:
        run_ablation(
            pop_size=args.pop, n_generations=args.ngen, mode=args.mode,
            n_runs=args.n_runs, resume=args.resume, smoke=args.smoke,
        )
    elif args.convergence:
        run_convergence(
            pop_size=args.pop, mode=args.mode,
            n_runs=args.n_runs, resume=args.resume, smoke=args.smoke,
        )
    elif args.grid:
        run_grid(
            n_runs=args.n_runs, resume=args.resume,
            n_jobs=args.n_jobs, smoke=args.smoke,
        )
    else:
        run_experiment(
            pop_size=args.pop, n_generations=args.ngen, mode=args.mode,
            n_runs=args.n_runs, resume=args.resume, n_jobs=args.n_jobs,
            smoke=args.smoke,
        )


if __name__ == "__main__":
    main()
