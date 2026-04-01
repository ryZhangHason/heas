from __future__ import annotations
from typing import Any, Dict

# Mesa is now a required dependency. Fail fast with a clear message if missing.
try:
    from mesa import Agent as MesaAgent, Model as MesaModel
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "Mesa is required by HEAS. Please install 'mesa>=2.1' (it is declared as a dependency of heas)."
    ) from e

class HeasAgent(MesaAgent):
    """Mixin base for HEAS agents. Override `step()` and populate `self.metrics`."""
    def __init__(self, unique_id: int, model: 'HeasModel'):
        super().__init__(unique_id, model)
        self.metrics: Dict[str, Any] = {}

class HeasModel(MesaModel):
    """Mixin base for HEAS models with metric hooks."""
    def __init__(self, **kwargs):
        super().__init__()
        self.heas_cfg = kwargs
        self._step_idx = 0
        self.metrics_last_step: Dict[str, Any] = {}
        self.metrics_last_episode: Dict[str, Any] = {}

    def step(self):  # to be implemented by subclass
        self._step_idx += 1

    def metrics_step(self) -> Dict[str, Any]:
        return {}

    def metrics_episode(self) -> Dict[str, Any]:
        return {}