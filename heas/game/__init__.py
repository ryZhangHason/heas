from __future__ import annotations

# Lazy-safe imports: some submodules (artifacts, arena, tournament) depend on
# pandas which may not be installed in lightweight environments.  Guard them
# so that importing heas.game.aggregation still works without pandas.

try:
    from .artifacts import ArtifactStore, save_df_smart, load_df_smart
except ImportError:
    ArtifactStore = save_df_smart = load_df_smart = None  # type: ignore[assignment]

from .scenarios import Scenario, ScenarioSet, make_scenarios, make_grid
from .voting import majority_vote, borda_count, weighted_vote, choose_voter

try:
    from .checkpoints import CheckpointManager
except ImportError:
    CheckpointManager = None  # type: ignore[assignment,misc]

try:
    from .arena import Arena
except ImportError:
    Arena = None  # type: ignore[assignment,misc]

try:
    from .tournament import Tournament, PlayResult
except ImportError:
    Tournament = PlayResult = None  # type: ignore[assignment]

from .aggregation import (
    Aggregator,
    HEASAggregator,
    AdHocStepAggregator,
    AdHocMeanAggregator,
    AdHocQ75Aggregator,
    AdHocEntropyAggregator,
    AGGREGATION_CONDITIONS,
    CONDITION_NAMES,
    make_aggregator,
)

__all__ = [
    # storage
    "ArtifactStore", "save_df_smart", "load_df_smart",
    # scenarios
    "Scenario", "ScenarioSet", "make_scenarios", "make_grid",
    # voting
    "majority_vote", "borda_count", "weighted_vote", "choose_voter",
    # checkpoints
    "CheckpointManager",
    # runners
    "Arena", "Tournament", "PlayResult",
    # aggregation (MAD experiment conditions)
    "Aggregator", "HEASAggregator",
    "AdHocStepAggregator", "AdHocMeanAggregator",
    "AdHocQ75Aggregator", "AdHocEntropyAggregator",
    "AGGREGATION_CONDITIONS", "CONDITION_NAMES", "make_aggregator",
]
