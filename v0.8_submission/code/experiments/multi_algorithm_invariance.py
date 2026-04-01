#!/usr/bin/env python3
"""
Multi-Algorithm Contract Invariance Experiment
===============================================

PRE-SPECIFICATION (locked 2026-03-28, before any code execution):
  TAU_VALUES    = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]   (same as tau-sweep)
  N_RUNS        = 20   per optimizer per tau level          (360 total runs x 2 conditions)
  N_POLICIES    = 12   (same Pareto front size as tau-sweep)
  N_SCENARIOS   = 18   (same evaluation scenarios)
  OPTIMIZERS    = ["random", "nsga2", "moead"]
  PRIMARY_DV    = divergence_reduction = adhoc_rate - HEAS_rate per run
  COMPARISONS   = HEAS vs AdHocEntropy (semantic) + HEAS vs AdHocStep (syntactic)
  PRIMARY_TEST  = Kruskal-Wallis H-test (DV ~ optimizer); H0: invariant across optimizers
  HYPOTHESIS    = H0: contract efficacy does not vary with optimizer (p > 0.05 = PASS)
  LOCKED_DATE   = "2026-03-28"

Scientific rationale:
  If aggregation divergence is a topological property of the metric computation pipeline
  (not a consequence of optimizer algorithm choice), then the rank-reversal rate
  for HEAS and ad-hoc conditions should be approximately constant across NSGA-II,
  MOEA/D, and random search. A non-significant Kruskal-Wallis main effect confirms
  optimizer-invariance of the contract guarantee.

  Three optimizers span the key axes of variation:
    1. Random search  -- no structure; includes dominated solutions
    2. NSGA-II        -- non-dominated sorting + crowding distance diversity
    3. MOEA/D         -- scalarization-based decomposition into weight vectors

  Non-significant ANOVA confirms that contract efficacy (divergence reduction)
  is independent of solution quality and Pareto front shape.
"""

from __future__ import annotations

import json
import random
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats as scipy_stats

# =============================================================================
# PRE-SPECIFIED PARAMETERS (DO NOT MODIFY)
# =============================================================================
TAU_VALUES  = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
N_RUNS      = 20
N_SCENARIOS = 18
N_POLICIES  = 12
N_STEPS     = 150
LOCKED_DATE = "2026-03-28"

OPTIMIZERS  = ["random", "nsga2", "moead"]
POP_SIZE    = 60    # evolutionary optimizer pool
ALPHA       = 0.05  # Kruskal-Wallis significance level (exploratory)


# =============================================================================
# Arena (identical to tau_sweep_boundary.py)
# =============================================================================
class MockArena:
    def __init__(self, n_steps: int = N_STEPS, noise: float = 0.15):
        self.n_steps = n_steps
        self.noise = noise

    def run_episode(self, genes: Tuple[float, float], scenario_id: int) -> List[float]:
        risk, dispersal = genes
        x = 40.0 + scenario_id * 5.0
        K = 100.0 + scenario_id * 3.0
        r = 0.5 + scenario_id * 0.03
        biomass = []
        for _ in range(self.n_steps):
            r_eff = r * (1.0 - risk * 0.3) + dispersal * 0.2
            x = x + r_eff * x * (1.0 - x / K) - risk * 0.5 * x
            x = max(0.1, x)
            x = max(0.1, x + np.random.normal(0, self.noise * x))
            biomass.append(x)
        return biomass

    def score_policy(
        self,
        genes: Tuple[float, float],
        scenario_id: int,
        seed_offset: int = 0,
    ) -> Dict[str, float]:
        seed = scenario_id + hash(genes) % 10000 + seed_offset
        np.random.seed(seed)
        random.seed(seed)
        biomass = self.run_episode(genes, scenario_id)
        hist, _ = np.histogram(biomass, bins=10)
        p = hist / hist.sum()
        p = p[p > 0]
        entropy = float(-np.sum(p * np.log(p)) / np.log(len(p) + 1))
        return {
            "final":   biomass[-1],
            "mean":    float(np.mean(biomass)),
            "median":  float(np.median(biomass)),
            "q75":     float(np.percentile(biomass, 75)),
            "entropy": entropy,
        }

    def eval_mean(self, genes: Tuple, n_sc: int = N_SCENARIOS, seed_offset: int = 0) -> float:
        return float(np.mean([
            self.score_policy(genes, sid, seed_offset)["mean"]
            for sid in range(n_sc)
        ]))

    def eval_entropy(self, genes: Tuple, n_sc: int = N_SCENARIOS, seed_offset: int = 0) -> float:
        return float(np.mean([
            self.score_policy(genes, sid, seed_offset)["entropy"]
            for sid in range(n_sc)
        ]))


# =============================================================================
# Optimizers
# =============================================================================

def optimizer_random(
    arena: MockArena,
    n_policies: int,
    run_seed: int,
) -> List[Tuple[float, float]]:
    """Uniform random sampling — no selection pressure."""
    rng = np.random.default_rng(run_seed)
    return [
        (float(rng.uniform(0.01, 0.99)), float(rng.uniform(0.01, 0.99)))
        for _ in range(n_policies)
    ]


def optimizer_nsga2(
    arena: MockArena,
    n_policies: int,
    run_seed: int,
    pop_size: int = POP_SIZE,
) -> List[Tuple[float, float]]:
    """
    Simplified NSGA-II: evaluates a pool on two objectives (mean biomass + entropy),
    non-dominated sort -> Pareto front -> crowding-distance selection.
    """
    rng = np.random.default_rng(run_seed)
    pool = [
        (float(rng.uniform(0.01, 0.99)), float(rng.uniform(0.01, 0.99)))
        for _ in range(pop_size)
    ]

    # Evaluate on half scenarios for speed during optimization phase
    n_eval = N_SCENARIOS // 2
    obj1 = np.array([arena.eval_mean(p,    n_eval) for p in pool])  # maximise
    obj2 = np.array([arena.eval_entropy(p, n_eval) for p in pool])  # maximise

    # Non-dominated sort: count how many solutions dominate each solution
    n = len(pool)
    dominated_count = np.zeros(n, dtype=int)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            # j dominates i if j >= i on all objectives and > i on at least one
            if (obj1[j] >= obj1[i] and obj2[j] >= obj2[i] and
                    (obj1[j] > obj1[i] or obj2[j] > obj2[i])):
                dominated_count[i] += 1

    pareto_idx = [i for i in range(n) if dominated_count[i] == 0]

    if len(pareto_idx) >= n_policies:
        # Select by crowding distance
        front_o1 = obj1[pareto_idx]
        front_o2 = obj2[pareto_idx]
        cd = np.zeros(len(pareto_idx))
        for obj_vals in (front_o1, front_o2):
            order = np.argsort(obj_vals)
            rng_v = obj_vals.max() - obj_vals.min()
            if rng_v < 1e-9:
                continue
            cd[order[0]] = np.inf
            cd[order[-1]] = np.inf
            for k in range(1, len(order) - 1):
                cd[order[k]] += (obj_vals[order[k + 1]] - obj_vals[order[k - 1]]) / rng_v
        top_idx = np.argsort(cd)[::-1][:n_policies]
        return [pool[pareto_idx[i]] for i in top_idx]
    else:
        selected = [pool[i] for i in pareto_idx]
        remaining = sorted(
            [i for i in range(n) if i not in pareto_idx],
            key=lambda i: obj1[i],
            reverse=True,
        )
        selected += [pool[i] for i in remaining[: n_policies - len(selected)]]
        return selected[:n_policies]


def optimizer_moead(
    arena: MockArena,
    n_policies: int,
    run_seed: int,
) -> List[Tuple[float, float]]:
    """
    Simplified MOEA/D: n_policies evenly-spaced weight vectors, each solved by
    finding the best policy in a dense candidate grid (scalarized objective).
    Per-run Gaussian perturbation (sigma=0.05) introduces run-to-run variation.
    """
    rng = np.random.default_rng(run_seed)
    n_eval = N_SCENARIOS // 2

    # Fixed candidate grid (12x12 = 144 candidates)
    grid_size = 12
    candidates = [
        (float(r), float(d))
        for r in np.linspace(0.05, 0.95, grid_size)
        for d in np.linspace(0.05, 0.95, grid_size)
    ]

    # Evaluate all candidates once
    can_mean    = np.array([arena.eval_mean(p,    n_eval) for p in candidates])
    can_entropy = np.array([arena.eval_entropy(p, n_eval) for p in candidates])

    # Normalise
    def _norm(v: np.ndarray) -> np.ndarray:
        lo, hi = v.min(), v.max()
        return (v - lo) / (hi - lo + 1e-9)

    can_mean_n    = _norm(can_mean)
    can_entropy_n = _norm(can_entropy)

    # Evenly-spaced weight vectors
    selected = []
    for i in range(n_policies):
        w1 = i / max(n_policies - 1, 1)
        w2 = 1.0 - w1
        scores = w1 * can_mean_n + w2 * can_entropy_n
        best_idx = int(np.argmax(scores))
        r_base, d_base = candidates[best_idx]
        # Small per-run perturbation
        r = float(np.clip(r_base + rng.normal(0, 0.05), 0.01, 0.99))
        d = float(np.clip(d_base + rng.normal(0, 0.05), 0.01, 0.99))
        selected.append((r, d))

    return selected


OPTIMIZER_FNS = {
    "random": optimizer_random,
    "nsga2":  optimizer_nsga2,
    "moead":  optimizer_moead,
}


# =============================================================================
# Aggregators (two focal conditions from tau-sweep)
# =============================================================================
class Aggregator:
    name: str
    def agg_optimizer(self, m: Dict) -> float:  raise NotImplementedError
    def agg_tournament(self, m: Dict) -> float: raise NotImplementedError


class HEASAggregator(Aggregator):
    name = "HEAS"
    def agg_optimizer(self, m):  return m["mean"]
    def agg_tournament(self, m): return m["mean"]       # contract: same callable


class AdHocStep(Aggregator):
    name = "Ad-hoc-Step"
    def agg_optimizer(self, m):  return m["final"]      # syntactic divergence
    def agg_tournament(self, m): return m["mean"]


class AdHocEntropy(Aggregator):
    name = "Ad-hoc-Entropy"
    def agg_optimizer(self, m):  return m["mean"]
    def agg_tournament(self, m): return m["entropy"]    # semantic divergence


AGGREGATORS = [HEASAggregator(), AdHocStep(), AdHocEntropy()]


# =============================================================================
# Statistics
# =============================================================================
def kendall_tau(r1: list, r2: list) -> float:
    tau, _ = scipy_stats.kendalltau(r1, r2)
    return float(tau)


def rank_reversal_rate(tau: float) -> float:
    return (1.0 - tau) / 2.0


def cohen_h(p1: float, p2: float) -> float:
    p1 = max(1e-9, min(1.0 - 1e-9, p1))
    p2 = max(1e-9, min(1.0 - 1e-9, p2))
    return 2.0 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


# =============================================================================
# Core experiment: one run given a policy set
# =============================================================================
def score_one_run(
    arena: MockArena,
    policies: List[Tuple[float, float]],
    run_id: int,
) -> Dict[str, float]:
    """Return rank-reversal rate for each aggregator for a given policy set."""
    results = {}
    for agg in AGGREGATORS:
        opt_scores, tourn_scores = [], []
        for policy in policies:
            opt_s, tourn_s = [], []
            for sid in range(N_SCENARIOS):
                m_opt   = arena.score_policy(policy, sid, seed_offset=0)
                m_tourn = arena.score_policy(policy, sid, seed_offset=500 + run_id * 7)
                opt_s.append(agg.agg_optimizer(m_opt))
                tourn_s.append(agg.agg_tournament(m_tourn))
            opt_scores.append(float(np.mean(opt_s)))
            tourn_scores.append(float(np.mean(tourn_s)))

        opt_rank   = np.argsort(opt_scores)[::-1].tolist()
        tourn_rank = np.argsort(tourn_scores)[::-1].tolist()
        tau_k      = kendall_tau(opt_rank, tourn_rank)
        results[agg.name] = rank_reversal_rate(tau_k)
    return results


# =============================================================================
# One tau level: all optimizers x N_RUNS
# =============================================================================
def run_one_tau_level(tau: float) -> Dict:
    arena = MockArena(n_steps=N_STEPS, noise=tau)

    # raw[optimizer][aggregator] = list of per-run reversal rates
    raw: Dict[str, Dict[str, List[float]]] = {
        opt: {agg.name: [] for agg in AGGREGATORS}
        for opt in OPTIMIZERS
    }

    for run_id in range(N_RUNS):
        for opt_name in OPTIMIZERS:
            run_seed = run_id * 137 + hash(opt_name) % 1000 + int(tau * 100)
            policies = OPTIMIZER_FNS[opt_name](arena, N_POLICIES, run_seed)
            scores   = score_one_run(arena, policies, run_id)
            for agg_name, rrr in scores.items():
                raw[opt_name][agg_name].append(rrr)

    # --- Per-optimizer summaries -------------------------------------------
    summary: Dict[str, Dict] = {}
    for opt_name in OPTIMIZERS:
        heas_rrr = raw[opt_name]["HEAS"]
        summary[opt_name] = {}
        for agg in AGGREGATORS:
            rrr_list = raw[opt_name][agg.name]
            mean_r   = float(np.mean(rrr_list))
            summary[opt_name][agg.name] = {
                "mean_reversal_rate": mean_r,
                "std": float(np.std(rrr_list)),
                "raw": rrr_list,
            }
            if agg.name != "HEAS":
                # Divergence reduction = ad-hoc rate - HEAS rate (per run)
                reduction = [rrr_list[i] - heas_rrr[i] for i in range(N_RUNS)]
                summary[opt_name][f"reduction_vs_{agg.name}"] = {
                    "mean":    float(np.mean(reduction)),
                    "std":     float(np.std(reduction)),
                    "raw":     reduction,
                    "cohen_h": cohen_h(mean_r, float(np.mean(heas_rrr))),
                }

    # --- Primary test: Kruskal-Wallis on divergence reduction ---------------
    kruskal: Dict[str, Dict] = {}
    for agg in AGGREGATORS:
        if agg.name == "HEAS":
            continue
        key    = f"reduction_vs_{agg.name}"
        groups = [summary[opt][key]["raw"] for opt in OPTIMIZERS]
        stat, p = scipy_stats.kruskal(*groups)
        f_stat, f_p = scipy_stats.f_oneway(*groups)
        kruskal[key] = {
            "statistic":   float(stat),
            "p_value":     float(p),
            "anova_f":     float(f_stat),
            "anova_p":     float(f_p),
            "invariant":   bool(p > ALPHA),   # True = optimizer-invariant (PASS)
        }

    return {
        "tau":     tau,
        "summary": summary,
        "kruskal": kruskal,
    }


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    import os

    print("MULTI-ALGORITHM CONTRACT INVARIANCE EXPERIMENT")
    print(f"Pre-specified: tau in {TAU_VALUES}  |  Locked {LOCKED_DATE}")
    print(f"n_runs={N_RUNS}  n_policies={N_POLICIES}  n_scenarios={N_SCENARIOS}")
    print(f"Optimizers: {OPTIMIZERS}")
    print("H0: Contract efficacy (divergence reduction) is invariant to optimizer choice")
    print("=" * 70)

    all_results = []
    for tau in TAU_VALUES:
        print(f"\n{'='*60}\ntau = {tau:.2f}")
        r = run_one_tau_level(tau)
        all_results.append(r)

        # Console table
        print(f"\n  {'Optimizer':<12} {'HEAS%':>7} {'Entropy%':>10} {'Step%':>7}"
              f"  {'h(Ent)':>7} {'h(Step)':>8}")
        print(f"  {'-'*55}")
        for opt_name in OPTIMIZERS:
            s      = r["summary"][opt_name]
            heas_r = s["HEAS"]["mean_reversal_rate"]
            ent_r  = s["Ad-hoc-Entropy"]["mean_reversal_rate"]
            step_r = s["Ad-hoc-Step"]["mean_reversal_rate"]
            h_ent  = s["reduction_vs_Ad-hoc-Entropy"]["cohen_h"]
            h_step = s["reduction_vs_Ad-hoc-Step"]["cohen_h"]
            print(f"  {opt_name:<12} {heas_r:>7.1%} {ent_r:>10.1%} {step_r:>7.1%}"
                  f"  {h_ent:>7.3f} {h_step:>8.3f}")

        print(f"\n  Kruskal-Wallis invariance tests (H0: no optimizer main effect):")
        for key, kw in r["kruskal"].items():
            status = "PASS (invariant)" if kw["invariant"] else "FAIL (optimizer effect)"
            print(f"    {key:<35} H={kw['statistic']:.3f}  p={kw['p_value']:.4f}"
                  f"  [{status}]  ANOVA p={kw['anova_p']:.4f}")

    # --- Grand summary -------------------------------------------------------
    print("\n\n" + "=" * 70)
    print("GRAND SUMMARY: CONTRACT INVARIANCE ACROSS OPTIMIZERS")
    print(f"{'tau':>6}  {'KW p(Entropy)':>14}  {'Pass?':>16}  "
          f"{'KW p(Step)':>12}  {'Pass?':>16}")
    print("-" * 70)
    for r in all_results:
        ek = r["kruskal"].get("reduction_vs_Ad-hoc-Entropy", {})
        sk = r["kruskal"].get("reduction_vs_Ad-hoc-Step",    {})
        e_pass = "PASS (invariant)" if ek.get("invariant") else "FAIL"
        s_pass = "PASS (invariant)" if sk.get("invariant") else "FAIL"
        print(f"  {r['tau']:.2f}  {ek.get('p_value', 0):>14.4f}  {e_pass:>16}  "
              f"{sk.get('p_value', 0):>12.4f}  {s_pass:>16}")

    n_pass_e = sum(1 for r in all_results
                   if r["kruskal"].get("reduction_vs_Ad-hoc-Entropy", {}).get("invariant"))
    n_pass_s = sum(1 for r in all_results
                   if r["kruskal"].get("reduction_vs_Ad-hoc-Step",    {}).get("invariant"))
    print(f"\n=> Semantic invariance (Entropy): {n_pass_e}/{len(all_results)} tau levels PASS")
    print(f"=> Syntactic invariance  (Step):  {n_pass_s}/{len(all_results)} tau levels PASS")

    print(f"\n  Per-optimizer mean Cohen's h (across all tau levels):")
    for opt_name in OPTIMIZERS:
        h_e = np.mean([r["summary"][opt_name].get(
            "reduction_vs_Ad-hoc-Entropy", {}).get("cohen_h", 0)
            for r in all_results])
        h_s = np.mean([r["summary"][opt_name].get(
            "reduction_vs_Ad-hoc-Step", {}).get("cohen_h", 0)
            for r in all_results])
        print(f"    {opt_name:<12}: h(Entropy)={h_e:.3f}  h(Step)={h_s:.3f}")

    # --- Save ----------------------------------------------------------------
    def to_python(obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return obj

    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "multi_algorithm_invariance_results.json",
    )
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=to_python)
    print(f"\nResults saved to: {out_path}")
