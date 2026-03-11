#!/usr/bin/env python3
"""
experiments/large_scale_comparison.py
======================================
Large-scale simulation study to demonstrate HEAS performance at big episode /
big tick regime — a key result for WSC submission.

Comparison design
-----------------
Previous experiments used at most steps=500, n_eval=20, pop=50, ngen=25.
This study pushes to:
  * Eco domain:        steps=1 000 × n_eval=30 = 30 000 step-evals / genome
  * Enterprise domain: steps=200  × n_eval=20 =  4 000 step-evals / genome
  * Population: 100 genomes, 40 generations, 20 independent runs

Three parts:

  Part 1 — Algorithm Showdown at Scale (Eco)
    NSGA-II vs Random search, 20 runs each at large scale.
    Proves NSGA-II advantage is amplified (not eroded) at big scale.

  Part 2 — Cross-Domain Scalability
    Both Eco and Enterprise at large scale, 20 NSGA-II runs each.
    Proves HEAS hierarchical composition scales across fundamentally
    different domain physics and parameter spaces.

  Part 3 — Large-Scale Champion Robustness (32-scenario stress test)
    Best eco champion (from Part 1) evaluated across a full 32-scenario OOD
    grid with 1 000 steps × 30 episodes.
    Proves evolved policy dominance is maintained — and often amplified —
    at higher simulation resolution.

Usage
-----
python experiments/large_scale_comparison.py            # all 3 parts
python experiments/large_scale_comparison.py --smoke    # quick smoke test
python experiments/large_scale_comparison.py --part 1
python experiments/large_scale_comparison.py --part 2
python experiments/large_scale_comparison.py --part 3

Results
-------
All outputs → experiments/results/large_scale_comparison/
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import random as _random
from typing import Any, Dict, List, Optional, Sequence, Tuple

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
import heas.experiments.enterprise as enterprise
from heas.utils.pareto import auto_reference_point, hypervolume
from heas.utils.stats import (
    bootstrap_ci,
    cohens_d,
    summarize_runs,
    wilcoxon_test,
)

try:
    from tqdm import tqdm
    _TQDM = True
except ImportError:
    _TQDM = False
    def tqdm(it, **kw):  # type: ignore[misc]
        return it


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "large_scale_comparison"
BASE_SEED = 7000

# ── Production defaults ────────────────────────────────────────────────────
# Eco: 1 000 steps × 30 episodes per genome eval
ECO_LARGE_STEPS = 1_000
ECO_LARGE_N_EVAL = 30
# Enterprise: 200 steps × 20 episodes per genome eval
ENT_LARGE_STEPS = 200
ENT_LARGE_N_EVAL = 20
# Optimizer
LARGE_POP = 100
LARGE_NGEN = 40
N_RUNS = 20

# 32 OOD scenarios for Part 3: 4×2×2×2 = 32 combos
EVAL_SCENARIOS_32 = [
    {"fragmentation": f, "shock_prob": s, "K": k, "move_cost": m}
    for f in [0.1, 0.3, 0.5, 0.7]
    for s in [0.05, 0.2]
    for k in [500.0, 1500.0]
    for m in [0.1, 0.3]
]  # 4×2×2×2 = 32

# Reference genome (paper's baseline)
REFERENCE_GENOME = [0.55, 0.35]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _quick_hv(result: Dict[str, Any]) -> float:
    pts = [tuple(float(v) for v in f) for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    return hypervolume(pts, auto_reference_point(pts))


def _set_eco_config(steps: int, n_eval: int, seed: int) -> None:
    eco._STEPS = steps
    eco._N_EVAL_EPISODES = n_eval
    eco._EVAL_SEED = seed


def _set_ent_config(n_eval: int, seed: int) -> None:
    enterprise._N_EVAL_EPISODES = n_eval
    enterprise._EVAL_SEED = seed


# ---------------------------------------------------------------------------
# Enterprise objective that honours configurable steps (unlike the module
# default which hardcodes steps=50).
# ---------------------------------------------------------------------------

def _enterprise_objective_large(genome: Sequence[Any]) -> tuple:
    """Large-scale enterprise fitness: same as enterprise_objective but uses
    ENT_LARGE_STEPS.  Module-level so it is picklable."""
    from heas.agent.runner import run_many

    tax, audit_intensity, subsidy, penalty_rate = (float(g) for g in genome[:4])
    result = run_many(
        enterprise.enterprise_model_factory,
        steps=enterprise._STEPS_LARGE,     # patched at runtime
        episodes=enterprise._N_EVAL_EPISODES,
        seed=enterprise._EVAL_SEED,
        tax=tax,
        audit_intensity=audit_intensity,
        subsidy=subsidy,
        penalty_rate=penalty_rate,
    )
    welfare_vals = [ep["episode"].get("agg.final_welfare", 0.0)
                    for ep in result["episodes"]]
    var_vals = [ep["episode"].get("agg.final_var_profit", 0.0)
                for ep in result["episodes"]]
    mean_welfare = sum(welfare_vals) / max(1, len(welfare_vals))
    mean_var = sum(var_vals) / max(1, len(var_vals))
    return (-mean_welfare, mean_var)


def _patch_enterprise_steps(steps: int) -> None:
    """Attach a _STEPS_LARGE attribute to the enterprise module."""
    enterprise._STEPS_LARGE = steps  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Random search baseline (same budget as NSGA-II)
# ---------------------------------------------------------------------------

def _random_search(
    objective_fn,
    gene_schema,
    pop_size: int,
    n_generations: int,
    seed: int,
) -> Dict[str, Any]:
    from heas.schemas.genes import Real, Int, Cat, Bool

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

    genomes = []
    fitnesses = []
    bar = tqdm(range(total), desc="  rand-eval", unit="genome", leave=False)
    for _ in bar:
        g = _sample()
        f = objective_fn(g)
        genomes.append(g)
        fitnesses.append(f)

    def _dominates(a, b):
        return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))

    pareto = [i for i in range(len(fitnesses))
              if not any(_dominates(fitnesses[j], fitnesses[i])
                         for j in range(len(fitnesses)) if j != i)]

    return {
        "best": [genomes[i] for i in pareto],
        "hall_of_fame": [genomes[i] for i in pareto],
        "hof_fitness": [list(fitnesses[i]) for i in pareto],
        "logbook": [],
    }


# ---------------------------------------------------------------------------
# Part 1 — Large-Scale Algorithm Showdown (Eco)
# ---------------------------------------------------------------------------

def run_part1_algorithm_showdown(
    steps: int = ECO_LARGE_STEPS,
    n_eval: int = ECO_LARGE_N_EVAL,
    pop_size: int = LARGE_POP,
    n_generations: int = LARGE_NGEN,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """NSGA-II vs Random at large scale — proves NSGA-II advantage scales up."""
    if smoke:
        steps, n_eval, pop_size, n_generations, n_runs = 200, 5, 10, 5, 2

    strategies = ["nsga2", "random"]
    config = dict(
        domain="eco",
        steps=steps, n_eval=n_eval,
        pop_size=pop_size, n_generations=n_generations,
        n_runs=n_runs, strategies=strategies,
    )
    print("\n" + "=" * 70)
    print("Part 1 — Large-Scale Algorithm Showdown (Ecological Domain)")
    print(f"  Scale: {steps:,} steps × {n_eval} episodes = "
          f"{steps * n_eval:,} step-evals / genome evaluation")
    print(f"  Budget: {pop_size} pop × {n_generations} gen × {n_runs} runs × 2 strategies")
    print_config_header(config)

    runs_by_strategy: Dict[str, List[Dict]] = {}

    for strategy in strategies:
        sub = f"{EXPERIMENT_NAME}/p1_{strategy}"
        done = completed_run_ids(sub) if resume else set()
        print(f"\n  ── Strategy: {strategy.upper()} ──")
        t0 = time.time()

        run_bar = tqdm(range(n_runs), desc=f"  {strategy}", unit="run")
        for run_id in run_bar:
            if run_id in done:
                run_bar.set_postfix(status="resumed")
                continue
            seed = BASE_SEED + run_id
            _set_eco_config(steps, n_eval, seed + 7)
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

            hv = _quick_hv(ea)
            result = {
                "run_id": run_id, "seed": seed, "strategy": strategy,
                "steps": steps, "n_eval": n_eval,
                "elapsed_s": time.time() - t_run,
                "hof_fitness": ea.get("hof_fitness", []),
                "hall_of_fame": ea.get("hall_of_fame", []),
                "logbook": ea.get("logbook", []),
            }
            save_run_result(result, sub, run_id)
            run_bar.set_postfix(hv=f"{hv:.4f}", elapsed=f"{time.time()-t0:.0f}s")

        runs_by_strategy[strategy] = load_completed_runs(sub)

    # Shared reference point
    all_runs = [r for runs in runs_by_strategy.values() for r in runs]
    ref_pt = pool_reference_point(all_runs)
    hvs_by_strategy = {
        s: compute_hvs_for_runs(runs, ref_pt)
        for s, runs in runs_by_strategy.items()
    }

    # Summary table
    print("\n=== Part 1 Results — Large-Scale Algorithm Showdown ===")
    rows = [(f"Eco {s} ({steps}s×{n_eval}ep)", hvs_by_strategy[s]) for s in strategies]
    print_summary_table(rows)

    # Wilcoxon + Cohen's d
    stat_table: Dict[str, Any] = {}
    hv_nsga2 = hvs_by_strategy.get("nsga2", [])
    hv_rand  = hvs_by_strategy.get("random", [])
    if len(hv_nsga2) >= 5 and len(hv_rand) >= 5:
        try:
            stat, pval = wilcoxon_test(hv_nsga2, hv_rand)
            d = cohens_d(hv_nsga2, hv_rand)
            stat_table["nsga2_vs_random"] = {
                "wilcoxon_stat": stat, "p_value": pval, "cohens_d": d,
            }
            sig = "***" if pval < 0.001 else ("**" if pval < 0.01 else
                                               ("*" if pval < 0.05 else "n.s."))
            print(f"\n  Wilcoxon (NSGA-II vs Random): stat={stat:.4f} "
                  f"p={pval:.4f}  d={d:.4f}  {sig}")
        except Exception as exc:
            print(f"  (Wilcoxon skipped: {exc})")

    # CSV
    csv_path = results_path(EXPERIMENT_NAME, "p1_algorithm_showdown.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strategy", "steps", "n_eval", "mean_hv", "std_hv",
                    "ci_lower", "ci_upper", "n"])
        for s in strategies:
            st = summarize_runs(hvs_by_strategy[s])
            w.writerow([s, steps, n_eval, st["mean"], st["std"],
                        st["ci_lower"], st["ci_upper"], st["n"]])
    print(f"  CSV → experiments/results/{EXPERIMENT_NAME}/p1_algorithm_showdown.csv")

    summary = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_by_strategy": {s: hvs_by_strategy[s] for s in strategies},
        "stats_by_strategy": {s: summarize_runs(hvs_by_strategy[s]) for s in strategies},
        "statistical_tests": stat_table,
    }
    save_json(results_path(EXPERIMENT_NAME, "p1_summary.json"), summary)

    # Best champion genome for Part 3
    best_genome: Optional[List[float]] = None
    best_hv = -1.0
    for run in runs_by_strategy.get("nsga2", []):
        hv = _quick_hv(run)
        if hv > best_hv and run.get("hall_of_fame"):
            best_hv = hv
            best_genome = run["hall_of_fame"][0]

    try:
        _plot_p1_showdown(strategies, hvs_by_strategy, steps, n_eval)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return {
        "summary": summary,
        "best_genome": best_genome,
        "steps": steps,
        "n_eval": n_eval,
    }


def _plot_p1_showdown(
    strategies: List[str],
    hvs_by_strategy: Dict[str, List[float]],
    steps: int,
    n_eval: int,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [s.upper() for s in strategies]
    means  = [np.mean(hvs_by_strategy[s]) for s in strategies]
    stds   = [np.std(hvs_by_strategy[s])  for s in strategies]

    def _ci(v):
        if len(v) >= 2:
            return bootstrap_ci(v)
        return (v[0], v[0]) if v else (0.0, 0.0)

    ci_lo = [_ci(hvs_by_strategy[s])[0] for s in strategies]
    ci_hi = [_ci(hvs_by_strategy[s])[1] for s in strategies]

    colors = {"nsga2": "#2196F3", "random": "#9E9E9E"}
    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(strategies))
    ax.bar(x, means, yerr=stds, capsize=6, alpha=0.75,
           color=[colors.get(s, "#4CAF50") for s in strategies], label="±1 σ")
    ax.errorbar(x, means,
                yerr=[[m - lo for m, lo in zip(means, ci_lo)],
                      [hi - m for m, hi in zip(means, ci_hi)]],
                fmt="none", color="red", capsize=10, linewidth=2, label="95% CI")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Hypervolume (shared ref)")
    ax.set_title(f"Large-Scale Algorithm Showdown\n"
                 f"({steps:,} steps × {n_eval} eps = {steps*n_eval:,} step-evals/genome)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    path = results_path(EXPERIMENT_NAME, "figs", "p1_algorithm_showdown.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot → experiments/results/{EXPERIMENT_NAME}/figs/p1_algorithm_showdown.pdf")


# ---------------------------------------------------------------------------
# Part 2 — Cross-Domain Scalability
# ---------------------------------------------------------------------------

def run_part2_cross_domain(
    eco_steps: int = ECO_LARGE_STEPS,
    eco_n_eval: int = ECO_LARGE_N_EVAL,
    ent_steps: int = ENT_LARGE_STEPS,
    ent_n_eval: int = ENT_LARGE_N_EVAL,
    pop_size: int = LARGE_POP,
    n_generations: int = LARGE_NGEN,
    n_runs: int = N_RUNS,
    resume: bool = False,
    smoke: bool = False,
) -> Dict[str, Any]:
    """NSGA-II on Eco + Enterprise at large scale — proves cross-domain generality."""
    if smoke:
        eco_steps, eco_n_eval = 200, 5
        ent_steps, ent_n_eval = 50, 3
        pop_size, n_generations, n_runs = 10, 5, 2

    domains = [
        {
            "name": "eco",
            "label": "Ecological",
            "steps": eco_steps,
            "n_eval": eco_n_eval,
            "sub": f"{EXPERIMENT_NAME}/p2_eco",
            "schema": eco.TRAIT_SCHEMA,
        },
        {
            "name": "ent",
            "label": "Enterprise",
            "steps": ent_steps,
            "n_eval": ent_n_eval,
            "sub": f"{EXPERIMENT_NAME}/p2_ent",
            "schema": enterprise.ENTERPRISE_SCHEMA,
        },
    ]

    config = dict(
        eco_steps=eco_steps, eco_n_eval=eco_n_eval,
        ent_steps=ent_steps, ent_n_eval=ent_n_eval,
        pop_size=pop_size, n_generations=n_generations, n_runs=n_runs,
    )
    print("\n" + "=" * 70)
    print("Part 2 — Cross-Domain Scalability (Eco + Enterprise)")
    print(f"  Eco:        {eco_steps:,} steps × {eco_n_eval} episodes = "
          f"{eco_steps * eco_n_eval:,} step-evals / genome")
    print(f"  Enterprise: {ent_steps:,} steps × {ent_n_eval} episodes = "
          f"{ent_steps * ent_n_eval:,} step-evals / genome")
    print_config_header(config)

    domain_results: Dict[str, Any] = {}
    _patch_enterprise_steps(ent_steps)

    domain_bar = tqdm(domains, desc="Domain", unit="domain")
    for dom in domain_bar:
        dname = dom["name"]
        dlabel = dom["label"]
        dom_steps = dom["steps"]
        dom_n_eval = dom["n_eval"]
        sub = dom["sub"]
        schema = dom["schema"]
        done = completed_run_ids(sub) if resume else set()

        domain_bar.set_description(f"Domain: {dlabel}")
        print(f"\n  ── {dlabel} ({dom_steps:,} steps × {dom_n_eval} eps) ──")

        if dname == "eco":
            _set_eco_config(dom_steps, dom_n_eval, BASE_SEED + 100)
            obj_fn = eco.trait_objective
        else:
            _set_ent_config(dom_n_eval, BASE_SEED + 200)
            obj_fn = _enterprise_objective_large

        t0 = time.time()
        run_bar = tqdm(range(n_runs), desc=f"  {dlabel}", unit="run", leave=False)
        for run_id in run_bar:
            if run_id in done:
                continue
            seed = BASE_SEED + 1000 + run_id + (500 if dname == "ent" else 0)
            if dname == "eco":
                _set_eco_config(dom_steps, dom_n_eval, seed + 13)
            else:
                _set_ent_config(dom_n_eval, seed + 17)

            t_run = time.time()
            ea = run_optimization_simple(
                objective_fn=obj_fn,
                gene_schema=schema,
                strategy="nsga2",
                pop_size=pop_size,
                n_generations=n_generations,
                seed=seed,
            )
            hv = _quick_hv(ea)
            result = {
                "run_id": run_id, "seed": seed, "domain": dname,
                "steps": dom_steps, "n_eval": dom_n_eval,
                "elapsed_s": time.time() - t_run,
                "hof_fitness": ea.get("hof_fitness", []),
                "hall_of_fame": ea.get("hall_of_fame", []),
                "logbook": ea.get("logbook", []),
            }
            save_run_result(result, sub, run_id)
            run_bar.set_postfix(hv=f"{hv:.4f}", elapsed=f"{time.time()-t0:.0f}s")

        runs = load_completed_runs(sub)
        ref_pt = pool_reference_point(runs)
        hvs = compute_hvs_for_runs(runs, ref_pt)
        st = summarize_runs(hvs)
        domain_results[dname] = {
            "label": dlabel, "steps": dom_steps, "n_eval": dom_n_eval,
            "reference_point": list(ref_pt),
            "hv_per_run": hvs, "stats": st,
        }
        print(f"  {dlabel}: HV = {st['mean']:.4f} ± {st['std']:.4f} "
              f"  95% CI=[{st['ci_lower']:.4f}, {st['ci_upper']:.4f}]")

    # Summary table
    print("\n=== Part 2 Results — Cross-Domain Scalability ===")
    rows = [
        (f"{domain_results[d]['label']} ({domain_results[d]['steps']:,}s×{domain_results[d]['n_eval']}ep)",
         domain_results[d]["hv_per_run"])
        for d in ["eco", "ent"] if d in domain_results
    ]
    print_summary_table(rows)

    # CSV
    csv_path = results_path(EXPERIMENT_NAME, "p2_cross_domain.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["domain", "steps", "n_eval", "mean_hv", "std_hv",
                    "ci_lower", "ci_upper", "n"])
        for dname, dr in domain_results.items():
            st = dr["stats"]
            w.writerow([dname, dr["steps"], dr["n_eval"], st["mean"], st["std"],
                        st["ci_lower"], st["ci_upper"], st["n"]])
    print(f"  CSV → experiments/results/{EXPERIMENT_NAME}/p2_cross_domain.csv")

    summary = {"config": config, "domain_results": domain_results}
    save_json(results_path(EXPERIMENT_NAME, "p2_summary.json"), summary)

    try:
        _plot_p2_cross_domain(domain_results)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return summary


def _plot_p2_cross_domain(domain_results: Dict[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(domain_results.keys())
    labels = [domain_results[d]["label"] for d in names]
    means  = [domain_results[d]["stats"]["mean"] for d in names]
    stds   = [domain_results[d]["stats"]["std"]  for d in names]
    ci_lo  = [domain_results[d]["stats"]["ci_lower"] for d in names]
    ci_hi  = [domain_results[d]["stats"]["ci_upper"] for d in names]
    step_labels = [
        f"{domain_results[d]['label']}\n"
        f"({domain_results[d]['steps']:,}s×{domain_results[d]['n_eval']}ep)"
        for d in names
    ]

    colors = {"eco": "#4CAF50", "ent": "#FF9800"}
    fig, ax = plt.subplots(figsize=(7, 4))
    x = range(len(names))
    ax.bar(x, means, yerr=stds, capsize=6, alpha=0.75,
           color=[colors.get(d, "#2196F3") for d in names], label="±1 σ")
    ax.errorbar(x, means,
                yerr=[[m - lo for m, lo in zip(means, ci_lo)],
                      [hi - m for m, hi in zip(means, ci_hi)]],
                fmt="none", color="red", capsize=10, linewidth=2, label="95% CI")
    ax.set_xticks(list(x))
    ax.set_xticklabels(step_labels)
    ax.set_ylabel("Hypervolume (domain-specific ref)")
    ax.set_title("Cross-Domain Scalability: NSGA-II at Large Scale")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()

    path = results_path(EXPERIMENT_NAME, "figs", "p2_cross_domain.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot → experiments/results/{EXPERIMENT_NAME}/figs/p2_cross_domain.pdf")


# ---------------------------------------------------------------------------
# Part 3 — Large-Scale Champion Robustness (32-scenario OOD stress test)
# ---------------------------------------------------------------------------

def _eval_genome_scenario(
    genome: List[float],
    scenario: Dict[str, Any],
    steps: int,
    n_episodes: int,
    seed: int,
) -> Dict[str, float]:
    """Evaluate one eco genome across one OOD scenario."""
    from heas.agent.runner import run_many

    risk, dispersal = float(genome[0]), float(genome[1])
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
    biomass_vals = [ep["episode"].get("agg.mean_biomass", 0.0)
                    for ep in result["episodes"]]
    cv_vals = [ep["episode"].get("agg.cv", 0.0) for ep in result["episodes"]]
    return {
        "mean_biomass": sum(biomass_vals) / max(len(biomass_vals), 1),
        "mean_cv":      sum(cv_vals) / max(len(cv_vals), 1),
    }


def run_part3_champion_robustness(
    champion_genome: Optional[List[float]] = None,
    steps: int = ECO_LARGE_STEPS,
    n_eval: int = ECO_LARGE_N_EVAL,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Champion vs reference across 32 OOD scenarios at large scale."""
    if smoke:
        steps, n_eval = 200, 5

    if champion_genome is None:
        # Try to load from Part 1 results
        p1_path = results_path(EXPERIMENT_NAME, "p1_summary.json")
        if os.path.exists(p1_path):
            with open(p1_path) as f:
                p1 = json.load(f)
            runs = load_completed_runs(f"{EXPERIMENT_NAME}/p1_nsga2")
            if runs:
                best_run = max(runs, key=_quick_hv)
                hof = best_run.get("hall_of_fame", [])
                champion_genome = hof[0] if hof else REFERENCE_GENOME
            else:
                champion_genome = REFERENCE_GENOME
        else:
            champion_genome = [0.3, 0.6]   # fallback

    config = dict(
        champion_genome=champion_genome,
        reference_genome=REFERENCE_GENOME,
        steps=steps, n_eval=n_eval,
        n_scenarios=len(EVAL_SCENARIOS_32),
    )
    print("\n" + "=" * 70)
    print("Part 3 — Large-Scale Champion Robustness (32-Scenario OOD Stress Test)")
    print(f"  Scale: {steps:,} steps × {n_eval} episodes = "
          f"{steps * n_eval:,} step-evals / scenario")
    print(f"  Champion : {[round(g, 4) for g in champion_genome]}")
    print(f"  Reference: {REFERENCE_GENOME}")
    print(f"  Scenarios: {len(EVAL_SCENARIOS_32)}")
    print_config_header(config)

    champ_scores: List[float] = []
    ref_scores:   List[float] = []
    per_scenario: List[Dict]  = []

    scenario_bar = tqdm(enumerate(EVAL_SCENARIOS_32),
                        total=len(EVAL_SCENARIOS_32),
                        desc="  OOD scenarios",
                        unit="scenario")
    for sc_idx, scenario in scenario_bar:
        seed = BASE_SEED + 9000 + sc_idx
        champ_res = _eval_genome_scenario(champion_genome, scenario, steps, n_eval, seed)
        ref_res   = _eval_genome_scenario(REFERENCE_GENOME, scenario, steps, n_eval, seed + 1)
        delta = champ_res["mean_biomass"] - ref_res["mean_biomass"]
        champ_scores.append(champ_res["mean_biomass"])
        ref_scores.append(ref_res["mean_biomass"])
        per_scenario.append({
            "scenario": scenario,
            "champ_biomass": champ_res["mean_biomass"],
            "ref_biomass":   ref_res["mean_biomass"],
            "delta": delta,
            "champ_cv": champ_res["mean_cv"],
            "ref_cv":   ref_res["mean_cv"],
        })
        scenario_bar.set_postfix(
            champ=f"{champ_res['mean_biomass']:.1f}",
            ref=f"{ref_res['mean_biomass']:.1f}",
            delta=f"{delta:+.1f}",
        )

    mean_champ = float(np.mean(champ_scores))
    mean_ref   = float(np.mean(ref_scores))
    mean_delta = float(np.mean([s["delta"] for s in per_scenario]))
    pct_gain   = 100.0 * mean_delta / max(abs(mean_ref), 1e-9)
    n_wins     = sum(1 for s in per_scenario if s["delta"] > 0)

    print(f"\n  Mean biomass — champion: {mean_champ:.2f}   reference: {mean_ref:.2f}")
    print(f"  Mean Δ: {mean_delta:+.2f} ({pct_gain:+.1f}%)")
    print(f"  Champion wins: {n_wins}/{len(EVAL_SCENARIOS_32)} scenarios")

    tests: Dict[str, Any] = {}
    try:
        stat, pval = wilcoxon_test(champ_scores, ref_scores)
        d = cohens_d(champ_scores, ref_scores)
        tests = {"wilcoxon_stat": stat, "p_value": pval, "cohens_d": d}
        sig = "***" if pval < 0.001 else ("**" if pval < 0.01 else
                                           ("*" if pval < 0.05 else "n.s."))
        print(f"  Wilcoxon: stat={stat:.4f}  p={pval:.4f}  Cohen's d={d:.4f}  {sig}")
    except Exception as exc:
        print(f"  (Statistical test skipped: {exc})")

    # CSV
    csv_path = results_path(EXPERIMENT_NAME, "p3_champion_vs_ref_32.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scenario_id", "frag", "shock_prob", "K", "move_cost",
                    "champ_biomass", "ref_biomass", "delta",
                    "champ_cv", "ref_cv"])
        for i, s in enumerate(per_scenario):
            sc = s["scenario"]
            w.writerow([
                i, sc["fragmentation"], sc["shock_prob"], sc["K"], sc["move_cost"],
                s["champ_biomass"], s["ref_biomass"], s["delta"],
                s["champ_cv"], s["ref_cv"],
            ])
    print(f"  CSV → experiments/results/{EXPERIMENT_NAME}/p3_champion_vs_ref_32.csv")

    result = {
        "config": config,
        "champion_genome": list(champion_genome),
        "reference_genome": REFERENCE_GENOME,
        "per_scenario": per_scenario,
        "aggregate": {
            "mean_champ": mean_champ, "mean_ref": mean_ref,
            "mean_delta": mean_delta, "pct_gain": pct_gain,
            "n_wins": n_wins, "n_scenarios": len(EVAL_SCENARIOS_32),
        },
        "statistical_tests": tests,
    }
    save_json(results_path(EXPERIMENT_NAME, "p3_summary.json"), result)

    try:
        _plot_p3_champion(per_scenario, mean_champ, mean_ref, steps, n_eval)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")

    return result


def _plot_p3_champion(
    per_scenario: List[Dict],
    mean_champ: float,
    mean_ref: float,
    steps: int,
    n_eval: int,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    champ_vals = [s["champ_biomass"] for s in per_scenario]
    ref_vals   = [s["ref_biomass"]   for s in per_scenario]
    deltas     = [s["delta"]         for s in per_scenario]
    ids        = list(range(len(per_scenario)))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: per-scenario lines
    ax1.plot(ids, champ_vals, "o-", color="#2196F3",
             label=f"Champion (μ={mean_champ:.1f})", linewidth=1.5, markersize=4)
    ax1.plot(ids, ref_vals, "s--", color="#9E9E9E",
             label=f"Reference (μ={mean_ref:.1f})", linewidth=1.5, markersize=4)
    ax1.fill_between(ids, ref_vals, champ_vals,
                     where=[c >= r for c, r in zip(champ_vals, ref_vals)],
                     alpha=0.15, color="#2196F3", label="Champion lead")
    ax1.fill_between(ids, ref_vals, champ_vals,
                     where=[c < r for c, r in zip(champ_vals, ref_vals)],
                     alpha=0.15, color="#F44336", label="Ref lead")
    ax1.set_xlabel("Scenario index (0–31)")
    ax1.set_ylabel("Mean prey biomass")
    ax1.set_title(f"Per-Scenario Performance\n({steps:,}s × {n_eval}ep)")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Panel 2: delta bars
    bar_colors = ["#2196F3" if d >= 0 else "#F44336" for d in deltas]
    ax2.bar(ids, deltas, color=bar_colors, alpha=0.8)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.axhline(float(np.mean(deltas)), color="#2196F3", linestyle="--",
                linewidth=1.5, label=f"Mean Δ={np.mean(deltas):+.1f}")
    ax2.set_xlabel("Scenario index (0–31)")
    ax2.set_ylabel("Δ prey biomass (champion − reference)")
    ax2.set_title("Champion − Reference per Scenario\n(32 OOD scenarios)")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3, axis="y")

    fig.suptitle(
        f"Large-Scale Champion Robustness: {steps:,} steps × {n_eval} episodes",
        fontsize=11,
    )
    fig.tight_layout()
    path = results_path(EXPERIMENT_NAME, "figs", "p3_champion_robustness.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot → experiments/results/{EXPERIMENT_NAME}/figs/p3_champion_robustness.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Large-scale HEAS comparison (WSC scalability evidence)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--smoke",  action="store_true", help="Quick smoke test (tiny params)")
    p.add_argument("--part",   type=int, choices=[1, 2, 3], default=None,
                   help="Run a single part only (default: all 3)")
    p.add_argument("--resume", action="store_true",
                   help="Resume from saved checkpoints")
    # Scale overrides
    p.add_argument("--eco-steps", type=int, default=ECO_LARGE_STEPS)
    p.add_argument("--eco-n-eval", type=int, default=ECO_LARGE_N_EVAL)
    p.add_argument("--ent-steps", type=int, default=ENT_LARGE_STEPS)
    p.add_argument("--ent-n-eval", type=int, default=ENT_LARGE_N_EVAL)
    p.add_argument("--pop",    type=int, default=LARGE_POP)
    p.add_argument("--ngen",   type=int, default=LARGE_NGEN)
    p.add_argument("--n-runs", type=int, default=N_RUNS)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    print("\n" + "#" * 70)
    print("# HEAS Large-Scale Comparison — WSC 2026 Supplementary Experiment")
    print("#" * 70)
    if args.smoke:
        print("# [SMOKE MODE — reduced parameters for quick validation]")

    run_parts = [1, 2, 3] if args.part is None else [args.part]
    p1_result: Dict[str, Any] = {}

    if 1 in run_parts:
        p1_result = run_part1_algorithm_showdown(
            steps=args.eco_steps,
            n_eval=args.eco_n_eval,
            pop_size=args.pop,
            n_generations=args.ngen,
            n_runs=args.n_runs,
            resume=args.resume,
            smoke=args.smoke,
        )

    if 2 in run_parts:
        run_part2_cross_domain(
            eco_steps=args.eco_steps,
            eco_n_eval=args.eco_n_eval,
            ent_steps=args.ent_steps,
            ent_n_eval=args.ent_n_eval,
            pop_size=args.pop,
            n_generations=args.ngen,
            n_runs=args.n_runs,
            resume=args.resume,
            smoke=args.smoke,
        )

    if 3 in run_parts:
        champion = p1_result.get("best_genome")
        best_steps = p1_result.get("steps", args.eco_steps)
        best_n_eval = p1_result.get("n_eval", args.eco_n_eval)
        run_part3_champion_robustness(
            champion_genome=champion,
            steps=best_steps,
            n_eval=best_n_eval,
            smoke=args.smoke,
        )

    print(f"\nAll outputs in: experiments/results/{EXPERIMENT_NAME}/")
    print("Done.")


if __name__ == "__main__":
    main()
