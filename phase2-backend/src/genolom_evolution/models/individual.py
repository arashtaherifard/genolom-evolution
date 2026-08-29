from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .genome import GenoLOMGenome


@dataclass(slots=True)
class Individual:
    individual_id: str
    content: str
    genome: GenoLOMGenome
    source_type: str = ""
    source_page: str = ""
    source_row_id: str = ""
    generation_created: int = 0
    parent_ids: tuple[str, ...] = ()
    created_by: str = "initial_population"

    # Evolutionary state
    age: int = 0
    longevity_chance: float | None = None
    alive: bool = True
    reproduction_count: int = 0
    generation_participations: int = 0
    fusion_history: list[str] = field(default_factory=list)
    defusion_history: list[str] = field(default_factory=list)

    # Optimization variables
    cohesion: float | None = None
    dependence: float | None = None
    micro_fitness: float | None = None
    selection_probability: float | None = None

    # Content-state separation
    content_status: str = "accepted"
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def coherence(self) -> float | None:
        """Backward-compatible alias for pre-M2 code.

        Canonical Phase-2 terminology is now ``dependence`` to align with the
        updated task sheet and proposal. ``coherence`` is retained only so that
        previously written consumers do not break.
        """
        return self.dependence

    @coherence.setter
    def coherence(self, value: float | None) -> None:
        self.dependence = value

    @property
    def fusion_count(self) -> int:
        return len(self.fusion_history)

    @property
    def defusion_count(self) -> int:
        return len(self.defusion_history)

    def record_fusion(self, event_id: str) -> None:
        self.fusion_history.append(str(event_id))

    def record_defusion(self, event_id: str) -> None:
        self.defusion_history.append(str(event_id))

    def reset_generation_participation(self) -> None:
        self.generation_participations = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "individual_id": self.individual_id,
            "content": self.content,
            "genome": self.genome.to_dict(),
            "source_type": self.source_type,
            "source_page": self.source_page,
            "source_row_id": self.source_row_id,
            "generation_created": self.generation_created,
            "parent_ids": list(self.parent_ids),
            "created_by": self.created_by,
            "age": self.age,
            "longevity_chance": self.longevity_chance,
            "alive": self.alive,
            "reproduction_count": self.reproduction_count,
            "generation_participations": self.generation_participations,
            "fusion_history": list(self.fusion_history),
            "defusion_history": list(self.defusion_history),
            "fusion_count": self.fusion_count,
            "defusion_count": self.defusion_count,
            "cohesion": self.cohesion,
            "dependence": self.dependence,
            "coherence": self.dependence,  # legacy alias for UI/API compatibility
            "micro_fitness": self.micro_fitness,
            "selection_probability": self.selection_probability,
            "content_status": self.content_status,
            "extra": self.extra,
        }
