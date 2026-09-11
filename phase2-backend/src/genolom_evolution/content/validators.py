from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..models.genome import GenoLOMGenome
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

    # The validator/annotation pipeline must explicitly provide what the
    # generated artifact appears to be. Appended to preserve positional API.
    realized_genome: GenoLOMGenome | None = None

    # M5 retry/repair support. Legacy validators remain one-shot because
    # retryable defaults to False.
    retryable: bool = False
    failure_details: tuple[dict[str, Any], ...] = ()


class ContentValidator(Protocol):
    name: str

    def validate(self, request: GenerationRequest, response: GenerationResponse) -> ContentValidationResult: ...


__all__ = ["ContentValidationResult", "ContentValidator"]
