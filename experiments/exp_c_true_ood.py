#!/usr/bin/env python3
"""
experiments/exp_c_true_ood.py
================================
Revision Experiment C — True out-of-distribution generalization test.

Addresses reviewer CRITICAL issue #3:
  "The 32-scenario test is *interpolation, not extrapolation*.  All 32 scenarios
   are constructed by crossing the same 4 factors within the training factor
   space.  This is not a truly out-of-distribution test."

Design (two-phase):

  Phase 1 — TRAINING
    Evolve n=15 independent NSGA-II champions on a SINGLE anchor scenario:
      fragmentation=0.2, shock_prob=0.05, K=80, move_cost=0.1
    This is the narrowest possible training distribution (one fixed scenario).
    Select the median-HV champion from the 15 runs.

  Phase 2 — OOD EVALUATION
    Evaluate the anchor champion against a reference genome [0.55, 0.35]
    on 24 held-out OOD scenarios that use factor values OUTSIDE the training
    range:
      fragmentation ∈ {0.65, 0.80}          (training: 0.2 — high fragmentation)
      shock_prob    ∈ {0.35, 0.50}          (training: 0.05 — high shock)
      K             ∈ {200, 400, 600}        (training: 80 — higher carrying cap)
      move_cost     ∈ {0.45, 0.60}          (training: 0.1 — high dispersal cost)
    All 24 = 2×2×3×2 combinations are tested with n_eval=10 episodes each.
    Reports: win rate, Wilcoxon p-value, Cohen's d, and % biomass gain.

  In-distribution comparison (sanity check):
    Also evaluate the same champion on 8 near-anchor scenarios:
      fragmentation ∈ {0.1, 0.3}, shock_prob ∈ {0.03, 0.07},
      K ∈ {60, 100}, move_cost ∈ {0.08, 0.12}
    These check that the evolved champion actually outperforms the reference in
    its training neighborhood before making OOD claims.

Results go to: experiments/results/true_ood/

Usage
-----
# Full run
python experiments/exp_c_true_ood.py

# Smoke test
python experiments/exp_c_true_ood.py --smoke

# Only run Phase 2 using a saved champion genome (skip re-evolution)
python experiments/exp_c_true_ood.py --eval-only

# Resume an interrupted Phase 1
python experiments/exp_c_true_ood.py --resume
"""
from __future__ import annotations

import argparse
import csv
import json
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
from heas.utils.stats import cohens_d, summarize_runs, wilcoxon_test

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EXPERIMENT_NAME = "true_ood"
BASE_SEED = 8000

# Reference genome (same as existing champion_vs_ref study)
REFERENCE_GENOME = [0.55, 0.35]

# --- Phase 1 training config (anchor scenario) ---
ANCHOR_SCENARIO = dict(
    fragmentation=0.2,
    shock_prob=0.05,
    K=80.0,
    move_cost=0.1,
)
TRAIN_STEPS = 500      # same evaluation scale as existing Part 3
TRAIN_N_EVAL = 5
N_TRAIN_RUNS = 15      # independent evolutions to select a stable champion
TRAIN_POP = 30
TRAIN_NGEN = 15

# --- OOD test scenarios (factor values NOT used during training) ---
# Training: fragmentation=0.2, shock_prob=0.05, K=80, move_cost=0.1
# OOD: move clearly outside training region in every factor simultaneously

OOD_SCENARIOS = [
    {"fragmentation": f, "shock_prob": s, "K": k, "move_cost": m}
    for f in [0.65, 0.80]      # training: 0.2   → high fragmentation
    for s in [0.35, 0.50]      # training: 0.05  → high shock probability
    for k in [200.0, 400.0, 600.0]  # training: 80    → higher carrying capacity
    for m in [0.45, 0.60]      # training: 0.1   → high dispersal cost
]  # 2×2×3×2 = 24 OOD scenarios

# --- In-distribution sanity check scenarios (near-anchor, for comparison) ---
IN_DIST_SCENARIOS = [
    {"fragmentation": f, "shock_prob": s, "K": k, "move_cost": m}
    for f in [0.1, 0.3]       # bracket training 0.2
    for s in [0.03, 0.07]     # bracket training 0.05
    for k in [60.0, 100.0]    # bracket training 80
    for m in [0.08, 0.12]     # bracket training 0.1
]  # 2×2×2×2 = 16 in-distribution scenarios

OOD_N_EVAL = 10      # episodes per OOD scenario


# ---------------------------------------------------------------------------
# Custom single-anchor training objective
# ---------------------------------------------------------------------------

def _make_anchor_objective(
    steps: int,
    n_eval: int,
    seed: int,
    fragmentation: float,
    shock_prob: float,
    K: float,
    move_cost: float,
):
    """Return a picklable objective function fixed to a single anchor scenario.

    Unlike eco.trait_objective (which uses module-level defaults), this
    objective explicitly passes fragmentation, shock_prob, K, and move_cost
    to run_many.  The champion evolved on this objective is NOT exposed to
    any variation in these parameters during training — making the OOD test
    a genuine distributional shift.
    """
    from heas.agent.runner import run_many

    # These must be captured in closure *not* via module globals so that
    # each training run sees the same fixed anchor regardless of other
    # concurrent module-level changes.
    _steps = steps
    _n_eval = n_eval
    _seed = seed
    _frag = fragmentation
    _shock = shock_prob
    _K = K
    _move = move_cost

    def objective(genome) -> tuple:
        risk = float(genome[0])
        dispersal = float(genome[1])
        result = run_many(
            eco.trait_model_factory,
            steps=_steps,
            episodes=_n_eval,
            seed=_seed,
            risk=risk,
            dispersal=dispersal,
            fragmentation=_frag,
            shock_prob=_shock,
            K=_K,
            move_cost=_move,
        )
        biomass_vals = [ep["episode"].get("agg.mean_biomass", 0.0)
                        for ep in result["episodes"]]
        cv_vals = [ep["episode"].get("agg.cv", 0.0)
                   for ep in result["episodes"]]
        mean_biomass = sum(biomass_vals) / max(1, len(biomass_vals))
        mean_cv = sum(cv_vals) / max(1, len(cv_vals))
        return (-mean_biomass, mean_cv)

    return objective


def _quick_hv(result: Dict[str, Any]) -> float:
    pts = [tuple(float(v) for v in f)
           for f in result.get("hof_fitness", []) if len(f) >= 2]
    if not pts:
        return 0.0
    return hypervolume(pts, auto_reference_point(pts))


# ---------------------------------------------------------------------------
# Phase 1: Evolve champions on anchor scenario
# ---------------------------------------------------------------------------

def run_phase1_training(
    n_runs: int = N_TRAIN_RUNS,
    pop_size: int = TRAIN_POP,
    n_gen: int = TRAIN_NGEN,
    resume: bool = False,
    smoke: bool = False,
) -> Tuple[List[float], List[Dict]]:
    """Evolve n_runs champions on the anchor scenario; return (champion_genome, all_runs)."""
    if smoke:
        n_runs, pop_size, n_gen = 3, 10, 5

    sub = f"{EXPERIMENT_NAME}/phase1_training"
    config = dict(
        phase="1_training",
        anchor_scenario=ANCHOR_SCENARIO,
        n_runs=n_runs,
        pop_size=pop_size,
        n_gen=n_gen,
        steps=TRAIN_STEPS,
        n_eval=TRAIN_N_EVAL,
        base_seed=BASE_SEED,
        purpose="Single-anchor training for true OOD test",
    )
    print("\n" + "=" * 70)
    print("Phase 1 — Evolve champions on ANCHOR scenario")
    print(f"  Anchor: {ANCHOR_SCENARIO}")
    print_config_header(config)

    done_ids = completed_run_ids(sub) if resume else set()
    if done_ids:
        print(f"  Resuming: {len(done_ids)} done.")

    t_start = time.time()
    for run_id in range(n_runs):
        if run_id in done_ids:
            continue
        seed = BASE_SEED + run_id
        # Each training run uses a slightly different eval seed to avoid
        # overfitting to a single stochastic realisation.
        objective = _make_anchor_objective(
            steps=TRAIN_STEPS,
            n_eval=TRAIN_N_EVAL,
            seed=seed + 37,
            **ANCHOR_SCENARIO,
        )
        t_run = time.time()
        ea = run_optimization_simple(
            objective_fn=objective,
            gene_schema=eco.TRAIT_SCHEMA,
            strategy="nsga2",
            pop_size=pop_size,
            n_generations=n_gen,
            seed=seed,
        )
        result = {
            "run_id": run_id,
            "seed": seed,
            "pop_size": pop_size,
            "n_gen": n_gen,
            "anchor_scenario": ANCHOR_SCENARIO,
            "base_seed": BASE_SEED,
            "elapsed_s": time.time() - t_run,
            "hof_fitness": ea.get("hof_fitness", []),
            "hall_of_fame": ea.get("hall_of_fame", []),
        }
        save_run_result(result, sub, run_id)
        log_run_progress(run_id, n_runs, _quick_hv(result), time.time() - t_start)

    all_runs = load_completed_runs(sub)
    print(f"\n  Loaded {len(all_runs)} completed training runs.")

    # Pool HV across runs and pick the MEDIAN champion
    # (median = typical run, not cherry-picked best; avoids selection bias)
    ref_pt = pool_reference_point(all_runs)
    hvs = compute_hvs_for_runs(all_runs, ref_pt)

    print(f"  Training HV: mean={np.mean(hvs):.4f} ± std={np.std(hvs):.4f}")
    print(f"  HV per run: {[round(h, 3) for h in hvs]}")

    median_hv = float(np.median(hvs))
    idx = int(np.argmin(np.abs(np.array(hvs) - median_hv)))
    median_run = all_runs[idx]
    hof = median_run.get("hall_of_fame", [])
    if not hof:
        # Fall back to best run
        idx = int(np.argmax(hvs))
        hof = all_runs[idx].get("hall_of_fame", [])

    champion_genome = hof[0] if hof else REFERENCE_GENOME
    print(f"\n  Selected champion genome (median-HV run {idx}): "
          f"risk={champion_genome[0]:.4f}, dispersal={champion_genome[1]:.4f}")

    # Save training summary
    training_summary = {
        "config": config,
        "reference_point": list(ref_pt),
        "hv_per_run": hvs,
        "hv_stats": summarize_runs(hvs),
        "selected_champion": list(champion_genome),
        "selected_run_id": int(idx),
        "selection_method": "median-HV run",
    }
    save_json(results_path(EXPERIMENT_NAME, "training_summary.json"), training_summary)
    print(f"  Training summary → experiments/results/{EXPERIMENT_NAME}/training_summary.json")

    return list(champion_genome), all_runs


# ---------------------------------------------------------------------------
# Phase 2: Evaluate champion on OOD and in-distribution scenarios
# ---------------------------------------------------------------------------

def _eval_genome_scenario(
    genome: List[float],
    scenario: Dict[str, Any],
    steps: int,
    n_eval: int,
    seed: int,
) -> Dict[str, float]:
    """Run genome in a scenario; return mean_biomass and cv."""
    from heas.agent.runner import run_many
    result = run_many(
        eco.trait_model_factory,
        steps=steps,
        episodes=n_eval,
        seed=seed,
        risk=float(genome[0]),
        dispersal=float(genome[1]),
        fragmentation=scenario.get("fragmentation", 0.2),
        shock_prob=scenario.get("shock_prob", 0.1),
        K=scenario.get("K", 1000.0),
        move_cost=scenario.get("move_cost", 0.2),
    )
    biomass_vals = [ep["episode"].get("agg.mean_biomass", 0.0)
                    for ep in result["episodes"]]
    cv_vals = [ep["episode"].get("agg.cv", 0.0) for ep in result["episodes"]]
    return {
        "mean_biomass": float(np.mean(biomass_vals)) if biomass_vals else 0.0,
        "mean_cv":      float(np.mean(cv_vals))      if cv_vals      else 0.0,
    }


def _evaluate_on_scenarios(
    champion_genome: List[float],
    scenarios: List[Dict[str, Any]],
    label: str,
    steps: int,
    n_eval: int,
    seed_offset: int,
    smoke: bool,
) -> Dict[str, Any]:
    """Head-to-head champion vs. reference on a list of scenarios."""
    if smoke:
        scenarios = scenarios[:2]
        n_eval = 2

    print(f"\n  Evaluating {len(scenarios)} {label} scenarios "
          f"({n_eval} episodes each)...")

    champ_scores: List[float] = []
    ref_scores:   List[float] = []
    per_scenario: List[Dict]  = []

    for i, sc in enumerate(scenarios):
        seed = BASE_SEED + seed_offset + i * 17
        champ = _eval_genome_scenario(champion_genome, sc, steps, n_eval, seed)
        ref   = _eval_genome_scenario(REFERENCE_GENOME, sc, steps, n_eval, seed + 1)
        delta = champ["mean_biomass"] - ref["mean_biomass"]
        champ_scores.append(champ["mean_biomass"])
        ref_scores.append(ref["mean_biomass"])
        per_scenario.append({
            "scenario": sc,
            "champ_biomass": champ["mean_biomass"],
            "ref_biomass":   ref["mean_biomass"],
            "delta":         delta,
            "champ_cv":      champ["mean_cv"],
            "ref_cv":        ref["mean_cv"],
        })
        print(f"    {label} sc {i+1:2d}: "
              f"champ={champ['mean_biomass']:7.2f}  "
              f"ref={ref['mean_biomass']:7.2f}  "
              f"Δ={delta:+7.2f}  "
              f"frag={sc.get('fragmentation'):.2f} "
              f"shock={sc.get('shock_prob'):.2f} "
              f"K={sc.get('K'):.0f} "
              f"move={sc.get('move_cost'):.2f}")

    mean_champ  = float(np.mean(champ_scores))
    mean_ref    = float(np.mean(ref_scores))
    mean_delta  = float(np.mean([s["delta"] for s in per_scenario]))
    pct_gain    = 100.0 * mean_delta / max(abs(mean_ref), 1e-9)
    n_wins      = sum(1 for s in per_scenario if s["delta"] > 0)
    win_rate    = n_wins / max(len(per_scenario), 1)

    print(f"\n  [{label}] mean biomass: champion={mean_champ:.2f}  reference={mean_ref:.2f}")
    print(f"  [{label}] mean Δ={mean_delta:+.2f} ({pct_gain:+.1f}%)")
    print(f"  [{label}] champion wins: {n_wins}/{len(scenarios)} ({win_rate:.1%})")

    tests: Dict = {}
    if len(champ_scores) >= 3:
        try:
            stat, pval = wilcoxon_test(champ_scores, ref_scores)
            d = cohens_d(champ_scores, ref_scores)
            sig = ("***" if pval < 0.001 else
                   ("**" if pval < 0.01 else
                    ("*" if pval < 0.05 else "n.s.")))
            tests = {"wilcoxon_stat": stat, "p_value": pval, "cohens_d": d}
            print(f"  [{label}] Wilcoxon: stat={stat:.4f}  p={pval:.6f}  ({sig})")
            print(f"  [{label}] Cohen's d={d:.4f}  "
                  f"({'negligible' if abs(d) < 0.2 else 'small' if abs(d) < 0.5 else 'medium' if abs(d) < 0.8 else 'large'})")
        except Exception as exc:
            print(f"  [{label}] Statistical tests skipped: {exc}")
    else:
        print(f"  [{label}] Statistical tests skipped: n < 3.")

    return {
        "label": label,
        "n_scenarios": len(scenarios),
        "n_eval_per_scenario": n_eval,
        "per_scenario": per_scenario,
        "aggregate": {
            "mean_champ": mean_champ,
            "mean_ref":   mean_ref,
            "mean_delta": mean_delta,
            "pct_gain":   pct_gain,
            "n_wins":     n_wins,
            "n_scenarios": len(scenarios),
            "win_rate":   win_rate,
        },
        "statistical_tests": tests,
    }


def run_phase2_evaluation(
    champion_genome: List[float],
    steps: int = TRAIN_STEPS,
    smoke: bool = False,
) -> Dict[str, Any]:
    """Evaluate champion on OOD and in-distribution scenarios."""
    print("\n" + "=" * 70)
    print("Phase 2 — OOD & In-distribution Evaluation")
    print(f"  Champion genome: risk={champion_genome[0]:.4f}, "
          f"dispersal={champion_genome[1]:.4f}")
    print(f"  Reference genome: risk={REFERENCE_GENOME[0]}, "
          f"dispersal={REFERENCE_GENOME[1]}")
    print(f"  Evaluation steps: {steps}, n_eval: {OOD_N_EVAL}")
    print(f"\n  OOD factor ranges (training anchor: "
          f"frag={ANCHOR_SCENARIO['fragmentation']}, "
          f"shock={ANCHOR_SCENARIO['shock_prob']}, "
          f"K={ANCHOR_SCENARIO['K']}, "
          f"move={ANCHOR_SCENARIO['move_cost']})")
    print(f"    fragmentation ∈ {{0.65, 0.80}}  [training: 0.2]")
    print(f"    shock_prob    ∈ {{0.35, 0.50}}  [training: 0.05]")
    print(f"    K             ∈ {{200, 400, 600}}  [training: 80]")
    print(f"    move_cost     ∈ {{0.45, 0.60}}  [training: 0.1]")
    print(f"  {len(OOD_SCENARIOS)} OOD scenarios  ×  {OOD_N_EVAL} episodes each")

    # --- OOD evaluation ---
    ood_result = _evaluate_on_scenarios(
        champion_genome=champion_genome,
        scenarios=OOD_SCENARIOS,
        label="OOD",
        steps=steps,
        n_eval=OOD_N_EVAL,
        seed_offset=10000,
        smoke=smoke,
    )

    # --- In-distribution sanity check ---
    print(f"\n  In-distribution sanity check: {len(IN_DIST_SCENARIOS)} near-anchor scenarios")
    id_result = _evaluate_on_scenarios(
        champion_genome=champion_genome,
        scenarios=IN_DIST_SCENARIOS,
        label="InDist",
        steps=steps,
        n_eval=OOD_N_EVAL,
        seed_offset=20000,
        smoke=smoke,
    )

    # --- Comparison summary ---
    print("\n  === OOD vs In-distribution Comparison ===")
    print(f"  In-dist  win rate: {id_result['aggregate']['win_rate']:.1%}  "
          f"gain: {id_result['aggregate']['pct_gain']:+.1f}%  "
          f"d={id_result['statistical_tests'].get('cohens_d', float('nan')):.4f}")
    print(f"  OOD      win rate: {ood_result['aggregate']['win_rate']:.1%}  "
          f"gain: {ood_result['aggregate']['pct_gain']:+.1f}%  "
          f"d={ood_result['statistical_tests'].get('cohens_d', float('nan')):.4f}")

    # --- Save CSV ---
    csv_path = results_path(EXPERIMENT_NAME, "ood_per_scenario.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["split", "sc_id", "frag", "shock", "K", "move_cost",
                    "champ_biomass", "ref_biomass", "delta", "win"])
        for split, res in [("ood", ood_result), ("in_dist", id_result)]:
            for i, s in enumerate(res["per_scenario"]):
                sc = s["scenario"]
                w.writerow([split, i,
                             sc.get("fragmentation"), sc.get("shock_prob"),
                             sc.get("K"), sc.get("move_cost"),
                             s["champ_biomass"], s["ref_biomass"],
                             s["delta"], int(s["delta"] > 0)])
    print(f"\n  CSV → experiments/results/{EXPERIMENT_NAME}/ood_per_scenario.csv")

    phase2_summary = {
        "champion_genome": list(champion_genome),
        "reference_genome": list(REFERENCE_GENOME),
        "anchor_scenario": ANCHOR_SCENARIO,
        "ood_scenarios": OOD_SCENARIOS,
        "in_dist_scenarios": IN_DIST_SCENARIOS,
        "ood_result": ood_result,
        "in_dist_result": id_result,
    }
    save_json(results_path(EXPERIMENT_NAME, "phase2_summary.json"), phase2_summary)
    print(f"  Phase 2 summary → experiments/results/{EXPERIMENT_NAME}/phase2_summary.json")

    _plot_ood_results(ood_result, id_result)
    return phase2_summary


def _plot_ood_results(
    ood_result: Dict[str, Any],
    id_result: Dict[str, Any],
) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(13, 4))

        for ax, res, title in [
            (axes[0], ood_result, "OOD scenarios"),
            (axes[1], id_result,  "In-distribution scenarios"),
        ]:
            per = res["per_scenario"]
            ids = range(len(per))
            champ = [s["champ_biomass"] for s in per]
            ref   = [s["ref_biomass"]   for s in per]
            deltas = [s["delta"]        for s in per]

            agg   = res["aggregate"]
            tests = res.get("statistical_tests", {})
            d_str = f"d={tests.get('cohens_d', float('nan')):.3f}"
            p_str = f"p={tests.get('p_value', float('nan')):.4f}"

            ax.plot(ids, champ, "o-", color="steelblue",
                    label=f"Champion (μ={agg['mean_champ']:.1f})")
            ax.plot(ids, ref,   "s--", color="gray",
                    label=f"Reference (μ={agg['mean_ref']:.1f})")
            ax.fill_between(
                list(ids), ref, champ,
                where=[c >= r for c, r in zip(champ, ref)],
                alpha=0.2, color="steelblue",
            )
            ax.fill_between(
                list(ids), ref, champ,
                where=[c < r for c, r in zip(champ, ref)],
                alpha=0.2, color="red",
            )
            ax.set_xlabel("Scenario index")
            ax.set_ylabel("Mean prey biomass")
            ax.set_title(
                f"{title}\n"
                f"Wins: {agg['n_wins']}/{agg['n_scenarios']} ({agg['win_rate']:.0%})  "
                f"{d_str}  {p_str}"
            )
            ax.legend(fontsize=8)
            ax.grid(True, alpha=0.3)

        fig.suptitle(
            "True OOD Generalization Test — Champion evolved on single anchor scenario",
            fontsize=10,
        )
        fig.tight_layout()

        path = results_path(EXPERIMENT_NAME, "figs", "ood_evaluation.pdf")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"  OOD plot → {path}")
    except Exception as exc:
        print(f"  (OOD plot skipped: {exc})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Exp C — True OOD generalization test (reviewer CRITICAL #3)"
    )
    p.add_argument("--smoke",     action="store_true",
                   help="Smoke test: 3 training runs, 2 OOD scenarios, 2 episodes")
    p.add_argument("--resume",    action="store_true",
                   help="Resume Phase 1 from checkpoint")
    p.add_argument("--eval-only", action="store_true",
                   help="Skip Phase 1; load saved champion from training_summary.json")
    p.add_argument("--n-train-runs", type=int, default=N_TRAIN_RUNS,
                   help=f"Phase 1 independent runs (default: {N_TRAIN_RUNS})")
    p.add_argument("--pop",       type=int, default=TRAIN_POP)
    p.add_argument("--ngen",      type=int, default=TRAIN_NGEN)
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    # --- Phase 1 ---
    if args.eval_only:
        # Load saved champion
        summary_path = results_path(EXPERIMENT_NAME, "training_summary.json")
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                ts = json.load(f)
            champion_genome = ts["selected_champion"]
            print(f"  Loaded saved champion: {champion_genome}")
        else:
            print("  No saved champion found. Running Phase 1 first...")
            champion_genome, _ = run_phase1_training(
                n_runs=args.n_train_runs,
                pop_size=args.pop,
                n_gen=args.ngen,
                resume=args.resume,
                smoke=args.smoke,
            )
    else:
        champion_genome, _ = run_phase1_training(
            n_runs=args.n_train_runs,
            pop_size=args.pop,
            n_gen=args.ngen,
            resume=args.resume,
            smoke=args.smoke,
        )

    # --- Phase 2 ---
    run_phase2_evaluation(
        champion_genome=champion_genome,
        steps=TRAIN_STEPS,
        smoke=args.smoke,
    )

    print(f"\n  All outputs in: experiments/results/{EXPERIMENT_NAME}/")


if __name__ == "__main__":
    main()
