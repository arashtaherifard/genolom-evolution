from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

from ...models.individual import Individual
from ...models.genome import GenoLOMGenome
from ..generator import ContentGenerator, GenerationRequest, GenerationResponse
from ..validators import ContentValidator, ContentValidationResult


@dataclass(frozen=True, slots=True)
class ContentOperationResult:
    operator_name: str
    request: GenerationRequest
    response: GenerationResponse
    validation: ContentValidationResult

    @property
    def accepted(self) -> bool:
        return self.validation.accepted

    def to_dict(self) -> dict:
        return {
            "operator_name": self.operator_name,
            "request": {
                "source_content": self.request.source_content,
                "target_genome": self.request.target_genome.to_dict(),
                "operator_name": self.request.operator_name,
                "prompt_template_id": self.request.prompt_template_id,
                "seed": self.request.seed,
                "metadata": self.request.metadata,
            },
            "response": self.response.to_dict(),
            "validation": {
                "accepted": self.validation.accepted,
                "genome_agreement": self.validation.genome_agreement,
                "faithfulness": self.validation.faithfulness,
                "factuality": self.validation.factuality,
                "hallucination_flags": list(self.validation.hallucination_flags),
                "reasons": list(self.validation.reasons),
                "metadata": self.validation.metadata,
            },
        }


class ContentOperator(Protocol):
    name: str
    prompt_template_id: str

    def build_request(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        seed: int | None = None,
    ) -> GenerationRequest: ...

    def execute(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        generator: ContentGenerator,
        validator: ContentValidator,
        seed: int | None = None,
    ) -> ContentOperationResult: ...


class BaseContentOperator:
    name = "base"
    prompt_template_id = "base-v1"
    instruction = "Transform the source learning object to match the target GenoLOM genome."

    def build_request(self, source: Individual, target_genome: GenoLOMGenome, *, seed: int | None = None) -> GenerationRequest:
        return GenerationRequest(
            source_content=source.content,
            target_genome=target_genome,
            operator_name=self.name,
            prompt_template_id=self.prompt_template_id,
            seed=seed,
            metadata={
                "source_individual_id": source.individual_id,
                "instruction": self.instruction,
                "source_genome": source.genome.to_dict(),
            },
        )

    def execute(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        generator: ContentGenerator,
        validator: ContentValidator,
        seed: int | None = None,
    ) -> ContentOperationResult:
        request = self.build_request(source, target_genome, seed=seed)
        response = generator.generate(request)
        validation = validator.validate(request, response)
        return ContentOperationResult(self.name, request, response, validation)
