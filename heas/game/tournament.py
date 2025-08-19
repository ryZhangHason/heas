from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
import pandas as pd

from .arena import Arena
from .voting import choose_voter

ScoreFn = Callable[[Dict[str, Any], str], float]
# signature: score_fn(episode_record, participant_name) -> float

@dataclass
class PlayResult:
    per_step: pd.DataFrame
    per_episode: pd.DataFrame
    votes: pd.DataFrame

class Tournament:
    """
    Generic tournament orchestrator:
      - Runs all (scenario × participant) via Arena
      - Computes scores via score_fn
      - Aggregates winners via voter
    """

    def __init__(self, build_model: Callable[[Any, str, Dict[str, Any]], Any]):
        self.arena = Arena(build_model)

    def play(
        self,
        scenarios: Iterable[Any],
        participants: Iterable[str],
        steps: int,
        episodes: int,
        seed: int,
        score_fn: ScoreFn,
        voter: Any = "argmax",        # 'argmax', 'majority', or callable
    ) -> PlayResult:
        per_step, per_ep = self.arena.run(scenarios, participants, steps, episodes, seed)
        # Compute scores per (scenario, episode, participant)
        score_rows: List[Dict[str, Any]] = []
        for _, row in per_ep.iterrows():
            sc = row["scenario"]; ep = int(row["episode_id"]); p = row["participant"]
            s = float(score_fn(row.to_dict(), p))
            score_rows.append({"scenario": sc, "episode_id": ep, "participant": p, "score": s})
        scores = pd.DataFrame(score_rows)

        # Vote winners per (scenario, episode)
        voter_fn = choose_voter(voter)
        votes: List[Dict[str, Any]] = []
        for (sc, ep), grp in scores.groupby(["scenario", "episode_id"]):
            # 'argmax' expects dict[label->score]; 'majority' expects labels
            if voter == "argmax" or callable(voter):
                mapping = {r["participant"]: float(r["score"]) for _, r in grp.iterrows()}
                winner = voter_fn(mapping)
            else:
                # majority over indicator of "A" vs others as a toy; provide your custom voter for real use
                labs = [1 if r["participant"] in ("A", "TeamA") else 0 for _, r in grp.iterrows()]
                winner = voter_fn(labs)
            votes.append({"scenario": sc, "episode_id": int(ep), "winner": winner})

        votes_df = pd.DataFrame(votes)
        return PlayResult(per_step=per_step, per_episode=per_ep.merge(scores, on=["scenario","participant","episode_id"]),
                          votes=votes_df)