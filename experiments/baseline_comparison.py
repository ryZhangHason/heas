#!/usr/bin/env python3
"""
experiments/baseline_comparison.py
====================================
Model-level and algorithm-level baseline comparison for HEAS.

Answers three questions the paper currently leaves open:

  Part 1 — Algorithm ablation
    Does NSGA-II actually outperform simpler optimizers on the same objective?
    Compare NSGA-II vs. simple (μ+λ) vs. random search across 10 independent
    runs each.  Reports HV mean ± CI, Wilcoxon(NSGA-II, random), Cohen's d.

  Part 2 — Scale sensitivity (steps × episodes)
    At what simulation scale does HEAS's evolved policy show the largest lead
    over a fixed baseline?  Grid: steps∈{140,300,500} × episodes∈{5,10,20}.
    For each cell: run 10 NSGA-II seeds, pool reference point, compute HV and
    mean-prey gap (champion − baseline).

  Part 3 — Champion vs. reference head-to-head
    Evaluate the best champion genome (from Part 2's largest-scale run) against
    a fixed reference policy across 16 held-out scenarios.  Reports per-scenario
    scores, aggregate Wilcoxon test, and Cohen's d.

Usage
-----
python experiments/baseline_comparison.py          # all 3 parts
python experiments/baseline_comparison.py --smoke  # quick test
python experiments/baseline_comparison.py --part 1
python experiments/baseline_comparison.py --part 2
python experiments/baseline_comparison.py --part 3

Results
-------
All outputs → experiments/results/baseline_comparison/
"""
from __future__ import annotations

import argparse
import csv
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
from heas.utils.stats import (
    bootstrap_ci, cohens_d, kendall_tau, summarize_runs, wilcoxon_test,
)

EXPERIMENT_NAME = "baseline_comparison"
BASE_SEED = 5000
N_RUNS = 10           # per algorithm cell (use 10 to keep runtime manageable)


# ---------------------------------------------------------------------------
# Random search (not in heas.api — implemented here for ablation fairness)
# ---------------------------------------------------------------------------

def _random_search(
    objective_fn,
    gene_schema,
    pop_size: int,
    n_generations: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Pure random search: sample pop_size * n_generations genomes uniformly,
    evaluate each, return the Pareto-optimal subset as 'hall of fame'.
    Equivalent budget to NSGA-II with same pop_size and n_generations.
    """
    import random as _random
    from heas.schemas.genes import Real, Int, Cat, Bool
    from heas.utils.pareto import auto_reference_point

    _random.seed(seed)
    np.random.seed(seed)

    total = pop_size * (n_generations + 1)

    def _sample() -> list:
        g = []
        for gene in gene_schema:
            if isinstance(gene, Real):
                g.append(_random.uniform(gene.low, gene.high))
            elif isinstance(gene, Int):
                g.append(_random.randint(gene.low, gene.high))
            elif isinstance(gene, Cat):
                g.append(_random.choice(gene.choices))
            elif isinstance(gene, Bool):
                g.append(bool(_random.getrandbits(1)))
        return g

    genomes = [_sample() for _ in range(total)]
    fitnesses = [objective_fn(g) for g in genomes]

    # Pareto filter (minimization)
    def _dominates(a, b):
        return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))

    pareto = []
    for i, fi in enumerate(fitnesses):
        dominated = any(_dominates(fitnesses[j], fi) for j in range(len(fitnesses)) if j != i)
        if not dominated:
            pareto.append(i)

    hof_genomes = [genomes[i] for i in pareto]
    hof_fitness = [list(fitnesses[i]) for i in pareto]

    return {
        "best": hof_genomes,
        "hall_of_fame": hof_genomes,
        "hof_fitness": hof_fitness,
        "logbook": [],
    }

# Reference genome: paper's baseline trait values
REFERENCE_GENOME = [0.55, 0.35]   # risk=0.55, dispersal=0.35

# 16 held-out scenarios (fragmentation × shock_prob × K × move_cost grid)
EVAL_SCENARIOS = [
    {"fragmentation": f, "shock_prob": s, "K": k, "move_cost": m}
    for f in [0.2, 0.5]
    for s in [0.05, 0.2]
    for k in [80.0, 150.0]
    for m in [0.1, 0.3]
]  # 2×2×2×2 = 16 scenarios


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _set_eco_config(steps: int, n_eval: int, seed: int) -> None:
    eco._STEPS = steps
    eco._N_EVAL_EPISODES = n_eval
    eco._EVAL_SEED = seed          # per-run seed → genuine stochasticity


def _quick_hv(result: Dict[str, Any]) -> float:
    pts = [tuple(float(v) for v in f) for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    return hypervolume(pts, auto_reference_point(pts))


def _eval_genome_scenario(
    genome: List[float],
    scenario: Dict[str, Any],
    steps: int,
    n_episodes: int,
    seed: int,
) -> Dict[str, float]:
    """Evaluate one genome in one scenario; return mean_biomass and cv."""
    from heas.agent.runner import run_many

    risk = float(genome[0])
    dispersal = float(genome[1])
    result = run_many(
        eco.trait_model_factory,
        steps=steps,
        episodes=n_episodes,
        seed=seed,
        risk=risk,
        dispersal=dispersal,
        fragmentation=scenario.get("fragmentation", 0.2),
        shock_prob=scenario.get("shock_prob", 0.1),
        K=scenario.get("K", 1000.0),
        move_cost=scenario.get("move_cost", 0.2),
    )
    biomass_vals = [ep["episode"].get("agg.mean_biomass", 0.0) for ep in result["episodes"]]
    cv_vals      = [ep["episode"].get("agg.cv", 0.0) for ep in result["episodes"]]
    return {
        "mean_biomass": sum(biomass_vals) / max(len(biomass_vals), 1),
        "mean_cv":      sum(cv_vals)      / max(len(cv_vals),      1),
    }


# ---------------------------------------------------------------------------
# Part 1 — Algorithm ablation: NSGA-II vs simple vs random
# ---------------------------------------------------------------------------

def run_part1_ablation(
    pop_size: int = 50,
    n_generations: int = 25,
    steps: int = 300,
    n_eval: int = 10,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Compare NSGA-II, simple (μ+λ), and random search."""
    if smoke:
        n_runs, pop_size, n_generations, steps, n_eval = 2, 8, 3, 140, 3

    strategies = ["nsga2", "simple", "random"]
    config = dict(strategies=strategies, pop_size=pop_size, n_generations=n_generations,
                  steps=steps, n_eval=n_eval, n_runs=n_runs)
    print("\n" + "="*70)
    print("Part 1 — Algorithm Ablation: NSGA-II vs Simple vs Random")
    print_config_header(config)

    runs_by_strategy: Dict[str, List[Dict]] = {}

    for strategy in strategies:
        sub = f"{EXPERIMENT_NAME}/ablation_{strategy}"
        done = completed_run_ids(sub) if resume else set()
        print(f"\n  --- Strategy: {strategy} ---")
        t0 = time.time()
        for run_id in range(n_runs):
            if run_id in done:
                continue
            seed = BASE_SEED + run_id
            _set_eco_config(steps, n_eval, seed + 7)   # run-specific eval seed
            t_run = time.time()
            if strategy == "random":
                ea = _random_search(
                    objective_fn=eco.trait_objective,
                    gene_schema=eco.TRAIT_SCHEMA,
                    pop_size=pop_size,
                    n_generations=n_generations,
                    seed=seed,
                )
            else:
                ea = run_optimization_simple(
                    objective_fn=eco.trait_objective,
                    gene_schema=eco.TRAIT_SCHEMA,
                    strategy=strategy,
                    pop_size=pop_size,
                    n_generations=n_generations,
                    seed=seed,
                )
            result = {
                "run_id": run_id, "seed": seed, "strategy": strategy,
                "elapsed_s": time.time() - t_run,
                "hof_fitness": ea.get("hof_fitness", []),
                "hall_of_fame": ea.get("hall_of_fame", []),
                "logbook": ea.get("logbook", []),
            }
            save_run_result(result, sub, run_id)
            log_run_progress(run_id, n_runs, _quick_hv(result), time.time() - t0)
        runs_by_strategy[strategy] = load_completed_runs(sub)

    # Shared reference point across all strategies
    all_runs = [r for runs in runs_by_strategy.values() for r in runs]
    ref_pt = pool_reference_point(all_runs)

    hvs_by_strategy: Dict[str, List[float]] = {
        s: compute_hvs_for_runs(runs, ref_pt) for s, runs in runs_by_strategy.items()
    }

    print("\n=== Algorithm Ablation Results ===")
    rows = [(f"Eco {s}", hvs_by_strategy[s]) for s in strategies]
    print_summary_table(rows)

    # Wilcoxon: NSGA-II vs random
    stat_table = {}
    for s_alt in ["simple", "random"]:
        hvs_nsga2 = hvs_by_strategy["nsga2"]
        hvs_alt   = hvs_by_strategy[s_alt]
        if len(hvs_nsga2) >= 5 and len(hvs_alt) >= 5:
            try:
                stat, pval = wilcoxon_test(hvs_nsga2, hvs_alt)
                d          = cohens_d(hvs_nsga2, hvs_alt)
                stat_table[f"nsga2_vs_{s_alt}"] = {
                    "wilcoxon_stat": stat, "p_value": pval, "cohens_d": d,
                }
                print(f"\n  Wilcoxon NSGA-II vs {s_alt}: stat={stat:.4f} p={pval:.4f} d={d:.4f}")
            except Exception as exc:
                print(f"  Wilcoxon NSGA-II vs {s_alt}: skipped ({exc})")

    # Save CSV
    csv_path = results_path(EXPERIMENT_NAME, "ablation.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strategy", "mean_hv", "std_hv", "ci_lower", "ci_upper", "n"])
        for s in strategies:
            st = summarize_runs(hvs_by_strategy[s])
            w.writerow([s, st["mean"], st["std"], st["ci_lower"], st["ci_upper"], st["n"]])
    print(f"\n  CSV → experiments/results/{EXPERIMENT_NAME}/ablation.csv")

    summary = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_by_strategy": {s: hvs_by_strategy[s] for s in strategies},
        "stats_by_strategy": {s: summarize_runs(hvs_by_strategy[s]) for s in strategies},
        "statistical_tests": stat_table,
    }
    save_json(results_path(EXPERIMENT_NAME, "ablation.json"), summary)

    try:
        _plot_ablation(strategies, hvs_by_strategy)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return summary


def _plot_ablation(strategies: List[str], hvs_by_strategy: Dict[str, List[float]]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    means = [np.mean(hvs_by_strategy[s]) for s in strategies]
    stds  = [np.std(hvs_by_strategy[s])  for s in strategies]
    ci_lo = [bootstrap_ci(hvs_by_strategy[s])[0] if len(hvs_by_strategy[s]) >= 2 else means[i]
             for i, s in enumerate(strategies)]
    ci_hi = [bootstrap_ci(hvs_by_strategy[s])[1] if len(hvs_by_strategy[s]) >= 2 else means[i]
             for i, s in enumerate(strategies)]

    colors = {"nsga2": "steelblue", "simple": "darkorange", "random": "gray"}
    x = range(len(strategies))
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(x, means, yerr=stds, capsize=5, alpha=0.7,
                  color=[colors.get(s, "teal") for s in strategies], label="±1 std")
    ax.errorbar(x, means,
                yerr=[[m - lo for m, lo in zip(means, ci_lo)],
                      [hi - m for m, hi in zip(means, ci_hi)]],
                fmt="none", color="red", capsize=8, linewidth=2, label="95% CI")
    ax.set_xticks(list(x))
    ax.set_xticklabels([s.upper() for s in strategies])
    ax.set_ylabel("Hypervolume (shared ref)")
    ax.set_title("Algorithm Ablation: NSGA-II vs Simple vs Random")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    path = results_path(EXPERIMENT_NAME, "figs", "ablation_hv.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Ablation plot → experiments/results/{EXPERIMENT_NAME}/figs/ablation_hv.pdf")


# ---------------------------------------------------------------------------
# Part 2 — Scale sensitivity (steps × episodes)
# ---------------------------------------------------------------------------

def run_part2_scale(
    steps_list: Optional[List[int]] = None,
    n_eval_list: Optional[List[int]] = None,
    pop_size: int = 50,
    n_generations: int = 25,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """HV and champion-vs-ref gap across (steps, n_eval) grid."""
    if smoke:
        steps_list, n_eval_list, n_runs, pop_size, n_generations = [140, 300], [5, 10], 2, 8, 3
    if steps_list is None:
        steps_list = [140, 300, 500]
    if n_eval_list is None:
        n_eval_list = [5, 10, 20]

    config = dict(steps_list=steps_list, n_eval_list=n_eval_list,
                  pop_size=pop_size, n_generations=n_generations, n_runs=n_runs)
    print("\n" + "="*70)
    print("Part 2 — Scale Sensitivity (steps × episodes)")
    print_config_header(config)

    grid_results: Dict[str, Dict] = {}
    best_genome_overall: Optional[List[float]] = None
    best_hv_overall: float = -1.0
    best_config: Dict = {}

    for steps in steps_list:
        for n_eval in n_eval_list:
            cell_key = f"steps{steps}_ep{n_eval}"
            sub = f"{EXPERIMENT_NAME}/scale_{cell_key}"
            done = completed_run_ids(sub) if resume else set()
            print(f"\n  --- {cell_key} ---")
            t0 = time.time()
            for run_id in range(n_runs):
                if run_id in done:
                    continue
                seed = BASE_SEED + 1000 + run_id
                _set_eco_config(steps, n_eval, seed + 13)
                t_run = time.time()
                ea = run_optimization_simple(
                    objective_fn=eco.trait_objective,
                    gene_schema=eco.TRAIT_SCHEMA,
                    strategy="nsga2",
                    pop_size=pop_size,
                    n_generations=n_generations,
                    seed=seed,
                )
                result = {
                    "run_id": run_id, "seed": seed, "steps": steps, "n_eval": n_eval,
                    "elapsed_s": time.time() - t_run,
                    "hof_fitness": ea.get("hof_fitness", []),
                    "hall_of_fame": ea.get("hall_of_fame", []),
                }
                save_run_result(result, sub, run_id)
                log_run_progress(run_id, n_runs, _quick_hv(result), time.time() - t0)

            runs = load_completed_runs(sub)
            ref_pt = pool_reference_point(runs)
            hvs = compute_hvs_for_runs(runs, ref_pt)
            st = summarize_runs(hvs)

            # Track best champion across all cells
            best_run = max(runs, key=lambda r: _quick_hv(r), default=None)
            if best_run and best_run.get("hall_of_fame"):
                cell_hv = st["mean"]
                if cell_hv > best_hv_overall:
                    best_hv_overall = cell_hv
                    best_genome_overall = best_run["hall_of_fame"][0]
                    best_config = {"steps": steps, "n_eval": n_eval}

            grid_results[cell_key] = {
                "steps": steps, "n_eval": n_eval,
                "reference_point": list(ref_pt),
                "hv_per_run": hvs, "stats": st,
            }
            print(f"  {cell_key}: HV={st['mean']:.6f} ± {st['std']:.6f}"
                  f"  CI=[{st['ci_lower']:.6f},{st['ci_upper']:.6f}]")

    # Print grid table
    print("\n=== Scale Sensitivity Grid (mean HV) ===")
    header = "             " + "".join(f"  ep={n:>2}" for n in n_eval_list)
    print(header)
    for steps in steps_list:
        row = f"  steps={steps:<5}"
        for n_eval in n_eval_list:
            k = f"steps{steps}_ep{n_eval}"
            st = grid_results[k]["stats"]
            row += f"  {st['mean']:.4f}"
        print(row)

    save_json(results_path(EXPERIMENT_NAME, "scale_grid.json"),
              {"config": config, "grid_results": grid_results,
               "best_genome": best_genome_overall, "best_config": best_config})
    print(f"\n  Scale grid → experiments/results/{EXPERIMENT_NAME}/scale_grid.json")
    print(f"  Best champion genome: {best_genome_overall} @ {best_config}")

    try:
        _plot_scale_grid(steps_list, n_eval_list, grid_results)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return {"grid_results": grid_results,
            "best_genome": best_genome_overall,
            "best_config": best_config}


def _plot_scale_grid(
    steps_list: List[int],
    n_eval_list: List[int],
    grid_results: Dict[str, Dict],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    matrix = np.array([
        [grid_results[f"steps{s}_ep{e}"]["stats"]["mean"]
         for e in n_eval_list]
        for s in steps_list
    ])
    fig, ax = plt.subplots(figsize=(6, 4))
    im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(range(len(n_eval_list)))
    ax.set_yticks(range(len(steps_list)))
    ax.set_xticklabels([f"ep={e}" for e in n_eval_list])
    ax.set_yticklabels([f"steps={s}" for s in steps_list])
    for i in range(len(steps_list)):
        for j in range(len(n_eval_list)):
            ax.text(j, i, f"{matrix[i,j]:.4f}", ha="center", va="center", fontsize=8)
    plt.colorbar(im, ax=ax, label="Mean HV")
    ax.set_title("HV by Simulation Scale (steps × episodes)")
    fig.tight_layout()
    path = results_path(EXPERIMENT_NAME, "figs", "scale_grid.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Scale grid plot → experiments/results/{EXPERIMENT_NAME}/figs/scale_grid.pdf")


# ---------------------------------------------------------------------------
# Part 3 — Champion vs. reference across 16 held-out scenarios
# ---------------------------------------------------------------------------

def run_part3_champion_vs_ref(
    champion_genome: Optional[List[float]] = None,
    steps: int = 500,
    n_eval: int = 20,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Head-to-head champion vs. fixed reference across 16 held-out scenarios."""
    if smoke:
        steps, n_eval = 140, 3

    # If no champion provided, try to load from scale grid results
    if champion_genome is None:
        scale_path = results_path(EXPERIMENT_NAME, "scale_grid.json")
        if os.path.exists(scale_path):
            import json
            with open(scale_path) as f:
                d = json.load(f)
            champion_genome = d.get("best_genome")
        if champion_genome is None:
            # Fall back to the best run in ablation/nsga2 sub-dir
            runs = load_completed_runs(f"{EXPERIMENT_NAME}/ablation_nsga2")
            if runs:
                best_run = max(runs, key=lambda r: _quick_hv(r))
                hof = best_run.get("hall_of_fame", [])
                champion_genome = hof[0] if hof else REFERENCE_GENOME
            else:
                champion_genome = [0.3, 0.6]   # placeholder

    config = dict(champion_genome=champion_genome, steps=steps, n_eval=n_eval,
                  n_scenarios=len(EVAL_SCENARIOS))
    print("\n" + "="*70)
    print("Part 3 — Champion vs. Reference: Head-to-Head on 16 Scenarios")
    print_config_header(config)
    print(f"  Champion genome : {[round(g, 4) for g in champion_genome]}")
    print(f"  Reference genome: {REFERENCE_GENOME}")

    champ_scores: List[float] = []
    ref_scores:   List[float] = []
    per_scenario: List[Dict]  = []

    for sc_idx, scenario in enumerate(EVAL_SCENARIOS):
        seed = BASE_SEED + 9000 + sc_idx
        champ_res = _eval_genome_scenario(champion_genome, scenario, steps, n_eval, seed)
        ref_res   = _eval_genome_scenario(REFERENCE_GENOME, scenario, steps, n_eval, seed + 1)
        delta = champ_res["mean_biomass"] - ref_res["mean_biomass"]
        champ_scores.append(champ_res["mean_biomass"])
        ref_scores.append(ref_res["mean_biomass"])
        per_scenario.append({
            "scenario": scenario,
            "champ_biomass": champ_res["mean_biomass"], "ref_biomass": ref_res["mean_biomass"],
            "delta": delta, "champ_cv": champ_res["mean_cv"],
            "ref_cv": ref_res["mean_cv"],
        })
        print(f"  Sc {sc_idx+1:2d}: champ={champ_res['mean_biomass']:7.2f}"
              f"  ref={ref_res['mean_biomass']:7.2f}  Δ={delta:+7.2f}"
              f"  frag={scenario['fragmentation']} shock={scenario['shock_prob']}"
              f" K={scenario['K']} move={scenario['move_cost']}")

    mean_champ = float(np.mean(champ_scores))
    mean_ref   = float(np.mean(ref_scores))
    mean_delta = float(np.mean([s["delta"] for s in per_scenario]))
    pct_gain   = 100.0 * mean_delta / max(abs(mean_ref), 1e-9)
    n_wins     = sum(1 for s in per_scenario if s["delta"] > 0)

    print(f"\n  Mean biomass — champion: {mean_champ:.2f}  reference: {mean_ref:.2f}")
    print(f"  Mean Δ: {mean_delta:+.2f} ({pct_gain:+.1f}%)")
    print(f"  Champion wins: {n_wins}/{len(EVAL_SCENARIOS)} scenarios")

    # Wilcoxon + Cohen's d
    tests: Dict = {}
    try:
        stat, pval = wilcoxon_test(champ_scores, ref_scores)
        d = cohens_d(champ_scores, ref_scores)
        tests = {"wilcoxon_stat": stat, "p_value": pval, "cohens_d": d}
        print(f"  Wilcoxon: stat={stat:.4f}  p={pval:.4f}  Cohen's d={d:.4f}")
        sig = "***" if pval < 0.001 else ("**" if pval < 0.01 else ("*" if pval < 0.05 else "n.s."))
        print(f"  Significance: {sig}")
    except Exception as exc:
        print(f"  (Statistical test skipped: {exc})")

    # Save CSV
    csv_path = results_path(EXPERIMENT_NAME, "champion_vs_ref.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "frag", "shock", "K", "move_cost",
                    "champ_biomass", "ref_biomass", "delta", "champ_cv", "ref_cv"])
        for i, s in enumerate(per_scenario):
            sc = s["scenario"]
            w.writerow([i, sc["fragmentation"], sc["shock_prob"], sc["K"], sc["move_cost"],
                        s["champ_biomass"], s["ref_biomass"], s["delta"],
                        s["champ_cv"], s["ref_cv"]])
    print(f"\n  CSV → experiments/results/{EXPERIMENT_NAME}/champion_vs_ref.csv")

    result = {
        "config": config,
        "champion_genome": list(champion_genome),
        "reference_genome": REFERENCE_GENOME,
        "per_scenario": per_scenario,
        "aggregate": {
            "mean_champ": mean_champ, "mean_ref": mean_ref,
            "mean_delta": mean_delta, "pct_gain": pct_gain,
            "n_wins": n_wins, "n_scenarios": len(EVAL_SCENARIOS),
        },
        "statistical_tests": tests,
    }
    save_json(results_path(EXPERIMENT_NAME, "champion_vs_ref.json"), result)

    try:
        _plot_champion_vs_ref(per_scenario, mean_champ, mean_ref)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return result


def _plot_champion_vs_ref(
    per_scenario: List[Dict],
    mean_champ: float,
    mean_ref: float,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    champ_vals = [s["champ_biomass"] for s in per_scenario]
    ref_vals   = [s["ref_biomass"]   for s in per_scenario]
    deltas     = [s["delta"]      for s in per_scenario]
    ids        = range(len(per_scenario))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # Panel 1: per-scenario comparison
    ax1.plot(ids, champ_vals, "o-", color="steelblue", label=f"Champion (μ={mean_champ:.1f})")
    ax1.plot(ids, ref_vals,   "s--", color="gray",      label=f"Reference (μ={mean_ref:.1f})")
    ax1.fill_between(ids, ref_vals, champ_vals,
                     where=[c >= r for c, r in zip(champ_vals, ref_vals)],
                     alpha=0.2, color="steelblue", label="Champion lead")
    ax1.fill_between(ids, ref_vals, champ_vals,
                     where=[c < r for c, r in zip(champ_vals, ref_vals)],
                     alpha=0.2, color="red", label="Ref lead")
    ax1.set_xlabel("Scenario index")
    ax1.set_ylabel("Mean prey biomass")
    ax1.set_title("Per-Scenario Performance")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Panel 2: delta bar chart
    colors = ["steelblue" if d >= 0 else "red" for d in deltas]
    ax2.bar(ids, deltas, color=colors, alpha=0.8)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(float(np.mean(deltas)), color="steelblue", linestyle="--",
                label=f"Mean Δ={np.mean(deltas):+.2f}")
    ax2.set_xlabel("Scenario index")
    ax2.set_ylabel("Δ prey biomass (champion − reference)")
    ax2.set_title("Champion − Reference per Scenario")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    path = results_path(EXPERIMENT_NAME, "figs", "champion_vs_ref.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Champion vs ref plot → experiments/results/{EXPERIMENT_NAME}/figs/champion_vs_ref.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Baseline comparison (Exp 1 replacement)")
    p.add_argument("--smoke", action="store_true", help="Quick smoke test")
    p.add_argument("--part", type=int, choices=[1, 2, 3], default=None,
                   help="Run one sub-experiment only (default: all 3)")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--pop", type=int, default=50)
    p.add_argument("--ngen", type=int, default=25)
    p.add_argument("--n-runs", type=int, default=N_RUNS)
    p.add_argument("--steps", type=int, default=300,
                   help="Steps for Part 1 and Part 3 (default 300)")
    p.add_argument("--n-eval", type=int, default=10,
                   help="Eval episodes for Part 1 (default 10)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    run_parts = [1, 2, 3] if args.part is None else [args.part]
    scale_result = {}

    if 1 in run_parts:
        run_part1_ablation(
            pop_size=args.pop, n_generations=args.ngen,
            steps=args.steps, n_eval=args.n_eval,
            n_runs=args.n_runs, resume=args.resume, smoke=args.smoke,
        )

    if 2 in run_parts:
        scale_result = run_part2_scale(
            pop_size=args.pop, n_generations=args.ngen,
            n_runs=args.n_runs, resume=args.resume, smoke=args.smoke,
        )

    if 3 in run_parts:
        champion = scale_result.get("best_genome") if scale_result else None
        best_cfg = scale_result.get("best_config", {})
        run_part3_champion_vs_ref(
            champion_genome=champion,
            steps=best_cfg.get("steps", 500),
            n_eval=best_cfg.get("n_eval", 20),
            smoke=args.smoke,
        )

    print(f"\nAll outputs in: experiments/results/{EXPERIMENT_NAME}/")


if __name__ == "__main__":
    main()
