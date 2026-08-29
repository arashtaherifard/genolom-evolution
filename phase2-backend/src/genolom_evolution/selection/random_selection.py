from __future__ import annotations
from typing import Sequence
import random
from ..models.individual import Individual


class RandomSelection:
    name = "random"

    def probabilities(self, individuals: Sequence[Individual]) -> list[float]:
        if not individuals:
            return []
        return [1.0 / len(individuals)] * len(individuals)

    def sample_indices(self, individuals: Sequence[Individual], count: int, rng: random.Random) -> list[int]:
        if count < 0:
            raise ValueError("count must be non-negative")
        if not individuals and count:
            raise ValueError("Cannot sample from an empty population.")
        return [rng.randrange(len(individuals)) for _ in range(count)]
