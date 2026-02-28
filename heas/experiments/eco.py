"""
heas.experiments.eco
====================
Canonical ecological metacommunity streams, factories, schemas, and objectives
for the HEAS WSC paper experiments.

Stream implementations are extracted from ``docs/py/playground.py`` and adapted
to import from the canonical ``heas`` package (rather than the browser-lite copy).

Two experimental setups are provided — matching the two distinct narratives in the
paper that were previously conflated:

trait_*
    Trait-based evolution: two evolvable genes (risk, dispersal) encoded as
    ``Real`` genes.  Used for the multi-objective NSGA-II Pareto front study
    (tournament narrative / Table 3 trait column).

mlp_*
    MLP policy evolution: an ``MLPPolicy(4, 2, (16,16))`` whose flattened
    weights form the gene vector.  Reads environmental observations from
    ``ctx.data`` and outputs ``policy.risk`` / ``policy.dispersal`` each tick.
    Used for the MLP-champion Table 3 results.
"""

from __future__ import annotations

import math
import random
from functools import partial
from typing import Any, Dict, List, Optional, Sequence

from ..hierarchy.base import Context, Layer, Stream
from ..hierarchy.orchestrator import (
    CompositeHeasModel,
    LayerSpec,
    StreamSpec,
    make_model_from_spec,
)
from ..schemas.genes import Real

# ============================================================================
# Ecological Streams  (copied verbatim from playground.py, adapted imports)
# ============================================================================


class Climate(Stream):
    def __init__(self, name: str, ctx: Context, amp: float = 0.4,
                 period: float = 12.0, shock_prob: float = 0.1,
                 out_key: str = "climate") -> None:
        super().__init__(name, ctx)
        self.amp = float(amp)
        self.period = float(period)
        self.shock_prob = float(shock_prob)
        self.out_key = out_key
        self.value = 0.0

    def step(self) -> None:
        seasonal = self.amp * math.sin(2.0 * math.pi * (self.ctx.t / max(self.period, 1.0)))
        shock = (self.amp * (2.0 * self.ctx.rng.random() - 1.0)
                 if self.ctx.rng.random() < self.shock_prob else 0.0)
        self.value = seasonal + shock
        self.ctx.data[self.out_key] = self.value

    def metrics_step(self) -> Dict[str, Any]:
        return {"value": self.value}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_value": self.value}


class Landscape(Stream):
    def __init__(self, name: str, ctx: Context, n_patches: int = 12,
                 fragmentation: float = 0.2, move_cost: float = 0.2,
                 out_key: str = "landscape.quality") -> None:
        super().__init__(name, ctx)
        self.n_patches = int(n_patches)
        self.frag = float(fragmentation)
        self.move_cost = float(move_cost)
        self.out_key = out_key
        self.quality = max(0.0, 1.0 - self.frag)

    def step(self) -> None:
        self.quality = max(0.0, 1.0 - self.frag)
        self.ctx.data[self.out_key] = self.quality
        self.ctx.data["landscape.move_cost"] = self.move_cost
        self.ctx.data["landscape.n_patches"] = self.n_patches

    def metrics_step(self) -> Dict[str, Any]:
        return {"quality": self.quality}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_quality": self.quality}


class PreyRisk(Stream):
    def __init__(self, name: str, ctx: Context, x0: float = 40.0,
                 r: float = 0.55, K: float = 120.0, risk: float = 0.55,
                 betaF: float = 0.3, gammaV: float = 0.2,
                 prey_key: str = "pop.prey", pred_key: str = "pop.pred") -> None:
        super().__init__(name, ctx)
        self.x0 = float(x0)
        self.r = float(r)
        self.K = float(K)
        self.risk = float(risk)
        self.betaF = float(betaF)
        self.gammaV = float(gammaV)
        self.prey_key = prey_key
        self.pred_key = pred_key
        if self.prey_key not in self.ctx.data:
            self.ctx.data[self.prey_key] = self.x0
        self.x = float(self.ctx.data.get(self.prey_key, self.x0))

    def step(self) -> None:
        climate = float(self.ctx.data.get("climate", 0.0))
        quality = float(self.ctx.data.get("landscape.quality", 1.0))
        pred = float(self.ctx.data.get(self.pred_key, 10.0))
        growth = self.r * (1.0 + self.betaF * climate) * self.x * (1.0 - self.x / max(self.K, 1e-6))
        forage = max(0.0, 1.0 - self.risk) * (1.0 + self.gammaV * quality)
        loss = self.risk * forage * self.x * pred * 0.01
        self.x = max(0.0, self.x + growth - loss)
        self.ctx.data[self.prey_key] = self.x

    def metrics_step(self) -> Dict[str, Any]:
        return {"prey": self.x}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_prey": self.x}


class PreyRiskDynamic(PreyRisk):
    """PreyRisk subclass that reads ``risk`` from ``ctx.data["policy.risk"]`` if set.

    Used in the MLP policy experiment (Exp 4) so that the evolved MLP's risk
    output actually feeds into prey dynamics each tick.
    """

    def step(self) -> None:
        # Override risk from policy if available
        policy_risk = self.ctx.data.get("policy.risk")
        if policy_risk is not None:
            self.risk = float(policy_risk)
        super().step()


class PredatorResponse(Stream):
    def __init__(self, name: str, ctx: Context, y0: float = 9.0,
                 conv: float = 0.02, mort: float = 0.15,
                 prey_key: str = "pop.prey", pred_key: str = "pop.pred") -> None:
        super().__init__(name, ctx)
        self.y0 = float(y0)
        self.conv = float(conv)
        self.mort = float(mort)
        self.prey_key = prey_key
        self.pred_key = pred_key
        if self.pred_key not in self.ctx.data:
            self.ctx.data[self.pred_key] = self.y0
        self.y = float(self.ctx.data.get(self.pred_key, self.y0))

    def step(self) -> None:
        prey = float(self.ctx.data.get(self.prey_key, 40.0))
        self.y = max(0.0, self.y + self.conv * prey * self.y * 0.01 - self.mort * self.y)
        self.ctx.data[self.pred_key] = self.y

    def metrics_step(self) -> Dict[str, Any]:
        return {"pred": self.y}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_pred": self.y}


class Movement(Stream):
    def __init__(self, name: str, ctx: Context, dispersal: float = 0.35,
                 prey_key: str = "pop.prey", pred_key: str = "pop.pred") -> None:
        super().__init__(name, ctx)
        self.dispersal = float(dispersal)
        self.prey_key = prey_key
        self.pred_key = pred_key

    def step(self) -> None:
        prey = float(self.ctx.data.get(self.prey_key, 0.0))
        pred = float(self.ctx.data.get(self.pred_key, 0.0))
        damp = max(0.0, min(1.0, self.dispersal))
        self.ctx.data[self.prey_key] = max(0.0, prey * (1.0 + 0.01 * damp))
        self.ctx.data[self.pred_key] = max(0.0, pred * (1.0 - 0.005 * damp))

    def metrics_step(self) -> Dict[str, Any]:
        return {"dispersal": self.dispersal}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_dispersal": self.dispersal}


class MovementDynamic(Movement):
    """Movement subclass that reads ``dispersal`` from ``ctx.data["policy.dispersal"]`` if set."""

    def step(self) -> None:
        policy_disp = self.ctx.data.get("policy.dispersal")
        if policy_disp is not None:
            self.dispersal = float(policy_disp)
        super().step()


class Aggregator(Stream):
    def __init__(self, name: str, ctx: Context, ext_thresh: float = 1.0,
                 prey_key: str = "pop.prey", pred_key: str = "pop.pred") -> None:
        super().__init__(name, ctx)
        self.ext_thresh = float(ext_thresh)
        self.prey_key = prey_key
        self.pred_key = pred_key
        self.extinct = False
        self.prey = 0.0
        self.pred = 0.0
        self._prey_hist: List[float] = []

    def step(self) -> None:
        self.prey = float(self.ctx.data.get(self.prey_key, 0.0))
        self.pred = float(self.ctx.data.get(self.pred_key, 0.0))
        self.extinct = (self.prey < self.ext_thresh) or (self.pred < self.ext_thresh)
        self._prey_hist.append(self.prey)

    def metrics_step(self) -> Dict[str, Any]:
        return {"prey": self.prey, "pred": self.pred, "extinct": float(self.extinct)}

    def metrics_episode(self) -> Dict[str, Any]:
        hist = self._prey_hist
        mean_bio = sum(hist) / len(hist) if hist else 0.0
        mean_sq = sum(x * x for x in hist) / len(hist) if hist else 0.0
        cv = (mean_sq - mean_bio ** 2) ** 0.5 / max(mean_bio, 1e-9)
        return {
            "final_prey": self.prey,
            "final_pred": self.pred,
            "extinct": float(self.extinct),
            "mean_biomass": mean_bio,
            "cv": cv,
        }


# ============================================================================
# MLP Policy Stream
# ============================================================================

class MLPPolicyStream(Stream):
    """Reads [prey, pred, climate, landscape_quality], runs MLP, writes to ctx.

    Writes ``policy.risk`` and ``policy.dispersal`` into ``ctx.data`` so that
    :class:`PreyRiskDynamic` and :class:`MovementDynamic` can consume them in
    the same tick (they execute in a later layer).
    """

    def __init__(self, name: str, ctx: Context, weights: List[float],
                 in_dim: int = 4, out_dim: int = 2,
                 hidden: tuple = (16, 16)) -> None:
        super().__init__(name, ctx)
        try:
            import torch
            from ...torch_integration.policies import MLPPolicy
            from ...torch_integration.params import unflatten_params
            self._policy = MLPPolicy(in_dim, out_dim, hidden)
            vec = torch.tensor(list(weights), dtype=torch.float32)
            unflatten_params(self._policy, vec)
            self._torch_available = True
        except Exception:
            self._torch_available = False
            self._weights = list(weights)

    def step(self) -> None:
        prey = float(self.ctx.data.get("pop.prey", 40.0))
        pred = float(self.ctx.data.get("pop.pred", 9.0))
        climate = float(self.ctx.data.get("climate", 0.0))
        quality = float(self.ctx.data.get("landscape.quality", 1.0))

        if self._torch_available:
            import torch
            obs = torch.tensor([prey, pred, climate, quality], dtype=torch.float32)
            with torch.no_grad():
                out = self._policy(obs).numpy()
            dispersal = float(max(0.0, min(1.0, out[0])))
            risk = float(max(0.0, min(1.0, out[1])))
        else:
            # Fallback: linear combination of weights (degenerate but picklable)
            w = self._weights
            n = len(w) // 2 if len(w) >= 2 else 1
            raw_d = sum(w[:n]) / max(n, 1)
            raw_r = sum(w[n:2*n]) / max(n, 1)
            dispersal = float(max(0.0, min(1.0, 0.5 + 0.1 * raw_d)))
            risk = float(max(0.0, min(1.0, 0.5 + 0.1 * raw_r)))

        self.ctx.data["policy.dispersal"] = dispersal
        self.ctx.data["policy.risk"] = risk

    def metrics_step(self) -> Dict[str, Any]:
        return {
            "dispersal": float(self.ctx.data.get("policy.dispersal", 0.0)),
            "risk": float(self.ctx.data.get("policy.risk", 0.0)),
        }

    def metrics_episode(self) -> Dict[str, Any]:
        return self.metrics_step()


# ============================================================================
# Spec builders
# ============================================================================

def make_trait_spec(
    risk: float = 0.55,
    dispersal: float = 0.35,
    n_patches: int = 12,
    fragmentation: float = 0.2,
    move_cost: float = 0.2,
    x0: float = 40.0,
    r: float = 0.55,
    K: float = 120.0,
    amp: float = 0.4,
    period: float = 12.0,
    shock_prob: float = 0.1,
) -> List[LayerSpec]:
    """4-layer trait-based ecological spec.

    Layer 1: Climate
    Layer 2: Landscape
    Layer 3: PreyRisk, PredatorResponse, Movement  (trait values fixed at init)
    Layer 4: Aggregator
    """
    return [
        LayerSpec(streams=[
            StreamSpec("climate", Climate,
                       dict(amp=amp, period=period, shock_prob=shock_prob)),
        ]),
        LayerSpec(streams=[
            StreamSpec("landscape", Landscape,
                       dict(n_patches=n_patches, fragmentation=fragmentation,
                            move_cost=move_cost)),
        ]),
        LayerSpec(streams=[
            StreamSpec("prey", PreyRisk,
                       dict(x0=x0, r=r, K=K, risk=risk, betaF=0.3, gammaV=0.2)),
            StreamSpec("pred", PredatorResponse, dict(y0=9.0, conv=0.02, mort=0.15)),
            StreamSpec("move", Movement, dict(dispersal=dispersal)),
        ]),
        LayerSpec(streams=[
            StreamSpec("agg", Aggregator, dict(ext_thresh=1.0)),
        ]),
    ]


def make_mlp_spec(
    weights: List[float],
    n_patches: int = 12,
    fragmentation: float = 0.2,
    move_cost: float = 0.2,
    x0: float = 40.0,
    r: float = 0.55,
    K: float = 120.0,
    amp: float = 0.4,
    period: float = 12.0,
    shock_prob: float = 0.1,
) -> List[LayerSpec]:
    """5-layer MLP-policy ecological spec.

    Layer 1: Climate
    Layer 2: Landscape
    Layer 3: MLPPolicyStream  (writes policy.risk / policy.dispersal to ctx)
    Layer 4: PreyRiskDynamic, PredatorResponse, MovementDynamic
             (read policy.* from ctx this tick)
    Layer 5: Aggregator
    """
    return [
        LayerSpec(streams=[
            StreamSpec("climate", Climate,
                       dict(amp=amp, period=period, shock_prob=shock_prob)),
        ]),
        LayerSpec(streams=[
            StreamSpec("landscape", Landscape,
                       dict(n_patches=n_patches, fragmentation=fragmentation,
                            move_cost=move_cost)),
        ]),
        LayerSpec(streams=[
            StreamSpec("policy", MLPPolicyStream, dict(weights=weights)),
        ]),
        LayerSpec(streams=[
            StreamSpec("prey", PreyRiskDynamic,
                       dict(x0=x0, r=r, K=K, risk=0.55, betaF=0.3, gammaV=0.2)),
            StreamSpec("pred", PredatorResponse, dict(y0=9.0, conv=0.02, mort=0.15)),
            StreamSpec("move", MovementDynamic, dict(dispersal=0.35)),
        ]),
        LayerSpec(streams=[
            StreamSpec("agg", Aggregator, dict(ext_thresh=1.0)),
        ]),
    ]


# ============================================================================
# Module-level factories (picklable — required for ProcessPoolExecutor)
# ============================================================================

def trait_model_factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
    """Build a trait-based ecological model from kwargs.

    Expected kwargs: ``risk``, ``dispersal``, ``seed``, and any
    ``make_trait_spec`` keyword argument.
    """
    kw = dict(kwargs)
    risk = float(kw.pop("risk", 0.55))
    dispersal = float(kw.pop("dispersal", 0.35))
    seed = int(kw.pop("seed", 0))
    spec = make_trait_spec(risk=risk, dispersal=dispersal, **kw)
    factory_fn = make_model_from_spec(spec, seed=seed)
    return factory_fn({})


def mlp_model_factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
    """Build an MLP-policy ecological model from kwargs.

    Expected kwargs: ``weights`` (list of floats), ``seed``, and any
    ``make_mlp_spec`` keyword argument.
    """
    kw = dict(kwargs)
    weights = kw.pop("weights", [])
    seed = int(kw.pop("seed", 0))
    spec = make_mlp_spec(weights=weights, **kw)
    factory_fn = make_model_from_spec(spec, seed=seed)
    return factory_fn({})


# ============================================================================
# Gene schemas
# ============================================================================

TRAIT_SCHEMA = [
    Real(name="risk",      low=0.0, high=1.0),
    Real(name="dispersal", low=0.0, high=1.0),
]

_MLP_SCHEMA: Optional[List[Real]] = None


def get_mlp_schema() -> List[Real]:
    """Lazily build and cache the MLP weight gene schema.

    Uses MLPPolicy(4, 2, (16, 16)) parameter count.
    """
    global _MLP_SCHEMA
    if _MLP_SCHEMA is not None:
        return _MLP_SCHEMA
    try:
        import torch
        from ..torch_integration.policies import MLPPolicy
        net = MLPPolicy(4, 2, (16, 16))
        n = sum(p.numel() for p in net.parameters())
    except Exception:
        # Fallback: 4*16 + 16 + 16*16 + 16 + 16*2 + 2 = 64+16+256+16+32+2 = 386
        n = 386
    _MLP_SCHEMA = [Real(name=f"w{i}", low=-1.0, high=1.0) for i in range(n)]
    return _MLP_SCHEMA


# ============================================================================
# Module-level config vars (set by experiment scripts before calling optimize)
# ============================================================================

_N_EVAL_EPISODES: int = 5
_EVAL_SEED: int = 42


# ============================================================================
# Objective functions (module-level, picklable)
# ============================================================================

def trait_objective(genome: Sequence[Any]) -> tuple:
    """Two-objective fitness for trait-based NSGA-II.

    Minimises ``(-mean_prey, extinction_rate)`` averaged over
    ``_N_EVAL_EPISODES`` episodes.
    """
    from ..agent.runner import run_many

    risk = float(genome[0])
    dispersal = float(genome[1])
    result = run_many(
        trait_model_factory,
        steps=140,
        episodes=_N_EVAL_EPISODES,
        seed=_EVAL_SEED,
        risk=risk,
        dispersal=dispersal,
    )
    prey_vals = [ep["episode"].get("agg.final_prey", 0.0)
                 for ep in result["episodes"]]
    ext_vals = [float(ep["episode"].get("agg.extinct", 1.0))
                for ep in result["episodes"]]
    mean_prey = sum(prey_vals) / max(1, len(prey_vals))
    mean_ext = sum(ext_vals) / max(1, len(ext_vals))
    return (-mean_prey, mean_ext)


def _mlp_objective_impl(genome: Sequence[Any], n_eval: int, eval_seed: int) -> tuple:
    """Implementation helper — module-level so partials of it are picklable."""
    from ..agent.runner import run_many

    weights = [float(g) for g in genome]
    result = run_many(
        mlp_model_factory,
        steps=140,
        episodes=n_eval,
        seed=eval_seed,
        weights=weights,
    )
    prey_vals = [ep["episode"].get("agg.final_prey", 0.0)
                 for ep in result["episodes"]]
    ext_vals = [float(ep["episode"].get("agg.extinct", 1.0))
                for ep in result["episodes"]]
    mean_prey = sum(prey_vals) / max(1, len(prey_vals))
    mean_ext = sum(ext_vals) / max(1, len(ext_vals))
    return (-mean_prey, mean_ext)


def mlp_objective(genome: Sequence[Any]) -> tuple:
    """Two-objective fitness for MLP weight evolution.

    Reads ``_N_EVAL_EPISODES`` and ``_EVAL_SEED`` module globals.
    """
    return _mlp_objective_impl(genome, _N_EVAL_EPISODES, _EVAL_SEED)
