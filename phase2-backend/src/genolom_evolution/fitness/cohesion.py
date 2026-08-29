from __future__ import annotations
from itertools import combinations
from ..ontology.protocols import OntologyDistanceProvider


def unique_keywords(keywords) -> list[str]:
    seen, out = set(), []
    for value in keywords:
        value = str(value).strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def calculate_cohesion(keywords, ontology: OntologyDistanceProvider) -> float:
    topics = unique_keywords(keywords)
    if not topics:
        return 0.0
    if len(topics) == 1:
        return 1.0
    scores: list[float] = []
    for a, b in combinations(topics, 2):
        d = ontology.undirected_distance(a, b)
        if d is None:
            scores.append(0.0)
        elif d == 0:
            scores.append(1.0)
        else:
            scores.append(1.0 / d)
    return sum(scores) / len(scores)
