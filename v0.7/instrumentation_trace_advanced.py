#!/usr/bin/env python3
"""
Instrumentation Trace (Advanced): NSGA-II Rank Reversal Scenario
================================================================

Goal: Reproduce the 5.2% rank reversal rate observed in the shared-function
baseline under NSGA-II. The key is evaluating policies on DIFFERENT SUBSETS
of scenarios across stages (or using DIFFERENT SEED OFFSETS), which breaks
monotonicity and allows ranking to change.

Key insight from the 5.2% finding:
  - Optimizer stage: Evolves against scenario subset A
  - Tournament stage: Evaluates policies on scenario subset B
  - Inference stage: Evaluates on scenario subset C

When subsets don't perfectly overlap, the same metric extraction (e.g., mean)
on different subsets → different orderings.

This script creates that scenario explicitly.
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, List, Tuple
import numpy as np
from dataclasses import dataclass
import scipy.stats


# ===========================================================================
# Mock Arena (from instrumentation_trace.py)
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

        # Return raw episode metrics
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
# Key scenario-based evaluation
# ===========================================================================

def evaluate_policy_on_scenario_set(
    arena: MockArena,
    policy: Tuple[float, float],
    scenario_ids: List[int],
    seed_offset: int = 0,
) -> float:
    """
    Evaluate policy on a given subset of scenarios.
    Return the mean biomass averaged over that subset.
    """
    metrics = []
    for sid in scenario_ids:
        ep = arena.run_episode(policy, sid, seed_offset)
        metrics.append(ep["mean_biomass"])
    return float(np.mean(metrics))


@dataclass
class StageResult:
    stage_name: str
    scenario_ids: List[int]
    policies: List[Tuple[float, float]]
    metric_values: List[float]
    ranking: List[int]

    def rank_of_policy(self, policy_idx: int) -> int:
        return list(self.ranking).index(policy_idx)


def run_advanced_instrumentation(
    n_policies: int = 12,
    n_total_scenarios: int = 18,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Main advanced instrumentation: evaluate policies on different scenario
    subsets in each stage, causing ranking divergence.

    Scenario design:
      - Optimizer: scenarios 0-5 (6 scenarios)
      - Tournament: scenarios 6-11 (6 scenarios, different subset)
      - Inference: scenarios 12-17 (6 scenarios, different subset)
    """

    rng = np.random.default_rng(seed)
    random.seed(seed)

    # Generate policy set
    policies = [
        (float(rng.uniform(0.01, 0.99)), float(rng.uniform(0.01, 0.99)))
        for _ in range(n_policies)
    ]

    print("\n" + "=" * 90)
    print("INSTRUMENTATION TRACE (ADVANCED): RANK REVERSAL VIA SCENARIO DIVERGENCE")
    print("=" * 90)
    print(f"\nSetup:")
    print(f"  Policies: {n_policies}")
    print(f"  Total scenarios: {n_total_scenarios}")
    print(f"  Scenario distribution:")
    print(f"    Optimizer stage: scenarios 0-5 (6 scenarios)")
    print(f"    Tournament stage: scenarios 6-11 (6 scenarios)")
    print(f"    Inference stage: scenarios 12-17 (6 scenarios)")
    print(f"\n  Policy set (risk, dispersal):")
    for i, (r, d) in enumerate(policies):
        print(f"    [{i:2d}] risk={r:.3f}  dispersal={d:.3f}")

    # Create arena
    arena = MockArena(n_steps=150, noise=0.15)

    # Define scenario subsets for each stage
    opt_scenarios = list(range(0, 6))
    tourn_scenarios = list(range(6, 12))
    inf_scenarios = list(range(12, 18))

    # ===========================================================================
    # Stage 1: Optimizer (evaluates on scenarios 0-5)
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print(f"STAGE 1: OPTIMIZER (evaluates on scenarios {opt_scenarios})")
    print(f"{'-' * 90}")

    opt_metrics = []
    for policy in policies:
        val = evaluate_policy_on_scenario_set(arena, policy, opt_scenarios, seed_offset=0)
        opt_metrics.append(val)

    opt_ranking = np.argsort(opt_metrics)[::-1].tolist()
    opt_result = StageResult(
        stage_name="Optimizer",
        scenario_ids=opt_scenarios,
        policies=policies,
        metric_values=opt_metrics,
        ranking=opt_ranking,
    )

    print(f"\nOptimizer Rankings:")
    print(f"  {'Rank':<5} {'Policy#':<8} {'Mean Biomass':<15} {'(risk, dispersal)':<30}")
    print(f"  {'-' * 65}")
    for rank, idx in enumerate(opt_ranking):
        r, d = policies[idx]
        val = opt_metrics[idx]
        print(f"  {rank:<5} {idx:<8} {val:<15.6f} ({r:.3f}, {d:.3f})")

    # ===========================================================================
    # Stage 2: Tournament (evaluates on scenarios 6-11)
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print(f"STAGE 2: TOURNAMENT (evaluates on scenarios {tourn_scenarios})")
    print(f"{'-' * 90}")

    tourn_metrics = []
    for policy in policies:
        val = evaluate_policy_on_scenario_set(arena, policy, tourn_scenarios, seed_offset=500)
        tourn_metrics.append(val)

    tourn_ranking = np.argsort(tourn_metrics)[::-1].tolist()
    tourn_result = StageResult(
        stage_name="Tournament",
        scenario_ids=tourn_scenarios,
        policies=policies,
        metric_values=tourn_metrics,
        ranking=tourn_ranking,
    )

    print(f"\nTournament Rankings:")
    print(f"  {'Rank':<5} {'Policy#':<8} {'Mean Biomass':<15} {'(risk, dispersal)':<30}")
    print(f"  {'-' * 65}")
    for rank, idx in enumerate(tourn_ranking):
        r, d = policies[idx]
        val = tourn_metrics[idx]
        print(f"  {rank:<5} {idx:<8} {val:<15.6f} ({r:.3f}, {d:.3f})")

    # ===========================================================================
    # Stage 3: Inference (evaluates on scenarios 12-17)
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print(f"STAGE 3: INFERENCE (evaluates on scenarios {inf_scenarios})")
    print(f"{'-' * 90}")

    inf_metrics = []
    for policy in policies:
        val = evaluate_policy_on_scenario_set(arena, policy, inf_scenarios, seed_offset=1000)
        inf_metrics.append(val)

    inf_ranking = np.argsort(inf_metrics)[::-1].tolist()
    inf_result = StageResult(
        stage_name="Inference",
        scenario_ids=inf_scenarios,
        policies=policies,
        metric_values=inf_metrics,
        ranking=inf_ranking,
    )

    print(f"\nInference Rankings:")
    print(f"  {'Rank':<5} {'Policy#':<8} {'Mean Biomass':<15} {'(risk, dispersal)':<30}")
    print(f"  {'-' * 65}")
    for rank, idx in enumerate(inf_ranking):
        r, d = policies[idx]
        val = inf_metrics[idx]
        print(f"  {rank:<5} {idx:<8} {val:<15.6f} ({r:.3f}, {d:.3f})")

    # ===========================================================================
    # RANK DIVERGENCE ANALYSIS
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print("RANK DIVERGENCE ANALYSIS (KENDALL TAU)")
    print(f"{'-' * 90}")

    def kendall_tau_for_stages(r1: StageResult, r2: StageResult) -> float:
        ranks1 = np.zeros(len(r1.ranking), dtype=int)
        ranks2 = np.zeros(len(r2.ranking), dtype=int)
        for rank, policy_idx in enumerate(r1.ranking):
            ranks1[policy_idx] = rank
        for rank, policy_idx in enumerate(r2.ranking):
            ranks2[policy_idx] = rank
        tau, _ = scipy.stats.kendalltau(ranks1, ranks2)
        return float(tau)

    all_stages = [opt_result, tourn_result, inf_result]
    stage_pairs = [
        (opt_result, tourn_result),
        (opt_result, inf_result),
        (tourn_result, inf_result),
    ]

    print(f"\nKendall τ correlation between stage rankings:")
    print(f"  {'Comparison':<40} {'τ':<10} {'Divergence Rate':<15}")
    print(f"  {'-' * 70}")

    divergence_rates = {}
    for r1, r2 in stage_pairs:
        tau = kendall_tau_for_stages(r1, r2)
        div_rate = (1.0 - tau) / 2.0
        comparison = f"{r1.stage_name} vs {r2.stage_name}"
        divergence_rates[comparison] = div_rate
        print(f"  {comparison:<40} {tau:>9.4f}  {div_rate:>13.1%}")

    # ===========================================================================
    # CONCRETE RANK REVERSALS
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print("CONCRETE RANK REVERSALS: SAME POLICY, DIFFERENT RANKS ACROSS STAGES")
    print(f"{'-' * 90}")

    reversals = []
    for policy_idx in range(n_policies):
        opt_rank = opt_result.rank_of_policy(policy_idx)
        tourn_rank = tourn_result.rank_of_policy(policy_idx)
        inf_rank = inf_result.rank_of_policy(policy_idx)

        rank_spread = max(opt_rank, tourn_rank, inf_rank) - min(opt_rank, tourn_rank, inf_rank)

        if rank_spread > 0:
            reversals.append({
                "policy_idx": policy_idx,
                "policy": policies[policy_idx],
                "opt_rank": opt_rank,
                "tourn_rank": tourn_rank,
                "inf_rank": inf_rank,
                "rank_spread": rank_spread,
                "opt_metric": opt_metrics[policy_idx],
                "tourn_metric": tourn_metrics[policy_idx],
                "inf_metric": inf_metrics[policy_idx],
            })

    reversals.sort(key=lambda x: x["rank_spread"], reverse=True)

    print(f"\nPolicies with rank reversals (top 10):\n")
    for i, rev in enumerate(reversals[:10]):
        r, d = rev["policy"]
        print(f"Policy [{rev['policy_idx']:2d}] (risk={r:.3f}, dispersal={d:.3f})")
        print(f"  Optimizer:   rank={rev['opt_rank']:<3}  metric={rev['opt_metric']:<10.6f}")
        print(f"  Tournament:  rank={rev['tourn_rank']:<3}  metric={rev['tourn_metric']:<10.6f}")
        print(f"  Inference:   rank={rev['inf_rank']:<3}  metric={rev['inf_metric']:<10.6f}")
        print(f"  → Rank spread: {rev['rank_spread']}")
        print()

    # Summary statistics
    reversal_rate = len(reversals) / n_policies
    print(f"Reversal Summary:")
    print(f"  Policies with at least one rank divergence: {len(reversals)}/{n_policies} ({reversal_rate:.1%})")

    # ===========================================================================
    # MECHANISM EXPLANATION
    # ===========================================================================

    print(f"\n{'-' * 90}")
    print("MECHANISM EXPLANATION")
    print(f"{'-' * 90}")

    print(f"""
The rank reversals occur because:

1. SHARED-FUNCTION BASELINE (no abstraction):
   - Each stage independently evaluates policies on a different scenario subset
   - Each stage extracts the same metric (mean_biomass) from its episode results
   - But the scenarios are DIFFERENT, so the underlying values differ

2. Example from the data:
   Policy A in Optimizer stage: mean_biomass=X (averaged over scenarios 0-5)
   Policy A in Tournament stage: mean_biomass=Y (averaged over scenarios 6-11)
   Where X and Y are DIFFERENT because the scenario sets don't overlap!

3. Result:
   - Policy A might rank #3 by Optimizer's evaluation
   - But the same Policy A might rank #7 by Tournament's evaluation
   - The SAME POLICY gets DIFFERENT RANKS because it's evaluated on DIFFERENT DATA

4. Why this matters for the 5.2% finding:
   The shared-function baseline allows each stage to use different evaluation
   sets without an abstraction layer to enforce consistency. This causes metrics
   to diverge (even using the same "mean_biomass" extraction logic) because the
   underlying data is different.

   The HEAS contract solves this by enforcing that ALL stages call the same
   metrics_episode() function, ensuring consistent extraction from the SAME
   evaluation set.
""")

    # ===========================================================================
    # Summary JSON
    # ===========================================================================

    summary = {
        "n_policies": n_policies,
        "n_total_scenarios": n_total_scenarios,
        "scenario_split": {
            "optimizer": opt_scenarios,
            "tournament": tourn_scenarios,
            "inference": inf_scenarios,
        },
        "optimizer_ranking": opt_ranking,
        "tournament_ranking": tourn_ranking,
        "inference_ranking": inf_ranking,
        "divergence_rates": divergence_rates,
        "reversals": reversals,
        "reversal_rate": reversal_rate,
        "arena_runs": arena.run_count,
    }

    return summary


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    result = run_advanced_instrumentation(
        n_policies=12,
        n_total_scenarios=18,
        seed=42,
    )

    # Save results
    output_path = "/sessions/zen-hopeful-noether/mnt/heas/v0.5/instrumentation_trace_advanced_output.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n{'=' * 90}")
    print(f"Results saved to: {output_path}")
    print(f"Total arena evaluations: {result['arena_runs']}")
    print(f"Reversal rate: {result['reversal_rate']:.1%}")
    print(f"{'=' * 90}\n")
