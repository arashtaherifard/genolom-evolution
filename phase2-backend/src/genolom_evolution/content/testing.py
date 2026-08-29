"""Deterministic test doubles for local/unit tests only.

These are intentionally unsuitable for final paper experiments. They let the
backend and future UI exercise the complete content-operator contract without
requiring network credentials or a particular model provider.
"""
from __future__ import annotations
from .generator import GenerationRequest, GenerationResponse
from .validators import ContentValidationResult


class DeterministicTestGenerator:
    provider_name = "deterministic-test"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        prefix = {
            "abstraction": "[ABSTRACTED] ",
            "elaboration": "[ELABORATED] ",
            "probing": "[PROBING] ",
        }.get(request.operator_name, "[GENERATED] ")
        return GenerationResponse(
            content=prefix + request.source_content,
            provider=self.provider_name,
            model="test-double",
            model_version="1",
            parameters={"seed": request.seed},
            raw_metadata={"not_for_scientific_use": True},
        )


class AcceptingTestValidator:
    name = "accepting-test-validator"

    def validate(self, request: GenerationRequest, response: GenerationResponse) -> ContentValidationResult:
        accepted = bool(response.content.strip())
        return ContentValidationResult(
            accepted=accepted,
            genome_agreement=1.0 if accepted else 0.0,
            faithfulness=1.0 if accepted else 0.0,
            factuality=None,
            reasons=() if accepted else ("empty_content",),
            metadata={"not_for_scientific_use": True},
        )
