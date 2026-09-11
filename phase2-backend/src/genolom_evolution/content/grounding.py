from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

GroundingMode = Literal["grounded", "parametric"]


@dataclass(frozen=True, slots=True)
class GroundingEvidence:
    source_id: str
    text: str
    relation: str = "approved_evidence"

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "text": self.text,
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class GroundingContext:
    mode: GroundingMode = "grounded"
    evidence: tuple[GroundingEvidence, ...] = ()

    @classmethod
    def from_source(cls, source_id: str, source_content: str) -> "GroundingContext":
        return cls(
            mode="grounded",
            evidence=(
                GroundingEvidence(
                    source_id=source_id,
                    text=source_content,
                    relation="parent_learning_object",
                ),
            ),
        )

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(item.source_id for item in self.evidence)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "source_ids": list(self.source_ids),
            "evidence": [item.to_dict() for item in self.evidence],
        }


__all__ = ["GroundingMode", "GroundingEvidence", "GroundingContext"]
