from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Sequence

# Types
ModelFactory = Callable[[dict], Any]
ObjectiveFn = Callable[[Any], tuple]  # returns fitness tuple

@dataclass  # ← no slots=True for Python 3.9
class Experiment:
    """Simulation/optimization experiment configuration."""
    model_factory: ModelFactory  # factory that builds a Mesa model from kwargs
    steps: int = 100
    episodes: int = 10
    seed: int = 42
    per_step_metrics: Optional[Sequence[str]] = None
    per_episode_metrics: Optional[Sequence[str]] = None
    model_kwargs: Dict[str, Any] = field(default_factory=dict)

@dataclass  # ← no slots=True
class Algorithm:
    """Evolutionary algorithm configuration."""
    objective_fn: ObjectiveFn
    pop_size: int = 50
    ngen: int = 20
    cx_prob: float = 0.8
    mut_prob: float = 0.2
    tournament_k: int = 3
    strategy: str = "nsga2"  # "simple" | "nsga2" | "mu_plus_lambda"
    mu: Optional[int] = None
    lambd: Optional[int] = None
    checkpoint_every: int = 5
    out_dir: str = "runs/heas"
    genes_schema: Optional[Any] = None  # schemas.genes.* or list thereof

@dataclass  # ← no slots=True
class Evaluation:
    """Batch evaluation configuration."""
    genotypes: Sequence[Any]
    objective_fn: ObjectiveFn