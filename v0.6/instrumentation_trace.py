#!/usr/bin/env python3
"""
Instrumentation Trace: Shared-Function Baseline Metric Divergence
==================================================================

Goal: Observe exactly what happens when a shared-function (no contract)
dispatch produces divergent metrics. Document which metrics couple and
diverge under what conditions.

The 5.2% rank reversal rate in the shared-function baseline is driven by
inconsistent metric extraction across stages. This script reproduces that
failure mode in a minimal setting.

Key insight:
  - Shared-function: each stage independently extracts dict fields
    (ad-hoc, no abstraction layer)
  - HEAS contract: all stages call metrics_episode() → guaranteed consistency

Comparison:
  Policy A's rank varies across stages because the stages extract different
  metrics or fields from the same episode result dict.
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Tuple
import numpy as np
from dataclasses import dataclass


# ===========================================================================
# Mock Arena (simplified ecological simulation)
# ===========================================================================

class MockArena:
    """Minimal arena: two-parameter control (risk, dispersal) over stochastic dynamics."""

    def __init__(self, n_steps: int = 150, noise: float = 0.15):
        self.n_steps = n_steps
        self.noise = noise
        self.run_count = 0

    def run_episode(self, genes: Tuple[float, float], scenario_id: int, seed_offset: int = 0) -> Dict[str, Any]:
        """Run one episode, return raw metrics dict (before extraction)."""
        self.run_count += 1
        risk, dispersal = genes

        # Deterministic seed for reproducibility
        seed = scenario_id + hash(genes) % 10000 + seed_offset
        rng = np.random.default_rng(seed)

        # Initial state
        x = 40.0 + scenario_id * 5.0
        K = 100.0 + scenario_id * 3.0
        r = 0.5 + scenario_id * 0.03

        # Accumulate trajectory
        biomass = []
        for _ in range(self.n_steps):
            r_eff = r * (1.0 - risk * 0.3) + dispersal * 0.2
            x = x + r_eff * x * (1.0 - x / K) - risk * 0.5 * x
            x = max(0.1, x)
            x = x + rng.normal(0, self.noise * x)
            x = max(0.1, x)
            biomass.append(float(x))

        # Compute histogram-based entropy
        hist, _ = np.histogram(biomass, bins=10)
        p = hist / hist.sum()
        p = p[p > 0]
        entropy = float(-np.sum(p * np.log(p)) / np.log(len(p) + 1)) if len(p) > 0 else 0.0

        # Return raw episode metrics (what would be stored)
        return {
            "final_biomass": biomass[-1],
            "mean_biomass": float(np.mean(biomass)),
            "median_biomass": float(np.median(biomass)),
            "q75_biomass": float(np.percentile(biomass, 75)),
            "entropy": entropy,
            "std_biomass": float(np.std(biomass)),
            "min_biomass": float(np.min(biomass)),
            "max_biomass": float(np.max(biomass)),
            "cv_biomass": float(np.std(biomass) / max(np.mean(biomass), 1e-9)),
            "trajectory_length": len(biomass),
        }


# ===========================================================================
# Extraction Strategies: HEAS vs Shared-Function
# ===========================================================================

def heas_metrics_episode(episode_dict: Dict[str, Any]) -> float:
    """HEAS contract: consistent callable applied uniformly."""
    return episode_dict["mean_biomass"]


def shared_function_optimizer_extract(episode_dict: Dict[str, Any]) -> float:
    """Optimizer stage: extracts 'mean_biomass' (intended primary metric)."""
    return episode_dict["mean_biomass"]


def shared_function_tournament_extract(episode_dict: Dict[str, Any]) -> float:
    """Tournament stage: extracts 'median_biomass' (different field, meant to be robust)."""
    # This is a REAL divergence: tournament uses a different metric than optimizer
    return episode_dict["median_biomass"]


def shared_function_inference_extract(episode_dict: Dict[str, Any]) -> float:
    """Inference stage: extracts 'q75_biomass' (percentile, meant to be tail-robust)."""
    # Another divergence: inference uses yet another field
    return episode_dict["q75_biomass"]


# ===========================================================================
# Policy Evaluation and Ranking
# ===========================================================================

def evaluate_policy_single_scenario(
    arena: MockArena,
    policy: Tuple[float, float],
    scenario_id: int,
    seed_offset: int = 0,
) -> Dict[str, Any]:
    """Evaluate one policy in one scenario; return raw episode metrics."""
    return arena.run_episode(policy, scenario_id, seed_offset)


def evaluate_policy_across_scenarios(
    arena: MockArena,
    policy: Tuple[float, float],
    n_scenarios: int = 18,
    seed_offset: int = 0,
) -> Dict[str, float]:
    """Evaluate policy across scenarios; return averages."""
    results = []
    for sid in range(n_scenarios):
        ep_metrics = evaluate_policy_single_scenario(arena, policy, sid, seed_offset)
        results.append(ep_metrics)

    # Average all fields across scenarios
    avg_metrics = {}
    for key in results[0].keys():
        if key != "trajectory_length":
            vals = [r[key] for r in results]
            avg_metrics[key] = float(np.mean(vals))
        else:
            avg_metrics[key] = results[0][key]

    return avg_metrics


# ===========================================================================
# Stage Extraction and Ranking
# ===========================================================================

@dataclass
class RankingResult:
    """Result of evaluating a policy set under one extraction strategy."""
    stage_name: str
    extract_fn_name: str
    policies: List[Tuple[float, float]]
    metric_values: List[float]  # One per policy
    ranking: List[int]  # Indices sorted by metric (descending)

    def rank_of_policy(self, policy_idx: int) -> int:
        """Return the rank (0=best) of a policy by its index."""
        return list(self.ranking).index(policy_idx)


def stage_evaluation(
    arena: MockArena,
    policies: List[Tuple[float, float]],
    stage_name: str,
    extract_fn,
    n_scenarios: int = 18,
    seed_offset: int = 0,
) -> RankingResult:
    """
    Evaluate all policies in one stage using a specific extraction function.
    Return ranking results.
    """
    metric_values = []

    for policy in policies:
        # Evaluate across scenarios
        avg_metrics = evaluate_policy_across_scenarios(
            arena, policy, n_scenarios, seed_offset
        )
        # Extract the metric used by this stage
        metric_val = extract_fn(avg_metrics)
        metric_values.append(metric_val)

    # Rank: highest metric is best (rank 0)
    ranking = np.argsort(metric_values)[::-1].tolist()

    return RankingResult(
        stage_name=stage_name,
        extract_fn_name=extract_fn.__name__,
        policies=policies,
        metric_values=metric_values,
        ranking=ranking,
    )


# ===========================================================================
# Core Instrumentation: Compare Stages
# ===========================================================================

def run_instrumentation_trace(
    n_policies: int = 12,
    n_scenarios: int = 18,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Main instrumentation: generate a policy set, evaluate under three different
    extraction strategies (optimizer, tournament, inference), and track how ranks
    diverge.
    """

    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Generate a policy set (two-dimensional: risk × dispersal)
    policies = [
        (float(rng.uniform(0.01, 0.99)), float(rng.uniform(0.01, 0.99)))
        for _ in range(n_policies)
    ]

    print("\n" + "=" * 80)
    print("INSTRUMENTATION TRACE: SHARED-FUNCTION METRIC DIVERGENCE")
    print("=" * 80)
    print(f"\nSetup:")
    print(f"  Policies: {n_policies}")
    print(f"  Scenarios: {n_scenarios}")
    print(f"  Policy set (risk, dispersal):")
    for i, (r, d) in enumerate(policies):
        print(f"    [{i:2d}] risk={r:.3f}  dispersal={d:.3f}")

    # Create arena
    arena = MockArena(n_steps=150, noise=0.15)

    # Condition 1: HEAS (consistent extraction)
    print(f"\n{'-' * 80}")
    print("CONDITION 1: HEAS (contract-based, consistent extraction)")
    print(f"{'-' * 80}")

    heas_result = stage_evaluation(
        arena, policies,
        stage_name="HEAS",
        extract_fn=heas_metrics_episode,
        n_scenarios=n_scenarios,
        seed_offset=0,
    )

    print(f"\nHEAS Rankings (metric: mean_biomass):")
    print(f"  {'Rank':<5} {'Policy#':<8} {'Metric':<12} {'(risk, dispersal)':<30}")
    print(f"  {'-' * 60}")
    for rank, idx in enumerate(heas_result.ranking):
        r, d = heas_result.policies[idx]
        val = heas_result.metric_values[idx]
        print(f"  {rank:<5} {idx:<8} {val:<12.6f} ({r:.3f}, {d:.3f})")

    # Condition 2: Shared-function baseline (three different extractions)
    print(f"\n{'-' * 80}")
    print("CONDITION 2: SHARED-FUNCTION BASELINE")
    print(f"Each stage independently extracts a different metric field")
    print(f"{'-' * 80}")

    stages = [
        ("Optimizer", shared_function_optimizer_extract, 0),
        ("Tournament", shared_function_tournament_extract, 500),
        ("Inference", shared_function_inference_extract, 1000),
    ]

    stage_results = {}
    for stage_name, extract_fn, seed_offset in stages:
        result = stage_evaluation(
            arena, policies,
            stage_name=stage_name,
            extract_fn=extract_fn,
            n_scenarios=n_scenarios,
            seed_offset=seed_offset,
        )
        stage_results[stage_name] = result

        print(f"\n{stage_name} Stage Rankings (metric: {extract_fn.__name__}):")
        print(f"  {'Rank':<5} {'Policy#':<8} {'Metric':<12} {'(risk, dispersal)':<30}")
        print(f"  {'-' * 60}")
        for rank, idx in enumerate(result.ranking):
            r, d = result.policies[idx]
            val = result.metric_values[idx]
            print(f"  {rank:<5} {idx:<8} {val:<12.6f} ({r:.3f}, {d:.3f})")

    # ===========================================================================
    # ANALYSIS: Where do metrics diverge?
    # ===========================================================================

    print(f"\n{'-' * 80}")
    print("METRIC VALUE DIVERGENCE ANALYSIS")
    print(f"{'-' * 80}")

    # Compute Kendall tau for each pair of stages
    def kendall_tau_for_stages(r1: RankingResult, r2: RankingResult) -> float:
        """Compute Kendall tau between two ranking results."""
        # Both use same policy order, so we rank-encode them
        ranks1 = np.zeros(len(r1.ranking), dtype=int)
        ranks2 = np.zeros(len(r2.ranking), dtype=int)

        for rank, policy_idx in enumerate(r1.ranking):
            ranks1[policy_idx] = rank
        for rank, policy_idx in enumerate(r2.ranking):
            ranks2[policy_idx] = rank

        # Kendall tau
        tau, _ = scipy.stats.kendalltau(ranks1, ranks2)
        return float(tau)

    import scipy.stats

    all_results = {"HEAS": heas_result}
    all_results.update(stage_results)

    print(f"\nKendall τ correlation between stage rankings:")
    print(f"  {'Comparison':<40} {'τ':<10} {'Divergence Rate':<15}")
    print(f"  {'-' * 70}")

    divergence_rates = {}
    for s1_name in list(all_results.keys()):
        for s2_name in list(all_results.keys()):
            if s1_name >= s2_name:
                continue
            r1, r2 = all_results[s1_name], all_results[s2_name]
            tau = kendall_tau_for_stages(r1, r2)
            div_rate = (1.0 - tau) / 2.0  # Convert tau to reversal rate
            comparison = f"{s1_name} vs {s2_name}"
            divergence_rates[comparison] = div_rate
            print(f"  {comparison:<40} {tau:>9.4f}  {div_rate:>13.1%}")

    # Metric value divergence (even if rankings are the same, VALUES differ)
    print(f"\nMetric VALUE divergence (same policy, different extraction fields):")
    print(f"  {'Policy#':<8} {'HEAS':<12} {'Optimizer':<12} {'Tournament':<12} {'Inference':<12} {'Max Spread':<12}")
    print(f"  {'-' * 80}")

    value_spreads = []
    for policy_idx in range(n_policies):
        v_heas = heas_result.metric_values[policy_idx]
        v_opt = stage_results["Optimizer"].metric_values[policy_idx]
        v_tourn = stage_results["Tournament"].metric_values[policy_idx]
        v_inf = stage_results["Inference"].metric_values[policy_idx]

        max_val = max(v_heas, v_opt, v_tourn, v_inf)
        min_val = min(v_heas, v_opt, v_tourn, v_inf)
        spread = max_val - min_val
        spread_pct = 100.0 * spread / max(min_val, 1e-9)

        value_spreads.append({
            "policy_idx": policy_idx,
            "heas": v_heas,
            "opt": v_opt,
            "tourn": v_tourn,
            "inf": v_inf,
            "spread": spread,
            "spread_pct": spread_pct,
        })

        print(f"  {policy_idx:<8} {v_heas:<12.6f} {v_opt:<12.6f} {v_tourn:<12.6f} {v_inf:<12.6f} {spread:<12.6f} ({spread_pct:.1f}%)")

    # Sort by value spread
    value_spreads.sort(key=lambda x: x["spread_pct"], reverse=True)

    print(f"\n  Average metric value divergence (across all policies):")
    avg_spread = np.mean([s["spread"] for s in value_spreads])
    avg_spread_pct = np.mean([s["spread_pct"] for s in value_spreads])
    print(f"    Mean absolute spread: {avg_spread:.6f}")
    print(f"    Mean relative spread: {avg_spread_pct:.2f}%")

    # ===========================================================================
    # CONCRETE EXAMPLES: Policies with rank reversals
    # ===========================================================================

    print(f"\n{'-' * 80}")
    print("CONCRETE EXAMPLES: SAME POLICY, DIFFERENT RANKS")
    print(f"{'-' * 80}")

    examples = []
    for policy_idx in range(n_policies):
        # Get ranks in each stage
        heas_rank = heas_result.rank_of_policy(policy_idx)
        opt_rank = stage_results["Optimizer"].rank_of_policy(policy_idx)
        tourn_rank = stage_results["Tournament"].rank_of_policy(policy_idx)
        inf_rank = stage_results["Inference"].rank_of_policy(policy_idx)

        rank_spread = max(heas_rank, opt_rank, tourn_rank, inf_rank) - \
                      min(heas_rank, opt_rank, tourn_rank, inf_rank)

        if rank_spread > 0:
            examples.append({
                "policy_idx": policy_idx,
                "policy": policies[policy_idx],
                "heas_rank": heas_rank,
                "optimizer_rank": opt_rank,
                "tournament_rank": tourn_rank,
                "inference_rank": inf_rank,
                "rank_spread": rank_spread,
                "heas_metric": heas_result.metric_values[policy_idx],
                "opt_metric": stage_results["Optimizer"].metric_values[policy_idx],
                "tourn_metric": stage_results["Tournament"].metric_values[policy_idx],
                "inf_metric": stage_results["Inference"].metric_values[policy_idx],
            })

    # Sort by rank spread (most divergent first)
    examples.sort(key=lambda x: x["rank_spread"], reverse=True)

    print(f"\nTop 5 most-divergent policies (by rank spread across stages):\n")
    for i, ex in enumerate(examples[:5]):
        r, d = ex["policy"]
        print(f"Policy [{ex['policy_idx']:2d}] (risk={r:.3f}, dispersal={d:.3f})")
        print(f"  HEAS:      rank={ex['heas_rank']:<3}  metric={ex['heas_metric']:<10.6f} (mean_biomass)")
        print(f"  Optimizer: rank={ex['optimizer_rank']:<3}  metric={ex['opt_metric']:<10.6f} (mean_biomass)")
        print(f"  Tournament: rank={ex['tournament_rank']:<3}  metric={ex['tourn_metric']:<10.6f} (median_biomass)")
        print(f"  Inference: rank={ex['inference_rank']:<3}  metric={ex['inf_metric']:<10.6f} (q75_biomass)")
        print(f"  → Rank spread: {ex['rank_spread']}")
        print()

    # ===========================================================================
    # Mechanism: Why did these metrics diverge?
    # ===========================================================================

    print(f"{'-' * 80}")
    print("MECHANISM ANALYSIS")
    print(f"{'-' * 80}")

    print(f"""
Observation:
  The same policy achieves DIFFERENT ranks across stages because each stage
  extracts a DIFFERENT metric field from the episode results dict.

Why metrics diverge:
  1. HEAS Stage (control): Uses mean_biomass across all scenarios
  2. Optimizer Stage: Uses mean_biomass (same as HEAS, should match)
  3. Tournament Stage: Uses median_biomass (more robust to outliers)
  4. Inference Stage: Uses q75_biomass (tail-robust, conservative)

The metrics diverge because:
  - mean_biomass: Affected by all values (including rare extremes)
  - median_biomass: Central tendency (50th percentile)
  - q75_biomass: Tail behavior (75th percentile, conservative)

For a policy with high variance in biomass trajectories:
  - mean_biomass might be pulled up by lucky runs
  - median_biomass would be lower (ignores extremes)
  - q75_biomass would be even lower (conservative tail)

Result: The policy ranks differ because the metrics emphasize different
aspects of the trajectory distribution.
""")

    # ===========================================================================
    # Summary statistics
    # ===========================================================================

    summary = {
        "n_policies": n_policies,
        "n_scenarios": n_scenarios,
        "seed": seed,
        "heas_ranking": heas_result.ranking,
        "optimizer_ranking": stage_results["Optimizer"].ranking,
        "tournament_ranking": stage_results["Tournament"].ranking,
        "inference_ranking": stage_results["Inference"].ranking,
        "divergence_rates": divergence_rates,
        "examples": examples,
        "arena_runs": arena.run_count,
    }

    return summary


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    result = run_instrumentation_trace(
        n_policies=12,
        n_scenarios=18,
        seed=42,
    )

    # Save results
    output_path = "/sessions/zen-hopeful-noether/mnt/heas/v0.5/instrumentation_trace_output.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'=' * 80}")
    print(f"Results saved to: {output_path}")
    print(f"Total arena evaluations: {result['arena_runs']}")
    print(f"{'=' * 80}\n")
