from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict

from .config import Experiment, Algorithm, Evaluation
from .utils.rng import seed_everything
from .utils.io import ensure_dir
from .utils.metrics import summarize_metrics

def simulate(exp: Experiment) -> Dict[str, Any]:
    seed_everything(exp.seed)
    try:
        from .agent.runner import run_many
    except Exception as e:
        raise RuntimeError("Mesa integration not available. Ensure 'mesa>=2.1' is installed.") from e

    results = run_many(
        model_factory=exp.model_factory,
        steps=exp.steps,
        episodes=exp.episodes,
        seed=exp.seed,
        per_step_metrics=exp.per_step_metrics,
        per_episode_metrics=exp.per_episode_metrics,
    )
    return results

def optimize(exp: Experiment, algo: Algorithm) -> Dict[str, Any]:
    seed_everything(exp.seed)
    ensure_dir(algo.out_dir)
    try:
        from .evolution.algorithms import run_ea
    except Exception as e:
        raise RuntimeError("DEAP integration not available. Ensure 'deap>=1.3' is installed.") from e
    return run_ea(exp=exp, algo=algo)

def evaluate(exp: Experiment, eval_cfg: Evaluation) -> Dict[str, Any]:
    seed_everything(exp.seed)
    scores = [eval_cfg.objective_fn(g) for g in eval_cfg.genotypes]
    summary = summarize_metrics(scores)
    return {
        "n": len(scores),
        "summary": summary,
        "raw": scores,
        "config": {
            "experiment": asdict(exp),
            "evaluation": asdict(eval_cfg)
        }
    }