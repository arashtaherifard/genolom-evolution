from __future__ import annotations
from typing import Protocol, Iterable


class OntologyDistanceProvider(Protocol):
    name: str

    def resolve_topic(self, topic: str) -> str | None: ...
    def undirected_distance(self, topic_a: str, topic_b: str) -> int | None: ...
    def ancestor_distance(self, ancestor_topic: str, descendant_topic: str) -> int | None: ...


class ReferenceOntologyProvider(OntologyDistanceProvider, Protocol):
    """Ontology contract needed by generation-level coverage metrics."""

    def reference_topics(self) -> Iterable[str]: ...
