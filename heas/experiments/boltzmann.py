"""
heas.experiments.boltzmann
===========================
Boltzmann Wealth Distribution model for multi-ABM MAD experiments (EA-7).

A lightweight, numpy-vectorised implementation of the canonical Boltzmann
wealth exchange model with optional progressive redistribution.  No Mesa
dependency required.

**Policy genes (2)**:
    redistribution_rate ∈ [0.0, 0.5] — tax rate on wealth above threshold
    tax_threshold       ∈ [0.5, 2.0] — multiplier of mean wealth for tax trigger

**Objectives** (NSGA-II, both minimised):
    −final_gini     (maximise equality → minimise Gini at final step)
     gini_variance  (minimise trajectory instability of inequality)

Each step: a random pair exchanges 1 unit (standard Boltzmann), then
progressive redistribution taxes excess wealth and redistributes equally.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np


def gini_coefficient(arr) -> float:
    """Compute Gini coefficient of a 1-D array or list."""
    a = np.asarray(arr, dtype=float)
    a = np.sort(a)
    n = len(a)
    if n == 0 or a.sum() == 0:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * a) / (n * a.sum())) - (n + 1) / n)


def run_episode(
    redistribution_rate: float,
    tax_threshold: float,
    seed: int,
    n_steps: int = 200,
    n_agents: int = 100,
) -> List[float]:
    """Run one episode of the Boltzmann wealth model.

    Parameters
    ----------
    redistribution_rate:
        Fraction of wealth above the threshold that is taxed each step.
    tax_threshold:
        Multiplier of mean wealth that triggers taxation.
    seed:
        RNG seed.
    n_steps:
        Number of simulation steps.
    n_agents:
        Number of agents in the population.

    Returns
    -------
    gini_trajectory : list of float
        Gini coefficient at each step (length ``n_steps``).  Lower = more equal.
    """
    rng = np.random.default_rng(seed)
    wealth = np.ones(n_agents, dtype=float)
    trajectory: List[float] = []

    for _step in range(n_steps):
        trajectory.append(gini_coefficient(wealth))

        # Standard Boltzmann exchange: random pair, one transfers 1 unit
        idx = rng.integers(0, n_agents, size=2)
        i, j = idx[0], idx[1]
        if i != j and wealth[i] >= 1:
            wealth[i] -= 1
            wealth[j] += 1

        # Progressive redistribution
        if redistribution_rate > 0:
            tax_threshold_val = tax_threshold * np.mean(wealth)
            tax_mask = wealth > tax_threshold_val
            taxes = np.where(
                tax_mask,
                redistribution_rate * (wealth - tax_threshold_val),
                0.0,
            )
            total_tax = taxes.sum()
            wealth -= taxes
            wealth += total_tax / n_agents
            wealth = np.maximum(wealth, 0.0)

    return trajectory


def score_detailed(
    redistribution_rate: float,
    tax_threshold: float,
    seed: int,
    n_steps: int = 200,
) -> Dict[str, float]:
    """Return per-episode score dict (mirrors MockArena.score_detailed).

    Keys: final, mean, median, q75, entropy.
    For Boltzmann, metrics are on the Gini trajectory (lower = better).
    """
    traj = run_episode(redistribution_rate, tax_threshold, seed, n_steps=n_steps)
    arr = np.array(traj)
    hist, _ = np.histogram(arr, bins=10)
    p = hist / hist.sum()
    p = p[p > 0]
    entropy = float(-np.sum(p * np.log(p)) / np.log(len(p) + 1))
    return {
        "final": float(arr[-1]) if arr.size > 0 else 0.0,
        "mean": float(np.mean(arr)) if arr.size > 0 else 0.0,
        "median": float(np.median(arr)) if arr.size > 0 else 0.0,
        "q75": float(np.percentile(arr, 75)) if arr.size > 0 else 0.0,
        "entropy": entropy,
    }


def evaluate_genes(
    redistribution_rate: float,
    tax_threshold: float,
    n_scenarios: int = 8,
    n_episodes: int = 5,
    n_steps: int = 200,
    seed_base: int = 0,
) -> Tuple[float, float]:
    """Return ``(obj1, obj2)`` for NSGA-II minimisation.

    ``obj1 = −final_gini`` (minimise → maximise equality),
    ``obj2 =  gini_variance`` (minimise → reduce trajectory instability).

    Note: for Boltzmann, we negate the final Gini (which is already
    "lower = better") to follow the minimisation convention.
    """
    all_finals: List[float] = []
    all_vars: List[float] = []
    for sc in range(n_scenarios):
        for ep in range(n_episodes):
            seed = seed_base + sc * 1000 + ep
            traj = run_episode(
                redistribution_rate, tax_threshold, seed,
                n_steps=n_steps,
            )
            arr = np.array(traj)
            if arr.size > 0:
                all_finals.append(float(arr[-1]))
                all_vars.append(float(np.var(arr)))
            else:
                all_finals.append(0.0)
                all_vars.append(0.0)
    # Minimise: −final_gini (so lower final_gini → better), gini_var
    return -float(np.mean(all_finals)), float(np.mean(all_vars))
