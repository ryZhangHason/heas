"""Tests for the HEAS game module.

Covers: Scenario, ScenarioSet, make_grid, make_scenarios, Arena, and
voting functions.  All tests are self-contained (no network, no disk
writes beyond Arena's internal simulate call) and complete in < 10 s.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from heas.game.scenarios import Scenario, ScenarioSet, make_grid, make_scenarios
from heas.game.voting import (
    majority_vote,
    borda_count,
    weighted_vote,
    choose_voter,
    copeland_vote,
    ranking_agreement,
)
from heas.hierarchy.base import Context, Stream
from heas.hierarchy.orchestrator import StreamSpec, LayerSpec, make_model_from_spec


# ── Scenario / ScenarioSet ──────────────────────────────────────────

class TestScenario:
    def test_creation(self):
        sc = Scenario(name="baseline", params={"alpha": 0.1})
        assert sc.name == "baseline"
        assert sc.params["alpha"] == 0.1

    def test_with_updates(self):
        sc = Scenario(name="baseline", params={"alpha": 0.1, "beta": 0.5})
        sc2 = sc.with_updates(alpha=0.9)
        assert sc2.params["alpha"] == 0.9
        assert sc2.params["beta"] == 0.5
        assert sc.params["alpha"] == 0.1  # original unchanged

    def test_with_updates_preserves_tags(self):
        sc = Scenario(name="s1", params={}, tags={"env": "prod"})
        sc2 = sc.with_updates(x=1)
        assert sc2.tags == {"env": "prod"}


class TestScenarioSet:
    def test_from_list(self):
        scenarios = [
            Scenario(name="a", params={"x": 1}),
            Scenario(name="b", params={"x": 2}),
            Scenario(name="c", params={"x": 1}),
        ]
        ss = ScenarioSet(scenarios)
        assert len(ss) == 3
        assert ss.names() == ["a", "b", "c"]

    def test_filter(self):
        scenarios = [
            Scenario(name="a", params={"env": "prod", "scale": 10}),
            Scenario(name="b", params={"env": "dev", "scale": 10}),
            Scenario(name="c", params={"env": "prod", "scale": 100}),
        ]
        ss = ScenarioSet(scenarios)
        filtered = ss.filter(env="prod")
        assert len(filtered) == 2
        assert filtered.names() == ["a", "c"]

    def test_iteration(self):
        scenarios = [Scenario(name="x"), Scenario(name="y")]
        ss = ScenarioSet(scenarios)
        names = [s.name for s in ss]
        assert names == ["x", "y"]


class TestMakeGrid:
    def test_cartesian_product(self):
        grid = make_grid({"alpha": [0.1, 0.2], "beta": [1, 2, 3]})
        assert len(grid) == 6  # 2 × 3

    def test_naming(self):
        grid = make_grid({"x": [1, 2]})
        names = grid.names()
        assert len(names) == 2
        assert all("x=" in n for n in names)

    def test_base_tags(self):
        grid = make_grid({"a": [1]}, base_tags={"env": "test"})
        for sc in grid:
            assert sc.tags["env"] == "test"


class TestMakeScenarios:
    def test_from_dicts(self):
        items = [
            {"name": "s1", "x": 1, "y": 2},
            {"name": "s2", "x": 3, "y": 4},
        ]
        ss = make_scenarios(items, name_key="name")
        assert len(ss) == 2
        assert ss.scenarios[0].params["x"] == 1


# ── Voting ──────────────────────────────────────────────────────────

class TestVoting:
    def test_majority_vote(self):
        # majority_vote takes Iterable[int] (binary labels per voter)
        labels = [1, 1, 0, 1, 0]  # 3 ones vs 2 zeros
        assert majority_vote(labels) == 1

    def test_majority_vote_zeros_win(self):
        labels = [0, 0, 1, 0]
        assert majority_vote(labels) == 0

    def test_borda_count(self):
        # borda_count takes Iterable[int] of rank values (lower = better)
        ranks = [1, 1, 3]  # rank 1 appears twice, rank 3 once
        winner = borda_count(ranks)
        assert winner == 1

    def test_borda_count_with_m(self):
        ranks = [0, 2, 1]
        winner = borda_count(ranks, m=3)
        assert winner == 0  # m - 0 = 3 is highest

    def test_weighted_vote(self):
        scores = {"A": 0.8, "B": 0.5}
        weights = {"A": 1.0, "B": 0.5}
        winner = weighted_vote(scores, weights)
        assert winner == "A"

    def test_weighted_vote_prefers_heavily_weighted(self):
        scores = {"A": 0.5, "B": 0.5}
        weights = {"A": 0.1, "B": 1.0}
        winner = weighted_vote(scores, weights)
        assert winner == "B"

    def test_choose_voter_majority(self):
        voter = choose_voter("majority")
        assert callable(voter)

    def test_choose_voter_argmax(self):
        voter = choose_voter("argmax")
        result = voter({"A": 3, "B": 1, "C": 2})
        assert result == "A"

    def test_choose_voter_passthrough(self):
        my_fn = lambda x: x
        voter = choose_voter(my_fn)
        assert voter is my_fn

    def test_choose_voter_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown voting rule"):
            choose_voter("nonexistent")

    def test_copeland_vote(self):
        ep_scores = {
            "ep1": {"A": 1.0, "B": 0.5},
            "ep2": {"A": 0.3, "B": 0.9},
            "ep3": {"A": 0.8, "B": 0.4},
        }
        winner = copeland_vote(ep_scores, ["A", "B"])
        assert winner == "A"  # A wins 2 of 3 episodes

    def test_ranking_agreement(self):
        assert ranking_agreement(["A", "A", "A"]) == 1.0
        assert ranking_agreement(["A", "B"]) == 0.0
        assert ranking_agreement(["A"]) == 1.0


# ── Arena (integration with simulate) ───────────────────────────────

class _TrivialStream(Stream):
    """Stream that writes a fixed value to context each step."""

    def __init__(self, name, ctx, value=1.0, **kw):
        super().__init__(name, ctx, **kw)
        self.value = value

    def step(self):
        self.ctx.data[f"{self.name}.val"] = self.value

    def metrics_step(self):
        return {"val": self.value}

    def metrics_episode(self):
        return {"total": self.value * 10}


def _trivial_model_factory(spec=None):
    if spec is None:
        spec = [
            LayerSpec(streams=[
                StreamSpec(name="L1", factory=_TrivialStream, kwargs={"value": 1.0}),
            ]),
        ]
    return make_model_from_spec(spec, seed=42)


class TestArena:
    def test_arena_runs(self):
        from heas.game.arena import Arena

        def build_model(scenario, participant, ctx):
            return _trivial_model_factory()

        arena = Arena(build_model)
        scenarios = [Scenario(name="s1", params={}), Scenario(name="s2", params={})]
        step_df, ep_df = arena.run(
            scenarios=scenarios,
            participants=["p1", "p2"],
            steps=5,
            episodes=2,
            seed=42,
        )
        # 2 scenarios × 2 participants × 2 episodes = 8 episode rows
        assert len(ep_df) == 8
        assert "scenario" in ep_df.columns
        assert "participant" in ep_df.columns

    def test_arena_metrics_present(self):
        from heas.game.arena import Arena

        def build_model(scenario, participant, ctx):
            return _trivial_model_factory()

        arena = Arena(build_model)
        scenarios = [Scenario(name="s1", params={})]
        _, ep_df = arena.run(
            scenarios=scenarios,
            participants=["p1"],
            steps=3,
            episodes=1,
            seed=0,
        )
        assert any("val" in col or "L1" in col for col in ep_df.columns)
