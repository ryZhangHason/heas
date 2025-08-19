from __future__ import annotations
from typing import Any, Dict, Callable, Tuple, Sequence
import os, json, random
import numpy as np

try:
    from deap import algorithms, tools
except Exception as e:  # pragma: no cover
    raise ImportError("DEAP is required by HEAS. Please install 'deap>=1.3'.") from e

from .toolbox import build_toolbox
from ..schemas.genes import Real, Int, Cat, Bool
from ..utils.io import ensure_dir, save_json

def _eval_factory(objective_fn: Callable[[Any], tuple]):
    def _evaluate(individual):
        vals = objective_fn(individual)
        if not isinstance(vals, tuple):
            vals = tuple(vals) if hasattr(vals, "__iter__") else (vals,)
        return vals
    return _evaluate

def _make_vector_stats() -> "tools.Statistics":
    stats = tools.Statistics(key=lambda ind: ind.fitness.values)

    def _avg(fits):
        arr = np.array(list(fits), dtype=float)
        if arr.ndim == 1:
            return float(arr.mean())
        return tuple(arr.mean(axis=0).tolist())

    def _vmin(fits):
        arr = np.array(list(fits), dtype=float)
        if arr.ndim == 1:
            return float(arr.min())
        return tuple(arr.min(axis=0).tolist())

    def _vmax(fits):
        arr = np.array(list(fits), dtype=float)
        if arr.ndim == 1:
            return float(arr.max())
        return tuple(arr.max(axis=0).tolist())

    stats.register("avg", _avg)
    stats.register("min", _vmin)
    stats.register("max", _vmax)
    return stats

def _sample_from_schema(schema: Sequence[Any]) -> list:
    geno = []
    for gene in schema:
        if isinstance(gene, Real):
            geno.append(random.uniform(gene.low, gene.high))
        elif isinstance(gene, Int):
            geno.append(random.randint(gene.low, gene.high))
        elif isinstance(gene, Cat):
            geno.append(random.choice(gene.choices))
        elif isinstance(gene, Bool):
            geno.append(bool(random.getrandbits(1)))
        else:
            raise TypeError(f"Unsupported gene type: {type(gene)}")
    return geno

def run_ea(exp, algo) -> Dict[str, Any]:
    schema = algo.genes_schema
    if not schema:
        raise ValueError("Algorithm.genes_schema is required for optimization.")

    # --- fitness weights (auto-infer objective arity if needed) ---
    weights: Tuple[float, ...] = getattr(algo, "fitness_weights", (-1.0,))
    if len(weights) == 1:
        try:
            probe_vals = _eval_factory(algo.objective_fn)(_sample_from_schema(schema))
            if len(probe_vals) > 1:
                weights = tuple([-1.0] * len(probe_vals))  # default: minimize all
        except Exception:
            pass

    toolbox = build_toolbox(schema, fitness_weights=weights)
    toolbox.register("evaluate", _eval_factory(algo.objective_fn))

    # --- Selection strategy ---
    strategy = getattr(algo, "strategy", "nsga2").lower()
    if strategy == "nsga2":
        toolbox.register("select", tools.selNSGA2)  # Pareto-based selection

    pop = toolbox.population(n=algo.pop_size)

    # --- Hall of Fame ---
    if len(weights) > 1 or strategy == "nsga2":
        hof = tools.ParetoFront()
    else:
        hof = tools.HallOfFame(5)

    stats = _make_vector_stats()

    if strategy == "simple":
        pop, log = algorithms.eaSimple(
            pop, toolbox,
            cxpb=algo.cx_prob, mutpb=algo.mut_prob, ngen=algo.ngen,
            stats=stats, halloffame=hof, verbose=True
        )
    elif strategy in {"nsga2", "mu_plus_lambda"}:
        mu = algo.mu or (algo.pop_size if strategy == "nsga2" else max(2, algo.pop_size // 2))
        lambd = algo.lambd or algo.pop_size
        pop, log = algorithms.eaMuPlusLambda(
            pop, toolbox, mu=mu, lambda_=lambd,
            cxpb=algo.cx_prob, mutpb=algo.mut_prob, ngen=algo.ngen,
            stats=stats, halloffame=hof, verbose=True
        )
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    ensure_dir(algo.out_dir)
    best = [list(ind) for ind in getattr(hof, "items", hof)]
    out = {
        "best": best,
        "hall_of_fame": best,
        "logbook": [dict(record) for record in (log or [])],
    }
    save_json(os.path.join(algo.out_dir, "result.json"), out)
    return out