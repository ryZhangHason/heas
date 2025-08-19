from __future__ import annotations
from typing import Dict, Any
import random

try:
    from mesa import Agent, Model  # noqa: F401
except Exception:
    class Agent:
        def __init__(self, unique_id, model): self.unique_id, self.model = unique_id, model
        def step(self): pass
    class Model:
        def step(self): pass

class DriftModel(Model):
    def __init__(self, start: float=1.0, drift: float=0.05, noise: float=0.01, **kwargs):
        super().__init__()
        self.x = start
        self.drift = drift
        self.noise = noise
        self.t = 0
    def step(self):
        self.t += 1
        self.x += self.drift + random.gauss(0, self.noise)
    def metrics_step(self):
        return {"t": self.t, "x": self.x}
    def metrics_episode(self):
        return {"final_abs_x": abs(self.x)}

def make_model(kwargs: Dict[str, Any]):
    params = {"start": 1.0, "drift": 0.05, "noise": 0.01}
    params.update(kwargs or {})
    return DriftModel(**params)

from heas.schemas.genes import Real
SCHEMA = [Real(name="drift", low=-0.2, high=0.2)]

def objective(genome):
    drift = float(genome[0])
    from heas.agent.runner import run_episode
    out = run_episode(make_model, steps=50, seed=123, drift=drift)
    return (out["episode"]["final_abs_x"],)