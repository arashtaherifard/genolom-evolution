from __future__ import annotations
from ..models.individual import Individual
from ..validation.genome_validator import validate_genome
from .diversity import population_diversity


def evaluate_population(individuals: list[Individual], reference_topics: set[str] | None = None) -> dict:
    valid_count = sum(not validate_genome(i.genome) for i in individuals)
    observed_topics = {k for i in individuals for k in i.genome.keywords}
    coverage = None
    if reference_topics is not None:
        coverage = 0.0 if not reference_topics else len(observed_topics & reference_topics) / len(reference_topics)
    return {
        "population_size": len(individuals),
        "valid_fraction": 0.0 if not individuals else valid_count / len(individuals),
        "reference_topic_coverage": coverage,
        "diversity": population_diversity(individuals),
    }
