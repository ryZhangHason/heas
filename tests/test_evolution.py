"""Tests for the HEAS evolutionary search module.

Covers: run_ea with single-objective and multi-objective configurations,
gene schemas (Real, Int, Bool, Cat), and hall-of-fame output.  Tests use
toy fitness functions and small populations for speed (< 5 s total).
"""
from __future__ import annotations

import os
import tempfile
from typing import Any, Tuple

import pytest

from heas.config import Experiment, Algorithm
from heas.schemas.genes import Real, Int, Bool, Cat
from heas.evolution.algorithms import run_ea


# ── Fixtures / helpers ──────────────────────────────────────────────

def _trivial_experiment():
    """Minimal Experiment (no actual simulation needed for pure EA test)."""
    return Experiment(
        model_factory=lambda kw: None,
        steps=1,
        episodes=1,
        seed=42,
    )


def _single_obj_algorithm(out_dir: str):
    schema = [Real("x", -5.0, 5.0), Real("y", -5.0, 5.0)]

    def fitness(individual: list) -> Tuple[float]:
        # Minimise distance from origin
        return (individual[0] ** 2 + individual[1] ** 2,)

    return Algorithm(
        objective_fn=fitness,
        pop_size=20,
        ngen=10,
        cx_prob=0.7,
        mut_prob=0.3,
        strategy="simple",
        genes_schema=schema,
        out_dir=out_dir,
    )


def _multi_obj_algorithm(out_dir: str):
    schema = [Real("x", -5.0, 5.0), Real("y", -5.0, 5.0)]

    def fitness(individual: list) -> Tuple[float, float]:
        # Two conflicting objectives
        return (individual[0] ** 2, (individual[0] - 1) ** 2)

    return Algorithm(
        objective_fn=fitness,
        pop_size=30,
        ngen=10,
        cx_prob=0.7,
        mut_prob=0.3,
        strategy="nsga2",
        genes_schema=schema,
        out_dir=out_dir,
    )


# ── Single-objective EA ─────────────────────────────────────────────

class TestSingleObjectiveEA:
    def test_returns_best_and_hof(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _single_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            assert "best" in result
            assert "hall_of_fame" in result
            assert len(result["hall_of_fame"]) > 0

    def test_hof_individuals_have_correct_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _single_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            for ind in result["hall_of_fame"]:
                assert len(ind) == 2  # two Real genes

    def test_hof_fitness_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _single_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            assert len(result["hof_fitness"]) == len(result["hall_of_fame"])
            for fit in result["hof_fitness"]:
                assert len(fit) == 1  # single objective

    def test_logbook_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _single_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            assert len(result["logbook"]) > 0

    def test_result_json_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _single_obj_algorithm(tmp)
            run_ea(_trivial_experiment(), algo)
            assert os.path.isfile(os.path.join(tmp, "result.json"))


# ── Multi-objective EA (NSGA-II) ────────────────────────────────────

class TestMultiObjectiveEA:
    def test_pareto_front_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _multi_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            assert len(result["hall_of_fame"]) > 0

    def test_hof_fitness_is_multi_objective(self):
        with tempfile.TemporaryDirectory() as tmp:
            algo = _multi_obj_algorithm(tmp)
            result = run_ea(_trivial_experiment(), algo)
            for fit in result["hof_fitness"]:
                assert len(fit) == 2


# ── Gene schema types ───────────────────────────────────────────────

class TestGeneSchemas:
    def test_int_genes(self):
        schema = [Int("a", 0, 10), Int("b", 0, 10)]

        def fitness(ind):
            return (abs(ind[0] - 5) + abs(ind[1] - 5),)

        with tempfile.TemporaryDirectory() as tmp:
            algo = Algorithm(
                objective_fn=fitness,
                pop_size=20,
                ngen=5,
                strategy="simple",
                genes_schema=schema,
                out_dir=tmp,
            )
            result = run_ea(_trivial_experiment(), algo)
            for ind in result["hall_of_fame"]:
                assert all(isinstance(v, (int, float)) for v in ind)

    def test_bool_genes(self):
        schema = [Bool("flag")]

        def fitness(ind):
            return (0 if ind[0] else 1,)

        with tempfile.TemporaryDirectory() as tmp:
            algo = Algorithm(
                objective_fn=fitness,
                pop_size=20,
                ngen=5,
                strategy="simple",
                genes_schema=schema,
                out_dir=tmp,
            )
            result = run_ea(_trivial_experiment(), algo)
            # The best individual should have flag=True (fitness=0)
            best_vals = [ind[0] for ind in result["hall_of_fame"]]
            assert any(v is True or v == 1 for v in best_vals)

    def test_categorical_genes(self):
        schema = [Cat("mode", ["a", "b", "c"])]

        def fitness(ind):
            return (0 if ind[0] == "b" else 1,)

        with tempfile.TemporaryDirectory() as tmp:
            algo = Algorithm(
                objective_fn=fitness,
                pop_size=20,
                ngen=5,
                strategy="simple",
                genes_schema=schema,
                out_dir=tmp,
            )
            result = run_ea(_trivial_experiment(), algo)
            best_vals = [ind[0] for ind in result["hall_of_fame"]]
            assert any(v == "b" for v in best_vals)


# ── Error handling ──────────────────────────────────────────────────

class TestErrorHandling:
    def test_missing_schema_raises(self):
        algo = Algorithm(
            objective_fn=lambda ind: (0,),
            pop_size=10,
            ngen=2,
            out_dir="/tmp/heas_test_err",
        )
        with pytest.raises(ValueError, match="genes_schema is required"):
            run_ea(_trivial_experiment(), algo)
