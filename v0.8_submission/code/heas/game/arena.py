from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import pandas as pd

from ..config import Experiment
from ..api import simulate

BuildModelFn = Callable[[Any, str, Dict[str, Any]], Any]
# signature: build_model(scenario, participant_name, context) -> model OR model_factory(kwargs)->model

class Arena:
    """
    Runs simulations across scenarios and participants, collecting tidy tables.
    - You provide `build_model` that, given (scenario, participant, ctx),
      returns either a HEAS model instance (has .step()) OR a model_factory kwargs->model.
    - `score_fn(episode_dict) -> Dict[label->float]` or -> float if per-participant loop.
    """

    def __init__(self, build_model: BuildModelFn) -> None:
        self.build_model = build_model

    def _coerce_factory(self, model_or_factory: Any) -> Callable[[Dict[str, Any]], Any]:
        if hasattr(model_or_factory, "step"):
            return lambda _kw: model_or_factory
        return model_or_factory

    def run(
        self,
        scenarios: Iterable[Any],
        participants: Iterable[str],
        steps: int,
        episodes: int,
        seed: int,
        ctx: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Returns (per_step_df, per_episode_df) with columns:
          scenario, participant, episode_id, (...metrics...)
        """
        step_rows: List[Dict[str, Any]] = []
        ep_rows: List[Dict[str, Any]] = []

        for sc in scenarios:
            sc_name = getattr(sc, "name", str(sc))
            for p in participants:
                model_or_factory = self.build_model(sc, p, dict(ctx or {}))
                factory = self._coerce_factory(model_or_factory)
                exp = Experiment(model_factory=factory, steps=steps, episodes=episodes, seed=seed)
                sim = simulate(exp)

                for ei, ep in enumerate(sim["episodes"]):
                    # per-step
                    for row in ep["per_step"]:
                        rec = dict(row)
                        rec.update({"scenario": sc_name, "participant": p, "episode_id": ei})
                        step_rows.append(rec)
                    # per-episode
                    epi = dict(ep["episode"])
                    epi.update({"scenario": sc_name, "participant": p, "episode_id": ei})
                    ep_rows.append(epi)

        return pd.DataFrame(step_rows), pd.DataFrame(ep_rows)