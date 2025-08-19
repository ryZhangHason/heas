from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence
import itertools

@dataclass
class Scenario:
    """A named scenario with arbitrary parameters & optional tags/meta."""
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, Any] = field(default_factory=dict)

    def with_updates(self, **updates: Any) -> "Scenario":
        new_params = dict(self.params)
        new_params.update(updates)
        return Scenario(name=self.name, params=new_params, tags=dict(self.tags))

class ScenarioSet:
    """A thin helper over a list of scenarios with filtering."""
    def __init__(self, scenarios: Sequence[Scenario]) -> None:
        self.scenarios = list(scenarios)

    def filter(self, **param_equals: Any) -> "ScenarioSet":
        out = []
        for sc in self.scenarios:
            if all(sc.params.get(k) == v for k, v in param_equals.items()):
                out.append(sc)
        return ScenarioSet(out)

    def names(self) -> List[str]:
        return [s.name for s in self.scenarios]

    def __iter__(self):
        return iter(self.scenarios)

    def __len__(self):
        return len(self.scenarios)

def _default_name(kv: Dict[str, Any]) -> str:
    parts = [f"{k}={kv[k]}" for k in sorted(kv.keys())]
    return "|".join(parts) if parts else "default"

def make_grid(param_grid: Dict[str, Iterable[Any]], name_fn=None, base_tags: Optional[Dict[str, Any]] = None) -> ScenarioSet:
    """
    Build a ScenarioSet from a parameter grid (cartesian product).
    name_fn(params_dict)->str can customize names.
    """
    keys = sorted(param_grid.keys())
    vals = [list(param_grid[k]) for k in keys]
    scenarios = []
    for combo in itertools.product(*vals):
        params = {k: v for k, v in zip(keys, combo)}
        name = (name_fn or _default_name)(params)
        scenarios.append(Scenario(name=name, params=params, tags=dict(base_tags or {})))
    return ScenarioSet(scenarios)

def make_scenarios(items: Sequence[Dict[str, Any]], name_key: Optional[str] = None) -> ScenarioSet:
    """
    Build a ScenarioSet from a list of dicts. If name_key provided, use it as scenario name.
    Otherwise generate from params.
    """
    scenarios = []
    for d in items:
        d = dict(d)
        name = d.pop(name_key) if (name_key and name_key in d) else _default_name(d)
        scenarios.append(Scenario(name=name, params=d))
    return ScenarioSet(scenarios)