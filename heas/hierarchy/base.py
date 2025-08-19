from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import random

@dataclass  # Python 3.9-compatible (no slots)
class Context:
    """Shared context across all streams & layers during an episode."""
    seed: int = 0
    t: int = 0
    rng: random.Random = field(default_factory=random.Random)
    data: Dict[str, Any] = field(default_factory=dict)         # stream/global scratch
    episode: Dict[str, Any] = field(default_factory=dict)      # end-of-episode summaries

    def step_tick(self) -> None:
        self.t += 1

class Stream:
    """Base stream: override step(), optionally metrics_step()/metrics_episode()."""
    def __init__(self, name: str, ctx: Context, **kwargs: Any) -> None:
        self.name = name
        self.ctx = ctx
        self.cfg = dict(kwargs)

    # Main tick
    def step(self) -> None:
        raise NotImplementedError("Stream.step() not implemented")

    # Per-step metrics (merged with prefix = stream name)
    def metrics_step(self) -> Dict[str, Any]:
        return {}

    # End-of-episode metrics (merged with prefix = stream name)
    def metrics_episode(self) -> Dict[str, Any]:
        return {}

class Layer:
    """A layer is an ordered list of streams. All streams tick before the next layer."""
    def __init__(self, streams: List[Stream]) -> None:
        self.streams = list(streams)

    def step(self) -> None:
        for s in self.streams:
            s.step()

    def metrics_step(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for s in self.streams:
            m = getattr(s, "metrics_step", None)
            if callable(m):
                for k, v in s.metrics_step().items():
                    out[f"{s.name}.{k}"] = v
        return out

    def metrics_episode(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for s in self.streams:
            m = getattr(s, "metrics_episode", None)
            if callable(m):
                for k, v in s.metrics_episode().items():
                    out[f"{s.name}.{k}"] = v
        return out