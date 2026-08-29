from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import Counter
from typing import Iterable, Mapping, Sequence
from ..models.individual import Individual
from ..tracking.events import EvolutionEvent


@dataclass(frozen=True, slots=True)
class LongevityPolicy:
    initial_chance: float
    reproduction_reward: float
    inactivity_penalty: float
    perish_threshold: float = 0.0

    def __post_init__(self):
        if self.initial_chance < 0:
            raise ValueError("initial_chance must be non-negative")
        if self.reproduction_reward < 0:
            raise ValueError("reproduction_reward must be non-negative")
        if self.inactivity_penalty < 0:
            raise ValueError("inactivity_penalty must be non-negative")

    def to_dict(self) -> dict:
        return asdict(self)


def initialize_longevity(population: Iterable[Individual], policy: LongevityPolicy) -> None:
    for individual in population:
        if individual.longevity_chance is None:
            individual.longevity_chance = float(policy.initial_chance)


def age_survivors(population: Iterable[Individual]) -> None:
    for individual in population:
        if individual.alive:
            individual.age += 1


def update_longevity_end_of_generation(
    population: Sequence[Individual],
    *,
    successful_parent_participations: Mapping[str, int] | Iterable[str],
    policy: LongevityPolicy,
    generation: int | None = None,
) -> list[EvolutionEvent]:
    """Apply proposal-aligned longevity reward/penalty.

    A parent receives one reward per successful participation in producing a
    viable learning resource. An alive LO with no successful participation in
    the generation receives one inactivity penalty.
    """
    initialize_longevity(population, policy)
    if isinstance(successful_parent_participations, Mapping):
        counts = Counter({str(k): int(v) for k, v in successful_parent_participations.items()})
    else:
        counts = Counter(str(x) for x in successful_parent_participations)

    events: list[EvolutionEvent] = []
    for individual in population:
        if not individual.alive:
            continue
        before = float(individual.longevity_chance or 0.0)
        successful = max(0, counts.get(individual.individual_id, 0))
        if successful:
            individual.longevity_chance = before + successful * policy.reproduction_reward
            individual.reproduction_count += successful
            action = "reproduction_reward"
        else:
            individual.longevity_chance = before - policy.inactivity_penalty
            action = "inactivity_penalty"
        events.append(EvolutionEvent(
            event_type="longevity_update",
            generation=(max((i.generation_created for i in population), default=0) if generation is None else generation),
            individual_ids=(individual.individual_id,),
            payload={
                "before": before,
                "after": individual.longevity_chance,
                "successful_participations": successful,
                "action": action,
            },
        ))
    return events


def apply_perish(
    population: Sequence[Individual],
    *,
    threshold: float = 0.0,
    generation: int,
) -> list[EvolutionEvent]:
    events: list[EvolutionEvent] = []
    for individual in population:
        if not individual.alive or individual.longevity_chance is None:
            continue
        if individual.longevity_chance <= threshold:
            individual.alive = False
            individual.content_status = "perished"
            events.append(EvolutionEvent(
                event_type="perish",
                generation=generation,
                individual_ids=(individual.individual_id,),
                payload={
                    "longevity_chance": individual.longevity_chance,
                    "threshold": threshold,
                    "reason": "longevity_at_or_below_threshold",
                },
            ))
    return events


def reset_generation_state(population: Iterable[Individual]) -> None:
    for individual in population:
        individual.reset_generation_participation()
        individual.selection_probability = None
