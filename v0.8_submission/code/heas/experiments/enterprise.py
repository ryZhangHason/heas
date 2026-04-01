"""
heas.experiments.enterprise
============================
Canonical enterprise decision-making streams, factories, schemas, and objectives
for the HEAS WSC paper experiments.

Stream implementations are extracted verbatim from ``docs/py/playground.py``
and adapted to import from the canonical ``heas`` package.

Experiment setup
----------------
Two focal firms operate in a regulated industry.  Exogenous drivers
(GovernmentPolicy, IndustryRegime, MarketSignal) live in Layer 1.
Firm-level processes (FirmGroup, AllianceMediator) are in Layers 2–3.
Aggregation (AggregatorFirm) lives in Layer 4.

The 32-scenario grid:
    regime × base_demand × audit_prob × firm_count × costs  =  2⁵ = 32
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ..hierarchy.base import Context, Stream
from ..hierarchy.orchestrator import (
    CompositeHeasModel,
    LayerSpec,
    StreamSpec,
    make_model_from_spec,
)
from ..schemas.genes import Real


# ============================================================================
# Enterprise Streams  (copied verbatim from playground.py, adapted imports)
# ============================================================================


class GovernmentPolicy(Stream):
    def __init__(self, name: str, ctx: Context, regime: str = "coop",
                 tax: float = 0.1, audit_intensity: float = 0.2,
                 subsidy: float = 0.0, penalty_rate: float = 0.1) -> None:
        super().__init__(name, ctx)
        self.regime = str(regime)
        self.tax = float(tax)
        self.audit_intensity = float(audit_intensity)
        self.subsidy = float(subsidy)
        self.penalty_rate = float(penalty_rate)

    def step(self) -> None:
        coop = 1.0 if self.regime == "coop" else 0.0
        self.ctx.data["gov.tax"] = self.tax
        self.ctx.data["gov.audit_intensity"] = self.audit_intensity
        self.ctx.data["gov.subsidy"] = self.subsidy * (0.5 + 0.5 * coop)
        self.ctx.data["gov.penalty_rate"] = self.penalty_rate * (0.5 + 0.5 * (1.0 - coop))

    def metrics_step(self) -> Dict[str, Any]:
        return {"tax": self.tax, "audit_intensity": self.audit_intensity}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_tax": self.tax, "final_audit_intensity": self.audit_intensity}


class IndustryRegime(Stream):
    def __init__(self, name: str, ctx: Context, audit_prob: float = 0.2,
                 penalty_intensity: float = 0.3) -> None:
        super().__init__(name, ctx)
        self.audit_prob = float(audit_prob)
        self.penalty_intensity = float(penalty_intensity)

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        target_idx = int(max(range(len(states)), key=lambda i: float(states[i]))) if states else 0
        self.ctx.data["reg.audit_prob"] = min(1.0, max(0.0, self.audit_prob))
        self.ctx.data["reg.penalty_intensity"] = max(0.0, self.penalty_intensity)
        self.ctx.data["reg.target_firm_idx"] = target_idx

    def metrics_step(self) -> Dict[str, Any]:
        return {"audit_prob": self.ctx.data.get("reg.audit_prob", self.audit_prob)}

    def metrics_episode(self) -> Dict[str, Any]:
        return {
            "final_audit_prob": self.ctx.data.get("reg.audit_prob", self.audit_prob),
            "final_penalty_intensity": self.ctx.data.get("reg.penalty_intensity", self.penalty_intensity),
        }


class MarketSignal(Stream):
    def __init__(self, name: str, ctx: Context, base_demand: float = 100.0,
                 shock_amp: float = 0.2, atr: float = 0.1,
                 growth_rate: float = 0.02, market_power: float = 0.2) -> None:
        super().__init__(name, ctx)
        self.base_demand = float(base_demand)
        self.shock_amp = float(shock_amp)
        self.atr = float(atr)
        self.growth_rate = float(growth_rate)
        self.market_power = float(market_power)
        self.demand_t = self.base_demand
        self.price_signal = 1.0

    def step(self) -> None:
        shock = self.ctx.rng.gauss(0.0, self.shock_amp)
        self.demand_t = max(0.0, self.base_demand * (
            1.0 + self.growth_rate * self.ctx.t + shock
        ))
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        max_balance = max((float(x) for x in states), default=0.0)
        power_bonus = self.market_power * max(0.0, max_balance)
        self.price_signal = max(0.1, 1.0 + self.atr * shock + power_bonus * 0.01)
        self.ctx.data["market.demand_t"] = self.demand_t
        self.ctx.data["market.price_signal"] = self.price_signal

    def metrics_step(self) -> Dict[str, Any]:
        return {"demand_t": self.demand_t, "price_signal": self.price_signal}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_demand_t": self.demand_t}


class FirmGroup(Stream):
    def __init__(self, name: str, ctx: Context, firm_count: int = 4,
                 costs: float = 0.4, initial_balance: float = 1.0) -> None:
        super().__init__(name, ctx)
        self.firm_count = max(1, int(firm_count))
        self.costs = float(costs)
        self.initial_balance = float(initial_balance)
        self.actions: List[float] = [0.0] * self.firm_count
        self.states: List[float] = [self.initial_balance] * self.firm_count
        self.compliance: List[float] = [1.0] * self.firm_count

    def step(self) -> None:
        demand = float(self.ctx.data.get("market.demand_t", 100.0))
        price = float(self.ctx.data.get("market.price_signal", 1.0))
        audit_prob = float(self.ctx.data.get("reg.audit_prob", 0.2))
        penalty_intensity = float(self.ctx.data.get("reg.penalty_intensity", 0.3))
        target_idx = int(self.ctx.data.get("reg.target_firm_idx", 0))
        tax = float(self.ctx.data.get("gov.tax", 0.1))
        intensity = (demand / 100.0) - self.costs
        base_action = max(0.0, intensity)
        for i in range(self.firm_count):
            action = max(0.0, base_action * (1.0 - 0.02 * i))
            compliance = 1.0 if action >= 0.05 else 0.0
            audit_risk = audit_prob * (1.0 - compliance)
            penalty = penalty_intensity * (1.0 - compliance) if i == target_idx else 0.0
            self.states[i] = self.states[i] + action * price - tax - audit_risk - penalty
            self.actions[i] = action
            self.compliance[i] = compliance
        self.ctx.data["firms.count"] = self.firm_count
        self.ctx.data["firms.actions"] = list(self.actions)
        self.ctx.data["firms.states"] = list(self.states)
        self.ctx.data["firms.compliance"] = list(self.compliance)

    def metrics_step(self) -> Dict[str, Any]:
        mean_state = sum(self.states) / max(1, len(self.states))
        return {"mean_balance": mean_state}

    def metrics_episode(self) -> Dict[str, Any]:
        mean_state = sum(self.states) / max(1, len(self.states))
        return {"final_mean_balance": mean_state, "final_firm_count": float(self.firm_count)}


class AllianceMediator(Stream):
    def __init__(self, name: str, ctx: Context, bargain_rule: str = "equal",
                 side_payment: float = 0.0) -> None:
        super().__init__(name, ctx)
        self.bargain_rule = str(bargain_rule)
        self.side_payment = float(side_payment)
        self.alliance_state = 0.0
        self.transfers = 0.0

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        total = sum(float(x) for x in states) if states else 0.0
        join = 1.0 if total > 0 else 0.0
        self.alliance_state = join
        split = 0.5 if self.bargain_rule == "equal" else 0.6
        self.transfers = self.side_payment * split
        self.ctx.data["alliance.state"] = self.alliance_state
        self.ctx.data["alliance.transfers"] = self.transfers

    def metrics_step(self) -> Dict[str, Any]:
        return {"alliance_state": self.alliance_state}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_alliance_state": self.alliance_state}


class AllianceRule(Stream):
    def __init__(self, name: str, ctx: Context, rule: Any = 1) -> None:
        super().__init__(name, ctx)
        self.rule = rule

    def step(self) -> None:
        val = 1.0 if (float(self.rule) >= 0.5 if isinstance(self.rule, (int, float))
                      else str(self.rule).lower() == "join") else 0.0
        self.ctx.data["rule.alliance"] = val

    def metrics_step(self) -> Dict[str, Any]:
        return {"alliance_rule": float(self.ctx.data.get("rule.alliance", 0.0))}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_alliance_rule": float(self.ctx.data.get("rule.alliance", 0.0))}


class GroupGamingRule(Stream):
    def __init__(self, name: str, ctx: Context, mode: Any = 1) -> None:
        super().__init__(name, ctx)
        self.mode = mode

    def step(self) -> None:
        val = 1.0 if (float(self.mode) >= 0.5 if isinstance(self.mode, (int, float))
                      else str(self.mode).lower() == "cooperate") else 0.0
        self.ctx.data["rule.group_mode"] = val

    def metrics_step(self) -> Dict[str, Any]:
        return {"group_mode": float(self.ctx.data.get("rule.group_mode", 0.0))}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_group_mode": float(self.ctx.data.get("rule.group_mode", 0.0))}


class PayoffAccounting(Stream):
    def __init__(self, name: str, ctx: Context, strategy: Any = "collaborate") -> None:
        super().__init__(name, ctx)
        self.strategy = strategy
        self.delta = 0.0

    def step(self) -> None:
        if isinstance(self.strategy, (int, float)):
            self.delta = float(self.strategy)
        else:
            self.delta = 2.0 if str(self.strategy).lower() == "collaborate" else -1.0
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        new_states = [float(s) + self.delta for s in states]
        self.ctx.data["firms.states"] = new_states
        self.ctx.data["payoff.profits"] = [self.delta] * len(new_states)
        self.ctx.data["payoff.welfare_t"] = self.delta * float(len(new_states))

    def metrics_step(self) -> Dict[str, Any]:
        count = float(len(self.ctx.data.get("firms.states", [])))
        return {"delta": self.delta, "welfare_t": self.delta * count}

    def metrics_episode(self) -> Dict[str, Any]:
        count = float(len(self.ctx.data.get("firms.states", [])))
        return {"final_delta": self.delta, "final_welfare_t": self.delta * count}


class AggregatorFirm(Stream):
    def __init__(self, name: str, ctx: Context, welfare_weights: float = 1.0,
                 risk_penalty: float = 0.2) -> None:
        super().__init__(name, ctx)
        self.welfare_weights = float(welfare_weights)
        self.risk_penalty = float(risk_penalty)
        self.mean_profit = 0.0
        self.var_profit = 0.0
        self.compliance = 0.0
        self.stability = 0.0
        self.welfare = 0.0
        self._hist: List[float] = []

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        alliance = float(self.ctx.data.get("rule.alliance", 0.0))
        group_mode = float(self.ctx.data.get("rule.group_mode", 1.0))
        mean_state = (sum(float(x) for x in states) / max(1, len(states))) if states else 0.0
        self.mean_profit = mean_state + alliance * 0.1
        self._hist.append(self.mean_profit)
        if len(self._hist) > 1:
            mean = sum(self._hist) / len(self._hist)
            self.var_profit = sum((x - mean) ** 2 for x in self._hist) / len(self._hist)
        comp = self.ctx.data.get("firms.compliance", [])
        if not isinstance(comp, list):
            comp = []
        self.compliance = (sum(float(x) for x in comp) / max(1, len(comp))) if comp else 0.0
        self.stability = 1.0 / (1.0 + self.var_profit) * (0.8 + 0.2 * group_mode)
        self.welfare = self.welfare_weights * self.mean_profit - self.risk_penalty * (1.0 - self.compliance)
        self.ctx.data["agg.mean_profit"] = self.mean_profit
        self.ctx.data["agg.var_profit"] = self.var_profit
        self.ctx.data["agg.compliance"] = self.compliance
        self.ctx.data["agg.stability"] = self.stability
        self.ctx.data["agg.welfare"] = self.welfare

    def metrics_step(self) -> Dict[str, Any]:
        return {
            "mean_profit": self.mean_profit,
            "var_profit": self.var_profit,
            "compliance": self.compliance,
            "stability": self.stability,
            "welfare": self.welfare,
        }

    def metrics_episode(self) -> Dict[str, Any]:
        return {
            "final_mean_profit": self.mean_profit,
            "final_var_profit": self.var_profit,
            "final_compliance": self.compliance,
            "final_stability": self.stability,
            "final_welfare": self.welfare,
        }


# ============================================================================
# Spec builder
# ============================================================================

def make_enterprise_spec(
    regime: str = "coop",
    tax: float = 0.1,
    audit_intensity: float = 0.2,
    subsidy: float = 0.0,
    penalty_rate: float = 0.1,
    audit_prob: float = 0.2,
    penalty_intensity: float = 0.3,
    base_demand: float = 100.0,
    shock_amp: float = 0.2,
    atr: float = 0.1,
    growth_rate: float = 0.02,
    market_power: float = 0.2,
    firm_count: int = 4,
    costs: float = 0.4,
    initial_balance: float = 1.0,
    bargain_rule: str = "equal",
    side_payment: float = 0.0,
    welfare_weights: float = 1.0,
    risk_penalty: float = 0.2,
    alliance_rule: int = 1,
    group_mode: int = 1,
    strategy: str = "collaborate",
) -> List[LayerSpec]:
    """5-layer enterprise spec.

    Layer 1: GovernmentPolicy
    Layer 2: IndustryRegime, MarketSignal
    Layer 3: FirmGroup
    Layer 4: AllianceMediator, AllianceRule, GroupGamingRule
    Layer 5: PayoffAccounting, AggregatorFirm
    """
    return [
        LayerSpec(streams=[
            StreamSpec("gov", GovernmentPolicy,
                       dict(regime=regime, tax=tax, audit_intensity=audit_intensity,
                            subsidy=subsidy, penalty_rate=penalty_rate)),
        ]),
        LayerSpec(streams=[
            StreamSpec("reg", IndustryRegime,
                       dict(audit_prob=audit_prob, penalty_intensity=penalty_intensity)),
            StreamSpec("market", MarketSignal,
                       dict(base_demand=base_demand, shock_amp=shock_amp, atr=atr,
                            growth_rate=growth_rate, market_power=market_power)),
        ]),
        LayerSpec(streams=[
            StreamSpec("firms", FirmGroup,
                       dict(firm_count=firm_count, costs=costs,
                            initial_balance=initial_balance)),
        ]),
        LayerSpec(streams=[
            StreamSpec("alliance", AllianceMediator,
                       dict(bargain_rule=bargain_rule, side_payment=side_payment)),
            StreamSpec("rule_a", AllianceRule, dict(rule=alliance_rule)),
            StreamSpec("rule_g", GroupGamingRule, dict(mode=group_mode)),
        ]),
        LayerSpec(streams=[
            StreamSpec("payoff", PayoffAccounting, dict(strategy=strategy)),
            StreamSpec("agg", AggregatorFirm,
                       dict(welfare_weights=welfare_weights, risk_penalty=risk_penalty)),
        ]),
    ]


# ============================================================================
# Module-level factories (picklable)
# ============================================================================

def enterprise_model_factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
    """Build an enterprise model.  All ``make_enterprise_spec`` params accepted."""
    kw = dict(kwargs)
    seed = int(kw.pop("seed", 0))
    spec = make_enterprise_spec(**kw)
    factory_fn = make_model_from_spec(spec, seed=seed)
    return factory_fn({})


def reference_participant_factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
    """Baseline enterprise model with default (untuned) parameters."""
    kw = dict(kwargs)
    seed = int(kw.pop("seed", 0))
    # Keep only scenario parameters, use default policy params
    scenario_keys = {"regime", "base_demand", "audit_prob", "firm_count", "costs"}
    scenario_kw = {k: v for k, v in kw.items() if k in scenario_keys}
    spec = make_enterprise_spec(tax=0.1, audit_intensity=0.2, **scenario_kw)
    factory_fn = make_model_from_spec(spec, seed=seed)
    return factory_fn({})


# ============================================================================
# Gene schema
# ============================================================================

ENTERPRISE_SCHEMA = [
    Real(name="tax",             low=0.0, high=0.5),
    Real(name="audit_intensity", low=0.0, high=1.0),
    Real(name="subsidy",         low=0.0, high=0.5),
    Real(name="penalty_rate",    low=0.0, high=0.5),
]


# ============================================================================
# 32-scenario grid
# ============================================================================

def make_32_scenarios():
    """Build the 32-scenario grid used in WSC Table 5.

    Grid: 2 × 2 × 2 × 2 × 2 = 32 scenarios
        regime:      ['coop', 'compete']
        base_demand: [80.0,  120.0]
        audit_prob:  [0.1,   0.4]
        firm_count:  [2,     6]
        costs:       [0.3,   0.5]
    """
    from ..game.scenarios import make_grid
    return make_grid({
        "regime":      ["coop", "compete"],
        "base_demand": [80.0,   120.0],
        "audit_prob":  [0.1,    0.4],
        "firm_count":  [2,      6],
        "costs":       [0.3,    0.5],
    })


# ============================================================================
# Module-level config vars (set by experiment scripts before calling optimize)
# ============================================================================

_N_EVAL_EPISODES: int = 5
_EVAL_SEED: int = 42


# ============================================================================
# Objective function
# ============================================================================

def enterprise_objective(genome: Sequence[Any]) -> tuple:
    """Two-objective fitness: minimise (-mean_welfare, mean_var_profit).

    Averages over ``_N_EVAL_EPISODES`` episodes.
    """
    from ..agent.runner import run_many

    tax, audit_intensity, subsidy, penalty_rate = (float(g) for g in genome[:4])
    result = run_many(
        enterprise_model_factory,
        steps=50,
        episodes=_N_EVAL_EPISODES,
        seed=_EVAL_SEED,
        tax=tax,
        audit_intensity=audit_intensity,
        subsidy=subsidy,
        penalty_rate=penalty_rate,
    )
    welfare_vals = [ep["episode"].get("agg.final_welfare", 0.0)
                    for ep in result["episodes"]]
    var_vals = [ep["episode"].get("agg.final_var_profit", 0.0)
                for ep in result["episodes"]]
    mean_welfare = sum(welfare_vals) / max(1, len(welfare_vals))
    mean_var = sum(var_vals) / max(1, len(var_vals))
    return (-mean_welfare, mean_var)
