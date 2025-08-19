
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Sequence
from ..utils.rng import seed_everything

def run_episode(model_factory: Callable[[dict], Any], steps: int, seed: int, per_step_metrics: Optional[Sequence[str]]=None, per_episode_metrics: Optional[Sequence[str]]=None, **model_kwargs) -> Dict[str, Any]:
    seed_everything(seed)
    model = model_factory(model_kwargs)
    step_log: List[Dict[str, Any]] = []
    for _ in range(steps):
        model.step()
        m = getattr(model, "metrics_step", lambda: {})()
        step_log.append(m)
    episode_metrics = getattr(model, "metrics_episode", lambda: {})()
    return {
        "seed": seed,
        "steps": steps,
        "per_step": step_log,
        "episode": episode_metrics
    }

def run_many(model_factory: Callable[[dict], Any], steps: int, episodes: int, seed: int, per_step_metrics=None, per_episode_metrics=None, **model_kwargs) -> Dict[str, Any]:
    runs = []
    for i in range(episodes):
        ep_seed = seed + i
        result = run_episode(model_factory, steps, ep_seed, per_step_metrics, per_episode_metrics, **model_kwargs)
        runs.append(result)
    return {
        "episodes": runs
    }
