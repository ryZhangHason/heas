from __future__ import annotations
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from collections import Counter


def majority_vote(labels: Iterable[int]) -> int:
    c = Counter(int(bool(x)) for x in labels)
    return 1 if c[1] >= c[0] else 0


def borda_count(ranks: Iterable[int], m: int | None = None) -> int:
    vals = list(ranks)
    if not vals: return 0
    m = m or max(vals)
    scores = [m - r for r in vals]
    return vals[scores.index(max(scores))]


def weighted_vote(scores: Dict[str, float], weights: Dict[str, float]) -> str:
    best_key, best_val = "", float("-inf")
    keys = set(scores) | set(weights)
    for k in keys:
        v = scores.get(k, 0.0) * weights.get(k, 1.0)
        if v >= best_val:
            best_key, best_val = k, v
    return best_key


def copeland_vote(
    episodes_scores: Dict[Any, Dict[str, float]],
    participants: List[str],
) -> str:
    """Copeland's pairwise majority method across multiple episodes.

    Parameters
    ----------
    episodes_scores:
        ``{episode_id: {participant_name: score}}``.
        Each episode provides one "vote" in each pairwise contest.
    participants:
        Ordered list of participant names to rank.

    Returns
    -------
    str
        Name of the Copeland winner (highest net pairwise score).
        Ties broken lexicographically for reproducibility.

    Notes
    -----
    The Copeland score for participant *i* is:
        sum over all opponents *j* of:
            +1 if *i* wins more episodes than *j* head-to-head
            +0.5 if tied
            0 otherwise (and *j* gets +1 or +0.5 symmetrically)
    """
    copeland: Dict[str, float] = {p: 0.0 for p in participants}

    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            pi, pj = participants[i], participants[j]
            wins_i = wins_j = 0
            for ep_scores in episodes_scores.values():
                si = float(ep_scores.get(pi, 0.0))
                sj = float(ep_scores.get(pj, 0.0))
                if si > sj:
                    wins_i += 1
                elif sj > si:
                    wins_j += 1
            if wins_i > wins_j:
                copeland[pi] += 1.0
            elif wins_j > wins_i:
                copeland[pj] += 1.0
            else:
                copeland[pi] += 0.5
                copeland[pj] += 0.5

    # Break ties lexicographically
    return max(participants, key=lambda p: (copeland[p], -ord(p[0]) if p else 0))


def ranking_agreement(winner_lists: List[Any]) -> float:
    """Fraction of all (i, j) rule pairs that agree on the winner.

    Parameters
    ----------
    winner_lists:
        List of winners, one per voting rule (same scenario/episode context).
        E.g. ``["A", "A", "B", "A"]`` for four rules.

    Returns
    -------
    float in [0, 1].  1.0 means all rules agree; 0.0 means no two agree.
    """
    n = len(winner_lists)
    if n < 2:
        return 1.0
    pairs = n * (n - 1) // 2
    agree = sum(
        1 for i in range(n) for j in range(i + 1, n)
        if winner_lists[i] == winner_lists[j]
    )
    return agree / pairs


def choose_voter(rule: str | Callable) -> Callable:
    """Factory that returns a voter callable for ``Tournament.play()``.

    Supported string rules:
      - ``'majority'``  — majority_vote (binary label list)
      - ``'argmax'``    — argmax over a score dict
      - ``'copeland'``  — label only; actual aggregation uses :func:`copeland_vote`
                          directly on the full per-episode DataFrame (not per-episode)
      - callable        — passed through unchanged

    Note
    ----
    ``'copeland'`` cannot be routed through ``Tournament.play()``'s per-episode
    interface because it requires cross-episode pairwise comparison.  In the
    experiment scripts, Copeland is computed by calling :func:`copeland_vote`
    directly on the Arena's ``per_episode_df``.
    """
    if callable(rule):
        return rule
    if rule == "majority":
        return lambda labels: 1 if sum(int(bool(x)) for x in labels) >= len(list(labels)) / 2 else 0
    if rule == "argmax":
        return lambda scores: max(scores.items(), key=lambda kv: kv[1])[0]
    if rule == "copeland":
        # Placeholder: signals that Copeland should be handled externally
        raise ValueError(
            "'copeland' cannot be used with choose_voter / Tournament.play() directly. "
            "Use heas.game.voting.copeland_vote(episodes_scores, participants) on the "
            "full per-episode DataFrame instead."
        )
    raise ValueError(f"Unknown voting rule: {rule!r}")