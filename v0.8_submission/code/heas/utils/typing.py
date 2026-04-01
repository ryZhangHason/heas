
from __future__ import annotations
from typing import Callable, Sequence, Tuple, Any

ModelFactory = Callable[[dict], Any]
Genome = Sequence[Any]
Fitness = Tuple[float, ...]
