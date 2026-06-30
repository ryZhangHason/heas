"""
heas.experiments.mock
======================
Synthetic test arenas for Metric Aggregation Divergence (MAD) experiments.

``MockArena``
    Two-gene ecological arena (risk × dispersal).  Logistic growth with
    multiplicative noise.  Used in EA-2, EA-3, EA-6, EA-8.

``Mock4GeneArena``
    Four-gene regulatory arena (tax, audit_intensity, subsidy, penalty_rate).
    Models a simplified enterprise economy with hump-shaped welfare dynamics
    and Gini inequality.  Used in EA-1 multiseed.

``MockArenaProblem``
    pymoo ``ElementwiseProblem`` wrapper for NSGA-II on MockArena.
    Used in EA-6, EA-6b, EA-12.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ============================================================================
# MockArena — 2-gene ecological arena
# ============================================================================


class MockArena:
    """Logistic-growth ecological arena for MAD experiments.

    Two policy genes:
        risk       ∈ [0, 1]  — predation / extraction intensity
        dispersal  ∈ [0, 1]  — spatial redistribution rate

    Dynamics:
        x_{t+1} = x_t + r_eff · x_t · (1 − x_t / K) − risk · 0.5 · x_t + ε

    where r_eff = r · (1 − risk · 0.3) + dispersal · 0.2, and
    ε ~ N(0, noise · x_t).

    Scenario variation is achieved by shifting K, r, and x_0 by
    ``scenario_id``.
    """

    def __init__(self, n_steps: int = 150, noise: float = 0.15) -> None:
        self.n_steps = int(n_steps)
        self.noise = float(noise)

    def run_episode(
        self,
        genes: Tuple[float, float],
        scenario_id: int,
        seed: int = 0,
    ) -> List[float]:
        """Run one episode.  Returns the full biomass trajectory."""
        risk, dispersal = genes
        x = 40.0 + scenario_id * 5.0
        K = 100.0 + scenario_id * 3.0
        r = 0.5 + scenario_id * 0.03
        rng = np.random.default_rng(seed)
        biomass: List[float] = []
        for _ in range(self.n_steps):
            r_eff = r * (1.0 - risk * 0.3) + dispersal * 0.2
            x = x + r_eff * x * (1.0 - x / K) - risk * 0.5 * x
            x = max(0.1, x)
            x = max(0.1, x + rng.normal(0, self.noise * x))
            biomass.append(float(x))
        return biomass

    def evaluate_genes(
        self,
        genes: Tuple[float, float],
        n_scenarios: int = 8,
        n_episodes: int = 5,
        seed_base: int = 0,
    ) -> Tuple[float, float]:
        """Return ``(obj1, obj2)`` for NSGA-II minimisation.

        ``obj1 = −mean_biomass`` (minimise → maximise biomass),
        ``obj2 =  var_biomass`` (minimise → reduce instability).
        """
        all_means: List[float] = []
        all_vars: List[float] = []
        for sc in range(n_scenarios):
            for ep in range(n_episodes):
                seed = seed_base + sc * 1000 + ep
                traj = self.run_episode(genes, sc, seed=seed)
                all_means.append(float(np.mean(traj)))
                all_vars.append(float(np.var(traj)))
        return -float(np.mean(all_means)), float(np.mean(all_vars))

    def score_detailed(
        self,
        genes: Tuple[float, float],
        scenario_id: int,
        seed: int = 0,
    ) -> Dict[str, float]:
        """Full per-scenario score dict (for re-scoring the Pareto front).

        Returns keys: final, mean, median, q75, entropy.
        """
        traj = self.run_episode(genes, scenario_id, seed=seed)
        hist, _ = np.histogram(traj, bins=10)
        p = hist / hist.sum()
        p = p[p > 0]
        entropy = float(-np.sum(p * np.log(p)) / np.log(len(p) + 1))
        return {
            "final": float(traj[-1]),
            "mean": float(np.mean(traj)),
            "median": float(np.median(traj)),
            "q75": float(np.percentile(traj, 75)),
            "entropy": entropy,
        }


# ============================================================================
# Mock4GeneArena — 4-gene enterprise regulatory arena
# ============================================================================


class Mock4GeneArena:
    """Synthetic 4-gene enterprise regulatory arena.

    Policy genes (all ∈ [0, 1]):
        tax              — direct tax rate on firm balances
        audit_intensity  — probability of targeted (vs random) audit
        subsidy          — injection amount during the first 30% of the episode
        penalty_rate     — extraction fraction on audited firms

    Dynamics:
        Firms carry balances that grow logistically.  Subsidy is injected
        early, then repaid in the second half.  Audit triggers redistribution.
        Cooperative surplus sharing occurs under ``coop`` regime.

    The welfare trajectory is hump-shaped (subsidy growth → repayment drain),
    which creates genuine ranking reversals between early-window and
    late-window metrics — the key ingredient for MAD.
    """

    def __init__(
        self,
        n_agents: int = 4,
        n_steps: int = 50,
    ) -> None:
        self.n_agents = int(n_agents)
        self.n_steps = int(n_steps)

    def run_episode(
        self,
        policy: Dict[str, float],
        scenario: Dict[str, Any],
        seed: int,
    ) -> Tuple[List[float], List[float]]:
        """Run one episode.

        Parameters
        ----------
        policy:
            Keys: tax, audit_intensity, subsidy, penalty_rate.
        scenario:
            Keys: regime ('coop'/'compete'), base_demand, audit_prob, costs.
        seed:
            RNG seed.

        Returns
        -------
        (welfare_trajectory, gini_trajectory) — each length ``n_steps``.
        """
        rng = np.random.default_rng(seed)
        n = self.n_agents
        steps = self.n_steps

        tax = float(policy["tax"])
        audit = float(policy["audit_intensity"])
        subsidy = float(policy["subsidy"])
        penalty = float(policy["penalty_rate"])

        regime = str(scenario.get("regime", "coop"))
        base_demand = float(scenario.get("base_demand", 100.0))
        audit_prob = float(scenario.get("audit_prob", 0.2))
        costs = float(scenario.get("costs", 0.4))

        K = 3.0 * (base_demand / 100.0)
        r_base = 0.06 * (base_demand / 100.0) * max(0.1, 1.0 - costs)

        T_inj = int(steps * 0.30)
        T_rep = int(steps * 0.50)
        sub_per_step = subsidy * 2.0
        total_sub = sub_per_step * T_inj
        rep_steps = max(1, steps - T_rep)
        rep_per_step = total_sub / rep_steps

        coop_share = 0.04 if regime == "coop" else 0.0

        balances = rng.uniform(0.8, 1.2, size=n)
        welfare_traj: List[float] = []
        gini_traj: List[float] = []

        for t in range(steps):
            sub_t = sub_per_step if t < T_inj else 0.0
            rep_t = rep_per_step if t >= T_rep else 0.0

            new_balances = np.zeros(n)
            for i in range(n):
                b = float(balances[i])
                growth = r_base * b * max(0.0, 1.0 - b / K)
                shock = float(rng.normal(0.0, 0.03 * (base_demand / 100.0)))
                tax_drain = tax * b
                new_balances[i] = max(0.01, b + growth + sub_t - tax_drain - rep_t + shock)

            # Audit-triggered redistribution
            if rng.random() < audit_prob:
                target_idx = (
                    int(np.argmax(new_balances))
                    if rng.random() < audit
                    else int(rng.integers(0, n))
                )
                extract = penalty * new_balances[target_idx]
                new_balances[target_idx] = max(0.01, new_balances[target_idx] - extract)
                if n > 1:
                    share = extract * 0.6 / (n - 1)
                    for j in range(n):
                        if j != target_idx:
                            new_balances[j] += share

            # Cooperative surplus sharing
            if coop_share > 0 and n > 1:
                rich_idx = int(np.argmax(new_balances))
                for j in range(n):
                    if j != rich_idx:
                        transfer = coop_share * new_balances[rich_idx] / (n - 1)
                        new_balances[rich_idx] -= transfer
                        new_balances[j] += transfer

            balances = new_balances
            welfare_traj.append(float(np.mean(balances)))
            gini_traj.append(_gini(balances))

        return welfare_traj, gini_traj


def _gini(arr: np.ndarray) -> float:
    """Gini coefficient of a 1-D numpy array."""
    a = np.sort(arr.astype(float))
    n = len(a)
    if n == 0 or a.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2.0 * (idx * a).sum()) / (n * a.sum()) - (n + 1.0) / n)


# ============================================================================
# MockArenaProblem — pymoo wrapper for NSGA-II
# ============================================================================

try:
    from pymoo.core.problem import ElementwiseProblem as _ElementwiseProblem

    class MockArenaProblem(_ElementwiseProblem):
        """pymoo ``ElementwiseProblem`` wrapper for :class:`MockArena`.

        2 variables (risk, dispersal) ∈ [0, 1]², 2 objectives
        (−mean_biomass, variance).
        """

        def __init__(
            self,
            arena: MockArena,
            n_scenarios: int = 8,
            n_episodes: int = 5,
            seed_base: int = 0,
        ) -> None:
            super().__init__(n_var=2, n_obj=2, xl=[0.0, 0.0], xu=[1.0, 1.0])
            self.arena = arena
            self.n_scenarios = n_scenarios
            self.n_episodes = n_episodes
            self.seed_base = seed_base

        def _evaluate(self, x, out, *args, **kwargs):
            genes = (float(x[0]), float(x[1]))
            f1, f2 = self.arena.evaluate_genes(
                genes,
                n_scenarios=self.n_scenarios,
                n_episodes=self.n_episodes,
                seed_base=self.seed_base,
            )
            out["F"] = [f1, f2]

except ImportError:
    # pymoo not installed — MockArenaProblem unavailable but other classes still work.
    pass
