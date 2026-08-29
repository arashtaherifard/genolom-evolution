from __future__ import annotations
from collections import Counter
from math import log
from typing import Iterable
from ..models.individual import Individual


def shannon_entropy(values: Iterable[str]) -> float:
    values = [str(v) for v in values]
    if not values:
        return 0.0
    counts = Counter(values)
    n = len(values)
    return -sum((c/n) * log(c/n) for c in counts.values())


def population_diversity(individuals: list[Individual]) -> dict[str, float | int]:
    if not individuals:
        return {
            "population_size": 0,
            "unique_genome_ratio": 0.0,
            "unique_keyword_count": 0,
            "resource_type_entropy": 0.0,
            "interactivity_type_entropy": 0.0,
        }
    signatures = {i.genome.signature() for i in individuals}
    keywords = {k for i in individuals for k in i.genome.keywords}
    return {
        "population_size": len(individuals),
        "unique_genome_ratio": len(signatures) / len(individuals),
        "unique_keyword_count": len(keywords),
        "resource_type_entropy": shannon_entropy(i.genome.learningResourceType for i in individuals),
        "interactivity_type_entropy": shannon_entropy(i.genome.interactivityType for i in individuals),
    }
