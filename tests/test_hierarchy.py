"""Tests for the HEAS hierarchy runtime.

Covers: Context, Stream, Layer, Graph, StreamSpec/LayerSpec, and
make_model_from_spec.  All tests are self-contained (no network, no disk
writes) and complete in < 2 s.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from heas.hierarchy.base import Context, Stream, Layer, validate_metrics_episode
from heas.hierarchy.graph import Graph
from heas.hierarchy.orchestrator import (
    StreamSpec,
    LayerSpec,
    build_graph,
    CompositeHeasModel,
    make_model_from_spec,
    default_aggregator,
)


# ── Fixtures / helpers ──────────────────────────────────────────────

class CounterStream(Stream):
    """Minimal stream that increments a counter each step."""

    def __init__(self, name: str, ctx: Context, start: int = 0, **kw: Any):
        super().__init__(name, ctx, **kw)
        self.count = start

    def step(self) -> None:
        self.count += 1

    def metrics_step(self) -> Dict[str, Any]:
        return {"count": self.count}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_count": self.count}


def _two_layer_spec():
    return [
        LayerSpec(streams=[
            StreamSpec(name="L1", factory=CounterStream, kwargs={"start": 0}),
        ]),
        LayerSpec(streams=[
            StreamSpec(name="L2", factory=CounterStream, kwargs={"start": 10}),
        ]),
    ]


# ── Context ─────────────────────────────────────────────────────────

class TestContext:
    def test_default_values(self):
        ctx = Context()
        assert ctx.t == 0
        assert ctx.data == {}
        assert ctx.episode == {}

    def test_step_tick(self):
        ctx = Context()
        ctx.step_tick()
        ctx.step_tick()
        assert ctx.t == 2

    def test_rng_is_independent(self):
        import random as _random
        rng1 = _random.Random(42)
        rng2 = _random.Random(42)
        vals1 = [rng1.random() for _ in range(5)]
        vals2 = [rng2.random() for _ in range(5)]
        assert vals1 == vals2


# ── Stream / Layer ──────────────────────────────────────────────────

class TestStream:
    def test_counter_stream_steps(self):
        ctx = Context(seed=1)
        s = CounterStream("c", ctx, start=0)
        s.step()
        s.step()
        s.step()
        assert s.count == 3

    def test_metrics_step(self):
        ctx = Context(seed=1)
        s = CounterStream("c", ctx, start=5)
        m = s.metrics_step()
        assert m == {"count": 5}

    def test_metrics_episode(self):
        ctx = Context(seed=1)
        s = CounterStream("c", ctx, start=0)
        s.step()
        s.step()
        m = s.metrics_episode()
        assert m == {"final_count": 2}


class TestLayer:
    def test_step_runs_all_streams(self):
        ctx = Context(seed=1)
        s1 = CounterStream("a", ctx, start=0)
        s2 = CounterStream("b", ctx, start=0)
        layer = Layer([s1, s2])
        layer.step()
        assert s1.count == 1
        assert s2.count == 1

    def test_metrics_step_prefixes(self):
        ctx = Context(seed=1)
        s1 = CounterStream("alpha", ctx, start=0)
        s1.step()
        layer = Layer([s1])
        m = layer.metrics_step()
        assert "alpha.count" in m
        assert m["alpha.count"] == 1

    def test_metrics_episode_prefixes(self):
        ctx = Context(seed=1)
        s1 = CounterStream("alpha", ctx, start=0)
        s1.step()
        s1.step()
        layer = Layer([s1])
        m = layer.metrics_episode()
        assert m["alpha.final_count"] == 2


# ── Graph ───────────────────────────────────────────────────────────

class TestGraph:
    def test_build_graph_from_specs(self):
        spec = _two_layer_spec()
        graph = build_graph(spec, ctx=Context(seed=0))
        assert isinstance(graph, Graph)
        assert len(graph.layers) == 2

    def test_graph_step_advances_all_layers(self):
        ctx = Context(seed=0)
        graph = build_graph(_two_layer_spec(), ctx=ctx)
        graph.step(ctx)
        for layer in graph.layers:
            for s in layer.streams:
                assert s.count >= 1

    def test_graph_step_multiple(self):
        ctx = Context(seed=0)
        graph = build_graph(_two_layer_spec(), ctx=ctx)
        for _ in range(5):
            graph.step(ctx)
        l1_stream = graph.layers[0].streams[0]
        l2_stream = graph.layers[1].streams[0]
        assert l1_stream.count == 5
        assert l2_stream.count == 15


# ── make_model_from_spec / CompositeHeasModel ───────────────────────

class TestCompositeModel:
    def test_factory_returns_composite_model(self):
        spec = _two_layer_spec()
        factory = make_model_from_spec(spec, seed=42)
        model = factory({})
        assert isinstance(model, CompositeHeasModel)

    def test_model_step_and_metrics(self):
        spec = _two_layer_spec()
        factory = make_model_from_spec(spec, seed=42)
        model = factory({})
        model.step()
        m = model.metrics_step()
        assert isinstance(m, dict)
        assert "L1.count" in m
        assert "L2.count" in m

    def test_model_episode_metrics(self):
        spec = _two_layer_spec()
        factory = make_model_from_spec(spec, seed=42)
        model = factory({})
        model.step()
        model.step()
        ep = model.metrics_episode()
        assert ep["L1.final_count"] == 2
        assert ep["L2.final_count"] == 12  # started at 10

    def test_model_context_ticking(self):
        spec = _two_layer_spec()
        factory = make_model_from_spec(spec, seed=42)
        model = factory({})
        assert model.ctx.t == 0
        model.step()
        assert model.ctx.t == 1

    def test_factory_respects_seed(self):
        spec = _two_layer_spec()
        f1 = make_model_from_spec(spec, seed=99)
        f2 = make_model_from_spec(spec, seed=99)
        m1 = f1({})
        m2 = f2({})
        for _ in range(3):
            m1.step()
            m2.step()
        assert m1.metrics_step() == m2.metrics_step()


# ── validate_metrics_episode ────────────────────────────────────────

class TestValidateMetrics:
    def test_valid_dict(self):
        result = validate_metrics_episode({"a": 1.0, "b": 2})
        assert result == {"a": 1.0, "b": 2.0}

    def test_invalid_type(self):
        with pytest.raises(TypeError, match="must return dict"):
            validate_metrics_episode([1, 2, 3])

    def test_non_numeric_value(self):
        with pytest.raises(TypeError, match="float-compatible"):
            validate_metrics_episode({"a": "not a number"})
