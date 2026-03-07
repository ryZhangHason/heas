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

    Mean-field collapse of Mesa's binary GrassPatch agents (each patch either
    fully_grown=True or counting down to regrowth after being eaten).

    Two processes act on G = (fully-grown patches) / N_patches:

      Regrowth:  each empty patch grows back in ``regrowth_time`` steps.
                 Rate = (1 - G) / regrowth_time   [Mesa: countdown → fully_grown]

      Grazing:   each sheep moves to a random patch each step.
                 P(sheep finds grown patch) = G.
                 Consumption rate = S · G · grazing_rate / N_patches
                 (grazing_rate is the policy gene ∈ [0,1])

    Combined ODE:
        dG/dt = (1 - G) / regrowth_time  −  S · G · grazing_rate / N
    """

    def __init__(self, name: str, ctx: Context,
                 regrowth_time: float = _GRASS_REGROWTH_TIME) -> None:
        super().__init__(name, ctx)
        self.regrowth_time = float(regrowth_time)
        self.G = 0.5                    # initial density (half patches grown, matching Mesa random init)

    def step(self) -> None:
        S = float(self.ctx.data.get("pop.sheep", _INITIAL_SHEEP))
        grazing_rate = float(self.ctx.data.get("policy.grazing_rate", 1.0))
        N = _N_PATCHES
        dG = (1.0 - self.G) / max(self.regrowth_time, 1.0) \
             - S * self.G * grazing_rate / N
        self.G = min(1.0, max(0.0, self.G + dG))
        self.ctx.data["grass.G"] = self.G

    def metrics_step(self) -> Dict[str, Any]:
        return {"G": self.G}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_G": self.G}


class SheepStream(Stream):
    """Sheep population dynamics.

    Mean-field collapse of Mesa's Sheep agent.  Three processes:

    (1) Reproduction (sheep_reproduce = 0.04):
        Each sheep spawns offspring with probability 0.04 per step.
        Rate = sheep_reproduce · S

    (2) Starvation (energy-based death):
        Mesa mechanic: energy -= 1 each step; energy += sheep_gain_from_food
        if the sheep lands on a fully-grown patch (probability G · grazing_rate).
        Expected energy change per step = sheep_gain_from_food · G · grazing_rate − 1
                                        = 4 · G · grazing_rate − 1.
        Mesa initial energy ~ U[0, 2·sheep_gain_from_food] → mean = sheep_gain_from_food = 4.
        Sheep die when energy < 0.  Mean-field starvation rate:
            starvation = max(0, 1 − sheep_gain_from_food · G · grazing_rate)
                         / sheep_gain_from_food
                       = max(0, 1 − 4·G·grazing_rate) / 4
        (Zero when G · grazing_rate ≥ 0.25; i.e. grass supplies enough energy.)

    (3) Predation:
        Each wolf moves to a random patch each step.
        P(wolf lands on a sheep's patch) = S / N_patches.
        Total sheep eaten per step = W · S / N.
        Predation rate per sheep = W / N.

    Combined ODE:
        dS/dt = (sheep_reproduce − starvation) · S  −  W · S / N
    """

    def __init__(self, name: str, ctx: Context,
                 initial_sheep: float = _INITIAL_SHEEP,
                 sheep_reproduce: float = _SHEEP_REPRODUCE,
                 sheep_gain_from_food: float = _SHEEP_GAIN_FROM_FOOD) -> None:
        super().__init__(name, ctx)
        self.sheep_reproduce = float(sheep_reproduce)
        self.sheep_gain_from_food = float(sheep_gain_from_food)
        self.S = float(initial_sheep)
        self.ctx.data["pop.sheep"] = self.S
        self._hist: List[float] = []

    def step(self) -> None:
        G = float(self.ctx.data.get("grass.G", 0.5))
        W = float(self.ctx.data.get("pop.wolves", _INITIAL_WOLVES))
        N = _N_PATCHES
        grazing_rate = float(self.ctx.data.get("policy.grazing_rate", 1.0))

        # Starvation: mean initial energy = sheep_gain_from_food (Mesa: U[0, 2·gain])
        effective_energy_gain = self.sheep_gain_from_food * G * grazing_rate
        starvation = max(0.0, 1.0 - effective_energy_gain) / self.sheep_gain_from_food

        # Predation: contact probability per wolf per step = S / N (random walk)
        predation_per_sheep = W / N

        dS = (self.sheep_reproduce - starvation) * self.S \
             - predation_per_sheep * self.S
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

    Mean-field collapse of Mesa's Wolf agent.  Three processes:

    (1) Reproduction from eating (wolf_reproduce = 0.05):
        Wolf eats a sheep (gains wolf_gain_from_food=20 energy) with probability
        S / N_patches per step (random-walk contact rate).
        Wolf reproduces with probability wolf_reproduce AFTER each eating event.
        Rate of eating events per step = W · S / N.
        Wolf birth rate = wolf_reproduce · W · S / N.

    (2) Starvation (energy-based death):
        Mesa mechanic: energy -= 1 each step; energy += wolf_gain_from_food
        when the wolf eats a sheep (prob S/N per step).
        Expected energy change per step = wolf_gain_from_food · S/N − 1
                                        = 20 · S/N − 1.
        Mesa initial energy ~ U[0, 2·wolf_gain_from_food] → mean = wolf_gain_from_food = 20.
        Wolf starvation rate:
            starvation = max(0, 1 − wolf_gain_from_food · S / N) / wolf_gain_from_food
                       = max(0, 1 − 20 · S / N) / 20
        (Zero when S ≥ N / wolf_gain_from_food = 400 / 20 = 20 sheep.)

    (3) Policy-based harvest:
        harvest_rate · W  (fraction of wolves removed per step; gene ∈ [0, 0.3])

    Combined ODE:
        dW/dt = wolf_reproduce · W · S / N
                − max(0, 1 − 20·S/N) / 20 · W
                − harvest_rate · W
    """

    def __init__(self, name: str, ctx: Context,
                 initial_wolves: float = _INITIAL_WOLVES,
                 wolf_reproduce: float = _WOLF_REPRODUCE,
                 wolf_gain_from_food: float = _WOLF_GAIN_FROM_FOOD) -> None:
        super().__init__(name, ctx)
        self.wolf_reproduce = float(wolf_reproduce)
        self.wolf_gain_from_food = float(wolf_gain_from_food)
        self.W = float(initial_wolves)
        self.ctx.data["pop.wolves"] = self.W
        self._hist: List[float] = []

    def step(self) -> None:
        S = float(self.ctx.data.get("pop.sheep", 0.0))
        N = _N_PATCHES
        harvest_rate = float(self.ctx.data.get("policy.harvest_rate", 0.0))

        # Wolf births: wolf_reproduce per eating event; eating rate = W·S/N
        wolf_births = self.wolf_reproduce * self.W * S / N

        # Starvation: mean initial energy = wolf_gain_from_food (Mesa: U[0, 2·gain])
        starvation = max(0.0, 1.0 - self.wolf_gain_from_food * S / N) \
                     / self.wolf_gain_from_food

        dW = wolf_births - starvation * self.W - harvest_rate * self.W
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
    """4-layer Wolf-Sheep spec using published Mesa Wolf-Sheep default parameters.

    All published parameters (sheep_reproduce, wolf_reproduce, wolf_gain_from_food,
    sheep_gain_from_food, grass_regrowth_time, initial populations, N=400 patches)
    are hard-wired to the Mesa defaults.  The ODE terms are derived analytically
    from Mesa's energy mechanics (see each Stream docstring for derivation).

    Layer 1: PolicyStream  (writes harvest_rate, grazing_rate to ctx)
    Layer 2: GrassStream   (dG = (1-G)/30 - S·G·grazing_rate/N)
    Layer 3: SheepStream   (reproduction, starvation, predation)
             WolfStream    (birth from eating, starvation, harvest)
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
