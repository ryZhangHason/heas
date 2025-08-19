from __future__ import annotations
from typing import Any, Optional
import numpy as np
import matplotlib.pyplot as plt

def _scalar(v):
    if isinstance(v, (list, tuple)) and v:
        return float(v[0])
    return float(v)

def plot_logbook_curves(log: Any, save: Optional[str]=None):
    """Thin wrapper over plots.plot_ea_log for convenience."""
    from .plots import plot_ea_log
    return plot_ea_log(log, save=save)

def plot_pareto_front(points, save: Optional[str]=None, title: str="Pareto"):
    from .plots import plot_pareto
    pts = np.asarray(points)
    return plot_pareto(pts, save=save, title=title)