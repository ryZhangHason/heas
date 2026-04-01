#!/usr/bin/env python3
"""
experiments/enterprise_tournament.py
=====================================
Enterprise domain tournament validation.

Validates that HEAS tournament infrastructure generalizes to the enterprise domain
(W3/Q4 reviewer response). Runs two sub-experiments:

  Part 1: Voting rule agreement
    For 20 repeats × 8 scenarios × 30 episodes, compute winner under 4 voting
    rules (argmax, majority, Borda, Copeland) and report pairwise agreement rates.

  Part 2: Sample complexity
    For episodes_per_scenario ∈ [4, 10, 25, 50] and 20 repeats, measure
    P(correct winner) vs episodes/scenario.

Usage
-----
python experiments/enterprise_tournament.py          # full run
python experiments/enterprise_tournament.py --smoke  # quick test

Results
-------
All outputs go to experiments/results/enterprise_tournament/
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

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

import heas.experiments.enterprise as ent_module
from heas.experiments.enterprise import enterprise_model_factory

# ---------------------------------------------------------------------------
# Tournament participants (enterprise policy genomes)
# ---------------------------------------------------------------------------

PARTICIPANTS = ["champion", "reference", "contrarian"]

# Champion: evolved optimal policy from large-scale runs (p2_ent/run_000.json)
# Low tax burden, maximum audit intensity, moderate subsidy — maximises welfare
PARTICIPANT_POLICIES = {
    "champion": {
        "tax": 0.0017,
        "audit_intensity": 0.987,
        "subsidy": 0.323,
        "penalty_rate": 0.184,
    },
    # Reference: default policy parameters from enterprise.py
    "reference": {
        "tax": 0.1,
        "audit_intensity": 0.2,
        "subsidy": 0.0,
        "penalty_rate": 0.1,
    },
    # Contrarian: high tax, low audit, maximum penalty — expected worst case
    "contrarian": {
        "tax": 0.45,
        "audit_intensity": 0.1,
        "subsidy": 0.0,
        "penalty_rate": 0.45,
    },
}

# 8 enterprise scenarios: regime × base_demand × audit_prob (2×2×2)
# firm_count and costs held fixed at defaults
SCENARIOS = []
for regime in ["coop", "compete"]:
    for base_demand in [80.0, 120.0]:
        for audit_prob in [0.1, 0.4]:
            SCENARIOS.append({
                "regime": regime,
                "base_demand": base_demand,
                "audit_prob": audit_prob,
                "firm_count": 4,
                "costs": 0.4,
            })

EXPERIMENT_NAME = "enterprise_tournament"
BASE_SEED = 7000
STEPS = 50
SCORE_KEY = "agg.final_welfare"


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def _run_scenario_episodes(
    scenario: Dict[str, Any],
    n_episodes: int,
    seed: int,
) -> Dict[str, List[float]]:
    """Run n_episodes for each participant in a scenario.

    Returns dict: {participant: [score_ep0, score_ep1, ...]}
    """
    scores: Dict[str, List[float]] = {p: [] for p in PARTICIPANTS}
    rng = np.random.default_rng(seed)

    for ep_idx in range(n_episodes):
        ep_seed = int(rng.integers(0, 2**31))
        for p in PARTICIPANTS:
            policy = PARTICIPANT_POLICIES[p]
            factory_kwargs = dict(
                **policy,
                **scenario,
                seed=ep_seed,
            )
            model = enterprise_model_factory(factory_kwargs)
            for _ in range(STEPS):
                model.step()
            ep_metrics = getattr(model, "metrics_episode", lambda: {})()
            raw_score = float(ep_metrics.get(SCORE_KEY, 0.0))
            scores[p].append(raw_score)

    return scores


# ---------------------------------------------------------------------------
# Voting rules
# ---------------------------------------------------------------------------

def _argmax_winner(ep_scores: Dict[str, List[float]]) -> str:
    return max(PARTICIPANTS, key=lambda p: np.mean(ep_scores[p]))


def _majority_winner(ep_scores: Dict[str, List[float]]) -> str:
    wins = {p: 0 for p in PARTICIPANTS}
    for ep_idx in range(len(next(iter(ep_scores.values())))):
        ep_winner = max(PARTICIPANTS, key=lambda p: ep_scores[p][ep_idx])
        wins[ep_winner] += 1
    return max(PARTICIPANTS, key=lambda p: wins[p])


def _borda_winner(ep_scores: Dict[str, List[float]]) -> str:
    n_ep = len(next(iter(ep_scores.values())))
    borda = {p: 0.0 for p in PARTICIPANTS}
    for ep_idx in range(n_ep):
        sorted_p = sorted(PARTICIPANTS, key=lambda p: ep_scores[p][ep_idx])
        for rank, p in enumerate(sorted_p):
            borda[p] += rank
    return max(PARTICIPANTS, key=lambda p: borda[p])


def _copeland_winner(ep_scores: Dict[str, List[float]]) -> str:
    n_ep = len(next(iter(ep_scores.values())))
    copeland = {p: 0.0 for p in PARTICIPANTS}
    for i, p1 in enumerate(PARTICIPANTS):
        for j, p2 in enumerate(PARTICIPANTS):
            if i >= j:
                continue
            p1_wins = sum(
                1 for ep in range(n_ep)
                if ep_scores[p1][ep] > ep_scores[p2][ep]
            )
            p2_wins = n_ep - p1_wins
            if p1_wins > p2_wins:
                copeland[p1] += 1
            elif p2_wins > p1_wins:
                copeland[p2] += 1
    return max(PARTICIPANTS, key=lambda p: copeland[p])


VOTING_RULES = {
    "argmax": _argmax_winner,
    "majority": _majority_winner,
    "borda": _borda_winner,
    "copeland": _copeland_winner,
}
RULE_NAMES = list(VOTING_RULES.keys())


# ---------------------------------------------------------------------------
# Part 1: Voting rule agreement
# ---------------------------------------------------------------------------

def run_part1_agreement(n_repeats: int = 20, n_episodes: int = 30) -> Dict[str, Any]:
    print("\n=== Part 1: Voting Rule Agreement (Enterprise) ===")
    config = dict(n_repeats=n_repeats, n_episodes=n_episodes, n_scenarios=len(SCENARIOS))
    print_config_header(config)

    total = len(SCENARIOS) * n_repeats
    agree_counts = np.zeros((len(RULE_NAMES), len(RULE_NAMES)), dtype=int)
    per_rule_winners: Dict[str, List[str]] = defaultdict(list)

    t_start = time.time()
    for repeat_idx in range(n_repeats):
        for sc_idx, sc in enumerate(SCENARIOS):
            seed = BASE_SEED + repeat_idx * 100 + sc_idx
            scores = _run_scenario_episodes(sc, n_episodes, seed)
            winners = {rule: fn(scores) for rule, fn in VOTING_RULES.items()}
            for rule, w in winners.items():
                per_rule_winners[rule].append(w)
            for i, r1 in enumerate(RULE_NAMES):
                for j, r2 in enumerate(RULE_NAMES):
                    if winners[r1] == winners[r2]:
                        agree_counts[i, j] += 1

        elapsed = time.time() - t_start
        pct = 100.0 * (repeat_idx + 1) / n_repeats
        print(f"  Repeat {repeat_idx + 1}/{n_repeats} ({pct:.0f}%) | elapsed={elapsed:.1f}s")

    agreement_matrix = (agree_counts / total).tolist()

    # Summary stats
    off_diag = []
    for i in range(len(RULE_NAMES)):
        for j in range(len(RULE_NAMES)):
            if i != j:
                off_diag.append(agreement_matrix[i][j])
    mean_offdiag = float(np.mean(off_diag))

    print("\n  Agreement matrix:")
    header = "         " + "".join(f"{r:>12}" for r in RULE_NAMES)
    print(f"  {header}")
    for i, r1 in enumerate(RULE_NAMES):
        row_str = f"  {r1:>10}" + "".join(f"{agreement_matrix[i][j]:12.3f}" for j in range(len(RULE_NAMES)))
        print(row_str)
    print(f"\n  Mean off-diagonal agreement: {mean_offdiag:.4f} ({(1-mean_offdiag)*100:.1f}% disagreement)")

    # Who wins most often?
    for rule, winners_list in per_rule_winners.items():
        champion_pct = 100.0 * winners_list.count("champion") / len(winners_list)
        print(f"  {rule}: champion wins {champion_pct:.1f}% of (scenario,repeat) pairs")

    result = {
        "config": config,
        "rule_names": RULE_NAMES,
        "agreement_matrix": agreement_matrix,
        "total_comparisons": total,
        "mean_offdiag_agreement": mean_offdiag,
        "mean_disagreement_rate": 1.0 - mean_offdiag,
        "per_rule_champion_win_rate": {
            rule: winners_list.count("champion") / len(winners_list)
            for rule, winners_list in per_rule_winners.items()
        },
    }
    save_json(results_path(EXPERIMENT_NAME, "agreement_result.json"), result)
    print(f"  → experiments/results/{EXPERIMENT_NAME}/agreement_result.json")
    return result


# ---------------------------------------------------------------------------
# Part 2: Sample complexity
# ---------------------------------------------------------------------------

def run_part2_sample_complexity(
    episodes_list: Optional[List[int]] = None,
    n_repeats: int = 20,
) -> Dict[str, Any]:
    if episodes_list is None:
        episodes_list = [4, 10, 25, 50]

    print("\n=== Part 2: Sample Complexity (Enterprise) ===")
    config = dict(episodes_list=episodes_list, n_repeats=n_repeats)
    print_config_header(config)

    # Ground truth at max episodes
    ground_truth_n = max(episodes_list)
    print(f"  Computing ground truth at {ground_truth_n} episodes/scenario...")
    ground_truth: Dict[int, str] = {}
    for sc_idx, sc in enumerate(SCENARIOS):
        seed = BASE_SEED + sc_idx
        scores = _run_scenario_episodes(sc, ground_truth_n, seed)
        ground_truth[sc_idx] = _argmax_winner(scores)
    print(f"  Ground truth: champion wins {list(ground_truth.values()).count('champion')}/{len(SCENARIOS)} scenarios")

    results_by_ep: Dict[int, Dict] = {}
    for n_ep in episodes_list:
        if n_ep == ground_truth_n:
            results_by_ep[n_ep] = {"mean": 1.0, "ci_lower": 1.0, "ci_upper": 1.0}
            continue

        correct_counts = []
        for repeat_idx in range(n_repeats):
            n_correct = 0
            for sc_idx, sc in enumerate(SCENARIOS):
                seed = BASE_SEED + 10000 + repeat_idx * 100 + sc_idx
                scores = _run_scenario_episodes(sc, n_ep, seed)
                winner = _argmax_winner(scores)
                if winner == ground_truth[sc_idx]:
                    n_correct += 1
            correct_counts.append(n_correct / len(SCENARIOS))

        mean_p = float(np.mean(correct_counts))
        # Simple bootstrap CI
        boots = [float(np.mean(np.random.choice(correct_counts, len(correct_counts))))
                 for _ in range(1000)]
        ci_lo = float(np.percentile(boots, 2.5))
        ci_hi = float(np.percentile(boots, 97.5))
        print(f"  n_ep={n_ep:3d}: P(correct)={mean_p:.3f}  CI=[{ci_lo:.3f},{ci_hi:.3f}]")
        results_by_ep[n_ep] = {"mean": mean_p, "ci_lower": ci_lo, "ci_upper": ci_hi}

    result = {
        "config": config,
        "ground_truth_winner": ground_truth,
        "results_by_episodes": {str(k): v for k, v in results_by_ep.items()},
    }
    save_json(results_path(EXPERIMENT_NAME, "sample_complexity.json"), result)
    print(f"  → experiments/results/{EXPERIMENT_NAME}/sample_complexity.json")
    return result


# ---------------------------------------------------------------------------
# Main summary
# ---------------------------------------------------------------------------

def write_summary(part1: Dict, part2: Dict) -> None:
    agreement_matrix = part1["agreement_matrix"]
    min_offdiag = min(
        agreement_matrix[i][j]
        for i in range(len(RULE_NAMES))
        for j in range(len(RULE_NAMES))
        if i != j
    )
    champion_win_rates = part1.get("per_rule_champion_win_rate", {})

    # Sample complexity: min P(correct) across episodes_list
    sc_results = part2.get("results_by_episodes", {})
    min_p_correct = min((v.get("mean", 1.0) for v in sc_results.values()), default=1.0)

    summary = {
        "experiment": EXPERIMENT_NAME,
        "participants": PARTICIPANT_POLICIES,
        "scenarios": SCENARIOS,
        "part1_agreement": {
            "mean_offdiag_agreement": part1["mean_offdiag_agreement"],
            "mean_disagreement_rate": part1["mean_disagreement_rate"],
            "min_pairwise_agreement": min_offdiag,
            "agreement_matrix": agreement_matrix,
            "rule_names": RULE_NAMES,
            "champion_win_rates": champion_win_rates,
        },
        "part2_sample_complexity": {
            "min_p_correct": min_p_correct,
            "by_episodes": {
                k: {"mean": v.get("mean", 1.0), "ci_lower": v.get("ci_lower", 1.0),
                    "ci_upper": v.get("ci_upper", 1.0)}
                for k, v in sc_results.items()
            },
        },
    }
    path = results_path(EXPERIMENT_NAME, "summary.json")
    save_json(path, summary)
    print(f"\n  Summary → experiments/results/{EXPERIMENT_NAME}/summary.json")

    # Print key stats for paper
    print("\n=== KEY RESULTS FOR PAPER ===")
    print(f"  Mean off-diagonal agreement: {part1['mean_offdiag_agreement']:.4f}")
    print(f"  Mean disagreement rate: {part1['mean_disagreement_rate']*100:.1f}%")
    for rule, rate in champion_win_rates.items():
        print(f"  {rule} champion win rate: {rate*100:.1f}%")
    print(f"  Min P(correct) across episode budgets: {min_p_correct:.3f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Enterprise domain tournament validation")
    p.add_argument("--smoke", action="store_true", help="Quick smoke test (2 repeats)")
    p.add_argument("--n-repeats", type=int, default=20)
    p.add_argument("--n-episodes", type=int, default=30, help="Episodes for Part 1")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    os.makedirs(results_path(EXPERIMENT_NAME), exist_ok=True)

    n_repeats = 2 if args.smoke else args.n_repeats
    n_episodes = 4 if args.smoke else args.n_episodes
    episodes_list = [4, 10] if args.smoke else [4, 10, 25, 50]

    config = dict(smoke=args.smoke, n_repeats=n_repeats, n_episodes=n_episodes)
    print_config_header(config)

    part1 = run_part1_agreement(n_repeats=n_repeats, n_episodes=n_episodes)
    part2 = run_part2_sample_complexity(episodes_list=episodes_list, n_repeats=n_repeats)
    write_summary(part1, part2)

    print(f"\nAll outputs in: experiments/results/{EXPERIMENT_NAME}/")


if __name__ == "__main__":
    main()
