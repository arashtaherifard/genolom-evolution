from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from ..models.individual import Individual
from .reference import ReferenceConceptSet


@dataclass(frozen=True, slots=True)
class CoherencyRankEntry:
    rank: int
    keyword: str
    resolved_topic: str
    coverage_count: int
    covered_reference_topics: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["covered_reference_topics"] = list(self.covered_reference_topics)
        return data


@dataclass(frozen=True, slots=True)
class GenerationMacroMetrics:
    generation: int
    population_size: int
    reference_topic_count: int
    keyword_occurrence_count: int
    coherent_keyword_occurrence_count: int
    unresolved_keyword_occurrence_count: int
    coherency_rate: float
    covered_reference_topic_count: int
    coverage_span: float
    recall: float
    precision: float
    generation_f1: float
    precision_component_count: int
    precision_subgraph_node_count: int
    coverage_rates: dict[int, float]
    threshold_covered_topic_counts: dict[int, int]
    topic_resource_counts: dict[str, int]
    coherency_rank: tuple[CoherencyRankEntry, ...]

    def to_dict(self) -> dict:
        return {
            "generation": self.generation,
            "population_size": self.population_size,
            "reference_topic_count": self.reference_topic_count,
            "keyword_occurrence_count": self.keyword_occurrence_count,
            "coherent_keyword_occurrence_count": self.coherent_keyword_occurrence_count,
            "unresolved_keyword_occurrence_count": self.unresolved_keyword_occurrence_count,
            "coherency_rate": self.coherency_rate,
            "covered_reference_topic_count": self.covered_reference_topic_count,
            "coverage_span": self.coverage_span,
            "recall": self.recall,
            "precision": self.precision,
            "generation_f1": self.generation_f1,
            "precision_component_count": self.precision_component_count,
            "precision_subgraph_node_count": self.precision_subgraph_node_count,
            "coverage_rates": {str(k): v for k, v in sorted(self.coverage_rates.items())},
            "threshold_covered_topic_counts": {
                str(k): v for k, v in sorted(self.threshold_covered_topic_counts.items())
            },
            "topic_resource_counts": dict(sorted(self.topic_resource_counts.items())),
            "coherency_rank": [entry.to_dict() for entry in self.coherency_rank],
        }


def _active(population: Sequence[Individual]) -> list[Individual]:
    return [individual for individual in population if individual.alive]


def _coverage_set(topic: str, reference: set[str], ontology) -> set[str]:
    """Reference concepts covered by a resolved keyword for Coherency Rank.

    A keyword covers itself when it belongs to the frozen reference set plus
    reference concepts hierarchically below it.  This descendant expansion is
    intentionally used only for Coherency Rate/Rank, not Recall/Coverage Rate.
    """

    covered: set[str] = set()
    for candidate in reference:
        if candidate == topic:
            covered.add(candidate)
            continue
        distance = ontology.ancestor_distance(topic, candidate)
        if distance is not None and distance > 0:
            covered.add(candidate)
    return covered


def _hierarchy_path(ontology, ancestor: str, descendant: str) -> tuple[str, ...] | None:
    if ancestor == descendant:
        return (ancestor,)
    method = getattr(ontology, "hierarchy_path", None)
    if method is None:
        raise TypeError(
            "Precision requires ontology.hierarchy_path(ancestor, descendant); "
            "CSOOntologyAdapter implements this contract."
        )
    path = method(ancestor, descendant)
    if not path:
        return None
    return tuple(str(item) for item in path)


def _precision_graph(covered_topics: set[str], ontology) -> tuple[float, int, int]:
    if not covered_topics:
        return 0.0, 0, 0

    adjacency: dict[str, set[str]] = defaultdict(set)
    nodes: set[str] = set(covered_topics)
    ordered = sorted(covered_topics)

    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            left_to_right = ontology.ancestor_distance(left, right)
            right_to_left = ontology.ancestor_distance(right, left)
            path: tuple[str, ...] | None = None
            if left_to_right is not None and left_to_right > 0:
                path = _hierarchy_path(ontology, left, right)
            elif right_to_left is not None and right_to_left > 0:
                path = _hierarchy_path(ontology, right, left)
            if not path:
                continue
            nodes.update(path)
            for a, b in zip(path, path[1:]):
                adjacency[a].add(b)
                adjacency[b].add(a)

    # Isolated directly covered topics remain graph components.
    for node in nodes:
        adjacency.setdefault(node, set())

    visited: set[str] = set()
    components = 0
    for start in sorted(nodes):
        if start in visited:
            continue
        components += 1
        queue: deque[str] = deque([start])
        visited.add(start)
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    node_count = len(nodes)
    precision = 1.0 - ((components - 1) / node_count)
    return max(0.0, min(1.0, precision)), components, node_count


def calculate_generation_macro_metrics(
    population: Sequence[Individual],
    ontology,
    reference: ReferenceConceptSet | Iterable[str],
    *,
    generation: int,
    coverage_thresholds: Iterable[int] = (1, 2, 3, 5),
) -> GenerationMacroMetrics:
    reference_topics = (
        set(reference.topics)
        if isinstance(reference, ReferenceConceptSet)
        else {str(item).strip() for item in reference if str(item).strip()}
    )
    thresholds = tuple(sorted({int(value) for value in coverage_thresholds}))
    if not thresholds or thresholds[0] < 1:
        raise ValueError("coverage_thresholds must contain integers >= 1")

    individuals = _active(population)
    topic_resource_counts: Counter[str] = Counter()
    keyword_occurrences = 0
    coherent_occurrences = 0
    unresolved_occurrences = 0
    unique_resolved_keywords: dict[str, str] = {}

    for individual in individuals:
        # Genome keywords are already deduplicated by the model, but keep this
        # explicit to preserve the frozen LO-level occurrence rule.
        seen_in_lo: set[str] = set()
        direct_reference_topics_for_lo: set[str] = set()
        for raw_keyword in individual.genome.keywords:
            normalized = str(raw_keyword).strip()
            if not normalized:
                continue
            dedup_key = normalized.casefold()
            if dedup_key in seen_in_lo:
                continue
            seen_in_lo.add(dedup_key)
            keyword_occurrences += 1

            resolved = ontology.resolve_topic(normalized)
            if resolved is None:
                unresolved_occurrences += 1
                continue
            resolved = str(resolved)
            unique_resolved_keywords.setdefault(normalized, resolved)
            covered_by_keyword = _coverage_set(resolved, reference_topics, ontology)
            if covered_by_keyword:
                coherent_occurrences += 1
            if resolved in reference_topics:
                direct_reference_topics_for_lo.add(resolved)
        topic_resource_counts.update(direct_reference_topics_for_lo)

    covered_topics = {topic for topic, count in topic_resource_counts.items() if count >= 1}
    denominator = len(reference_topics)
    coverage_span = (len(covered_topics) / denominator) if denominator else 0.0
    recall = coverage_span
    coherency_rate = (
        coherent_occurrences / keyword_occurrences if keyword_occurrences else 0.0
    )

    precision, component_count, subgraph_node_count = _precision_graph(
        covered_topics, ontology
    )
    generation_f1 = (
        (2.0 * precision * recall / (precision + recall))
        if (precision + recall) > 0
        else 0.0
    )

    coverage_rates: dict[int, float] = {}
    threshold_counts: dict[int, int] = {}
    for threshold in thresholds:
        count = sum(
            1
            for topic in reference_topics
            if topic_resource_counts.get(topic, 0) >= threshold
        )
        threshold_counts[threshold] = count
        coverage_rates[threshold] = (count / denominator) if denominator else 0.0

    rank_rows: list[tuple[str, str, tuple[str, ...]]] = []
    for keyword, resolved in unique_resolved_keywords.items():
        covered = tuple(sorted(_coverage_set(resolved, reference_topics, ontology)))
        if covered:
            rank_rows.append((keyword, resolved, covered))
    rank_rows.sort(key=lambda item: (-len(item[2]), item[0].casefold(), item[0]))
    coherency_rank = tuple(
        CoherencyRankEntry(
            rank=index,
            keyword=keyword,
            resolved_topic=resolved,
            coverage_count=len(covered),
            covered_reference_topics=covered,
        )
        for index, (keyword, resolved, covered) in enumerate(rank_rows, start=1)
    )

    return GenerationMacroMetrics(
        generation=int(generation),
        population_size=len(individuals),
        reference_topic_count=denominator,
        keyword_occurrence_count=keyword_occurrences,
        coherent_keyword_occurrence_count=coherent_occurrences,
        unresolved_keyword_occurrence_count=unresolved_occurrences,
        coherency_rate=coherency_rate,
        covered_reference_topic_count=len(covered_topics),
        coverage_span=coverage_span,
        recall=recall,
        precision=precision,
        generation_f1=generation_f1,
        precision_component_count=component_count,
        precision_subgraph_node_count=subgraph_node_count,
        coverage_rates=coverage_rates,
        threshold_covered_topic_counts=threshold_counts,
        topic_resource_counts=dict(sorted(topic_resource_counts.items())),
        coherency_rank=coherency_rank,
    )


__all__ = [
    "CoherencyRankEntry",
    "GenerationMacroMetrics",
    "calculate_generation_macro_metrics",
]
