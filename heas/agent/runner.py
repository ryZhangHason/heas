from __future__ import annotations

import concurrent.futures
import os
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..utils.rng import seed_everything


def run_episode(
    model_factory: Callable[[dict], Any],
    steps: int,
    seed: int,
    per_step_metrics: Optional[Sequence[str]] = None,
    per_episode_metrics: Optional[Sequence[str]] = None,
    **model_kwargs,
) -> Dict[str, Any]:
    """Run a single simulation episode and return metrics.

    Parameters
    ----------
    model_factory:
        Callable ``(kwargs: dict) -> model``; the model must have ``.step()``
        and optionally ``.metrics_step()`` / ``.metrics_episode()``.
    steps:
        Number of ticks to simulate.
    seed:
        RNG seed applied via :func:`heas.utils.rng.seed_everything`.
    per_step_metrics:
        Unused filter (kept for API compatibility).
    per_episode_metrics:
        Unused filter (kept for API compatibility).
    **model_kwargs:
        Forwarded to *model_factory*.

    Returns
    -------
    dict with keys ``seed``, ``steps``, ``per_step`` (list of dicts),
    ``episode`` (dict).
    """
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
        "episode": episode_metrics,
    }


# ---------------------------------------------------------------------------
# Module-level worker — must NOT be a closure or lambda so it is picklable
# by concurrent.futures.ProcessPoolExecutor.
# ---------------------------------------------------------------------------

def _run_episode_worker(args: tuple) -> Dict[str, Any]:
    """Unpacks *args* and delegates to :func:`run_episode`.

    *args* = (model_factory, steps, seed, per_step_metrics,
               per_episode_metrics, model_kwargs_dict)
    """
    model_factory, steps, seed, ps_metrics, ep_metrics, model_kwargs = args
    return run_episode(
        model_factory, steps, seed,
        ps_metrics, ep_metrics,
        **model_kwargs,
    )


def run_many(
    model_factory: Callable[[dict], Any],
    steps: int,
    episodes: int,
    seed: int,
    per_step_metrics: Optional[Sequence[str]] = None,
    per_episode_metrics: Optional[Sequence[str]] = None,
    n_jobs: int = 1,
    **model_kwargs,
) -> Dict[str, Any]:
    """Run *episodes* independent episodes, optionally in parallel.

    Parameters
    ----------
    model_factory, steps, seed:
        Same as :func:`run_episode`.
    episodes:
        Number of independent episodes to run.  Episode *i* uses seed
        ``seed + i``.
    n_jobs:
        Number of parallel worker processes.

        * ``1`` (default) — sequential; original behaviour preserved.
        * ``-1`` — use ``os.cpu_count()`` workers.
        * ``> 1`` — use exactly *n_jobs* workers.

        .. note::
            *model_factory* must be **picklable** (i.e. defined at module
            level, not as a lambda or closure) when ``n_jobs != 1``.

    Returns
    -------
    dict with key ``"episodes"`` containing a list of per-episode result
    dicts in order (episode 0, 1, …, episodes-1).
    """
    ep_seeds = [seed + i for i in range(episodes)]

    if n_jobs == 1:
        # Original sequential path — unchanged behaviour
        runs = []
        for ep_seed in ep_seeds:
            result = run_episode(
                model_factory, steps, ep_seed,
                per_step_metrics, per_episode_metrics,
                **model_kwargs,
            )
            runs.append(result)
        return {"episodes": runs}

    # Parallel path
    max_workers = os.cpu_count() if n_jobs == -1 else n_jobs
    args_list = [
        (model_factory, steps, ep_seed,
         per_step_metrics, per_episode_metrics,
         dict(model_kwargs))
        for ep_seed in ep_seeds
    ]
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_run_episode_worker, args) for args in args_list]
        runs = [f.result() for f in futures]   # preserves submission order

    return {"episodes": runs}
