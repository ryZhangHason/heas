#!/usr/bin/env python3
"""
experiments/near_tie_tournament.py
==================================
Supplementary tournament experiment that automatically searches for participant
trait sets and scoring conditions that induce voting-rule disagreement.

Why this exists
---------------
The main tournament_stress experiment often yields unanimous agreement across
argmax/majority/Borda/Copeland when one participant dominates. This script
searches near-tie settings and reports the best disagreement case found.

Outputs
-------
experiments/results/near_tie_tournament/
  - search_summary.json
  - best_case.json
  - best_agreement_matrix.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import tournament_stress as ts
from common import print_config_header, results_path, save_json


@dataclass
class SearchConfig:
    trials: int
    repeats_search: int
    repeats_final: int
    episodes_grid: Sequence[int]
    noise_grid: Sequence[float]
    seed: int
    smoke: bool


def _offdiag_agreement_mean(matrix: np.ndarray) -> float:
    vals: List[float] = []
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            if i < j:
                vals.append(float(matrix[i, j]))
    return float(np.mean(vals)) if vals else 1.0


def _sample_near_tie_traits(rng: random.Random) -> Dict[str, Dict[str, float]]:
    # Center in middle of trait space and apply small perturbations to create
    # close competitors likely to induce near ties.
    center_risk = rng.uniform(0.35, 0.65)
    center_disp = rng.uniform(0.35, 0.65)
    delta = rng.uniform(0.01, 0.08)
    return {
        "A": {
            "risk": max(0.0, min(1.0, center_risk - delta)),
            "dispersal": max(0.0, min(1.0, center_disp + delta)),
        },
        "B": {
            "risk": max(0.0, min(1.0, center_risk)),
            "dispersal": max(0.0, min(1.0, center_disp)),
        },
        "C": {
            "risk": max(0.0, min(1.0, center_risk + delta)),
            "dispersal": max(0.0, min(1.0, center_disp - delta)),
        },
    }


def _compute_agreement_matrix(
    traits: Dict[str, Dict[str, float]],
    episodes_per_scenario: int,
    repeats: int,
    noise_sigma: float,
    base_seed: int,
) -> np.ndarray:
    rule_names = list(ts.VOTING_RULES.keys())
    agree = np.zeros((len(rule_names), len(rule_names)), dtype=int)

    # Save/restore global participant config used by tournament_stress helpers.
    orig_participants = ts.PARTICIPANTS[:]
    orig_traits = dict(ts.PARTICIPANT_TRAITS)
    try:
        ts.PARTICIPANTS[:] = list(traits.keys())
        ts.PARTICIPANT_TRAITS.clear()
        ts.PARTICIPANT_TRAITS.update(traits)

        total = repeats * len(ts.SCENARIOS)
        for rep in range(repeats):
            for sc in ts.SCENARIOS:
                seed = base_seed + rep * 100 + int(sc["scenario_id"])
                scores = ts._run_scenario_episodes(
                    scenario=sc,
                    n_episodes=episodes_per_scenario,
                    seed=seed,
                    noise_sigma=noise_sigma,
                )
                winners = {rule: fn(scores) for rule, fn in ts.VOTING_RULES.items()}
                for i, r1 in enumerate(rule_names):
                    for j, r2 in enumerate(rule_names):
                        if winners[r1] == winners[r2]:
                            agree[i, j] += 1
        return agree / total
    finally:
        ts.PARTICIPANTS[:] = orig_participants
        ts.PARTICIPANT_TRAITS.clear()
        ts.PARTICIPANT_TRAITS.update(orig_traits)


def run_search(cfg: SearchConfig) -> Dict[str, Any]:
    rng = random.Random(cfg.seed)
    rule_names = list(ts.VOTING_RULES.keys())

    best: Dict[str, Any] = {
        "disagreement_score": -1.0,  # 1 - mean_offdiag_agreement
    }
    history: List[Dict[str, Any]] = []

    for trial in range(cfg.trials):
        traits = _sample_near_tie_traits(rng)
        episodes = rng.choice(list(cfg.episodes_grid))
        noise = rng.choice(list(cfg.noise_grid))

        matrix = _compute_agreement_matrix(
            traits=traits,
            episodes_per_scenario=episodes,
            repeats=cfg.repeats_search,
            noise_sigma=float(noise),
            base_seed=cfg.seed + trial * 1000,
        )
        mean_agree = _offdiag_agreement_mean(matrix)
        disagreement = 1.0 - mean_agree
        row = {
            "trial": trial,
            "episodes_per_scenario": episodes,
            "noise_sigma": float(noise),
            "mean_offdiag_agreement": mean_agree,
            "disagreement_score": disagreement,
            "traits": traits,
        }
        history.append(row)

        if disagreement > float(best["disagreement_score"]):
            best = dict(row)
            best["agreement_matrix"] = matrix.tolist()
            print(
                f"  trial={trial:03d} new-best disagreement={disagreement:.4f} "
                f"(agree={mean_agree:.4f}, eps={episodes}, noise={noise})",
                flush=True,
            )

    # Re-evaluate best setting with larger repeats for stable estimate.
    final_matrix = _compute_agreement_matrix(
        traits=best["traits"],
        episodes_per_scenario=int(best["episodes_per_scenario"]),
        repeats=cfg.repeats_final,
        noise_sigma=float(best["noise_sigma"]),
        base_seed=cfg.seed + 999_999,
    )
    final_mean_agree = _offdiag_agreement_mean(final_matrix)

    out = {
        "config": {
            "trials": cfg.trials,
            "repeats_search": cfg.repeats_search,
            "repeats_final": cfg.repeats_final,
            "episodes_grid": list(cfg.episodes_grid),
            "noise_grid": list(cfg.noise_grid),
            "seed": cfg.seed,
        },
        "rule_names": rule_names,
        "best_search_case": best,
        "best_final_eval": {
            "traits": best["traits"],
            "episodes_per_scenario": int(best["episodes_per_scenario"]),
            "noise_sigma": float(best["noise_sigma"]),
            "agreement_matrix": final_matrix.tolist(),
            "mean_offdiag_agreement": final_mean_agree,
            "disagreement_score": 1.0 - final_mean_agree,
            "total_comparisons": cfg.repeats_final * len(ts.SCENARIOS),
        },
        "search_history_top10": sorted(
            history, key=lambda x: x["disagreement_score"], reverse=True
        )[:10],
    }
    return out


def _save_outputs(result: Dict[str, Any]) -> None:
    out_dir = results_path("near_tie_tournament")
    os.makedirs(out_dir, exist_ok=True)

    save_json(results_path("near_tie_tournament", "search_summary.json"), result)
    save_json(
        results_path("near_tie_tournament", "best_case.json"),
        result.get("best_final_eval", {}),
    )

    rules = result["rule_names"]
    matrix = result["best_final_eval"]["agreement_matrix"]
    csv_path = results_path("near_tie_tournament", "best_agreement_matrix.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rule"] + rules)
        for i, r in enumerate(rules):
            w.writerow([r] + [f"{float(matrix[i][j]):.4f}" for j in range(len(rules))])

    print("Saved:")
    print("  experiments/results/near_tie_tournament/search_summary.json")
    print("  experiments/results/near_tie_tournament/best_case.json")
    print("  experiments/results/near_tie_tournament/best_agreement_matrix.csv")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Search near-tie tournament disagreement settings")
    p.add_argument("--trials", type=int, default=120)
    p.add_argument("--repeats-search", type=int, default=6)
    p.add_argument("--repeats-final", type=int, default=30)
    p.add_argument("--episodes-grid", type=int, nargs="+", default=[4, 8, 12, 20])
    p.add_argument("--noise-grid", type=float, nargs="+", default=[0.0, 10.0, 25.0, 50.0, 100.0])
    p.add_argument("--seed", type=int, default=20260306)
    p.add_argument("--smoke", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    cfg = SearchConfig(
        trials=12 if args.smoke else args.trials,
        repeats_search=2 if args.smoke else args.repeats_search,
        repeats_final=4 if args.smoke else args.repeats_final,
        episodes_grid=[4, 8] if args.smoke else args.episodes_grid,
        noise_grid=[0.0, 25.0, 50.0] if args.smoke else args.noise_grid,
        seed=args.seed,
        smoke=args.smoke,
    )
    print_config_header(
        {
            "trials": cfg.trials,
            "repeats_search": cfg.repeats_search,
            "repeats_final": cfg.repeats_final,
            "episodes_grid": cfg.episodes_grid,
            "noise_grid": cfg.noise_grid,
            "seed": cfg.seed,
            "smoke": cfg.smoke,
        }
    )
    result = run_search(cfg)
    _save_outputs(result)
    best = result["best_final_eval"]
    print(
        f"Best final disagreement score: {best['disagreement_score']:.4f} "
        f"(mean offdiag agreement={best['mean_offdiag_agreement']:.4f})"
    )


if __name__ == "__main__":
    main()

