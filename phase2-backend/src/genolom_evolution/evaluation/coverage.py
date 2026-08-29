from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence
from ..models.individual import Individual
from ..ontology.protocols import ReferenceOntologyProvider


@dataclass(frozen=True, slots=True)
class CoverageResult:
    population_size: int
    reference_topic_count: int
    covered_topic_count: int
    coverage_span: float
    coverage_threshold: int
    threshold_covered_topic_count: int
    coverage_rate: float
    unresolved_keyword_count: int
    topic_resource_counts: dict[str, int]

    def to_dict(self) -> dict:
        return asdict(self)


def _reference_set(ontology: ReferenceOntologyProvider) -> set[str]:
    return {str(x).strip() for x in ontology.reference_topics() if str(x).strip()}


def calculate_coverage(
    population: Sequence[Individual],
    ontology: ReferenceOntologyProvider,
    *,
    coverage_threshold: int = 1,
) -> CoverageResult:
    """Compute proposal-aligned generation coverage variables.

    Coverage Span is the proportion of reference ontology nodes directly
    covered by at least one LO keyword in the generation.

    Coverage Threshold is the minimum number of distinct learning resources
    required to cover a reference node. Coverage Rate is included as a necessary
    dependency: the proportion of reference nodes whose resource count meets or
    exceeds that threshold.
    """
    if coverage_threshold < 1:
        raise ValueError("coverage_threshold must be >= 1")

    reference = _reference_set(ontology)
    counts: Counter[str] = Counter()
    unresolved = 0

    for individual in population:
        if not individual.alive:
            continue
        resolved_for_lo: set[str] = set()
        for keyword in individual.genome.keywords:
            resolved = ontology.resolve_topic(keyword)
            if resolved is None:
                unresolved += 1
                continue
            if not reference or resolved in reference:
                resolved_for_lo.add(resolved)
        # Count resources, not repeated keyword mentions in one resource.
        counts.update(resolved_for_lo)

    denominator = len(reference)
    covered = {topic for topic, count in counts.items() if count >= 1}
    threshold_covered = {topic for topic, count in counts.items() if count >= coverage_threshold}
    span = (len(covered) / denominator) if denominator else 0.0
    rate = (len(threshold_covered) / denominator) if denominator else 0.0

    return CoverageResult(
        population_size=sum(1 for i in population if i.alive),
        reference_topic_count=denominator,
        covered_topic_count=len(covered),
        coverage_span=span,
        coverage_threshold=coverage_threshold,
        threshold_covered_topic_count=len(threshold_covered),
        coverage_rate=rate,
        unresolved_keyword_count=unresolved,
        topic_resource_counts=dict(sorted(counts.items())),
    )
