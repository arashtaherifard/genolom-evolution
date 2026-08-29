from __future__ import annotations
from typing import Protocol, Sequence
import random
from ..models.individual import Individual


class SelectionStrategy(Protocol):
    name: str
    def probabilities(self, individuals: Sequence[Individual]) -> list[float]: ...
    def sample_indices(self, individuals: Sequence[Individual], count: int, rng: random.Random) -> list[int]: ...
