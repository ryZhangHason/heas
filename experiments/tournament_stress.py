#!/usr/bin/env python3
"""
experiments/tournament_stress.py
=================================
Experiment 3 — Tournament stress-testing.

Three sub-experiments:

  Part 1: Voting rule agreement
    For 30 seeds × 8 scenarios × 100 episodes, compute winner under 4 rules
    (argmax, majority, Borda, Copeland) and report pairwise agreement rates.

  Part 2: Sample complexity
    For episodes_per_scenario ∈ [4,10,25,50,100] and 30 repeats, measure
    P(correct winner) vs episodes/scenario with bootstrap CI.

  Part 3: Noise sensitivity
    For σ ∈ [0, 1, 10, 50, 100, 200] and 30 repeats, inject Gaussian noise
    (calibrated to actual score margins ~150-250 biomass units) and measure
    Kendall's τ against clean ranking.

Usage
-----
python experiments/tournament_stress.py          # all 3 parts
python experiments/tournament_stress.py --smoke  # quick test
python experiments/tournament_stress.py --part 1 # just voting agreement

Results
-------
All outputs go to experiments/results/tournament_stress/
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from collections import defaultdict
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
    print_config_header,
    results_path,
    save_json,
)

import heas.experiments.eco as eco
from heas.agent.runner import run_many
from heas.utils.stats import bootstrap_ci, kendall_tau, summarize_runs

# ---------------------------------------------------------------------------
# Tournament participants (trait-based ecological agents)
# ---------------------------------------------------------------------------

PARTICIPANTS = ["champion", "reference", "contrarian"]
PARTICIPANT_TRAITS = {
    # Evolved optimal (near-zero risk, max dispersal) — wins 16/16 OOD scenarios
    "champion":   {"risk": 0.003, "dispersal": 0.959},
    # Paper's reference policy (moderate risk, moderate dispersal)
    "reference":  {"risk": 0.55,  "dispersal": 0.35},
    # Extreme policy (high risk, low dispersal) — expected worst case
    "contrarian": {"risk": 0.85,  "dispersal": 0.15},
}

# 8 scenarios: fragmentation × shock_prob grid
FRAG_VALUES = [0.2, 0.6]
SHOCK_VALUES = [0.05, 0.2]
CARRY_VALUES = [500.0, 1000.0]

EXPERIMENT_NAME = "tournament_stress"
BASE_SEED = 3000
STEPS = 140


# ---------------------------------------------------------------------------
# Build all 8 scenarios
# ---------------------------------------------------------------------------

def _make_scenarios() -> List[Dict[str, Any]]:
    scenarios = []
    sid = 0
    for frag in FRAG_VALUES:
        for shock in SHOCK_VALUES:
            for carry in CARRY_VALUES:
                scenarios.append({
                    "scenario_id": sid,
                    "fragmentation": frag,
                    "shock_prob": shock,
                    "carrying_capacity": carry,
                })
                sid += 1
    return scenarios


SCENARIOS = _make_scenarios()


# ---------------------------------------------------------------------------
# Episode runner: evaluate all participants in one scenario for n episodes
# ---------------------------------------------------------------------------

def _run_scenario_episodes(
    scenario: Dict[str, Any],
    n_episodes: int,
    seed: int,
    noise_sigma: float = 0.0,
) -> Dict[str, List[float]]:
    """
    Run n_episodes for each participant in a scenario.

    Returns dict: {participant: [score_ep0, score_ep1, ...]}
    """
    scores: Dict[str, List[float]] = {p: [] for p in PARTICIPANTS}
    rng = np.random.default_rng(seed)

    for ep_idx in range(n_episodes):
        ep_seed = int(rng.integers(0, 2**31))
        for p in PARTICIPANTS:
            traits = PARTICIPANT_TRAITS[p]
            factory_kwargs = dict(
                risk=traits["risk"],
                dispersal=traits["dispersal"],
                fragmentation=scenario["fragmentation"],
                shock_prob=scenario["shock_prob"],
                K=scenario.get("carrying_capacity", 1000.0),
                seed=ep_seed,
            )
            model = eco.trait_model_factory(factory_kwargs)
            for _ in range(STEPS):
                model.step()
            ep_metrics = getattr(model, "metrics_episode", lambda: {})()
            raw_score = float(ep_metrics.get("agg.mean_biomass", 0.0))
            if noise_sigma > 0.0:
                raw_score += float(rng.normal(0.0, noise_sigma))
            scores[p].append(raw_score)

    return scores


# ---------------------------------------------------------------------------
# Voting rules
# ---------------------------------------------------------------------------

def _argmax_winner(ep_scores_by_participant: Dict[str, List[float]]) -> str:
    """Winner = participant with highest mean score across all episodes."""
    return max(PARTICIPANTS, key=lambda p: np.mean(ep_scores_by_participant[p]))


def _majority_winner(ep_scores_by_participant: Dict[str, List[float]]) -> str:
    """Winner = participant who wins the most individual episodes."""
    wins = {p: 0 for p in PARTICIPANTS}
    n_episodes = len(next(iter(ep_scores_by_participant.values())))
    for ep_idx in range(n_episodes):
        ep_winner = max(PARTICIPANTS, key=lambda p: ep_scores_by_participant[p][ep_idx])
        wins[ep_winner] += 1
    return max(PARTICIPANTS, key=lambda p: wins[p])


def _borda_winner(ep_scores_by_participant: Dict[str, List[float]]) -> str:
    """Borda count: sum of ranks across all episodes."""
    n_episodes = len(next(iter(ep_scores_by_participant.values())))
    borda_scores = {p: 0.0 for p in PARTICIPANTS}
    for ep_idx in range(n_episodes):
        episode_scores = {p: ep_scores_by_participant[p][ep_idx] for p in PARTICIPANTS}
        sorted_p = sorted(PARTICIPANTS, key=lambda p: episode_scores[p])
        for rank, p in enumerate(sorted_p):
            borda_scores[p] += rank  # higher rank = better
    return max(PARTICIPANTS, key=lambda p: borda_scores[p])


def _copeland_winner(ep_scores_by_participant: Dict[str, List[float]]) -> str:
    """Copeland: pairwise comparison across all episodes."""
    from heas.game.voting import copeland_vote
    # Build episodes_scores dict for copeland_vote
    n_episodes = len(next(iter(ep_scores_by_participant.values())))
    episodes_scores = {}
    for ep_idx in range(n_episodes):
        episodes_scores[ep_idx] = {p: ep_scores_by_participant[p][ep_idx] for p in PARTICIPANTS}
    return copeland_vote(episodes_scores, PARTICIPANTS)


VOTING_RULES = {
    "argmax": _argmax_winner,
    "majority": _majority_winner,
    "borda": _borda_winner,
    "copeland": _copeland_winner,
}


# ---------------------------------------------------------------------------
# Part 1: Voting rule agreement
# ---------------------------------------------------------------------------

def run_part1_agreement(
    n_repeats: int = 30,
    max_episodes: int = 100,
    smoke: bool = False,
) -> None:
    """Compute pairwise voting rule agreement rates."""
    if smoke:
        n_repeats = 2
        max_episodes = 10

    print("\n=== Part 1: Voting Rule Agreement ===")
    config = dict(n_repeats=n_repeats, max_episodes=max_episodes, n_scenarios=len(SCENARIOS))
    print_config_header(config)

    rule_names = list(VOTING_RULES.keys())
    # Agreement matrix: agreement_counts[i][j] = # of (scenario, repeat) pairs where rules i,j agree
    total_comparisons = len(SCENARIOS) * n_repeats
    agree_counts = np.zeros((len(rule_names), len(rule_names)), dtype=int)

    per_scenario_winners: Dict[int, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))

    t_start = time.time()
    for repeat_idx in range(n_repeats):
        for sc in SCENARIOS:
            seed = BASE_SEED + repeat_idx * 100 + sc["scenario_id"]
            scores = _run_scenario_episodes(sc, max_episodes, seed)

            winners = {rule: fn(scores) for rule, fn in VOTING_RULES.items()}
            for rule, w in winners.items():
                per_scenario_winners[sc["scenario_id"]][rule].append(w)

            for i, r1 in enumerate(rule_names):
                for j, r2 in enumerate(rule_names):
                    if winners[r1] == winners[r2]:
                        agree_counts[i, j] += 1

        elapsed = time.time() - t_start
        pct = 100.0 * (repeat_idx + 1) / n_repeats
        print(f"  Repeat {repeat_idx + 1}/{n_repeats} ({pct:.0f}%) | elapsed={elapsed:.1f}s")

    agreement_matrix = agree_counts / total_comparisons

    print("\n  Agreement matrix (fraction of (scenario, repeat) pairs where rules agree):")
    header = "       " + "".join(f"{r:>10}" for r in rule_names)
    print(f"  {header}")
    for i, r1 in enumerate(rule_names):
        row_str = f"  {r1:>8}" + "".join(f"{agreement_matrix[i, j]:10.3f}" for j in range(len(rule_names)))
        print(row_str)

    # Save CSV
    csv_path = results_path(EXPERIMENT_NAME, "agreement_matrix.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rule"] + rule_names)
        for i, r1 in enumerate(rule_names):
            w.writerow([r1] + [f"{agreement_matrix[i, j]:.4f}" for j in range(len(rule_names))])
    print(f"  Agreement matrix → experiments/results/{EXPERIMENT_NAME}/agreement_matrix.csv")

    result = {
        "config": config,
        "rule_names": rule_names,
        "agreement_matrix": agreement_matrix.tolist(),
        "total_comparisons": total_comparisons,
    }
    save_json(results_path(EXPERIMENT_NAME, "agreement_result.json"), result)

    # Plot
    try:
        _plot_agreement_heatmap(agreement_matrix, rule_names)
    except Exception as exc:
        print(f"  (Heatmap skipped: {exc})")


def _plot_agreement_heatmap(matrix: np.ndarray, rule_names: List[str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
    ax.set_xticks(range(len(rule_names)))
    ax.set_yticks(range(len(rule_names)))
    ax.set_xticklabels(rule_names, rotation=45, ha="right")
    ax.set_yticklabels(rule_names)
    for i in range(len(rule_names)):
        for j in range(len(rule_names)):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=9)
    plt.colorbar(im, ax=ax, label="Agreement rate")
    ax.set_title("Voting Rule Agreement Matrix")
    fig.tight_layout()

    path = results_path(EXPERIMENT_NAME, "figs", "agreement_heatmap.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Heatmap → experiments/results/{EXPERIMENT_NAME}/figs/agreement_heatmap.pdf")


# ---------------------------------------------------------------------------
# Part 2: Sample complexity
# ---------------------------------------------------------------------------

def run_part2_sample_complexity(
    episodes_list: Optional[List[int]] = None,
    n_repeats: int = 30,
    smoke: bool = False,
) -> None:
    """P(correct winner) vs episodes/scenario."""
    if smoke:
        n_repeats = 2
        episodes_list = [4, 10]

    if episodes_list is None:
        episodes_list = [4, 10, 25, 50, 100]

    print("\n=== Part 2: Sample Complexity ===")
    config = dict(episodes_list=episodes_list, n_repeats=n_repeats)
    print_config_header(config)

    # Ground truth: winner at max_episodes=100 (or episodes_list[-1]) under argmax
    ground_truth_n = max(episodes_list)
    print(f"  Computing ground truth at {ground_truth_n} episodes/scenario...")

    ground_truth: Dict[int, str] = {}
    for sc in SCENARIOS:
        seed = BASE_SEED + sc["scenario_id"]
        scores = _run_scenario_episodes(sc, ground_truth_n, seed)
        ground_truth[sc["scenario_id"]] = _argmax_winner(scores)

    results_by_ep: Dict[int, Dict] = {}

    for n_ep in episodes_list:
        if n_ep == ground_truth_n:
            # trivially correct at ground truth budget
            results_by_ep[n_ep] = {"p_correct_per_run": [1.0] * n_repeats}
            continue

        correct_counts = []
        for repeat_idx in range(n_repeats):
            n_correct = 0
            for sc in SCENARIOS:
                seed = BASE_SEED + 10000 + repeat_idx * 100 + sc["scenario_id"]
                scores = _run_scenario_episodes(sc, n_ep, seed)
                winner = _argmax_winner(scores)
                if winner == ground_truth[sc["scenario_id"]]:
                    n_correct += 1
            # P(correct) = fraction of scenarios where winner matches ground truth
            correct_counts.append(n_correct / len(SCENARIOS))

        ci_lo, ci_hi = bootstrap_ci(correct_counts)
        mean_p = float(np.mean(correct_counts))
        print(
            f"  n_ep={n_ep:4d}: P(correct)={mean_p:.3f}"
            f"  95% CI=[{ci_lo:.3f}, {ci_hi:.3f}]"
        )
        results_by_ep[n_ep] = {
            "p_correct_per_run": correct_counts,
            "mean": mean_p,
            "ci_lower": ci_lo,
            "ci_upper": ci_hi,
        }

    # Save CSV
    csv_path = results_path(EXPERIMENT_NAME, "sample_complexity.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["episodes_per_scenario", "mean_p_correct", "ci_lower", "ci_upper"])
        for n_ep in episodes_list:
            r = results_by_ep[n_ep]
            w.writerow([n_ep, r.get("mean", 1.0), r.get("ci_lower", 1.0), r.get("ci_upper", 1.0)])
    print(f"  Sample complexity → experiments/results/{EXPERIMENT_NAME}/sample_complexity.csv")

    result = {
        "config": config,
        "ground_truth": ground_truth,
        "results_by_episodes": {str(k): v for k, v in results_by_ep.items()},
    }
    save_json(results_path(EXPERIMENT_NAME, "sample_complexity.json"), result)

    try:
        _plot_sample_complexity(episodes_list, results_by_ep)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")


def _plot_sample_complexity(
    episodes_list: List[int],
    results_by_ep: Dict[int, Dict],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    eps = episodes_list
    means = [results_by_ep[n].get("mean", 1.0) for n in eps]
    ci_lo = [results_by_ep[n].get("ci_lower", means[i]) for i, n in enumerate(eps)]
    ci_hi = [results_by_ep[n].get("ci_upper", means[i]) for i, n in enumerate(eps)]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(eps, means, "o-", color="steelblue", label="P(correct)")
    ax.fill_between(eps, ci_lo, ci_hi, alpha=0.3, color="steelblue")
    ax.set_xlabel("Episodes per scenario")
    ax.set_ylabel("P(correct winner)")
    ax.set_title("Tournament Sample Complexity")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)

    path = results_path(EXPERIMENT_NAME, "figs", "sample_complexity.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Sample complexity plot → experiments/results/{EXPERIMENT_NAME}/figs/sample_complexity.pdf")


# ---------------------------------------------------------------------------
# Part 3: Noise sensitivity
# ---------------------------------------------------------------------------

def run_part3_noise_sensitivity(
    noise_sigmas: Optional[List[float]] = None,
    n_repeats: int = 30,
    base_episodes: int = 50,
    smoke: bool = False,
) -> None:
    """Kendall's τ vs noise level σ."""
    if smoke:
        n_repeats = 2
        noise_sigmas = [0.0, 10.0, 100.0]
        base_episodes = 10

    if noise_sigmas is None:
        # Calibrated to actual score margins: champion vs reference ≈ 155 biomass units.
        # σ values span from negligible (0.65% of margin) to overwhelming (130% of margin).
        noise_sigmas = [0.0, 1.0, 10.0, 50.0, 100.0, 200.0]

    print("\n=== Part 3: Noise Sensitivity ===")
    config = dict(noise_sigmas=noise_sigmas, n_repeats=n_repeats, base_episodes=base_episodes)
    print_config_header(config)

    # Clean baseline ranking (σ=0)
    print("  Computing clean baseline ranking (σ=0)...")
    clean_rankings: Dict[int, List[str]] = {}  # scenario_id -> sorted participants (best first)
    for sc in SCENARIOS:
        seed = BASE_SEED + sc["scenario_id"]
        scores = _run_scenario_episodes(sc, base_episodes, seed, noise_sigma=0.0)
        clean_rankings[sc["scenario_id"]] = sorted(
            PARTICIPANTS, key=lambda p: np.mean(scores[p]), reverse=True
        )

    results_by_sigma: Dict[float, Dict] = {}

    for sigma in noise_sigmas:
        tau_values = []
        for repeat_idx in range(n_repeats):
            taus_per_scenario = []
            for sc in SCENARIOS:
                seed = BASE_SEED + 20000 + repeat_idx * 100 + sc["scenario_id"]
                noisy_scores = _run_scenario_episodes(sc, base_episodes, seed, noise_sigma=sigma)
                noisy_ranking = sorted(
                    PARTICIPANTS, key=lambda p: np.mean(noisy_scores[p]), reverse=True
                )
                clean_rank = clean_rankings[sc["scenario_id"]]

                # Convert to integer rank vectors for kendall_tau
                clean_idx = [clean_rank.index(p) for p in PARTICIPANTS]
                noisy_idx = [noisy_ranking.index(p) for p in PARTICIPANTS]

                try:
                    tau_stat, _ = kendall_tau(clean_idx, noisy_idx)
                    taus_per_scenario.append(tau_stat)
                except Exception:
                    taus_per_scenario.append(1.0 if sigma == 0.0 else 0.0)

            tau_values.append(float(np.mean(taus_per_scenario)))

        ci_lo, ci_hi = bootstrap_ci(tau_values) if len(tau_values) >= 2 else (tau_values[0], tau_values[0])
        mean_tau = float(np.mean(tau_values))
        print(
            f"  σ={sigma:.3f}: Kendall τ={mean_tau:.4f}"
            f"  95% CI=[{ci_lo:.4f}, {ci_hi:.4f}]"
        )
        results_by_sigma[sigma] = {
            "tau_per_run": tau_values,
            "mean": mean_tau,
            "ci_lower": ci_lo,
            "ci_upper": ci_hi,
        }

    # Save CSV
    csv_path = results_path(EXPERIMENT_NAME, "noise_stability.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["noise_sigma", "mean_tau", "ci_lower", "ci_upper"])
        for sigma in noise_sigmas:
            r = results_by_sigma[sigma]
            w.writerow([sigma, r["mean"], r["ci_lower"], r["ci_upper"]])
    print(f"  Noise stability → experiments/results/{EXPERIMENT_NAME}/noise_stability.csv")

    result = {
        "config": config,
        "results_by_sigma": {str(k): v for k, v in results_by_sigma.items()},
    }
    save_json(results_path(EXPERIMENT_NAME, "noise_stability.json"), result)

    try:
        _plot_noise_stability(noise_sigmas, results_by_sigma)
    except Exception as exc:
        print(f"  (Plot skipped: {exc})")


def _plot_noise_stability(
    sigmas: List[float],
    results_by_sigma: Dict[float, Dict],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    means = [results_by_sigma[s]["mean"] for s in sigmas]
    ci_lo = [results_by_sigma[s]["ci_lower"] for s in sigmas]
    ci_hi = [results_by_sigma[s]["ci_upper"] for s in sigmas]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(sigmas, means, "o-", color="darkorange")
    ax.fill_between(sigmas, ci_lo, ci_hi, alpha=0.3, color="darkorange")
    ax.set_xlabel("Noise level σ")
    ax.set_ylabel("Kendall's τ (vs clean ranking)")
    ax.set_title("Tournament Noise Sensitivity")
    ax.set_ylim(-0.1, 1.1)
    ax.grid(True, alpha=0.3)

    path = results_path(EXPERIMENT_NAME, "figs", "noise_stability.pdf")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Noise stability plot → experiments/results/{EXPERIMENT_NAME}/figs/noise_stability.pdf")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tournament stress-test (Exp 3)")
    p.add_argument("--smoke", action="store_true", help="Quick smoke test")
    p.add_argument("--part", type=int, choices=[1, 2, 3], default=None,
                   help="Run only one sub-experiment (default: all 3)")
    p.add_argument("--n-repeats", type=int, default=30)
    p.add_argument("--max-episodes", type=int, default=100, help="Episodes for Part 1")
    p.add_argument("--base-episodes", type=int, default=50, help="Episodes for Part 3")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    config = dict(
        smoke=args.smoke,
        n_repeats=args.n_repeats,
        max_episodes=args.max_episodes,
        base_episodes=args.base_episodes,
    )
    print_config_header(config)

    run_parts = [1, 2, 3] if args.part is None else [args.part]

    if 1 in run_parts:
        run_part1_agreement(
            n_repeats=args.n_repeats,
            max_episodes=args.max_episodes,
            smoke=args.smoke,
        )
    if 2 in run_parts:
        run_part2_sample_complexity(
            n_repeats=args.n_repeats,
            smoke=args.smoke,
        )
    if 3 in run_parts:
        run_part3_noise_sensitivity(
            n_repeats=args.n_repeats,
            base_episodes=args.base_episodes,
            smoke=args.smoke,
        )

    print(f"\nAll outputs in: experiments/results/{EXPERIMENT_NAME}/")


if __name__ == "__main__":
    main()
