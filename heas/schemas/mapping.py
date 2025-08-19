
from __future__ import annotations
from typing import Any, Dict, Sequence

def list_to_named(schema: Sequence[Any], genome: Sequence[Any]) -> Dict[str, Any]:
    names = [getattr(g, "name", f"x{i}") for i, g in enumerate(schema)]
    return {n: v for n, v in zip(names, genome)}

def named_to_kwargs(prefix: str, named: Dict[str, Any]) -> Dict[str, Any]:
    return {f"{prefix}_{k}": v for k, v in named.items()}
