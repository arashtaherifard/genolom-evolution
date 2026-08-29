from __future__ import annotations
from typing import Sequence
import random
from ..models.individual import Individual


def fitness_proportionate_probabilities(values: Sequence[float]) -> list[float]:
    values = [float(v) for v in values]
    if any(v < 0 for v in values):
        raise ValueError("Fitness values must be non-negative.")
    if not values:
        return []
    total = sum(values)
    if total <= 0:
        return [1.0 / len(values)] * len(values)
    return [v / total for v in values]


class FitnessProportionateSelection:
    name = "fitness_proportionate"

    def probabilities(self, individuals: Sequence[Individual]) -> list[float]:
        values = [float(i.micro_fitness or 0.0) for i in individuals]
        return fitness_proportionate_probabilities(values)

    def sample_indices(self, individuals: Sequence[Individual], count: int, rng: random.Random) -> list[int]:
        if count < 0:
            raise ValueError("count must be non-negative")
        probs = self.probabilities(individuals)
        if not probs and count:
            raise ValueError("Cannot sample from an empty population.")
        return rng.choices(range(len(individuals)), weights=probs, k=count)
