from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def hypervolume(
    points: Sequence[Tuple[float, float]],
    reference_point: Tuple[float, float],
) -> float:
    """Hypervolume indicator for a set of 2-D minimisation objective points.

    The function first attempts to use DEAP's WFG-based implementation
    (``deap.tools.hypervolume``).  If DEAP is unavailable or raises an error
    the pure-Python 2-D sweep-line fallback is used instead.

    Parameters
    ----------
    points:
        Objective vectors, each a 2-element sequence ``(obj1, obj2)``.
        Dominated points are filtered automatically.
    reference_point:
        A point that is strictly WORSE (larger) than every point in every
        objective.  Typical choice: ``auto_reference_point(all_points)``.

    Returns
    -------
    float
        The hypervolume area; 0.0 when *points* is empty or no point lies
        within the reference box.
    """
    if not points:
        return 0.0

    pts = np.asarray([[float(p[0]), float(p[1])] for p in points], dtype=float)
    ref = (float(reference_point[0]), float(reference_point[1]))

    # Filter to points strictly inside the reference box
    mask = (pts[:, 0] < ref[0]) & (pts[:, 1] < ref[1])
    pts = pts[mask]
    if len(pts) == 0:
        return 0.0

    # Try DEAP first (handles arbitrary dimensions correctly)
    try:
        from deap.tools._hypervolume import hv as _deap_hv  # type: ignore
        return float(_deap_hv.compute(pts.tolist(), list(ref)))
    except Exception:
        pass
    try:
        from deap import tools as _deap_tools  # type: ignore
        return float(_deap_tools.hypervolume(pts.tolist(), list(ref)))
    except Exception:
        pass

    # Pure-Python 2-D fallback
    front = _filter_nondominated_2d(pts)
    return _hv_2d_sweep(front, ref)


def auto_reference_point(
    points: Sequence[Tuple[float, float]],
    margin: float = 0.1,
) -> Tuple[float, float]:
    """Compute a reference point from a collection of objective points.

    Returns ``(max_obj1 * (1+margin), max_obj2 * (1+margin))``, ensuring the
    reference is strictly worse than all points in both objectives.

    .. important::
        For valid cross-run hypervolume comparison, this function must be
        called on the **union** of all runs' Pareto fronts, not per-run.

    Parameters
    ----------
    points:
        All objective vectors (from one or many runs pooled together).
    margin:
        Fractional margin; default 0.10 (10 %).

    Returns
    -------
    (ref1, ref2) : Tuple[float, float]
    """
    if not points:
        return (1.0 + margin, 1.0 + margin)
    arr = np.asarray([[float(p[0]), float(p[1])] for p in points], dtype=float)
    max1 = float(arr[:, 0].max())
    max2 = float(arr[:, 1].max())
    # Handle negative maxima correctly
    ref1 = max1 + abs(max1) * margin if max1 != 0.0 else margin
    ref2 = max2 + abs(max2) * margin if max2 != 0.0 else margin
    return (ref1, ref2)


def pareto_hv_from_ea_result(
    ea_result: dict,
    reference_point: Optional[Tuple[float, float]] = None,
    margin: float = 0.1,
) -> float:
    """Compute hypervolume from a ``run_ea()`` result dict.

    Reads ``ea_result["hof_fitness"]`` (added to ``run_ea()`` output in the
    WSC revision).  If the key is absent, returns 0.0.

    Parameters
    ----------
    ea_result:
        Dict returned by ``heas.api.optimize()`` / ``run_ea()``.
    reference_point:
        Fixed reference point.  If ``None``, one is derived automatically
        from the front (suitable for single-run inspection; for multi-run
        studies always pass a pre-computed shared reference point).
    margin:
        Used only when *reference_point* is ``None``.
    """
    hof_fitness = ea_result.get("hof_fitness", [])
    if not hof_fitness:
        return 0.0
    pts = [tuple(float(v) for v in f) for f in hof_fitness if len(f) >= 2]
    if not pts:
        return 0.0
    if reference_point is None:
        reference_point = auto_reference_point(pts, margin=margin)
    return hypervolume(pts, reference_point)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_nondominated_2d(points: np.ndarray) -> np.ndarray:
    """Return the Pareto-nondominated subset of 2-D minimisation points.

    A point *p* dominates *q* iff ``p[i] <= q[i]`` for all *i* with at least
    one strict inequality.  Runs in O(n log n) via sort-then-scan.
    """
    if len(points) == 0:
        return points
    # Sort ascending by obj1; ties broken by ascending obj2
    idx = np.lexsort((points[:, 1], points[:, 0]))
    pts = points[idx]
    nondom = [pts[0]]
    min_obj2 = pts[0, 1]
    for p in pts[1:]:
        if p[1] < min_obj2:
            nondom.append(p)
            min_obj2 = p[1]
    return np.array(nondom)


def _hv_2d_sweep(front: np.ndarray, ref: Tuple[float, float]) -> float:
    """Sweep-line hypervolume for a 2-D non-dominated front (minimisation).

    *front* is sorted ASCENDING by obj1 (so obj2 is descending for a
    non-dominated front under minimisation).  *ref* is strictly worse than
    all front points.

    Algorithm — left-to-right strip decomposition, O(n):
      For each front point i, the strip x ∈ [x_i, x_{i+1}] (or [x_i, ref_x]
      for the last point) contributes height (ref_y − y_i).  Strips are
      non-overlapping by construction.

    Example: front=[(0,1),(1,0)], ref=(2,2)
      Strip 0: x∈[0,1], height=2-1=1 → area 1
      Strip 1: x∈[1,2], height=2-0=2 → area 2
      Total = 3  ✓
    """
    if len(front) == 0:
        return 0.0
    ref1, ref2 = float(ref[0]), float(ref[1])
    # Ensure sorted by obj1 ascending
    front = front[np.argsort(front[:, 0])]
    area = 0.0
    n = len(front)
    for i in range(n):
        x_i = float(front[i, 0])
        y_i = float(front[i, 1])
        x_right = float(front[i + 1, 0]) if i + 1 < n else ref1
        width = x_right - x_i
        height = ref2 - y_i
        if width > 0.0 and height > 0.0:
            area += width * height
    return area
