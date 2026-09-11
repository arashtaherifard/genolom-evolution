from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Protocol

from ...models.individual import Individual
from ...models.genome import GenoLOMGenome
from ..generator import ContentGenerator, GenerationRequest, GenerationResponse
from ..grounding import GroundingContext
from ..planning import compile_proposal_content_plan
from ..proposal_rules import ProposalRuleSet
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
                "source_genome": None if self.request.source_genome is None else self.request.source_genome.to_dict(),
                "target_genome": self.request.target_genome.to_dict(),
                "content_plan": None if self.request.content_plan is None else self.request.content_plan.to_dict(),
                "grounding_context": None if self.request.grounding_context is None else self.request.grounding_context.to_dict(),
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
                "realized_genome": (
                    None
                    if self.validation.realized_genome is None
                    else self.validation.realized_genome.to_dict()
                ),
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
        grounding_context: GroundingContext | None = None,
        planning_rules: ProposalRuleSet | None = None,
    ) -> GenerationRequest: ...

    def execute(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        generator: ContentGenerator,
        validator: ContentValidator,
        seed: int | None = None,
        grounding_context: GroundingContext | None = None,
        planning_rules: ProposalRuleSet | None = None,
    ) -> ContentOperationResult: ...


class BaseContentOperator:
    name = "base"
    prompt_template_id = "base-v1"
    instruction = "Transform the source learning object to match the target GenoLOM genome."

    def build_request(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        seed: int | None = None,
        grounding_context: GroundingContext | None = None,
        planning_rules: ProposalRuleSet | None = None,
    ) -> GenerationRequest:
        content_plan = compile_proposal_content_plan(
            source.genome,
            target_genome,
            operator_name=self.name,
            rules=planning_rules,
        )
        if grounding_context is None:
            grounding_context = GroundingContext.from_source(
                source.individual_id, source.content
            )
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
                "planning_stage": content_plan.planning_stage,
                "planning_status": content_plan.planning_status,
                "grounding_mode": grounding_context.mode,
            },
            source_genome=source.genome,
            content_plan=content_plan,
            grounding_context=grounding_context,
        )

    def execute(
        self,
        source: Individual,
        target_genome: GenoLOMGenome,
        *,
        generator: ContentGenerator,
        validator: ContentValidator,
        seed: int | None = None,
        grounding_context: GroundingContext | None = None,
        planning_rules: ProposalRuleSet | None = None,
    ) -> ContentOperationResult:
        request = self.build_request(
            source,
            target_genome,
            seed=seed,
            grounding_context=grounding_context,
            planning_rules=planning_rules,
        )
        plan = request.content_plan
        plan_blocked = plan is not None and not plan.executable

        # M4 scientific runs must never generate through a blocked proposal plan.
        # The only exception is the explicit deterministic unit-test double used
        # by the pre-existing M3/session tests. That test double never produces
        # scientific output and intentionally assumes target realization so the
        # orchestration/archive contracts can be tested independently of the
        # proposal realization capability. Keeping this as an explicit opt-in
        # flag avoids weakening the production gate or keying behavior to a class
        # name/provider string.
        test_only_bypass = bool(
            getattr(generator, "test_only_allow_blocked_plan", False)
        )

        if plan_blocked and not test_only_bypass:
            reasons = tuple(issue.code for issue in plan.issues if issue.blocking)
            response = GenerationResponse(
                content="",
                provider="content-planner",
                model="generation-skipped",
                model_version="m4-v1",
                parameters={},
                raw_metadata={
                    "generation_skipped": True,
                    "planning_status": plan.planning_status,
                },
            )
            validation = ContentValidationResult(
                accepted=False,
                reasons=reasons,
                metadata={
                    "planning_blocked": True,
                    "planning_issues": [issue.to_dict() for issue in plan.issues],
                },
            )
            return ContentOperationResult(self.name, request, response, validation)

        if plan_blocked and test_only_bypass:
            request = replace(
                request,
                metadata={
                    **request.metadata,
                    "test_only_planning_bypass": True,
                    "scientific_use_allowed": False,
                },
            )

        response = generator.generate(request)
        validation = validator.validate(request, response)
        return ContentOperationResult(self.name, request, response, validation)
