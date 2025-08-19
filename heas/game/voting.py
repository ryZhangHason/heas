from __future__ import annotations
from typing import Callable, Dict, Iterable, List, Tuple
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

def choose_voter(rule: str | Callable) -> Callable:
    """
    rule can be:
      - 'majority'  -> expects iterable of labels {0,1}, returns winner label {0,1}
      - 'argmax'    -> expects dict[label->score], returns label with max score
      - callable(labels_or_scores) -> your custom function
    """
    if callable(rule):
        return rule
    if rule == "majority":
        return lambda labels: 1 if sum(int(bool(x)) for x in labels) >= len(list(labels))/2 else 0
    if rule == "argmax":
        return lambda scores: max(scores.items(), key=lambda kv: kv[1])[0]
    raise ValueError(f"Unknown voting rule: {rule}")