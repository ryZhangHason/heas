#!/usr/bin/env python3
"""
Controlled Aggregation Consistency Experiment
==============================================

This script runs a controlled experiment to isolate the effect of the
metric contract on rank reversal rates. We use a synthetic mock arena
that generates random biomass trajectories, then apply three different
aggregation strategies to the same raw data.

Three conditions:
1. HEAS (uniform): All stages read the same aggregation function
2. Ad-hoc-Step: EA reads final step, tournament reads episode mean,
                CI reads rolling 10-step mean
3. Ad-hoc-Mean: EA reads episode mean, tournament reads episode median,
               CI reads trimmed mean (10th-90th percentile)

The dependent variable is rank reversal rate, measured as (1 - tau) / 2
where tau is Kendall's tau between optimizer and tournament rankings.
"""

from __future__ import annotations

import json
import random
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats as scipy_stats


class MockArena:
    """Synthetic arena that generates random biomass trajectories."""

    def __init__(self, n_steps: int = 150, noise: float = 0.15):
        self.n_steps = n_steps
        self.noise = noise

    def run_episode(self, genes: Tuple[float, float], scenario_id: int = 0) -> List[float]:
        """
        Simulate an episode with parameters determined by genes.

        Parameters
        ----------
        genes : (risk, dispersal)
            Two parameters that modulate the biomass trajectory.
        scenario_id : int
            Which scenario (affects RNG seed and dynamics).

        Returns
        -------
        biomass : list of float
            Biomass at each timestep.
        """
        risk, dispersal = genes

        # Vary initial conditions and dynamics by scenario
        x = 40.0 + scenario_id * 10.0  # Initial pop varies by scenario
        K = 100.0 + scenario_id * 5.0   # Carrying capacity varies
        r = 0.5 + scenario_id * 0.05    # Growth rate varies

        # Base trajectory: logistic growth with noise
        biomass = []

        for t in range(self.n_steps):
            # Growth depends on risk (predation pressure) and dispersal (colonization)
            r_eff = r * (1.0 - risk * 0.3) + dispersal * 0.2
            x = x + r_eff * x * (1.0 - x / K) - risk * 0.5 * x
            x = max(0.0, x + np.random.normal(0, self.noise * x))
            biomass.append(x)

        return biomass

    def score_policy(self, genes: Tuple[float, float], scenario_id: int) -> Dict[str, float]:
        """
        Run episode and return a metrics dict.

        Parameters
        ----------
        genes : (risk, dispersal)
            Policy parameters.
        scenario_id : int
            Which scenario (affects RNG seed and dynamics).

        Returns
        -------
        metrics : dict[str, float]
            Raw biomass trajectory (used by aggregators).
        """
        # Use scenario_id to vary RNG
        np.random.seed(scenario_id + hash(genes) % 1000)
        random.seed(scenario_id + hash(genes) % 1000)

        biomass = self.run_episode(genes, scenario_id)

        # Return raw trajectory as a dict (this is the "contract")
        return {
            "biomass_trajectory": biomass,
            "final": biomass[-1],
            "mean": np.mean(biomass),
            "median": np.median(biomass),
            "rolling_mean_10": np.mean(biomass[-10:]),
            "trimmed_mean": np.mean(sorted(biomass)[15:-15]) if len(biomass) > 30 else np.mean(biomass),
        }


class Aggregator:
    """Base class for metric aggregation strategies."""

    def aggregate_tournament_score(self, metrics: Dict[str, float]) -> float:
        """Return a scalar score for tournament ranking."""
        raise NotImplementedError

    def aggregate_optimizer_fitness(self, metrics: Dict[str, float]) -> float:
        """Return a scalar fitness for optimizer ranking."""
        raise NotImplementedError

    def aggregate_inference_ci(self, metrics: Dict[str, float]) -> float:
        """Return a scalar for CI ranking."""
        raise NotImplementedError


class HEASAggregator(Aggregator):
    """HEAS condition: uniform metrics_episode() contract."""

    def aggregate_tournament_score(self, metrics: Dict[str, float]) -> float:
        return metrics["mean"]

    def aggregate_optimizer_fitness(self, metrics: Dict[str, float]) -> float:
        return metrics["mean"]

    def aggregate_inference_ci(self, metrics: Dict[str, float]) -> float:
        return metrics["mean"]


class AdHocStepAggregator(Aggregator):
    """Ad-hoc-Step: EA reads final, tournament reads mean, CI reads rolling mean."""

    def aggregate_tournament_score(self, metrics: Dict[str, float]) -> float:
        return metrics["mean"]

    def aggregate_optimizer_fitness(self, metrics: Dict[str, float]) -> float:
        return metrics["final"]

    def aggregate_inference_ci(self, metrics: Dict[str, float]) -> float:
        return metrics["rolling_mean_10"]


class AdHocMeanAggregator(Aggregator):
    """Ad-hoc-Mean: EA reads mean, tournament reads median, CI reads trimmed mean."""

    def aggregate_tournament_score(self, metrics: Dict[str, float]) -> float:
        return metrics["median"]

    def aggregate_optimizer_fitness(self, metrics: Dict[str, float]) -> float:
        return metrics["mean"]

    def aggregate_inference_ci(self, metrics: Dict[str, float]) -> float:
        return metrics["trimmed_mean"]


def kendall_tau(rank1: List[int], rank2: List[int]) -> float:
    """Compute Kendall's tau correlation between two rankings."""
    tau, _ = scipy_stats.kendalltau(rank1, rank2)
    return tau


def compute_rank_reversal_rate(tau: float) -> float:
    """
    Convert Kendall's tau to rank reversal rate.

    rank_reversal_rate = (1 - tau) / 2

    This maps tau in [-1, 1] to reversal_rate in [0, 1]:
    - tau = 1 (identical) -> reversal_rate = 0
    - tau = 0 (independent) -> reversal_rate = 0.5
    - tau = -1 (opposite) -> reversal_rate = 1
    """
    return (1.0 - tau) / 2.0


def cohen_h(p1: float, p2: float) -> float:
    """
    Compute Cohen's h effect size for two proportions.

    h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
    """
    return 2.0 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Compute Wilson score confidence interval for a proportion.

    Parameters
    ----------
    successes : int
        Number of successes.
    n : int
        Total number of trials.
    confidence : float
        Confidence level (default 0.95 for 95% CI).

    Returns
    -------
    (lower, upper) : tuple of float
        Lower and upper bounds of the CI.
    """
    if n == 0:
        return 0.0, 1.0

    p = successes / n
    z = scipy_stats.norm.ppf((1.0 + confidence) / 2.0)

    denom = 1.0 + z**2 / n
    numerator_p = p + z**2 / (2.0 * n)
    margin = z * np.sqrt(p * (1.0 - p) / n + z**2 / (4.0 * n**2))

    lower = (numerator_p - margin) / denom
    upper = (numerator_p + margin) / denom

    return max(0.0, lower), min(1.0, upper)


def run_controlled_experiment(
    n_runs: int = 15,
    n_scenarios: int = 8,
    n_policies_per_run: int = 4,
) -> Dict:
    """
    Run the controlled aggregation experiment.

    Parameters
    ----------
    n_runs : int
        Number of independent evolutionary runs per condition.
    n_scenarios : int
        Number of scenarios per tournament.
    n_policies_per_run : int
        Top-k policies to extract and rank.

    Returns
    -------
    results : dict
        Dictionary with rank reversal rates and effect sizes.
    """
    arena = MockArena(n_steps=150)
    aggregators = {
        "HEAS": HEASAggregator(),
        "Ad-hoc-Step": AdHocStepAggregator(),
        "Ad-hoc-Mean": AdHocMeanAggregator(),
    }

    results = {
        condition: {
            "rank_reversals": [],
            "voting_agreement": [],
            "n_comparisons": 0,
            "stage2_kendall_taus": [],  # Stage 2: robustness across seeds
            "stage2_policies": [],  # Store 15 policies per condition for Stage 2
        }
        for condition in aggregators
    }

    # For each condition, simulate n_runs NSGA-II searches
    for condition, aggregator in aggregators.items():
        print(f"\nRunning {condition} condition...")

        for run_id in range(n_runs):
            # Simulate Pareto front: randomly sample top-k policies
            # (In a real experiment, these come from NSGA-II)
            np.random.seed(42 + run_id)
            policies = [(np.random.uniform(0, 1), np.random.uniform(0, 1))
                       for _ in range(n_policies_per_run)]

            # Step 1: Score each policy across all scenarios (tournament)
            tournament_scores = []
            optimizer_scores = []
            ci_scores = []

            for policy_idx, policy in enumerate(policies):
                policy_tournament_scores = []
                policy_optimizer_scores = []
                policy_ci_scores = []

                for scenario_id in range(n_scenarios):
                    metrics = arena.score_policy(policy, scenario_id)

                    policy_tournament_scores.append(
                        aggregator.aggregate_tournament_score(metrics)
                    )
                    policy_optimizer_scores.append(
                        aggregator.aggregate_optimizer_fitness(metrics)
                    )
                    policy_ci_scores.append(
                        aggregator.aggregate_inference_ci(metrics)
                    )

                # Average across scenarios (this is what tournament does)
                tournament_scores.append(np.mean(policy_tournament_scores))
                optimizer_scores.append(np.mean(policy_optimizer_scores))
                ci_scores.append(np.mean(policy_ci_scores))

            # Step 2: Rank policies according to tournament vs optimizer
            tournament_ranking = np.argsort(tournament_scores)[::-1].tolist()
            optimizer_ranking = np.argsort(optimizer_scores)[::-1].tolist()

            # Step 3: Compute rank reversal rate (Kendall's tau)
            tau = kendall_tau(tournament_ranking, optimizer_ranking)
            reversal_rate = compute_rank_reversal_rate(tau)

            # Step 4: Voting agreement: check if tournament and optimizer agree on top-2
            tournament_top2 = set(tournament_ranking[:2])
            optimizer_top2 = set(optimizer_ranking[:2])
            agreement = 1.0 if tournament_top2 == optimizer_top2 else 0.0

            results[condition]["rank_reversals"].append(reversal_rate)
            results[condition]["voting_agreement"].append(agreement)
            results[condition]["n_comparisons"] += 1

            # Store the 15 policies for Stage 2 evaluation
            if run_id == 0:  # Only store from the first run (representative)
                results[condition]["stage2_policies"] = policies

            print(f"  Run {run_id+1:2d}: tau={tau:6.3f}, reversal_rate={reversal_rate:6.3f}, agreement={agreement:.1f}")

    # STAGE 2: Re-evaluate the same policies with a different random seed
    print("\n" + "="*70)
    print("STAGE 2: STOCHASTIC ROBUSTNESS TEST (Different Random Seed)")
    print("="*70)

    for condition, aggregator in aggregators.items():
        print(f"\nStage 2: {condition} condition (seed offset +1000)...")

        # Use the stored policies from Stage 1 (run_id=0)
        policies = results[condition]["stage2_policies"]

        # Re-evaluate with a different seed offset
        tournament_scores_s2 = []
        optimizer_scores_s2 = []

        for policy_idx, policy in enumerate(policies):
            policy_tournament_scores_s2 = []
            policy_optimizer_scores_s2 = []

            for scenario_id in range(n_scenarios):
                # Override arena seed with offset +1000 to ensure different randomness
                np.random.seed(1000 + scenario_id + hash(policy) % 1000)
                random.seed(1000 + scenario_id + hash(policy) % 1000)

                # Regenerate biomass with different seed
                arena_s2 = MockArena(n_steps=150, noise=0.15)
                metrics_s2 = {
                    "biomass_trajectory": arena_s2.run_episode(policy, scenario_id),
                }
                # Recompute all metrics with new trajectory
                biomass_s2 = metrics_s2["biomass_trajectory"]
                metrics_s2.update({
                    "final": biomass_s2[-1],
                    "mean": np.mean(biomass_s2),
                    "median": np.median(biomass_s2),
                    "rolling_mean_10": np.mean(biomass_s2[-10:]),
                    "trimmed_mean": np.mean(sorted(biomass_s2)[15:-15]) if len(biomass_s2) > 30 else np.mean(biomass_s2),
                })

                policy_tournament_scores_s2.append(
                    aggregator.aggregate_tournament_score(metrics_s2)
                )
                policy_optimizer_scores_s2.append(
                    aggregator.aggregate_optimizer_fitness(metrics_s2)
                )

            tournament_scores_s2.append(np.mean(policy_tournament_scores_s2))
            optimizer_scores_s2.append(np.mean(policy_optimizer_scores_s2))

        # Rank policies in Stage 2
        tournament_ranking_s2 = np.argsort(tournament_scores_s2)[::-1].tolist()

        # Use Stage 1 tournament ranking as baseline
        np.random.seed(42)  # Reset seed for Stage 1 re-evaluation to be deterministic
        policies_s1 = results[condition]["stage2_policies"]
        tournament_scores_s1 = []
        for policy_idx, policy in enumerate(policies_s1):
            policy_tournament_scores_s1 = []
            for scenario_id in range(n_scenarios):
                metrics_s1 = arena.score_policy(policy, scenario_id)
                policy_tournament_scores_s1.append(
                    aggregator.aggregate_tournament_score(metrics_s1)
                )
            tournament_scores_s1.append(np.mean(policy_tournament_scores_s1))

        tournament_ranking_s1 = np.argsort(tournament_scores_s1)[::-1].tolist()

        # Compute Kendall tau between Stage 1 and Stage 2 rankings
        tau_s2 = kendall_tau(tournament_ranking_s1, tournament_ranking_s2)
        results[condition]["stage2_kendall_taus"].append(tau_s2)

        print(f"  Stage 1 tournament ranking: {tournament_ranking_s1}")
        print(f"  Stage 2 tournament ranking: {tournament_ranking_s2}")
        print(f"  Kendall τ (Stage 1 vs Stage 2): {tau_s2:.4f}")

    # Step 5: Analyze results
    summary = {}
    for condition in aggregators:
        reversals = results[condition]["rank_reversals"]
        agreements = results[condition]["voting_agreement"]
        stage2_taus = results[condition]["stage2_kendall_taus"]

        mean_reversal = np.mean(reversals)
        std_reversal = np.std(reversals, ddof=1) if len(reversals) > 1 else 0.0
        se_reversal = std_reversal / np.sqrt(len(reversals))

        mean_agreement = np.mean(agreements)

        # Stage 2 statistics
        mean_stage2_tau = np.mean(stage2_taus) if stage2_taus else 1.0
        se_stage2_tau = (np.std(stage2_taus, ddof=1) / np.sqrt(len(stage2_taus))) if len(stage2_taus) > 1 else 0.0

        # Wilson CI for reversal rate (use mean as proportion)
        # For simplicity, compute binomial CI from count
        n_reversals = int(round(mean_reversal * n_runs))
        ci_lower, ci_upper = wilson_ci(n_reversals, n_runs)

        summary[condition] = {
            "mean_reversal_rate": mean_reversal,
            "se_reversal_rate": se_reversal,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "mean_agreement": mean_agreement,
            "n_runs": n_runs,
            "stage2_kendall_tau": mean_stage2_tau,
            "stage2_se": se_stage2_tau,
        }

    # Compute effect size (Cohen's h) for HEAS vs Ad-hoc conditions
    heas_prop = summary["HEAS"]["mean_reversal_rate"]
    adhoc_step_prop = summary["Ad-hoc-Step"]["mean_reversal_rate"]
    adhoc_mean_prop = summary["Ad-hoc-Mean"]["mean_reversal_rate"]

    h_heas_vs_step = cohen_h(adhoc_step_prop, heas_prop)
    h_heas_vs_mean = cohen_h(adhoc_mean_prop, heas_prop)

    # Bootstrap CI for effect sizes
    np.random.seed(42)
    bootstrap_h_step = []
    bootstrap_h_mean = []
    n_bootstrap = 10000

    heas_reversals = results["HEAS"]["rank_reversals"]
    step_reversals = results["Ad-hoc-Step"]["rank_reversals"]
    mean_reversals = results["Ad-hoc-Mean"]["rank_reversals"]

    for _ in range(n_bootstrap):
        boot_heas = np.mean(np.random.choice(heas_reversals, len(heas_reversals)))
        boot_step = np.mean(np.random.choice(step_reversals, len(step_reversals)))
        boot_mean = np.random.choice(mean_reversals, len(mean_reversals))
        bootstrap_h_step.append(cohen_h(boot_step, boot_heas))
        bootstrap_h_mean.append(cohen_h(np.mean(boot_mean), boot_heas))

    h_ci_step = (np.percentile(bootstrap_h_step, 2.5), np.percentile(bootstrap_h_step, 97.5))
    h_ci_mean = (np.percentile(bootstrap_h_mean, 2.5), np.percentile(bootstrap_h_mean, 97.5))

    summary["effect_sizes"] = {
        "HEAS_vs_AdHocStep": {
            "cohen_h": h_heas_vs_step,
            "ci_lower": h_ci_step[0],
            "ci_upper": h_ci_step[1],
        },
        "HEAS_vs_AdHocMean": {
            "cohen_h": h_heas_vs_mean,
            "ci_lower": h_ci_mean[0],
            "ci_upper": h_ci_mean[1],
        },
    }

    return summary


if __name__ == "__main__":
    print("="*70)
    print("CONTROLLED AGGREGATION CONSISTENCY EXPERIMENT")
    print("="*70)

    summary = run_controlled_experiment(n_runs=15, n_scenarios=8, n_policies_per_run=4)

    print("\n" + "="*70)
    print("SUMMARY RESULTS")
    print("="*70)

    for condition in ["HEAS", "Ad-hoc-Step", "Ad-hoc-Mean"]:
        r = summary[condition]
        print(f"\n{condition}:")
        print(f"  Mean rank reversal rate: {r['mean_reversal_rate']:.1%}")
        print(f"  95% Wilson CI: [{r['ci_lower']:.1%}, {r['ci_upper']:.1%}]")
        print(f"  Mean voting agreement: {r['mean_agreement']:.1%}")
        print(f"  Stage 2 Kendall τ: {r['stage2_kendall_tau']:.4f} ± {r['stage2_se']:.4f}")
        print(f"  n_runs: {r['n_runs']}")

    print("\n" + "="*70)
    print("EFFECT SIZES (Cohen's h)")
    print("="*70)

    h_step = summary["effect_sizes"]["HEAS_vs_AdHocStep"]
    h_mean = summary["effect_sizes"]["HEAS_vs_AdHocMean"]

    print(f"\nHEAS vs Ad-hoc-Step:")
    print(f"  h = {h_step['cohen_h']:.3f}")
    print(f"  95% CI: [{h_step['ci_lower']:.3f}, {h_step['ci_upper']:.3f}]")

    print(f"\nHEAS vs Ad-hoc-Mean:")
    print(f"  h = {h_mean['cohen_h']:.3f}")
    print(f"  95% CI: [{h_mean['ci_lower']:.3f}, {h_mean['ci_upper']:.3f}]")

    # Save results to JSON
    output_file = "/sessions/zen-hopeful-noether/mnt/HEAS_WSC/heas/experiments/agg_consistency_results.json"
    output_file_stage2 = "/sessions/zen-hopeful-noether/mnt/HEAS_WSC/heas/experiments/agg_consistency_results_stage2.json"

    # Convert numpy types to Python types for JSON serialization
    results_serializable = {}
    for condition in summary:
        results_serializable[condition] = {
            k: float(v) if isinstance(v, (np.floating, float)) else v
            for k, v in summary[condition].items()
        }

    with open(output_file, "w") as f:
        json.dump(results_serializable, f, indent=2)

    # Also save Stage 2 results separately for clarity
    stage2_results = {}
    for condition in ["HEAS", "Ad-hoc-Step", "Ad-hoc-Mean"]:
        stage2_results[condition] = {
            "stage2_kendall_tau": float(summary[condition]["stage2_kendall_tau"]),
            "stage2_se": float(summary[condition]["stage2_se"]),
        }

    with open(output_file_stage2, "w") as f:
        json.dump(stage2_results, f, indent=2)

    print(f"\n\nResults saved to: {output_file}")
    print(f"Stage 2 results saved to: {output_file_stage2}")
