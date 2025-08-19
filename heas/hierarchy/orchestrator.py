from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union
import inspect
import random

from .base import Context, Stream, Layer
from .graph import Graph

# ---------- Specs ----------

@dataclass
class StreamSpec:
    """Declaration for a stream instance in a layer."""
    name: str
    factory: Callable[..., Stream]  # factory(ctx, name, **kwargs) -> Stream
    kwargs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LayerSpec:
    """A layer is an ordered list of StreamSpec."""
    streams: List[StreamSpec]

SpecType = Sequence[LayerSpec]

# ---------- Utilities ----------

def _resolve_kwargs(ctx: Context, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve callables in kwargs against the context for dynamic wiring."""
    out: Dict[str, Any] = {}
    for k, v in (kwargs or {}).items():
        if callable(v):
            try:
                # If the callable expects ctx, pass it (best effort)
                sig = inspect.signature(v)
                if len(sig.parameters) >= 1:
                    out[k] = v(ctx)
                else:
                    out[k] = v()  # type: ignore[call-arg]
            except Exception:
                out[k] = v
        else:
            out[k] = v
    return out

def _instantiate_stream(spec: StreamSpec, ctx: Context) -> Stream:
    resolved = _resolve_kwargs(ctx, spec.kwargs)
    factory = spec.factory
    try:
        return factory(ctx=ctx, name=spec.name, **resolved)
    except TypeError:
        # fallback: factory(ctx, **kwargs) then set .name if missing
        obj = factory(ctx=ctx, **resolved)
        if not hasattr(obj, "name"):
            setattr(obj, "name", spec.name)
        return obj

def build_graph(spec: SpecType, ctx: Optional[Context] = None) -> Graph:
    ctx = ctx or Context(seed=0)
    layers: List[Layer] = []
    for layer_spec in spec:
        streams = [ _instantiate_stream(s, ctx) for s in layer_spec.streams ]
        layers.append(Layer(streams))
    return Graph(layers)

# ---------- Composite model (HEAS-compatible) ----------

def default_aggregator(ctx: Context, per_step: Dict[str, Any]) -> Dict[str, Any]:
    """Optional global summaries; users can provide their own."""
    out = dict(per_step)
    out["t"] = ctx.t
    return out

class CompositeHeasModel:
    """
    Wraps a Graph so it behaves like a HEAS model:
      - step()
      - metrics_step()
      - metrics_episode()
    """
    def __init__(
        self,
        spec_or_graph: Union[SpecType, Graph],
        seed: int = 0,
        aggregator: Optional[Callable[[Context, Dict[str, Any]], Dict[str, Any]]] = None,
        ctx_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        rng = random.Random(seed)
        self.ctx = Context(seed=seed, rng=rng, data=(ctx_data or {}))
        self.graph = spec_or_graph if isinstance(spec_or_graph, Graph) else build_graph(spec_or_graph, self.ctx)
        self._aggregator = aggregator or default_aggregator
        self._last_step_metrics: Dict[str, Any] = {}
        self._last_episode_metrics: Dict[str, Any] = {}

    def step(self) -> None:
        self.graph.step(self.ctx)
        per_step = self.graph.metrics_step()
        self._last_step_metrics = self._aggregator(self.ctx, per_step)

    def metrics_step(self) -> Dict[str, Any]:
        return dict(self._last_step_metrics)

    def metrics_episode(self) -> Dict[str, Any]:
        per_ep = self.graph.metrics_episode()
        # allow streams to write ctx.episode during the run, merge here
        out = dict(per_ep)
        out.update(self.ctx.episode)
        self._last_episode_metrics = out
        return dict(out)

# ---------- Convenience factory for HEAS Experiment.model_factory ----------

def make_model_from_spec(spec: SpecType, seed: int = 0,
                         aggregator: Optional[Callable[[Context, Dict[str, Any]], Dict[str, Any]]] = None,
                         **ctx_data: Any) -> CompositeHeasModel:
    """
    Returns a model factory suitable for HEAS Experiment:
      model_factory = lambda kwargs: CompositeHeasModel(spec, seed=..., **kwargs)
    """
    def _factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
        # kwargs may contain overrides like aggregator=..., ctx_data=...
        agg = kwargs.pop("aggregator", aggregator)
        seed_override = kwargs.pop("seed", seed)
        # Any remaining kwargs are stored into ctx.data for streams to read
        data = dict(ctx_data)
        data.update(kwargs)
        return CompositeHeasModel(spec, seed=seed_override, aggregator=agg, ctx_data=data)
    return _factory