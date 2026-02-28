"""
experiments/common.py
=====================
Shared utilities for all HEAS WSC supplementary experiment scripts.

Provides:
  - Filesystem helpers (paths under experiments/results/)
  - Checkpoint / resume support (save & load per-run JSON files)
  - Summary table formatting (LaTeX-compatible)
  - Reproducibility header printing
  - Progress logging
  - HV computation helpers
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set

import numpy as np

# All results go under experiments/results/<experiment_name>/
_EXPERIMENTS_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(_EXPERIMENTS_DIR, "results")


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def results_path(*parts: str) -> str:
    """Build an absolute path under ``experiments/results/``.

    Creates intermediate directories automatically.

    Example::

        results_path("eco_stats", "run_000.json")
        # → experiments/results/eco_stats/run_000.json
    """
    path = os.path.join(RESULTS_DIR, *parts)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def save_json(path: str, obj: Any) -> None:
    """Save *obj* as JSON to *path*, creating parent directories."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)


def load_json(path: str) -> Any:
    """Load and return a JSON file."""
    with open(path) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Checkpoint / resume
# ---------------------------------------------------------------------------

def save_run_result(result: Dict[str, Any], experiment: str, run_id: int) -> str:
    """Save one run's result dict to ``results/<experiment>/run_<run_id:03d>.json``.

    Returns the file path written.
    """
    path = results_path(experiment, f"run_{run_id:03d}.json")
    save_json(path, result)
    return path


def load_completed_runs(experiment: str) -> List[Dict[str, Any]]:
    """Load all ``run_*.json`` files for *experiment* in sorted order."""
    dir_ = results_path(experiment)
    if not os.path.isdir(dir_):
        return []
    runs = []
    for fname in sorted(os.listdir(dir_)):
        if fname.startswith("run_") and fname.endswith(".json"):
            try:
                runs.append(load_json(os.path.join(dir_, fname)))
            except Exception:
                pass
    return runs


def completed_run_ids(experiment: str) -> Set[int]:
    """Return the set of already-completed run IDs for *experiment*."""
    return {r["run_id"] for r in load_completed_runs(experiment) if "run_id" in r}


# ---------------------------------------------------------------------------
# Summary table formatting
# ---------------------------------------------------------------------------

def format_table_row(
    label: str,
    values: Sequence[float],
    n_bootstrap: int = 10_000,
    confidence: float = 0.95,
) -> str:
    """Return a LaTeX table row string for *values*.

    Format::

        label & mean ± std & [ci_lower, ci_upper] & n \\\\

    Uses :func:`heas.utils.stats.summarize_runs` internally.
    """
    from heas.utils.stats import summarize_runs
    s = summarize_runs(values, n_bootstrap=n_bootstrap, confidence=confidence)
    return (
        f"{label} & "
        f"{s['mean']:.4f} $\\pm$ {s['std']:.4f} & "
        f"[{s['ci_lower']:.4f}, {s['ci_upper']:.4f}] & "
        f"{s['n']} \\\\"
    )


def print_summary_table(
    rows: List[tuple],
    headers: Sequence[str] = ("Config", "Mean ± Std", "95% CI", "N"),
) -> None:
    """Print a summary table to stdout.

    Parameters
    ----------
    rows:
        List of ``(label, values)`` pairs.
    headers:
        Column header strings.
    """
    sep = " | "
    header_str = sep.join(f"{h:>30}" for h in headers)
    print(header_str)
    print("-" * len(header_str))
    for label, values in rows:
        print(format_table_row(label, values))


# ---------------------------------------------------------------------------
# Reproducibility header
# ---------------------------------------------------------------------------

def print_config_header(config: Dict[str, Any]) -> None:
    """Print a reproducibility config block to stdout."""
    print("=" * 70)
    print(f"HEAS Experiment  —  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python {sys.version}")
    try:
        import numpy
        print(f"numpy {numpy.__version__}")
    except ImportError:
        pass
    try:
        import deap
        print(f"deap {deap.__version__}")
    except ImportError:
        pass
    print("Config:")
    print(json.dumps(config, indent=2, default=str))
    print("=" * 70)
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Progress logging
# ---------------------------------------------------------------------------

def log_run_progress(
    run_id: int,
    total: int,
    metric: float,
    elapsed: float,
    label: str = "HV",
) -> None:
    """Print a one-line progress update."""
    pct = 100.0 * (run_id + 1) / max(total, 1)
    print(
        f"  Run {run_id + 1:3d}/{total} ({pct:.0f}%) "
        f"| {label}={metric:.6f} "
        f"| elapsed={elapsed:.1f}s",
        flush=True,
    )


# ---------------------------------------------------------------------------
# HV computation helpers
# ---------------------------------------------------------------------------

def compute_hv_from_result(
    ea_result: Dict[str, Any],
    reference_point: Optional[tuple] = None,
) -> float:
    """Extract Pareto front fitness from *ea_result* and compute hypervolume.

    Reads ``ea_result["hof_fitness"]``.  If *reference_point* is ``None``,
    derives one automatically (suitable for single-run calls; for multi-run
    studies always pass a fixed shared reference point).
    """
    from heas.utils.pareto import hypervolume, auto_reference_point
    hof_fitness = ea_result.get("hof_fitness", [])
    if not hof_fitness:
        return 0.0
    pts = [tuple(float(v) for v in f) for f in hof_fitness if len(f) >= 2]
    if not pts:
        return 0.0
    if reference_point is None:
        reference_point = auto_reference_point(pts)
    return hypervolume(pts, reference_point)


def pool_reference_point(all_runs: List[Dict[str, Any]], margin: float = 0.1) -> tuple:
    """Compute a consistent reference point from all runs' Pareto fronts.

    Pools ``hof_fitness`` across every run, then calls ``auto_reference_point``
    on the union.  Must be called AFTER all runs complete.
    """
    from heas.utils.pareto import auto_reference_point
    all_pts = []
    for run in all_runs:
        for f in run.get("hof_fitness", []):
            if len(f) >= 2:
                all_pts.append(tuple(float(v) for v in f))
    if not all_pts:
        return (1.0, 1.0)
    return auto_reference_point(all_pts, margin=margin)


def compute_hvs_for_runs(
    all_runs: List[Dict[str, Any]],
    ref_pt: Optional[tuple] = None,
) -> List[float]:
    """Compute HV for each run using a shared reference point.

    If *ref_pt* is ``None``, computes it from the pooled front.
    """
    from heas.utils.pareto import hypervolume
    if ref_pt is None:
        ref_pt = pool_reference_point(all_runs)
    hvs = []
    for run in all_runs:
        pts = [tuple(float(v) for v in f)
               for f in run.get("hof_fitness", []) if len(f) >= 2]
        hvs.append(hypervolume(pts, ref_pt) if pts else 0.0)
    return hvs


# ---------------------------------------------------------------------------
# Optimization wrapper
# ---------------------------------------------------------------------------

def run_optimization_simple(
    objective_fn,
    gene_schema,
    pop_size: int = 50,
    n_generations: int = 20,
    strategy: str = "nsga2",
    seed: int = 42,
    cx_prob: float = 0.8,
    mut_prob: float = 0.2,
    out_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Thin wrapper around ``heas.api.optimize`` using flat keyword args.

    Constructs :class:`~heas.config.Experiment` and
    :class:`~heas.config.Algorithm` dataclasses, then delegates to
    ``heas.api.optimize(exp, algo)``.

    Parameters
    ----------
    objective_fn:
        Callable ``genome -> tuple`` (fitness values, one per objective).
    gene_schema:
        List of gene descriptors (``Real``, ``Int``, ``Cat``, …).
    pop_size:
        Population size.
    n_generations:
        Number of NSGA-II generations.
    strategy:
        ``"nsga2"`` | ``"simple"`` | ``"mu_plus_lambda"`` | ``"random"``.
    seed:
        Master random seed (passed to ``seed_everything``).
    cx_prob:
        Crossover probability.
    mut_prob:
        Mutation probability per gene.
    out_dir:
        Directory for DEAP's result JSON.  Defaults to a temp path under
        ``experiments/results/_ea_tmp/``.

    Returns
    -------
    dict
        Same dict returned by ``heas.api.optimize``:
        ``{best, hall_of_fame, hof_fitness, logbook}``.
    """
    import sys as _sys
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _REPO_ROOT not in _sys.path:
        _sys.path.insert(0, _REPO_ROOT)

    from heas.config import Experiment, Algorithm
    from heas.api import optimize

    if out_dir is None:
        out_dir = results_path("_ea_tmp")

    exp = Experiment(
        model_factory=lambda kwargs: None,  # unused for optimize()
        seed=seed,
    )
    algo = Algorithm(
        objective_fn=objective_fn,
        pop_size=pop_size,
        ngen=n_generations,
        strategy=strategy,
        genes_schema=gene_schema,
        out_dir=out_dir,
        cx_prob=cx_prob,
        mut_prob=mut_prob,
    )
    return optimize(exp, algo)
