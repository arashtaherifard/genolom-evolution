from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from .generator import GenerationRequest, GenerationResponse


@dataclass(frozen=True, slots=True)
class ContentValidationResult:
    accepted: bool
    genome_agreement: float | None = None
    faithfulness: float | None = None
    factuality: float | None = None
    hallucination_flags: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)


class ContentValidator(Protocol):
    name: str
    def validate(self, request: GenerationRequest, response: GenerationResponse) -> ContentValidationResult: ...
