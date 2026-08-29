from __future__ import annotations
from dataclasses import dataclass, asdict
from ..ontology.protocols import OntologyDistanceProvider
from .cohesion import calculate_cohesion, unique_keywords
from .dependence import calculate_dependence


@dataclass(frozen=True, slots=True)
class MicroFitnessResult:
    cohesion: float
    dependence: float
    fitness: float
    keyword_count: int

    @property
    def coherence(self) -> float:
        return self.dependence

    def to_dict(self):
        data = asdict(self)
        data["coherence"] = self.dependence  # legacy alias
        return data


def calculate_micro_fitness(
    keywords,
    ontology: OntologyDistanceProvider,
    *,
    cohesion_weight: float = 0.5,
    dependence_weight: float | None = None,
    coherence_weight: float | None = None,
):
    """Compute the frozen V1 micro fitness.

    ``coherence_weight`` is accepted as a deprecated configuration alias from
    Milestone 1. New code should use ``dependence_weight``.
    """
    if dependence_weight is None:
        dependence_weight = 0.5 if coherence_weight is None else coherence_weight
    if cohesion_weight < 0 or dependence_weight < 0:
        raise ValueError("Weights must be non-negative.")
    if abs(cohesion_weight + dependence_weight - 1.0) > 1e-12:
        raise ValueError("Fitness weights must sum to 1.")

    cohesion = calculate_cohesion(keywords, ontology)
    dependence = calculate_dependence(keywords, ontology)
    return MicroFitnessResult(
        cohesion=cohesion,
        dependence=dependence,
        fitness=cohesion_weight * cohesion + dependence_weight * dependence,
        keyword_count=len(unique_keywords(keywords)),
    )
