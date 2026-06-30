"""
heas.experiments.schelling
===========================
Schelling Segregation model for multi-ABM MAD experiments (EA-6, EA-7).

A lightweight, numpy-vectorised implementation of the classic Schelling
segregation model.  No Mesa dependency required.

**Policy genes (2)**:
    homophily  ∈ [0.1, 0.9] — fraction of same-type neighbours required for happiness
    density    ∈ [0.4, 0.8] — fraction of grid cells occupied

**Objectives** (NSGA-II, both minimised):
    −mean_happiness   (maximise average fraction of happy agents)
     var_happiness    (minimise trajectory instability)

The model runs on a toroidal grid with Moore neighbourhood (8 neighbours).
Unhappy agents move to random empty cells each step.  The simulation returns
a happiness trajectory (fraction of satisfied agents per step).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np


def run_episode(
    homophily: float,
    density: float,
    seed: int,
    n_steps: int = 80,
    grid_size: int = 15,
) -> List[float]:
    """Run one episode of the Schelling segregation model.

    Parameters
    ----------
    homophily:
        Minimum fraction of same-type neighbours for an agent to be happy.
    density:
        Fraction of grid cells that are occupied.
    seed:
        RNG seed.
    n_steps:
        Maximum number of simulation steps.
    grid_size:
        Side length of the square grid.

    Returns
    -------
    happiness : list of float
        Fraction of happy agents at each step (length ≤ *n_steps*).
    """
    rng = np.random.default_rng(seed)
    n_total = grid_size * grid_size
    n_agents = int(density * n_total)
    n_agents = max(n_agents, 2)
    n_red = n_agents // 2

    cells = np.zeros(n_total, dtype=np.int8)
    positions = rng.choice(n_total, n_agents, replace=False)
    cells[positions[:n_red]] = 1   # red
    cells[positions[n_red:]] = 2   # blue
    grid = cells.reshape(grid_size, grid_size)

    happiness_traj: List[float] = []
    consecutive_happy = 0

    # Moore neighbourhood offsets (8 directions)
    SHIFTS = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),           ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1),
    ]

    for _step in range(n_steps):
        # Vectorised neighbourhood count
        n_same = np.zeros((grid_size, grid_size), dtype=np.float32)
        n_occ = np.zeros((grid_size, grid_size), dtype=np.float32)

        for di, dj in SHIFTS:
            shifted = np.roll(np.roll(grid, di, axis=0), dj, axis=1)
            occupied_shifted = shifted != 0
            n_occ += occupied_shifted.astype(np.float32)
            n_same += ((shifted == grid) & occupied_shifted).astype(np.float32)

        occupied = grid != 0
        no_nbr = occupied & (n_occ == 0)

        with np.errstate(divide="ignore", invalid="ignore"):
            same_frac = np.where(
                n_occ > 0,
                n_same / np.where(n_occ > 0, n_occ, 1.0),
                0.0,
            )
        is_happy = (same_frac >= homophily) | no_nbr

        n_occupied = occupied.sum()
        if n_occupied > 0:
            happiness_traj.append(float(is_happy[occupied].mean()))
        else:
            happiness_traj.append(0.0)

        # Convergence check
        frac_happy = happiness_traj[-1]
        if frac_happy > 0.99:
            consecutive_happy += 1
            if consecutive_happy >= 5:
                break
        else:
            consecutive_happy = 0

        # Move unhappy agents to random empty cells
        unhappy_mask = occupied & ~is_happy
        unhappy_flat = np.where(unhappy_mask.ravel())[0]
        empty_flat = np.where((grid == 0).ravel())[0]

        if len(unhappy_flat) > 0 and len(empty_flat) > 0:
            rng.shuffle(unhappy_flat)
            n_moves = min(len(unhappy_flat), len(empty_flat))
            move_src = unhappy_flat[:n_moves]
            dest_idx = rng.choice(len(empty_flat), n_moves, replace=False)
            move_dst = empty_flat[dest_idx]

            flat_grid = grid.ravel().copy()
            flat_grid[move_dst] = flat_grid[move_src]
            flat_grid[move_src] = 0
            grid = flat_grid.reshape(grid_size, grid_size)

    return happiness_traj


def score_detailed(
    homophily: float,
    density: float,
    seed: int,
    n_steps: int = 80,
) -> Dict[str, float]:
    """Return per-episode score dict (mirrors MockArena.score_detailed).

    Keys: final, mean, median, q75, entropy.
    """
    traj = run_episode(homophily, density, seed, n_steps=n_steps)
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
    homophily: float,
    density: float,
    n_scenarios: int = 8,
    n_episodes: int = 5,
    n_steps: int = 80,
    seed_base: int = 0,
) -> Tuple[float, float]:
    """Return ``(obj1, obj2)`` for NSGA-II minimisation.

    ``obj1 = −mean_happiness`` (minimise → maximise happiness),
    ``obj2 =  var_happiness`` (minimise → reduce instability).
    """
    all_means: List[float] = []
    all_vars: List[float] = []
    for sc in range(n_scenarios):
        for ep in range(n_episodes):
            seed = seed_base + sc * 1000 + ep
            traj = run_episode(homophily, density, seed, n_steps=n_steps)
            arr = np.array(traj)
            all_means.append(float(np.mean(arr)) if arr.size > 0 else 0.0)
            all_vars.append(float(np.var(arr)) if arr.size > 0 else 0.0)
    return -float(np.mean(all_means)), float(np.mean(all_vars))


# ---------------------------------------------------------------------------
# pymoo wrapper (optional)
# ---------------------------------------------------------------------------

try:
    from pymoo.core.problem import ElementwiseProblem as _ElementwiseProblem

    class SchellingProblem(_ElementwiseProblem):
        """pymoo ``ElementwiseProblem`` wrapper for Schelling segregation.

        2 variables (homophily, density), 2 objectives.
        """

        def __init__(
            self,
            n_scenarios: int = 8,
            n_episodes: int = 5,
            n_steps: int = 80,
            seed_base: int = 0,
        ) -> None:
            super().__init__(
                n_var=2, n_obj=2,
                xl=[0.1, 0.4],
                xu=[0.9, 0.8],
            )
            self.n_scenarios = n_scenarios
            self.n_episodes = n_episodes
            self.n_steps = n_steps
            self.seed_base = seed_base

        def _evaluate(self, x, out, *args, **kwargs):
            f1, f2 = evaluate_genes(
                homophily=float(x[0]),
                density=float(x[1]),
                n_scenarios=self.n_scenarios,
                n_episodes=self.n_episodes,
                n_steps=self.n_steps,
                seed_base=self.seed_base,
            )
            out["F"] = [f1, f2]

except ImportError:
    pass
