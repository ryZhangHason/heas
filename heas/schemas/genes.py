from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Sequence

@dataclass
class Real:
    name: str
    low: float
    high: float

@dataclass
class Int:
    name: str
    low: int
    high: int

@dataclass
class Cat:
    name: str
    choices: Sequence[Any]

@dataclass
class Bool:
    name: str