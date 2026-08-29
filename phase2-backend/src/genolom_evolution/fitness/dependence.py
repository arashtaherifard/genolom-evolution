from __future__ import annotations
from ..ontology.protocols import OntologyDistanceProvider
from .cohesion import unique_keywords


def calculate_dependence(keywords, ontology: OntologyDistanceProvider) -> float:
    """Operational V1 proxy for conceptual Dependence.

    For each keyword, find the strongest support from another same-LO keyword
    that is an ontology ancestor/broader concept. Support is inverse directed
    hierarchy distance. The LO score is the mean support over its keywords.

    The proposal defines Dependence conceptually rather than mathematically;
    therefore this ontology-hierarchy formulation is explicitly treated as a
    testable proxy and remains eligible for later expert validation.
    """
    topics = unique_keywords(keywords)
    if not topics:
        return 0.0

    supports: list[float] = []
    for descendant in topics:
        best = 0.0
        for ancestor in topics:
            if ancestor == descendant:
                continue
            distance = ontology.ancestor_distance(ancestor, descendant)
            if distance is not None and distance > 0:
                best = max(best, 1.0 / distance)
        supports.append(best)
    return sum(supports) / len(supports)
