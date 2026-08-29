from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Protocol
from ..models.genome import GenoLOMGenome


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    source_content: str
    target_genome: GenoLOMGenome
    operator_name: str
    prompt_template_id: str
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    content: str
    provider: str
    model: str
    model_version: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class ContentGenerator(Protocol):
    provider_name: str
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...
