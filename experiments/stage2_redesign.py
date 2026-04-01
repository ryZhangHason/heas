#!/usr/bin/env python3
"""
Stage 2 Redesigned: Non-Deterministic Aggregation Consistency Test
===================================================================

PRE-SPECIFICATION (locked 2026-03-27, before any code execution):
  τ_tournament = 0.3  — arena noise parameter for Stage 2 (tournament phase)
  n_runs       = 30   — increased from Stage 1 n=15 for statistical power
  τ_optimizer  = 0.15 — arena noise parameter for Stage 1 (unchanged)
  No re-tuning or parameter adjustment will occur based on results.
  If HEAS shows no advantage: diagnose in paper §5.4, do not re-run.

Design
------
Stage 1 (optimizer phase): policies evaluated with MockArena(noise=0.15).
Stage 2 (tournament phase): SAME policies re-evaluated with MockArena(noise=0.30).

This introduces genuine non-determinism between pipeline stages: the
optimizer used noise=0.15 to build its Pareto rankings, but the tournament
uses noise=0.30.  For the ad-hoc conditions the aggregation function also
differs (optimizer uses "final" or "mean"; tournament uses "mean" or "median")
creating two simultaneous divergence sources.  For HEAS, the same callable
is dispatched at both stages; the only divergence source is noise.

Contribution claim being tested
--------------------------------
"Metric contracts provide runtime-enforceable guarantees against aggregation
 divergence in non-deterministic execution stages of loosely-coupled ABM
 pipelines, where determinism alone cannot apply."

Expected result: HEAS rank reversal rate ≈ 0%; Ad-hoc rates significantly
higher, demonstrating that the contract — not determinism — suppresses
divergence.
"""

from __future__ import annotations

import json
import random
from typing import Dict, List, Tuple

import numpy as np
from scipy import stats as scipy_stats


# ─────────────────────────────────────────────────────────────────────────────
# PRE-SPECIFIED PARAMETERS (DO NOT MODIFY WITHOUT NEW PRE-SPECIFICATION)
# ─────────────────────────────────────────────────────────────────────────────
TAU_OPTIMIZER  = 0.15   # arena noise: Stage 1 / optimizer phase (unchanged from original)
TAU_TOURNAMENT = 0.30   # arena noise: Stage 2 / tournament phase (pre-specified 2026-03-27)
N_RUNS         = 30     # independent runs per condition (pre-specified 2026-03-27)
N_SCENARIOS    = 8      # scenario families (unchanged)
N_POLICIES     = 4      # policies per Pareto front (unchanged)
N_STEPS        = 150    # episode length (unchanged)
ALPHA_CORRECTED = 0.025  # Bonferroni-corrected α for this confirmatory test


# ─────────────────────────────────────────────────────────────────────────────
# Arena
# ─────────────────────────────────────────────────────────────────────────────
class MockArena:
    """Synthetic arena that generates random biomass trajectories."""

    def __init__(self, n_steps: int = N_STEPS, noise: float = TAU_OPTIMIZER):
        self.n_steps = n_steps
        self.noise = noise

    def run_episode(self, genes: Tuple[float, float], scenario_id: int = 0) -> List[float]:
        risk, dispersal = genes
        x = 40.0 + scenario_id * 10.0
        K = 100.0 + scenario_id * 5.0
        r = 0.5  + scenario_id * 0.05
        biomass = []
        for _ in range(self.n_steps):
            r_eff = r * (1.0 - risk * 0.3) + dispersal * 0.2
            x = x + r_eff * x * (1.0 - x / K) - risk * 0.5 * x
            x = max(0.0, x + np.random.normal(0, self.noise * x))
            biomass.append(x)
        return biomass

    def score_policy(
        self, genes: Tuple[float, float], scenario_id: int
    ) -> Dict[str, float]:
        np.random.seed(scenario_id + hash(genes) % 1000)
        random.seed(scenario_id + hash(genes) % 1000)
        biomass = self.run_episode(genes, scenario_id)
        return {
            "final":           biomass[-1],
            "mean":            np.mean(biomass),
            "median":          np.median(biomass),
            "rolling_mean_10": np.mean(biomass[-10:]),
            "trimmed_mean":    (np.mean(sorted(biomass)[15:-15])
                               if len(biomass) > 30 else np.mean(biomass)),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Aggregators (identical to original experiment)
# ─────────────────────────────────────────────────────────────────────────────
class Aggregator:
    def agg_optimizer(self, m: Dict[str, float]) -> float:
        raise NotImplementedError

    def agg_tournament(self, m: Dict[str, float]) -> float:
        raise NotImplementedError


class HEASAggregator(Aggregator):
    """Uniform contract: same callable at all stages."""

    def agg_optimizer(self, m):
        return m["mean"]

    def agg_tournament(self, m):
        return m["mean"]          # identical to optimizer → contract enforced


class AdHocStepAggregator(Aggregator):
    """EA reads final; tournament reads mean."""

    def agg_optimizer(self, m):
        return m["final"]

    def agg_tournament(self, m):
        return m["mean"]


class AdHocMeanAggregator(Aggregator):
    """EA reads mean; tournament reads median."""

    def agg_optimizer(self, m):
        return m["mean"]

    def agg_tournament(self, m):
        return m["median"]


# ─────────────────────────────────────────────────────────────────────────────
# Statistics helpers
# ─────────────────────────────────────────────────────────────────────────────
def kendall_tau(rank1: List[int], rank2: List[int]) -> float:
    tau, _ = scipy_stats.kendalltau(rank1, rank2)
    return tau


def rank_reversal_rate(tau: float) -> float:
    return (1.0 - tau) / 2.0


def cohen_h(p1: float, p2: float) -> float:
    return 2.0 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))


def wilson_ci(
    successes: int, n: int, confidence: float = 0.95
) -> Tuple[float, float]:
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    z = scipy_stats.norm.ppf((1.0 + confidence) / 2.0)
    denom = 1.0 + z ** 2 / n
    num_p = p + z ** 2 / (2.0 * n)
    margin = z * np.sqrt(p * (1.0 - p) / n + z ** 2 / (4.0 * n ** 2))
    return max(0.0, (num_p - margin) / denom), min(1.0, (num_p + margin) / denom)


# ─────────────────────────────────────────────────────────────────────────────
# Main experiment
# ─────────────────────────────────────────────────────────────────────────────
def run_stage2_redesign(
    n_runs:     int   = N_RUNS,
    n_scenarios: int  = N_SCENARIOS,
    n_policies: int   = N_POLICIES,
    tau_opt:    float = TAU_OPTIMIZER,
    tau_tourn:  float = TAU_TOURNAMENT,
) -> Dict:
    """
    Run redesigned Stage 2 with non-deterministic tournament aggregation.

    Each run:
      1. Sample n_policies policies (NSGA-II surrogate, same seeds as Stage 1).
      2. Score each policy with the OPTIMIZER arena (noise = tau_opt = 0.15).
         Obtain optimizer ranking using each condition's agg_optimizer().
      3. Score each policy with the TOURNAMENT arena (noise = tau_tourn = 0.30).
         Obtain tournament ranking using each condition's agg_tournament().
      4. Compute rank reversal rate (Kendall tau between optimizer vs tournament).

    For HEAS: agg_optimizer = agg_tournament = mean.
      Noise changes, but the same callable is used → only noise-driven divergence.
    For Ad-hoc: agg_optimizer ≠ agg_tournament AND noise differs → two divergence sources.

    Returns
    -------
    summary : dict  (structured for JSON export and paper table row)
    """
    arena_opt   = MockArena(n_steps=N_STEPS, noise=tau_opt)
    arena_tourn = MockArena(n_steps=N_STEPS, noise=tau_tourn)

    aggregators = {
        "HEAS":          HEASAggregator(),
        "Ad-hoc-Step":   AdHocStepAggregator(),
        "Ad-hoc-Mean":   AdHocMeanAggregator(),
    }

    raw: Dict[str, Dict] = {
        cond: {"rank_reversals": [], "taus": []} for cond in aggregators
    }

    for cond, agg in aggregators.items():
        print(f"\n  [{cond}] Stage 2 redesign (τ_opt={tau_opt}, τ_tourn={tau_tourn})...")

        for run_id in range(n_runs):
            # ── generate policies (same seed structure as original Stage 1) ──
            np.random.seed(42 + run_id)
            policies = [
                (np.random.uniform(0, 1), np.random.uniform(0, 1))
                for _ in range(n_policies)
            ]

            # ── score with OPTIMIZER arena (Stage 1 noise) ───────────────────
            opt_scores = []
            for policy in policies:
                scores = []
                for sid in range(n_scenarios):
                    m = arena_opt.score_policy(policy, sid)
                    scores.append(agg.agg_optimizer(m))
                opt_scores.append(np.mean(scores))

            # ── score with TOURNAMENT arena (Stage 2 noise = 0.30) ───────────
            # Use a seed offset to ensure genuinely different randomness
            tourn_scores = []
            for policy in policies:
                scores = []
                for sid in range(n_scenarios):
                    # Offset seed: distinguishable from optimizer seeds
                    np.random.seed(2000 + run_id * 100 + sid + hash(policy) % 1000)
                    random.seed(2000 + run_id * 100 + sid + hash(policy) % 1000)
                    biomass = arena_tourn.run_episode(policy, sid)
                    m = {
                        "final":           biomass[-1],
                        "mean":            np.mean(biomass),
                        "median":          np.median(biomass),
                        "rolling_mean_10": np.mean(biomass[-10:]),
                        "trimmed_mean":    (np.mean(sorted(biomass)[15:-15])
                                           if len(biomass) > 30 else np.mean(biomass)),
                    }
                    scores.append(agg.agg_tournament(m))
                tourn_scores.append(np.mean(scores))

            # ── rank & measure ────────────────────────────────────────────────
            opt_rank   = np.argsort(opt_scores)[::-1].tolist()
            tourn_rank = np.argsort(tourn_scores)[::-1].tolist()
            tau        = kendall_tau(opt_rank, tourn_rank)
            rrr        = rank_reversal_rate(tau)

            raw[cond]["rank_reversals"].append(rrr)
            raw[cond]["taus"].append(tau)

            print(f"    run {run_id+1:2d}: τ={tau:6.3f}  reversal={rrr:.3f}")

    # ── aggregate statistics ──────────────────────────────────────────────────
    summary: Dict = {}

    for cond in aggregators:
        reversals   = raw[cond]["rank_reversals"]
        mean_rrr    = float(np.mean(reversals))
        n_reversal_events = int(round(mean_rrr * n_runs))
        ci_lo, ci_hi = wilson_ci(n_reversal_events, n_runs)

        mean_tau     = float(np.mean(raw[cond]["taus"]))
        se_tau       = float(np.std(raw[cond]["taus"], ddof=1) / np.sqrt(n_runs))

        summary[cond] = {
            "mean_reversal_rate": mean_rrr,
            "ci_lower":           float(ci_lo),
            "ci_upper":           float(ci_hi),
            "mean_tau":           mean_tau,
            "se_tau":             se_tau,
            "n_runs":             n_runs,
        }

    # ── effect sizes ─────────────────────────────────────────────────────────
    h_vs_step = cohen_h(summary["Ad-hoc-Step"]["mean_reversal_rate"],
                         summary["HEAS"]["mean_reversal_rate"])
    h_vs_mean = cohen_h(summary["Ad-hoc-Mean"]["mean_reversal_rate"],
                         summary["HEAS"]["mean_reversal_rate"])

    # Bootstrap CI for Cohen's h
    np.random.seed(42)
    boot_h_step, boot_h_mean = [], []
    heas_r  = raw["HEAS"]["rank_reversals"]
    step_r  = raw["Ad-hoc-Step"]["rank_reversals"]
    mean_r  = raw["Ad-hoc-Mean"]["rank_reversals"]
    for _ in range(10_000):
        bh = float(np.mean(np.random.choice(heas_r,  len(heas_r),  replace=True)))
        bs = float(np.mean(np.random.choice(step_r,  len(step_r),  replace=True)))
        bm = float(np.mean(np.random.choice(mean_r,  len(mean_r),  replace=True)))
        boot_h_step.append(cohen_h(bs, bh))
        boot_h_mean.append(cohen_h(bm, bh))

    summary["effect_sizes"] = {
        "HEAS_vs_AdHocStep": {
            "cohen_h":  h_vs_step,
            "ci_lower": float(np.percentile(boot_h_step, 2.5)),
            "ci_upper": float(np.percentile(boot_h_step, 97.5)),
        },
        "HEAS_vs_AdHocMean": {
            "cohen_h":  h_vs_mean,
            "ci_lower": float(np.percentile(boot_h_mean, 2.5)),
            "ci_upper": float(np.percentile(boot_h_mean, 97.5)),
        },
    }

    # ── Binomial test: HEAS reversal rate vs Ad-hoc-Step ─────────────────────
    # Confirmatory test: H0: HEAS divergence_rate >= Ad-hoc-Step rate
    # (one-sided; α_corrected = 0.025)
    heas_reversals_count  = sum(1 for r in heas_r  if r > 0.0)
    step_reversals_count  = sum(1 for r in step_r  if r > 0.0)
    if step_reversals_count > 0:
        binom_result = scipy_stats.binomtest(
            heas_reversals_count, n_runs,
            step_reversals_count / n_runs,
            alternative="less",
        )
        binom_p = float(binom_result.pvalue)
    else:
        binom_p = 1.0

    summary["confirmatory_test"] = {
        "test":                 "Binomial (one-sided: HEAS < Ad-hoc-Step)",
        "heas_reversals_count": heas_reversals_count,
        "step_reversals_count": step_reversals_count,
        "n":                    n_runs,
        "raw_p":                float(binom_p),
        "alpha_corrected":      ALPHA_CORRECTED,
        "significant":          bool(binom_p < ALPHA_CORRECTED),
        "prespecification":     (
            "Family size n=2 (Stage 2 binomial + Cohen h), "
            "α_corrected=0.025 (Bonferroni, FWER=0.05). "
            "Pre-specified 2026-03-27 before any Stage 2 code execution."
        ),
    }

    summary["prespecification"] = {
        "tau_optimizer":  tau_opt,
        "tau_tournament": tau_tourn,
        "n_runs":         n_runs,
        "locked_date":    "2026-03-27",
        "no_retuning":    True,
    }

    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    print("=" * 70)
    print("STAGE 2 REDESIGNED: NON-DETERMINISTIC AGGREGATION CONSISTENCY TEST")
    print(f"Pre-specified τ_tournament = {TAU_TOURNAMENT}  |  n_runs = {N_RUNS}")
    print(f"Locked 2026-03-27 — no re-tuning on results")
    print("=" * 70)

    summary = run_stage2_redesign()

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for cond in ["HEAS", "Ad-hoc-Step", "Ad-hoc-Mean"]:
        r = summary[cond]
        print(f"\n{cond}:")
        print(f"  Mean rank reversal rate : {r['mean_reversal_rate']:.1%}")
        print(f"  95% Wilson CI           : [{r['ci_lower']:.1%}, {r['ci_upper']:.1%}]")
        print(f"  Mean Kendall τ          : {r['mean_tau']:.4f} ± {r['se_tau']:.4f}")

    print("\n" + "=" * 70)
    print("EFFECT SIZES (Cohen's h)")
    print("=" * 70)
    for key, label in [("HEAS_vs_AdHocStep", "HEAS vs Ad-hoc-Step"),
                        ("HEAS_vs_AdHocMean",  "HEAS vs Ad-hoc-Mean")]:
        es = summary["effect_sizes"][key]
        print(f"\n{label}:")
        print(f"  h = {es['cohen_h']:.3f}  95% CI [{es['ci_lower']:.3f}, {es['ci_upper']:.3f}]")

    print("\n" + "=" * 70)
    print("CONFIRMATORY TEST")
    print("=" * 70)
    ct = summary["confirmatory_test"]
    print(f"  {ct['test']}")
    print(f"  HEAS reversals: {ct['heas_reversals_count']}/{ct['n']}")
    print(f"  Ad-hoc-Step reversals: {ct['step_reversals_count']}/{ct['n']}")
    print(f"  Raw p = {ct['raw_p']:.4f}  |  α_corrected = {ct['alpha_corrected']}")
    print(f"  Significant (Bonferroni-corrected): {ct['significant']}")

    # ── save ──────────────────────────────────────────────────────────────────
    out_dir  = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "stage2_redesign_results.json")

    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n\nResults saved to: {out_path}")
