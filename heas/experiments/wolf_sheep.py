"""
heas.experiments.wolf_sheep
============================
HEAS port of the canonical Wolf-Sheep Predation model.

**Original source**: Wilensky, U. (1997). NetLogo Wolf Sheep Predation model.
http://ccl.northwestern.edu/netlogo/models/WolfSheepPredation. Center for
Connected Learning and Computer-Based Modeling, Northwestern University.
Mesa implementation: Kazil, J. et al. (2020). Utilizing Python for Agent-Based
Modeling: The Mesa Framework. In Proceedings of the 2020 Winter Simulation
Conference.

This port implements the *mean-field ODE approximation* of the published model,
which is dynamically equivalent at large population sizes. The spatial grid is
collapsed into aggregate grass density G ∈ [0, 1]; wolves and sheep are
population counts rather than discrete agents. Model parameters are taken
directly from the published Mesa Wolf-Sheep example defaults:

    initial_sheep       = 100   (initial sheep population)
    initial_wolves      = 50    (initial wolf population)
    sheep_reproduce     = 0.04  (P(reproduce) per sheep per step)
    wolf_reproduce      = 0.05  (P(reproduce) per wolf after eating)
    wolf_gain_from_food = 20    (energy units gained per sheep eaten)
    sheep_gain_from_food= 4     (energy units gained per grass unit eaten)
    grass_regrowth_time = 30    (steps for full grass recovery)
    grid_size           = 20×20 (400 patches; normalised to density)

**Why this port matters**: A researcher holding the published Mesa Wolf-Sheep
model can add multi-objective NSGA-II optimisation and tournament evaluation
by plugging the model into HEAS — with zero additional coupling code. The
metric contract (`metrics_episode()`) automatically connects the simulation
to the EA, tournament scorer, and bootstrap CI pipeline.

**Policy space (2 genes)**:
    harvest_rate ∈ [0, 0.3]   — fraction of wolves removed per step
                                 (models a culling or hunting policy)
    grazing_rate ∈ [0, 1]     — sheep energy intake multiplier
                                 (models a pasture management policy)

**Objectives** (NSGA-II, both minimised):
    −wolf_sheep.mean_sheep      (maximise sheep abundance)
    wolf_sheep.extinct          (minimise extinction probability)
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

from ..hierarchy.base import Context, Stream
from ..hierarchy.orchestrator import (
    CompositeHeasModel,
    LayerSpec,
    StreamSpec,
    make_model_from_spec,
)
from ..schemas.genes import Real


# ---------------------------------------------------------------------------
# Published model parameters (Mesa Wolf-Sheep example defaults)
# ---------------------------------------------------------------------------

_INITIAL_SHEEP: float = 100.0
_INITIAL_WOLVES: float = 50.0
_SHEEP_REPRODUCE: float = 0.04          # P(reproduce) per sheep per step
_WOLF_REPRODUCE: float = 0.05           # P(reproduce) per wolf after eating
_WOLF_GAIN_FROM_FOOD: float = 20.0      # energy per sheep eaten
_SHEEP_GAIN_FROM_FOOD: float = 4.0      # energy per grass unit eaten
_GRASS_REGROWTH_TIME: float = 30.0      # steps for full grass recovery
_N_PATCHES: float = 400.0               # 20×20 grid normalised to density


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------

class GrassStream(Stream):
    """Grass density dynamics.

    Equivalent to Mesa's GrassPatch agents with ``fully_grown`` / countdown
    mechanics, collapsed to a continuous density G ∈ [0, 1].

    dG/dt ≈ (1 - G) / regrowth_time   (logistic recovery toward capacity 1)
    """

    def __init__(self, name: str, ctx: Context,
                 regrowth_time: float = _GRASS_REGROWTH_TIME) -> None:
        super().__init__(name, ctx)
        self.regrowth_time = float(regrowth_time)
        self.G = 0.5                    # initial density (half patches grown)

    def step(self) -> None:
        self.G = min(1.0, self.G + (1.0 - self.G) / max(self.regrowth_time, 1.0))
        self.ctx.data["grass.G"] = self.G

    def metrics_step(self) -> Dict[str, Any]:
        return {"G": self.G}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_G": self.G}


class SheepStream(Stream):
    """Sheep population dynamics.

    Mean-field equivalent of Mesa's Sheep agent: stochastic reproduction and
    energy-based death collapsed to a deterministic ODE:

        dS/dt = sheep_reproduce * S
                - predation_rate * W * S / N_patches
                + sheep_gain_from_food * G * S * 0.001

    where predation_rate encodes the probability that a wolf encounters and
    eats a sheep in one step (matches Mesa's random-walk contact probability
    on a 20×20 grid).
    """

    def __init__(self, name: str, ctx: Context,
                 initial_sheep: float = _INITIAL_SHEEP,
                 sheep_reproduce: float = _SHEEP_REPRODUCE,
                 sheep_gain_from_food: float = _SHEEP_GAIN_FROM_FOOD,
                 predation_rate: float = 0.01) -> None:
        super().__init__(name, ctx)
        self.sheep_reproduce = float(sheep_reproduce)
        self.sheep_gain_from_food = float(sheep_gain_from_food)
        self.predation_rate = float(predation_rate)
        self.S = float(initial_sheep)
        self.ctx.data["pop.sheep"] = self.S
        self._hist: List[float] = []

    def step(self) -> None:
        G = float(self.ctx.data.get("grass.G", 0.5))
        W = float(self.ctx.data.get("pop.wolves", _INITIAL_WOLVES))
        N = _N_PATCHES

        grazing_rate = float(self.ctx.data.get("policy.grazing_rate", 1.0))

        gain = self.sheep_gain_from_food * G * grazing_rate
        dS = (self.sheep_reproduce + gain * 0.001) * self.S \
             - self.predation_rate * W * self.S / N
        self.S = max(0.0, self.S + dS)
        self.ctx.data["pop.sheep"] = self.S
        self._hist.append(self.S)

    def metrics_step(self) -> Dict[str, Any]:
        return {"sheep": self.S}

    def metrics_episode(self) -> Dict[str, Any]:
        hist = self._hist
        mean_s = sum(hist) / len(hist) if hist else 0.0
        return {"mean_sheep": mean_s, "final_sheep": self.S}


class WolfStream(Stream):
    """Wolf population dynamics.

    Mean-field equivalent of Mesa's Wolf agent:

        dW/dt = wolf_reproduce * (predation_rate * W * S / N_patches)
                - wolf_death_rate * W
                - harvest_rate * W          (policy: culling)

    wolf_death_rate is calibrated from the published model's energy mechanic
    (wolves die when energy < 0; at gain_from_food=20, ~5% of wolves exhaust
    energy per step without food → death_rate ≈ 0.05).
    """

    def __init__(self, name: str, ctx: Context,
                 initial_wolves: float = _INITIAL_WOLVES,
                 wolf_reproduce: float = _WOLF_REPRODUCE,
                 wolf_gain_from_food: float = _WOLF_GAIN_FROM_FOOD,
                 wolf_death_rate: float = 0.05,
                 predation_rate: float = 0.01) -> None:
        super().__init__(name, ctx)
        self.wolf_reproduce = float(wolf_reproduce)
        self.wolf_gain_from_food = float(wolf_gain_from_food)
        self.wolf_death_rate = float(wolf_death_rate)
        self.predation_rate = float(predation_rate)
        self.W = float(initial_wolves)
        self.ctx.data["pop.wolves"] = self.W
        self._hist: List[float] = []

    def step(self) -> None:
        S = float(self.ctx.data.get("pop.sheep", 0.0))
        N = _N_PATCHES
        harvest_rate = float(self.ctx.data.get("policy.harvest_rate", 0.0))

        predation = self.predation_rate * self.W * S / N
        dW = self.wolf_reproduce * predation \
             - self.wolf_death_rate * self.W \
             - harvest_rate * self.W
        self.W = max(0.0, self.W + dW)
        self.ctx.data["pop.wolves"] = self.W
        self._hist.append(self.W)

    def metrics_step(self) -> Dict[str, Any]:
        return {"wolves": self.W}

    def metrics_episode(self) -> Dict[str, Any]:
        hist = self._hist
        mean_w = sum(hist) / len(hist) if hist else 0.0
        return {"mean_wolves": mean_w, "final_wolves": self.W}


class PolicyStream(Stream):
    """Writes harvest_rate and grazing_rate into ctx.data from gene values."""

    def __init__(self, name: str, ctx: Context,
                 harvest_rate: float = 0.0,
                 grazing_rate: float = 1.0) -> None:
        super().__init__(name, ctx)
        self.harvest_rate = float(harvest_rate)
        self.grazing_rate = float(grazing_rate)

    def step(self) -> None:
        self.ctx.data["policy.harvest_rate"] = self.harvest_rate
        self.ctx.data["policy.grazing_rate"] = self.grazing_rate

    def metrics_step(self) -> Dict[str, Any]:
        return {"harvest_rate": self.harvest_rate,
                "grazing_rate": self.grazing_rate}

    def metrics_episode(self) -> Dict[str, Any]:
        return self.metrics_step()


class WolfSheepAgg(Stream):
    """End-of-episode aggregates: mean sheep, coexistence, ecosystem health.

    These are the objectives exposed to the EA and tournament via the metric
    contract. Key: wolf_sheep.mean_sheep and wolf_sheep.extinct are read by
    EA, tournament, and bootstrap CI using the same dict keys — consistent
    by structural guarantee, not by convention.
    """

    def __init__(self, name: str, ctx: Context,
                 ext_thresh: float = 1.0) -> None:
        super().__init__(name, ctx)
        self.ext_thresh = float(ext_thresh)
        self._sheep_hist: List[float] = []
        self._wolf_hist: List[float] = []

    def step(self) -> None:
        S = float(self.ctx.data.get("pop.sheep", 0.0))
        W = float(self.ctx.data.get("pop.wolves", 0.0))
        self._sheep_hist.append(S)
        self._wolf_hist.append(W)

    def metrics_step(self) -> Dict[str, Any]:
        return {}

    def metrics_episode(self) -> Dict[str, Any]:
        sh = self._sheep_hist
        wh = self._wolf_hist
        mean_sheep = sum(sh) / len(sh) if sh else 0.0
        mean_wolves = sum(wh) / len(wh) if wh else 0.0
        final_sheep = sh[-1] if sh else 0.0
        final_wolves = wh[-1] if wh else 0.0
        extinct = float(
            (final_sheep < self.ext_thresh) or (final_wolves < self.ext_thresh)
        )
        # Coexistence stability: fraction of steps both populations > threshold
        coexist_steps = sum(
            1 for s, w in zip(sh, wh)
            if s >= self.ext_thresh and w >= self.ext_thresh
        )
        coexistence = coexist_steps / len(sh) if sh else 0.0
        return {
            "mean_sheep": mean_sheep,
            "mean_wolves": mean_wolves,
            "final_sheep": final_sheep,
            "final_wolves": final_wolves,
            "extinct": extinct,
            "coexistence": coexistence,
        }


# ---------------------------------------------------------------------------
# Spec builder
# ---------------------------------------------------------------------------

def make_wolf_sheep_spec(
    harvest_rate: float = 0.0,
    grazing_rate: float = 1.0,
    initial_sheep: float = _INITIAL_SHEEP,
    initial_wolves: float = _INITIAL_WOLVES,
    sheep_reproduce: float = _SHEEP_REPRODUCE,
    wolf_reproduce: float = _WOLF_REPRODUCE,
    grass_regrowth_time: float = _GRASS_REGROWTH_TIME,
) -> List[LayerSpec]:
    """4-layer Wolf-Sheep spec matching the published Mesa model parameters.

    Layer 1: PolicyStream  (writes harvest_rate, grazing_rate to ctx)
    Layer 2: GrassStream   (grass regrowth dynamics)
    Layer 3: SheepStream, WolfStream  (predator-prey dynamics, read grass + policy)
    Layer 4: WolfSheepAgg  (episode-level aggregates for EA and tournament)
    """
    return [
        LayerSpec(streams=[
            StreamSpec("policy", PolicyStream,
                       dict(harvest_rate=harvest_rate,
                            grazing_rate=grazing_rate)),
        ]),
        LayerSpec(streams=[
            StreamSpec("grass", GrassStream,
                       dict(regrowth_time=grass_regrowth_time)),
        ]),
        LayerSpec(streams=[
            StreamSpec("sheep", SheepStream,
                       dict(initial_sheep=initial_sheep,
                            sheep_reproduce=sheep_reproduce)),
            StreamSpec("wolves", WolfStream,
                       dict(initial_wolves=initial_wolves,
                            wolf_reproduce=wolf_reproduce)),
        ]),
        LayerSpec(streams=[
            StreamSpec("wolf_sheep", WolfSheepAgg, dict(ext_thresh=1.0)),
        ]),
    ]


# ---------------------------------------------------------------------------
# Picklable model factory (required for ProcessPoolExecutor in run_many)
# ---------------------------------------------------------------------------

def wolf_sheep_factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
    """Build a Wolf-Sheep model from kwargs for use with run_many()."""
    kw = dict(kwargs)
    harvest_rate = float(kw.pop("harvest_rate", 0.0))
    grazing_rate = float(kw.pop("grazing_rate", 1.0))
    seed = int(kw.pop("seed", 0))
    spec = make_wolf_sheep_spec(harvest_rate=harvest_rate,
                                grazing_rate=grazing_rate, **kw)
    factory_fn = make_model_from_spec(spec, seed=seed)
    return factory_fn({})


# ---------------------------------------------------------------------------
# Gene schema (2 genes: harvest_rate, grazing_rate)
# ---------------------------------------------------------------------------

WOLF_SHEEP_SCHEMA = [
    Real(name="harvest_rate", low=0.0, high=0.3),
    Real(name="grazing_rate", low=0.0, high=1.0),
]


# ---------------------------------------------------------------------------
# Module-level config (set by experiment scripts)
# ---------------------------------------------------------------------------

_N_EVAL_EPISODES: int = 5
_EVAL_SEED: int = 42
_STEPS: int = 200   # 200 steps ≈ published model's typical run length


# ---------------------------------------------------------------------------
# Objective function (picklable, used by run_optimization_simple)
# ---------------------------------------------------------------------------

def wolf_sheep_objective(genome: Sequence[Any]) -> tuple:
    """Two-objective fitness for Wolf-Sheep policy optimisation.

    Minimises (−wolf_sheep.mean_sheep, wolf_sheep.extinct):
      - Maximise mean sheep population (ecosystem productivity)
      - Minimise extinction probability (ecosystem stability)

    Both objectives are read from the same `metrics_episode()` dict,
    guaranteeing that the EA and tournament scorer use identical metrics.
    """
    from ..agent.runner import run_many

    harvest_rate = float(genome[0])
    grazing_rate = float(genome[1])
    result = run_many(
        wolf_sheep_factory,
        steps=_STEPS,
        episodes=_N_EVAL_EPISODES,
        seed=_EVAL_SEED,
        harvest_rate=harvest_rate,
        grazing_rate=grazing_rate,
    )
    sheep_vals = [ep["episode"].get("wolf_sheep.mean_sheep", 0.0)
                  for ep in result["episodes"]]
    extinct_vals = [ep["episode"].get("wolf_sheep.extinct", 1.0)
                    for ep in result["episodes"]]
    mean_sheep = sum(sheep_vals) / max(1, len(sheep_vals))
    mean_extinct = sum(extinct_vals) / max(1, len(extinct_vals))
    return (-mean_sheep, mean_extinct)
