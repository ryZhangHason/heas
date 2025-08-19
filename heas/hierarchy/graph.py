from __future__ import annotations
from typing import List, Dict, Any
from .base import Layer, Context

class Graph:
    """Ordered list of layers; ticks in sequence each step."""
    def __init__(self, layers: List[Layer]) -> None:
        self.layers = list(layers)

    def step(self, ctx: Context) -> None:
        ctx.step_tick()
        for layer in self.layers:
            layer.step()

    def metrics_step(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for layer in self.layers:
            out.update(layer.metrics_step())
        return out

    def metrics_episode(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for layer in self.layers:
            out.update(layer.metrics_episode())
        return out