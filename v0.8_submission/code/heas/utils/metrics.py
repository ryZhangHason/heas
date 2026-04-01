
from __future__ import annotations
from typing import Iterable, Dict, Any

def summarize_metrics(values: Iterable) -> Dict[str, Any]:
    vals = list(values)
    if not vals: 
        return {}
    try:
        import numpy as np
        arr = np.array(vals, dtype=float)
        return {
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "n": int(arr.size),
        }
    except Exception:
        return {"n": len(vals)}

def running_best(seq: Iterable[float]) -> Iterable[float]:
    best = None
    for v in seq:
        if best is None or v < best:
            best = v
        yield best
