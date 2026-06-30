"""
heas.game.aggregation
======================
Aggregation pathway classes for Metric Aggregation Divergence (MAD) experiments.

The core MAD finding is that using *different* aggregation functions at
optimizer selection vs. tournament re-ranking causes policy-champion flips.
These classes encode the five aggregation conditions used in EA-2, EA-6,
EA-6b, and EA-12:

HEAS (contract)
    Same callable (episode-mean) at all stages — the metric contract.

AdHocStep
    Optimizer reads final-step value; tournament reads episode-mean.

AdHocMean
    Optimizer reads episode-mean; tournament reads median.

AdHocQ75
    Optimizer reads episode-mean; tournament reads 75th percentile.

AdHocEntropy
    Optimizer reads episode-mean; tournament reads normalised entropy.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class Aggregator(ABC):
    """Base class for aggregation pathway conditions."""

    @abstractmethod
    def agg_optimizer(self, m: Dict[str, float]) -> float:
        """Scalarise the metric dict for the optimizer/EVOLVER stage."""

    @abstractmethod
    def agg_tournament(self, m: Dict[str, float]) -> float:
        """Scalarise the metric dict for the tournament/re-ranking stage."""


class HEASAggregator(Aggregator):
    """Metric contract: same callable (episode-mean) at all stages.

    This is the HEAS prescription — the aggregation function is fixed and
    identical across optimiser, tournament, and inference.  By construction,
    it cannot cause champion flips due to aggregation divergence.
    """

    def agg_optimizer(self, m: Dict[str, float]) -> float:
        return m["mean"]

    def agg_tournament(self, m: Dict[str, float]) -> float:
        return m["mean"]


class AdHocStepAggregator(Aggregator):
    """Ad-hoc step: optimizer uses final-step value; tournament uses mean.

    This is the most common ad-hoc pattern in the MOEA literature:
    the optimiser's objective function evaluates the final snapshot, but
    the post-hoc evaluation averages over the full trajectory.
    """

    def agg_optimizer(self, m: Dict[str, float]) -> float:
        return m["final"]

    def agg_tournament(self, m: Dict[str, float]) -> float:
        return m["mean"]


class AdHocMeanAggregator(Aggregator):
    """Ad-hoc mean: optimizer uses mean; tournament uses median.

    Both use central-tendency measures but from different distributional
    locations, creating subtle re-ranking under skewed trajectories.
    """

    def agg_optimizer(self, m: Dict[str, float]) -> float:
        return m["mean"]

    def agg_tournament(self, m: Dict[str, float]) -> float:
        return m["median"]


class AdHocQ75Aggregator(Aggregator):
    """Ad-hoc Q75: optimizer uses mean; tournament uses 75th percentile.

    The Q75 emphasises peak performance rather than average, rewarding
    policies that occasionally spike even if they are unstable.
    """

    def agg_optimizer(self, m: Dict[str, float]) -> float:
        return m["mean"]

    def agg_tournament(self, m: Dict[str, float]) -> float:
        return m["q75"]


class AdHocEntropyAggregator(Aggregator):
    """Ad-hoc entropy: optimizer uses mean; tournament uses normalised entropy.

    Entropy measures trajectory diversity (histogram shape) rather than
    location.  High entropy means the trajectory visits many states —
    rewarded as "diversity" even when mean performance is mediocre.
    """

    def agg_optimizer(self, m: Dict[str, float]) -> float:
        return m["mean"]

    def agg_tournament(self, m: Dict[str, float]) -> float:
        return m["entropy"]


# ---------------------------------------------------------------------------
# Convenience registry
# ---------------------------------------------------------------------------

#: All five aggregation conditions, keyed by name (matches EA-2 / EA-6).
AGGREGATION_CONDITIONS: Dict[str, type] = {
    "HEAS":           HEASAggregator,
    "Ad-hoc-Step":    AdHocStepAggregator,
    "Ad-hoc-Mean":    AdHocMeanAggregator,
    "Ad-hoc-Q75":     AdHocQ75Aggregator,
    "Ad-hoc-Entropy": AdHocEntropyAggregator,
}

#: The five condition names used in EA-6, EA-6b, EA-12.
CONDITION_NAMES = list(AGGREGATION_CONDITIONS.keys())


def make_aggregator(name: str) -> Aggregator:
    """Instantiate an aggregator by condition name.

    Raises ``ValueError`` if *name* is not in :data:`AGGREGATION_CONDITIONS`.
    """
    if name not in AGGREGATION_CONDITIONS:
        raise ValueError(
            f"Unknown aggregation condition: {name!r}.  "
            f"Valid: {CONDITION_NAMES}"
        )
    return AGGREGATION_CONDITIONS[name]()
