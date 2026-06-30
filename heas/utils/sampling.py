"""
heas.utils.sampling
====================
Sampling utilities for policy-space exploration.

Provides Latin Hypercube Sampling (LHS) for generating near-space-filling
candidate policy sets — used across EA-1, EA-6, and any experiment that
needs a diverse initial population of candidate policies.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np


def latin_hypercube_policies(
    n: int,
    bounds: Sequence[Tuple[float, float]],
    seed: int,
) -> np.ndarray:
    """Generate *n* candidate policies via Latin Hypercube Sampling.

    Each dimension is independently stratified into *n* equal-probability
    bins, one sample drawn per bin, then randomly permuted and jittered.
    This guarantees better space coverage than pure random sampling for the
    same *n*.

    Parameters
    ----------
    n:
        Number of candidate policies to generate.
    bounds:
        Sequence of ``(low, high)`` tuples, one per policy gene dimension.
    seed:
        RNG seed for reproducibility.

    Returns
    -------
    samples : np.ndarray, shape ``(n, len(bounds))``
        Candidate policy matrix.  ``samples[i, d]`` ∈ ``[bounds[d][0], bounds[d][1]]``.
    """
    rng = np.random.default_rng(seed)
    n_dims = len(bounds)
    samples = np.zeros((n, n_dims))
    for d in range(n_dims):
        perm = rng.permutation(n)
        u = (perm + rng.random(n)) / n
        lo, hi = bounds[d]
        samples[:, d] = lo + u * (hi - lo)
    return samples
