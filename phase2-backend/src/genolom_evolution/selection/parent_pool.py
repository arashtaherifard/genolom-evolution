from __future__ import annotations
from dataclasses import dataclass
import random
from typing import Sequence

from ..models.individual import Individual
from ..evolution.eligibility import check_parent_eligibility
from .fitness_proportionate import FitnessProportionateSelection
from .random_selection import RandomSelection


@dataclass(frozen=True, slots=True)
class ParentSelectionResult:
    operator: str
    strategy: str
    eligible_ids: tuple[str, ...]
    ranked_eligible_ids: tuple[str, ...]
    selected_ids: tuple[str, ...]
    fitnesses: dict[str, float]
    probabilities: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "operator": self.operator,
            "strategy": self.strategy,
            "eligible_ids": list(self.eligible_ids),
            "ranked_eligible_ids": list(self.ranked_eligible_ids),
            "selected_ids": list(self.selected_ids),
            "fitnesses": dict(self.fitnesses),
            "probabilities": dict(self.probabilities),
        }


def _strategy(name: str):
    name = name.strip().lower()
    if name == "fitness_proportionate":
        return FitnessProportionateSelection()
    if name in {"random", "uniform"}:
        return RandomSelection()
    raise ValueError(f"Unknown selection strategy: {name}")


def select_parents(
    population: Sequence[Individual],
    *,
    operator: str,
    count: int,
    rng: random.Random,
    strategy: str = "fitness_proportionate",
    maturity_age: int | None = None,
    max_parent_participations_per_generation: int | None = None,
    repeated_parent_selection: bool = True,
) -> ParentSelectionResult:
    if count < 0:
        raise ValueError("count must be non-negative")

    eligible = [
        i for i in population
        if check_parent_eligibility(
            i,
            operator=operator,
            maturity_age=maturity_age,
            max_parent_participations_per_generation=max_parent_participations_per_generation,
        ).eligible
    ]
    if count and not eligible:
        raise ValueError(f"No eligible parents for operator {operator!r}.")
    if not repeated_parent_selection and count > len(eligible):
        raise ValueError("Requested more distinct parents than eligible individuals.")

    # Task-sheet selection workflow: fitness calculation -> descending rank ->
    # probability mapping -> stochastic parent draw. Ranking is exposed for UI
    # inspection but does not replace probabilistic selection.
    ranked = sorted(
        eligible,
        key=lambda i: (-float(i.micro_fitness or 0.0), i.individual_id),
    )
    selector = _strategy(strategy)
    probs = selector.probabilities(ranked)
    fitness_map = {i.individual_id: float(i.micro_fitness or 0.0) for i in ranked}
    probability_map = {i.individual_id: p for i, p in zip(ranked, probs)}
    for i, p in zip(ranked, probs):
        i.selection_probability = p

    requires_distinct_within_draw = operator.strip().lower() in {"crossover", "fusion", "composition"} and count > 1
    without_replacement = (not repeated_parent_selection) or requires_distinct_within_draw

    if not without_replacement:
        indices = selector.sample_indices(ranked, count, rng)
        selected = [ranked[idx] for idx in indices]
    else:
        if count > len(ranked):
            raise ValueError("Requested more distinct parents than eligible individuals.")
        remaining = list(ranked)
        selected = []
        for _ in range(count):
            local_probs = selector.probabilities(remaining)
            idx = rng.choices(range(len(remaining)), weights=local_probs, k=1)[0]
            selected.append(remaining.pop(idx))

    return ParentSelectionResult(
        operator=operator,
        strategy=selector.name,
        eligible_ids=tuple(i.individual_id for i in eligible),
        ranked_eligible_ids=tuple(i.individual_id for i in ranked),
        selected_ids=tuple(i.individual_id for i in selected),
        fitnesses=fitness_map,
        probabilities=probability_map,
    )
