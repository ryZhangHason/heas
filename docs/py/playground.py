from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence
import inspect
import random

# -------------------- Core HEAS (lite) --------------------

@dataclass
class Context:
    seed: int = 0
    t: int = 0
    rng: random.Random = field(default_factory=random.Random)
    data: Dict[str, Any] = field(default_factory=dict)
    episode: Dict[str, Any] = field(default_factory=dict)

    def step_tick(self) -> None:
        self.t += 1

class Stream:
    def __init__(self, name: str, ctx: Context, **kwargs: Any) -> None:
        self.name = name
        self.ctx = ctx
        self.cfg = dict(kwargs)

    def step(self) -> None:
        raise NotImplementedError("Stream.step() not implemented")

    def metrics_step(self) -> Dict[str, Any]:
        return {}

    def metrics_episode(self) -> Dict[str, Any]:
        return {}

class Layer:
    def __init__(self, streams: List[Stream]) -> None:
        self.streams = list(streams)

    def step(self) -> None:
        for s in self.streams:
            s.step()

    def metrics_step(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for s in self.streams:
            for k, v in s.metrics_step().items():
                out[f"{s.name}.{k}"] = v
        return out

    def metrics_episode(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for s in self.streams:
            for k, v in s.metrics_episode().items():
                out[f"{s.name}.{k}"] = v
        return out

class Graph:
    def __init__(self, layers: List[Layer]) -> None:
        self.layers = list(layers)

    def step(self, ctx: Context) -> None:
        ctx.step_tick()
        for layer in self.layers:
            layer.step()

    def metrics_step(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for layer in self.layers:
            out.update(layer.metrics_step())
        return out

    def metrics_episode(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for layer in self.layers:
            out.update(layer.metrics_episode())
        return out

@dataclass
class StreamSpec:
    name: str
    factory: Callable[..., Stream]
    kwargs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LayerSpec:
    streams: List[StreamSpec]

SpecType = Sequence[LayerSpec]

def _resolve_kwargs(ctx: Context, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in (kwargs or {}).items():
        if callable(v):
            try:
                out[k] = v(ctx)
            except Exception:
                out[k] = v
        else:
            out[k] = v
    return out

def _instantiate_stream(spec: StreamSpec, ctx: Context) -> Stream:
    resolved = _resolve_kwargs(ctx, spec.kwargs)
    return spec.factory(ctx=ctx, name=spec.name, **resolved)

def _safe_instantiate(factory: Callable[..., Stream], name: str, ctx: Context, kwargs: Dict[str, Any]) -> Stream:
    try:
        return factory(ctx=ctx, name=name, **kwargs)
    except TypeError:
        try:
            sig = inspect.signature(factory)
            allowed = set(sig.parameters.keys())
            filtered = {k: v for k, v in kwargs.items() if k in allowed}
            return factory(ctx=ctx, name=name, **filtered)
        except Exception:
            return GenericParams(ctx=ctx, name=name, **kwargs)

def build_graph(spec: SpecType, ctx: Optional[Context] = None) -> Graph:
    ctx = ctx or Context(seed=0)
    layers: List[Layer] = []
    for layer_spec in spec:
        streams = []
        for s in layer_spec.streams:
            resolved = _resolve_kwargs(ctx, s.kwargs)
            streams.append(_safe_instantiate(s.factory, s.name, ctx, resolved))
        layers.append(Layer(streams))
    return Graph(layers)

def default_aggregator(ctx: Context, per_step: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(per_step)
    out["t"] = ctx.t
    return out

class CompositeHeasModel:
    def __init__(self, spec_or_graph: SpecType | Graph, seed: int = 0,
                 aggregator: Optional[Callable[[Context, Dict[str, Any]], Dict[str, Any]]] = None,
                 ctx_data: Optional[Dict[str, Any]] = None) -> None:
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
        out = dict(per_ep)
        out.update(self.ctx.episode)
        self._last_episode_metrics = out
        return dict(out)

def make_model_from_spec(spec: SpecType, seed: int = 0,
                         aggregator: Optional[Callable[[Context, Dict[str, Any]], Dict[str, Any]]] = None,
                         **ctx_data: Any):
    def _factory(kwargs: Dict[str, Any]) -> CompositeHeasModel:
        agg = kwargs.pop("aggregator", aggregator)
        seed_override = int(kwargs.pop("seed", seed))
        data = dict(ctx_data)
        data.update(kwargs)
        return CompositeHeasModel(spec, seed=seed_override, aggregator=agg, ctx_data=data)
    return _factory

# -------------------- Playground Streams --------------------

class Price(Stream):
    def __init__(self, name: str, ctx: Context, start: float = 100.0,
                 drift: float = 0.03, noise: float = 0.05, out_key: Optional[str] = None):
        super().__init__(name, ctx)
        self.p = float(start)
        self.drift = float(drift)
        self.noise = float(noise)
        self.out_key = out_key or f"{self.name}.price"

    def step(self) -> None:
        self.p += self.drift + self.ctx.rng.gauss(0.0, self.noise)
        self.ctx.data[self.out_key] = self.p

    def metrics_step(self) -> Dict[str, Any]:
        return {"price": self.p}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_price": self.p}

class Policy(Stream):
    def __init__(self, name: str, ctx: Context, alpha: float = 0.05, x_key: str = "L1S1.price"):
        super().__init__(name, ctx)
        self.alpha = float(alpha)
        self.key = x_key
        self.pos = 0.0
        self.pnl = 0.0
        self.prev = None

    def step(self) -> None:
        x = float(self.ctx.data.get(self.key, self.prev if self.prev is not None else 100.0))
        if self.prev is not None:
            sig = x - self.prev
            self.pos += self.alpha * sig
            self.pnl += self.pos * (x - self.prev)
        self.prev = x
        self.ctx.data[f"{self.name}.pnl"] = self.pnl

    def metrics_step(self) -> Dict[str, Any]:
        return {"pos": self.pos, "pnl": self.pnl}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_pos": self.pos, "final_pnl": self.pnl}

class GenericParams(Stream):
    def __init__(self, name: str, ctx: Context, out_key: str = "", **kwargs: Any) -> None:
        super().__init__(name, ctx)
        self.params = dict(kwargs)
        self.out_key = out_key or f"{self.name}.params"

    def step(self) -> None:
        # Store params into context for inspection/links to other streams.
        self.ctx.data[self.out_key] = dict(self.params)

    def metrics_step(self) -> Dict[str, Any]:
        # Expose a compact count to avoid bloating per-step output.
        return {"param_count": len(self.params)}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_param_count": len(self.params)}

class GovernmentPolicy(Stream):
    def __init__(self, name: str, ctx: Context, regime: str = "coop", tax: float = 0.1,
                 audit_intensity: float = 0.2, subsidy: float = 0.0, penalty_rate: float = 0.1) -> None:
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
        # Pick the richest firm from last step (monopoly target)
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        if states:
            target_idx = int(max(range(len(states)), key=lambda i: float(states[i])))
        else:
            target_idx = 0
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
                 shock_amp: float = 0.2, atr: float = 0.1, growth_rate: float = 0.02,
                 market_power: float = 0.2) -> None:
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
        self.demand_t = max(0.0, self.base_demand * (1.0 + self.growth_rate * self.ctx.t + shock))
        balances = self.ctx.data.get("firms.states", [])
        if not isinstance(balances, list):
            balances = []
        max_balance = max([float(x) for x in balances], default=0.0)
        power_bonus = self.market_power * max(0.0, max_balance)
        self.price_signal = max(0.1, 1.0 + self.atr * (shock) + power_bonus * 0.01)
        self.ctx.data["market.demand_t"] = self.demand_t
        self.ctx.data["market.price_signal"] = self.price_signal

    def metrics_step(self) -> Dict[str, Any]:
        return {"demand_t": self.demand_t, "price_signal": self.price_signal}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_demand_t": self.demand_t}

class FirmGroup(Stream):
    def __init__(self, name: str, ctx: Context, firm_count: int = 4, costs: float = 0.4,
                 initial_balance: float = 1.0) -> None:
        super().__init__(name, ctx)
        self.firm_count = max(1, int(firm_count))
        self.costs = float(costs)
        self.initial_balance = float(initial_balance)
        self.actions: List[float] = [0.0 for _ in range(self.firm_count)]
        self.states: List[float] = [self.initial_balance for _ in range(self.firm_count)]
        self.compliance: List[float] = [1.0 for _ in range(self.firm_count)]

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
    def __init__(self, name: str, ctx: Context, bargain_rule: str = "equal", side_payment: float = 0.0) -> None:
        super().__init__(name, ctx)
        self.bargain_rule = str(bargain_rule)
        self.side_payment = float(side_payment)
        self.alliance_state = 0.0
        self.transfers = 0.0

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        total = sum([float(x) for x in states]) if states else 0.0
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
        # Rule: Join (1) or Split (0)
        if isinstance(self.rule, (int, float)):
            val = 1.0 if float(self.rule) >= 0.5 else 0.0
        else:
            val = 1.0 if str(self.rule).lower() == "join" else 0.0
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
        # Mode: Cooperate (1) or Compete (0)
        if isinstance(self.mode, (int, float)):
            val = 1.0 if float(self.mode) >= 0.5 else 0.0
        else:
            val = 1.0 if str(self.mode).lower() == "cooperate" else 0.0
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
        # Prisoner's dilemma style: strategy maps to a numeric delta (e.g., +2 / -1)
        if isinstance(self.strategy, (int, float)):
            self.delta = float(self.strategy)
        else:
            s = str(self.strategy).lower()
            self.delta = 2.0 if s == "collaborate" else -1.0
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        new_states = []
        for state in states:
            new_states.append(float(state) + self.delta)
        self.ctx.data["firms.states"] = new_states
        self.ctx.data["payoff.profits"] = [self.delta for _ in new_states]
        self.ctx.data["payoff.welfare_t"] = self.delta * float(len(new_states))

    def metrics_step(self) -> Dict[str, Any]:
        count = float(len(self.ctx.data.get("firms.states", [])))
        return {"delta": self.delta, "welfare_t": self.delta * count}

    def metrics_episode(self) -> Dict[str, Any]:
        count = float(len(self.ctx.data.get("firms.states", [])))
        return {"final_delta": self.delta, "final_welfare_t": self.delta * count}

class PayoffAccountingGroup(Stream):
    def __init__(self, name: str, ctx: Context, price_fn: str = "linear",
                 cost_fn: str = "linear", penalties: float = 0.2, alliance_weight: float = 0.5) -> None:
        super().__init__(name, ctx)
        self.price_fn = str(price_fn)
        self.cost_fn = str(cost_fn)
        self.penalties = float(penalties)
        self.alliance_weight = float(alliance_weight)
        self.group_AB = 0.0
        self.group_CD = 0.0

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        n = len(states)
        half = max(1, n // 2)
        group_ab = sum(float(x) for x in states[:half])
        group_cd = sum(float(x) for x in states[half:])
        alliance = float(self.ctx.data.get("rule.alliance", self.ctx.data.get("alliance.state", 0.0)))
        self.group_AB = group_ab + self.alliance_weight * alliance
        self.group_CD = group_cd + self.alliance_weight * alliance
        self.ctx.data["group.profit_AB"] = self.group_AB
        self.ctx.data["group.profit_CD"] = self.group_CD

    def metrics_step(self) -> Dict[str, Any]:
        return {"group_AB": self.group_AB, "group_CD": self.group_CD}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_group_AB": self.group_AB, "final_group_CD": self.group_CD}

class AggregatorFirm(Stream):
    def __init__(self, name: str, ctx: Context, welfare_weights: float = 1.0, risk_penalty: float = 0.2) -> None:
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
        return {"mean_profit": self.mean_profit, "var_profit": self.var_profit, "compliance": self.compliance, "stability": self.stability, "welfare": self.welfare}

    def metrics_episode(self) -> Dict[str, Any]:
        return {
            "final_mean_profit": self.mean_profit,
            "final_var_profit": self.var_profit,
            "final_compliance": self.compliance,
            "final_stability": self.stability,
            "final_welfare": self.welfare,
        }

class AggregatorTotalWealth(Stream):
    def __init__(self, name: str, ctx: Context) -> None:
        super().__init__(name, ctx)
        self.total_wealth = 0.0

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        self.total_wealth = sum(float(x) for x in states) if states else 0.0
        self.ctx.data["agg.total_wealth"] = self.total_wealth

    def metrics_step(self) -> Dict[str, Any]:
        return {"total_wealth": self.total_wealth}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_total_wealth": self.total_wealth}

class AggregatorInequality(Stream):
    def __init__(self, name: str, ctx: Context) -> None:
        super().__init__(name, ctx)
        self.gini = 0.0

    def step(self) -> None:
        states = self.ctx.data.get("firms.states", [])
        if not isinstance(states, list):
            states = []
        values = [float(x) for x in states if x is not None]
        n = len(values)
        if n <= 1:
            self.gini = 0.0
        else:
            mean = sum(values) / n
            if mean == 0:
                self.gini = 0.0
            else:
                diff_sum = 0.0
                for i in range(n):
                    for j in range(n):
                        diff_sum += abs(values[i] - values[j])
                self.gini = diff_sum / (2.0 * n * n * mean)
        self.ctx.data["agg.gini"] = self.gini

    def metrics_step(self) -> Dict[str, Any]:
        return {"gini": self.gini}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_gini": self.gini}
class Climate(Stream):
    def __init__(self, name: str, ctx: Context, amp: float = 0.4, period: float = 12.0,
                 shock_prob: float = 0.1, out_key: str = "climate") -> None:
        super().__init__(name, ctx)
        self.amp = float(amp)
        self.period = float(period)
        self.shock_prob = float(shock_prob)
        self.out_key = out_key
        self.value = 0.0

    def step(self) -> None:
        # Simple seasonal driver with occasional shocks
        import math
        seasonal = self.amp * math.sin(2.0 * math.pi * (self.ctx.t / max(self.period, 1.0)))
        shock = self.amp * (2.0 * self.ctx.rng.random() - 1.0) if self.ctx.rng.random() < self.shock_prob else 0.0
        self.value = seasonal + shock
        self.ctx.data[self.out_key] = self.value

    def metrics_step(self) -> Dict[str, Any]:
        return {"value": self.value}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_value": self.value}

class Landscape(Stream):
    def __init__(self, name: str, ctx: Context, n_patches: int = 12, fragmentation: float = 0.2,
                 move_cost: float = 0.2, out_key: str = "landscape.quality") -> None:
        super().__init__(name, ctx)
        self.n_patches = int(n_patches)
        self.frag = float(fragmentation)
        self.move_cost = float(move_cost)
        self.out_key = out_key
        self.quality = max(0.0, 1.0 - self.frag)

    def step(self) -> None:
        # Static quality for now; could be extended to dynamic landscapes
        self.quality = max(0.0, 1.0 - self.frag)
        self.ctx.data[self.out_key] = self.quality
        self.ctx.data["landscape.move_cost"] = self.move_cost
        self.ctx.data["landscape.n_patches"] = self.n_patches

    def metrics_step(self) -> Dict[str, Any]:
        return {"quality": self.quality}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_quality": self.quality}

class PreyRisk(Stream):
    def __init__(self, name: str, ctx: Context, x0: float = 40.0, r: float = 0.55, K: float = 120.0, risk: float = 0.55,
                 betaF: float = 0.3, gammaV: float = 0.2, prey_key: str = "pop.prey",
                 pred_key: str = "pop.pred") -> None:
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

class PredatorResponse(Stream):
    def __init__(self, name: str, ctx: Context, y0: float = 9.0, conv: float = 0.02, mort: float = 0.15,
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
        # Simple effect: dispersal reduces effective predation pressure slightly
        prey = float(self.ctx.data.get(self.prey_key, 0.0))
        pred = float(self.ctx.data.get(self.pred_key, 0.0))
        damp = max(0.0, min(1.0, self.dispersal))
        self.ctx.data[self.prey_key] = max(0.0, prey * (1.0 + 0.01 * damp))
        self.ctx.data[self.pred_key] = max(0.0, pred * (1.0 - 0.005 * damp))

    def metrics_step(self) -> Dict[str, Any]:
        return {"dispersal": self.dispersal}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_dispersal": self.dispersal}

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

    def step(self) -> None:
        self.prey = float(self.ctx.data.get(self.prey_key, 0.0))
        self.pred = float(self.ctx.data.get(self.pred_key, 0.0))
        self.extinct = (self.prey < self.ext_thresh) or (self.pred < self.ext_thresh)

    def metrics_step(self) -> Dict[str, Any]:
        return {"prey": self.prey, "pred": self.pred, "extinct": float(self.extinct)}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_prey": self.prey, "final_pred": self.pred, "extinct": float(self.extinct)}

class Prey(Stream):
    def __init__(self, name: str, ctx: Context, x0: float = 40.0, growth: float = 0.1,
                 predation: float = 0.02, pred_key: str = "pop.pred", out_key: str = "pop.prey") -> None:
        super().__init__(name, ctx)
        self.x = float(x0)
        self.growth = float(growth)
        self.predation = float(predation)
        self.pred_key = pred_key
        self.out_key = out_key
        if self.out_key not in self.ctx.data:
            self.ctx.data[self.out_key] = self.x

    def step(self) -> None:
        pred = float(self.ctx.data.get(self.pred_key, 0.0))
        self.x = max(0.0, self.x + self.growth * self.x - self.predation * self.x * pred)
        self.ctx.data[self.out_key] = self.x

    def metrics_step(self) -> Dict[str, Any]:
        return {"pop": self.x}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_pop": self.x}

class Predator(Stream):
    def __init__(self, name: str, ctx: Context, y0: float = 9.0, death: float = 0.1,
                 reproduction: float = 0.01, prey_key: str = "pop.prey", out_key: str = "pop.pred") -> None:
        super().__init__(name, ctx)
        self.y = float(y0)
        self.death = float(death)
        self.repro = float(reproduction)
        self.prey_key = prey_key
        self.out_key = out_key
        if self.out_key not in self.ctx.data:
            self.ctx.data[self.out_key] = self.y

    def step(self) -> None:
        prey = float(self.ctx.data.get(self.prey_key, 0.0))
        self.y = max(0.0, self.y + self.repro * prey * self.y - self.death * self.y)
        self.ctx.data[self.out_key] = self.y

    def metrics_step(self) -> Dict[str, Any]:
        return {"pop": self.y}

    def metrics_episode(self) -> Dict[str, Any]:
        return {"final_pop": self.y}

class Probe(Stream):
    def __init__(self, name: str, ctx: Context, key: str = "pop.prey", label: str = "value") -> None:
        super().__init__(name, ctx)
        self.key = key
        self.label = label
        self.value = None

    def step(self) -> None:
        self.value = self.ctx.data.get(self.key, None)

    def metrics_step(self) -> Dict[str, Any]:
        return {self.label: self.value}

    def metrics_episode(self) -> Dict[str, Any]:
        return {f"final_{self.label}": self.value}

STREAM_TYPES: Dict[str, Callable[..., Stream]] = {
    "Price": Price,
    "Policy": Policy,
    "Prey": Prey,
    "Predator": Predator,
    "Probe": Probe,
    "Climate": Climate,
    "Landscape": Landscape,
    "PreyRisk": PreyRisk,
    "PredatorResponse": PredatorResponse,
    "Movement": Movement,
    "Aggregator": Aggregator,
    "Custom": GenericParams,
    "GovernmentPolicy": GovernmentPolicy,
    "IndustryRegime": IndustryRegime,
    "MarketSignal": MarketSignal,
    "FirmGroup": FirmGroup,
    "AllianceMediator": AllianceMediator,
    "AllianceRule": AllianceRule,
    "GroupGamingRule": GroupGamingRule,
    "PayoffAccounting": PayoffAccounting,
    "PayoffAccountingGroup": PayoffAccountingGroup,
    "AggregatorFirm": AggregatorFirm,
    "AggregatorTotalWealth": AggregatorTotalWealth,
    "AggregatorInequality": AggregatorInequality,
}

DEFAULT_STREAM_FACTORY: Callable[..., Stream] = GenericParams

# -------------------- Runner --------------------

def _to_py(obj: Any) -> Any:
    if hasattr(obj, "to_py"):
        try:
            return obj.to_py()
        except Exception:
            pass
    return obj

def _to_dict(obj: Any) -> Dict[str, Any]:
    obj = _to_py(obj)
    if isinstance(obj, dict):
        return obj
    try:
        return dict(obj)
    except Exception:
        return {}


def _make_spec(config: Dict[str, Any]) -> List[LayerSpec]:
    layers_cfg = _to_py(config.get("layers", []))
    if not isinstance(layers_cfg, list):
        try:
            layers_cfg = list(layers_cfg)
        except Exception:
            layers_cfg = []
    spec: List[LayerSpec] = []
    for layer in layers_cfg:
        layer = _to_py(layer)
        try:
            layer_list = list(layer)
        except Exception:
            layer_list = []
        streams: List[StreamSpec] = []
        for s in layer_list:
            s = _to_dict(s)
            name = str(s.get("name", "stream"))
            stype = str(s.get("type", "Price"))
            params = _to_dict(s.get("params", {}))
            factory = STREAM_TYPES.get(stype, DEFAULT_STREAM_FACTORY)
            streams.append(StreamSpec(name=name, factory=factory, kwargs=params))
        spec.append(LayerSpec(streams))
    return spec


def run_sim(config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _to_dict(config)
    steps = int(cfg.get("steps", 20))
    episodes = int(cfg.get("episodes", 1))
    seed = int(cfg.get("seed", 123))

    spec = _make_spec(cfg)
    model_factory = make_model_from_spec(spec, seed=seed)

    runs: List[Dict[str, Any]] = []
    for i in range(episodes):
        ep_seed = seed + i
        model = model_factory({"seed": ep_seed})
        step_log: List[Dict[str, Any]] = []
        for _ in range(steps):
            model.step()
            step_log.append(model.metrics_step())
        episode_metrics = model.metrics_episode()
        runs.append({
            "seed": ep_seed,
            "steps": steps,
            "per_step": step_log,
            "episode": episode_metrics,
        })

    return {"episodes": runs}
