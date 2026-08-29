from __future__ import annotations
from functools import lru_cache
import math


class CSOOntologyAdapter:
    name = "Computer Science Ontology (CSO)"

    def __init__(self, ontology=None, *, root_topic: str = "computer science"):
        if ontology is None:
            from cso_classifier.ontology import Ontology
            ontology = Ontology(load_ontology=True, silent=True)
        self.ontology = ontology
        self.graph = ontology.get_ontology_graph()
        self.root_topic = self.resolve_topic(root_topic)
        if self.root_topic is None:
            raise ValueError(f"Could not resolve root topic {root_topic!r}.")
        self.hierarchy_mode = self._infer_hierarchy_mode()

    def _vertex_exists(self, topic: str) -> bool:
        try:
            self.graph.vs.find(name=topic)
            return True
        except Exception:
            return False

    @lru_cache(maxsize=None)
    def resolve_topic(self, topic: str) -> str | None:
        topic = str(topic).strip()
        if not topic:
            return None
        candidates: list[str] = []
        try:
            primary = self.ontology.get_primary_label(topic)
            if primary:
                candidates.append(str(primary))
        except Exception:
            pass
        candidates.append(topic)
        for candidate in dict.fromkeys(candidates):
            candidate = candidate.strip()
            if candidate and self._vertex_exists(candidate):
                return candidate
        return None

    def _reachable_count(self, mode: str) -> int:
        try:
            idx = self.graph.vs.find(name=self.root_topic).index
            return len(self.graph.subcomponent(idx, mode=mode))
        except Exception:
            return 0

    def _infer_hierarchy_mode(self) -> str:
        return "OUT" if self._reachable_count("OUT") >= self._reachable_count("IN") else "IN"

    @staticmethod
    def _clean_distance(value) -> int | None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if math.isinf(value):
            return None
        return int(value)

    @lru_cache(maxsize=None)
    def undirected_distance(self, topic_a: str, topic_b: str) -> int | None:
        a, b = self.resolve_topic(topic_a), self.resolve_topic(topic_b)
        if a is None or b is None:
            return None
        if a == b:
            return 0
        try:
            value = self.graph.distances(source=a, target=b, mode="ALL")[0][0]
        except Exception:
            return None
        return self._clean_distance(value)

    @lru_cache(maxsize=None)
    def ancestor_distance(self, ancestor_topic: str, descendant_topic: str) -> int | None:
        a = self.resolve_topic(ancestor_topic)
        d = self.resolve_topic(descendant_topic)
        if a is None or d is None:
            return None
        if a == d:
            return 0
        try:
            value = self.graph.distances(source=a, target=d, mode=self.hierarchy_mode)[0][0]
        except Exception:
            return None
        return self._clean_distance(value)
    @lru_cache(maxsize=1)
    def reference_topics(self) -> tuple[str, ...]:
        """Return the CSO reference slice reachable from the configured root.

        Coverage metrics operate on the ontology slice rooted at ``computer
        science`` rather than every disconnected/auxiliary node in the graph.
        This keeps the denominator aligned with the domain represented by the
        educational corpus.
        """
        try:
            idx = self.graph.vs.find(name=self.root_topic).index
            indices = self.graph.subcomponent(idx, mode=self.hierarchy_mode)
            names = [self.graph.vs[i]["name"] for i in indices]
        except Exception:
            return ()
        return tuple(sorted({str(name).strip() for name in names if str(name).strip()}))

