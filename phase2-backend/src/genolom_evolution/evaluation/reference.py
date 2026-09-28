from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Sequence

from ..models.individual import Individual


@dataclass(frozen=True, slots=True)
class ReferenceConceptSet:
    """Frozen chapter-level ontology reference used by generation metrics.

    Operationalization frozen for Team 405: resolve every Generation-0 keyword
    against CSO, deduplicate the successfully resolved concepts, sort them, and
    freeze that set before evolution.
    """

    topics: tuple[str, ...]
    unresolved_generation0_keywords: tuple[str, ...]
    construction: str = "generation0_unique_successfully_resolved_keywords_v1"
    source_generation: int = 0
    ontology_name: str = ""

    @property
    def checksum(self) -> str:
        payload = json.dumps(
            {
                "topics": list(self.topics),
                "construction": self.construction,
                "source_generation": self.source_generation,
                "ontology_name": self.ontology_name,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["topics"] = list(self.topics)
        data["unresolved_generation0_keywords"] = list(self.unresolved_generation0_keywords)
        data["checksum"] = self.checksum
        return data


def build_reference_concept_set(
    generation0: Sequence[Individual],
    ontology,
) -> ReferenceConceptSet:
    resolved: set[str] = set()
    unresolved: set[str] = set()
    for individual in generation0:
        for keyword in individual.genome.keywords:
            topic = ontology.resolve_topic(keyword)
            if topic is None:
                text = str(keyword).strip()
                if text:
                    unresolved.add(text)
            else:
                resolved.add(str(topic).strip())
    return ReferenceConceptSet(
        topics=tuple(sorted(x for x in resolved if x)),
        unresolved_generation0_keywords=tuple(sorted(unresolved)),
        ontology_name=str(getattr(ontology, "name", type(ontology).__name__)),
    )


__all__ = ["ReferenceConceptSet", "build_reference_concept_set"]
