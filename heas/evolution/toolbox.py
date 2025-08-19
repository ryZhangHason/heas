from __future__ import annotations
from typing import Any, Sequence, Tuple, Callable
import random

try:
    from deap import base, creator, tools
except Exception as e:  # pragma: no cover
    raise ImportError("DEAP is required by HEAS. Please install 'deap>=1.3'.") from e

from ..schemas.genes import Real, Int, Cat, Bool

def _make_individual_from_schema(schema: Sequence[Any]) -> Callable[[], list]:
    def factory():
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
    return factory

# --- schema-aware mutation that handles Real/Int/Cat/Bool ---
def mutate_by_schema(individual, schema: Sequence[Any], indpb: float = 0.2, sigma: float = 0.1):
    for i, spec in enumerate(schema):
        if random.random() >= indpb:
            continue
        if isinstance(spec, Real):
            val = float(individual[i]) + random.gauss(0.0, sigma)
            val = max(spec.low, min(spec.high, val))
            individual[i] = val
        elif isinstance(spec, Int):
            step = random.choice([-1, 1])
            val = int(individual[i]) + step
            val = max(spec.low, min(spec.high, val))
            individual[i] = val
        elif isinstance(spec, Bool):
            individual[i] = not bool(individual[i])
        elif isinstance(spec, Cat):
            choices = list(spec.choices)
            if choices:
                cur = individual[i]
                options = [c for c in choices if c != cur] or choices
                individual[i] = random.choice(options)
    return (individual,)

def _weights_tag(weights: Tuple[float, ...]) -> str:
    # Encode weights pattern to avoid class collisions across runs (e.g., 1D vs 2D fitness)
    return f"{len(weights)}d_" + "".join("p" if w > 0 else "m" if w < 0 else "0" for w in weights)

def build_toolbox(schema: Sequence[Any], fitness_weights: Tuple[float, ...] = (-1.0,)) -> 'base.Toolbox':
    """Create a DEAP toolbox from a HEAS genes schema.

    fitness_weights follow DEAP semantics: positive = maximize, negative = minimize.
    """
    tag = _weights_tag(fitness_weights)
    fit_name = f"FitnessHEAS_{tag}"
    ind_name = f"IndividualHEAS_{tag}"

    if not hasattr(creator, fit_name):
        creator.create(fit_name, base.Fitness, weights=fitness_weights)
    if not hasattr(creator, ind_name):
        creator.create(ind_name, list, fitness=getattr(creator, fit_name))

    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, getattr(creator, ind_name), _make_individual_from_schema(schema))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # --- 1-gene safe crossover ---
    if len(schema) >= 2:
        toolbox.register("mate", tools.cxTwoPoint)
    else:
        toolbox.register("mate", tools.cxUniform, indpb=1.0)

    # --- schema-aware mutation ---
    toolbox.register("mutate", mutate_by_schema, schema=schema, indpb=0.2, sigma=0.1)

    # Default selection (algorithms can override)
    toolbox.register("select", tools.selTournament, tournsize=3)
    return toolbox

def clear_heas_creator_classes():
    """Utility to clear HEAS-created classes from deap.creator (handy for notebooks)."""
    names = [n for n in dir(creator) if n.startswith(("FitnessHEAS_", "IndividualHEAS_"))] + ["FitnessHEAS", "IndividualHEAS"]
    for n in names:
        if hasattr(creator, n):
            delattr(creator, n)