from __future__ import annotations

import warnings
from typing import Callable, Sequence, Tuple

import numpy as np


def bootstrap_ci(
    values: Sequence[float],
    n_bootstrap: int = 10_000,
    confidence: float = 0.95,
    statistic: Callable = np.mean,
    rng_seed: int = 0,
) -> Tuple[float, float]:
    """Non-parametric bootstrap confidence interval for any statistic.

    Uses a private RNG (``np.random.default_rng``) so it does NOT disturb the
    global numpy/random/torch RNG state used by HEAS and DEAP.

    Parameters
    ----------
    values:
        Sequence of scalar observations (e.g. per-run hypervolume values).
    n_bootstrap:
        Number of bootstrap resamples.
    confidence:
        Desired confidence level, e.g. 0.95 for a 95 % CI.
    statistic:
        Aggregation function applied to each resample; default is ``np.mean``.
    rng_seed:
        Seed for the private RNG — set explicitly to reproduce the same CI.

    Returns
    -------
    (lower, upper) : float, float
        Bootstrap percentile CI.

    Raises
    ------
    ValueError
        If fewer than 2 values are provided.
    """
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        raise ValueError(
            f"bootstrap_ci requires at least 2 values, got {len(arr)}."
        )
    rng = np.random.default_rng(rng_seed)
    n = len(arr)
    boot_stats = np.array(
        [statistic(arr[rng.integers(0, n, size=n)]) for _ in range(n_bootstrap)]
    )
    alpha = (1.0 - confidence) / 2.0
    lower = float(np.percentile(boot_stats, 100.0 * alpha))
    upper = float(np.percentile(boot_stats, 100.0 * (1.0 - alpha)))
    return lower, upper


def wilcoxon_test(
    x: Sequence[float],
    y: Sequence[float],
) -> Tuple[float, float]:
    """Paired Wilcoxon signed-rank test (two-sided).

    Wraps ``scipy.stats.wilcoxon(d)`` where ``d = x - y``.

    Parameters
    ----------
    x, y:
        Paired observation sequences of equal length.

    Returns
    -------
    (statistic, p_value) : float, float

    Raises
    ------
    ImportError
        If scipy is not installed.
    ValueError
        If ``len(x) != len(y)``.
    """
    try:
        from scipy import stats as _scipy_stats
    except ImportError as exc:
        raise ImportError(
            "scipy is required for wilcoxon_test.  "
            "Install it with:  pip install scipy"
        ) from exc

    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) != len(y_arr):
        raise ValueError(
            f"x and y must have the same length, got {len(x_arr)} vs {len(y_arr)}."
        )
    if len(x_arr) < 10:
        warnings.warn(
            f"wilcoxon_test: only {len(x_arr)} pairs; results may be unreliable.",
            UserWarning,
            stacklevel=2,
        )
    result = _scipy_stats.wilcoxon(x_arr - y_arr, alternative="two-sided")
    return float(result.statistic), float(result.pvalue)


def cohens_d(
    x: Sequence[float],
    y: Sequence[float],
) -> float:
    """Cohen's d effect size using the pooled standard deviation.

    Formula::

        d = (mean_x - mean_y) / pooled_std

        pooled_std = sqrt(((n1-1)*s1^2 + (n2-1)*s2^2) / (n1+n2-2))

    Returns 0.0 if the pooled standard deviation is zero.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n1, n2 = len(x_arr), len(y_arr)
    if n1 < 2 or n2 < 2:
        return 0.0
    s1_sq = np.var(x_arr, ddof=1)
    s2_sq = np.var(y_arr, ddof=1)
    pooled_var = ((n1 - 1) * s1_sq + (n2 - 1) * s2_sq) / (n1 + n2 - 2)
    pooled_std = float(np.sqrt(pooled_var))
    if pooled_std == 0.0:
        return 0.0
    return float((np.mean(x_arr) - np.mean(y_arr)) / pooled_std)


def kendall_tau(
    rank1: Sequence[float],
    rank2: Sequence[float],
) -> Tuple[float, float]:
    """Kendall's tau-b ranking correlation.

    Wraps ``scipy.stats.kendalltau``.

    Returns
    -------
    (statistic, p_value) : float, float

    Raises
    ------
    ImportError
        If scipy is not installed.
    """
    try:
        from scipy import stats as _scipy_stats
    except ImportError as exc:
        raise ImportError(
            "scipy is required for kendall_tau.  "
            "Install it with:  pip install scipy"
        ) from exc

    result = _scipy_stats.kendalltau(rank1, rank2)
    return float(result.statistic), float(result.pvalue)


def summarize_runs(
    values: Sequence[float],
    n_bootstrap: int = 10_000,
    confidence: float = 0.95,
) -> dict:
    """Aggregate per-run scalar values into a summary statistics dict.

    Parameters
    ----------
    values:
        One float per independent run (e.g. hypervolume, champion welfare).
    n_bootstrap:
        Resamples for bootstrap CI.
    confidence:
        CI confidence level.

    Returns
    -------
    dict with keys:
        mean, std, median, min, max, n,
        ci_lower, ci_upper, ci_width
    """
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n < 2:
        mean = float(arr[0]) if n == 1 else 0.0
        return dict(
            mean=mean, std=0.0, median=mean,
            min=mean, max=mean, n=n,
            ci_lower=mean, ci_upper=mean, ci_width=0.0,
        )
    ci_lower, ci_upper = bootstrap_ci(arr, n_bootstrap=n_bootstrap,
                                       confidence=confidence)
    return dict(
        mean=float(arr.mean()),
        std=float(arr.std(ddof=1)),
        median=float(np.median(arr)),
        min=float(arr.min()),
        max=float(arr.max()),
        n=int(n),
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_width=ci_upper - ci_lower,
    )
