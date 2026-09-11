from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Protocol, Any

from ...models.individual import Individual
from ...models.genome import GenoLOMGenome
from ..generator import ContentGenerator, GenerationRequest, GenerationResponse
from ..grounding import GroundingContext
from ..planning import compile_proposal_content_plan
from ..proposal_rules import ProposalRuleSet
from ..prompts import (
    DEFAULT_PROMPT_REGISTRY,
    GENOLOM_CONTENT_REPAIR_V1,
    PromptRegistry,
    generation_prompt_id,
)
from ..validators import ContentValidator, ContentValidationResult


MAX_CONTENT_ATTEMPTS = 3


def _request_dict(request: GenerationRequest) -> dict[str, Any]:
    return {
        "source_content": request.source_content,
        "source_genome": None if request.source_genome is None else request.source_genome.to_dict(),
        "target_genome": request.target_genome.to_dict(),
        "content_plan": None if request.content_plan is None else request.content_plan.to_dict(),
        "grounding_context": None if request.grounding_context is None else request.grounding_context.to_dict(),
        "operator_name": request.operator_name,
        "prompt_template_id": request.prompt_template_id,
        "prompt_version": request.prompt_version,
        "prompt_hash": request.prompt_hash,
        "attempt_index": request.attempt_index,
        "validator_feedback": list(request.validator_feedback),
        "previous_candidate_content": request.previous_candidate_content,
        "seed": request.seed,
        "metadata": request.metadata,
    }


def _validation_dict(validation: ContentValidationResult) -> dict[str, Any]:
    return {
        "accepted": validation.accepted,
        "genome_agreement": validation.genome_agreement,
        "faithfulness": validation.faithfulness,
        "factuality": validation.factuality,
        "hallucination_flags": list(validation.hallucination_flags),
        "reasons": list(validation.reasons),
        "metadata": validation.metadata,
        "realized_genome": (
            None if validation.realized_genome is None else validation.realized_genome.to_dict()
        ),
        "retryable": validation.retryable,
        "failure_details": list(validation.failure_details),
    }


@dataclass(frozen=True, slots=True)
class ContentAttempt:
    attempt_index: int
    request: GenerationRequest
    response: GenerationResponse
    validation: ContentValidationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_index": self.attempt_index,
            "request": _request_dict(self.request),
            "response": self.response.to_dict(),
            "validation": _validation_dict(self.validation),
        }


@dataclass(frozen=True, slots=True)
class ContentOperationResult:
    operator_name: str
    request: GenerationRequest
    response: GenerationResponse
    validation: ContentValidationResult
    # M5: exact generated attempts are retained; final request/response/
    # validation above remain for backward compatibility.
    attempts: tuple[ContentAttempt, ...] = ()
    max_attempts: int = 1

    @property
    def accepted(self) -> bool:
        return self.validation.accepted

    @property
    def retries_exhausted(self) -> bool:
        return bool(
            not self.accepted
            and self.validation.retryable
            and len(self.attempts) >= self.max_attempts
        )

    def to_dict(self) -> dict:
        return {
            "operator_name": self.operator_name,
            "request": _request_dict(self.request),
            "response": self.response.to_dict(),
            "validation": _validation_dict(self.validation),
            "attempt_count": len(self.attempts),
            "max_attempts": self.max_attempts,
            "retries_exhausted": self.retries_exhausted,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
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
        generation_info: dict[str, Any] | None = None,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
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
        generation_info: dict[str, Any] | None = None,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
        max_attempts: int = MAX_CONTENT_ATTEMPTS,
    ) -> ContentOperationResult: ...


class BaseContentOperator:
    name = "base"
    # Retained as a legacy/operator-level identifier. M5 GenerationRequest uses
    # the frozen grounded/parametric prompt template ID instead.
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
        generation_info: dict[str, Any] | None = None,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
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
        template = prompt_registry.get(generation_prompt_id(grounding_context.mode))
        return GenerationRequest(
            source_content=source.content,
            target_genome=target_genome,
            operator_name=self.name,
            prompt_template_id=template.template_id,
            seed=seed,
            metadata={
                "source_individual_id": source.individual_id,
                "instruction": self.instruction,
                "source_genome": source.genome.to_dict(),
                "planning_stage": content_plan.planning_stage,
                "planning_status": content_plan.planning_status,
                "grounding_mode": grounding_context.mode,
                "legacy_operator_prompt_template_id": self.prompt_template_id,
                "generation_info": {} if generation_info is None else dict(generation_info),
                "max_attempts": MAX_CONTENT_ATTEMPTS,
            },
            source_genome=source.genome,
            content_plan=content_plan,
            grounding_context=grounding_context,
            prompt_version=template.version,
            prompt_hash=template.prompt_hash,
            attempt_index=1,
        )

    @staticmethod
    def _attempt_seed(base_seed: int | None, attempt_index: int) -> int | None:
        if base_seed is None or attempt_index == 1:
            return base_seed
        payload = f"{base_seed}|content-retry|{attempt_index}".encode("utf-8")
        return int.from_bytes(sha256(payload).digest()[:8], "big") & 0x7FFFFFFF

    @staticmethod
    def _feedback(validation: ContentValidationResult) -> tuple[dict[str, Any], ...]:
        if validation.failure_details:
            return validation.failure_details
        return tuple({"code": reason, "stage": "legacy_validator"} for reason in validation.reasons)

    def _repair_request(
        self,
        previous_request: GenerationRequest,
        previous_response: GenerationResponse,
        previous_validation: ContentValidationResult,
        *,
        attempt_index: int,
        base_seed: int | None,
        prompt_registry: PromptRegistry,
    ) -> GenerationRequest:
        template = prompt_registry.get(GENOLOM_CONTENT_REPAIR_V1)
        return replace(
            previous_request,
            prompt_template_id=template.template_id,
            prompt_version=template.version,
            prompt_hash=template.prompt_hash,
            seed=self._attempt_seed(base_seed, attempt_index),
            attempt_index=attempt_index,
            validator_feedback=self._feedback(previous_validation),
            previous_candidate_content=previous_response.content,
            metadata={
                **previous_request.metadata,
                "repair_attempt": attempt_index,
                "repair_of_attempt": attempt_index - 1,
                "previous_response_status": previous_response.status,
                "previous_validation_reasons": list(previous_validation.reasons),
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
        grounding_context: GroundingContext | None = None,
        planning_rules: ProposalRuleSet | None = None,
        generation_info: dict[str, Any] | None = None,
        prompt_registry: PromptRegistry = DEFAULT_PROMPT_REGISTRY,
        max_attempts: int = MAX_CONTENT_ATTEMPTS,
    ) -> ContentOperationResult:
        if max_attempts < 1 or max_attempts > MAX_CONTENT_ATTEMPTS:
            raise ValueError(f"max_attempts must be between 1 and {MAX_CONTENT_ATTEMPTS}.")

        request = self.build_request(
            source,
            target_genome,
            seed=seed,
            grounding_context=grounding_context,
            planning_rules=planning_rules,
            generation_info=generation_info,
            prompt_registry=prompt_registry,
        )

        # Backward-compatibility is restricted to the explicit deterministic
        # unit-test generator. Pre-M5 operator contract tests expect request
        # prompt IDs such as ``elaboration-v1``. Real scientific/local-LLM runs
        # MUST keep the frozen M5 registry ID/version/hash produced above.
        legacy_test_prompt_contract = bool(
            getattr(generator, "test_only_preserve_legacy_operator_prompt_id", False)
        )
        if legacy_test_prompt_contract:
            scientific_prompt_id = request.prompt_template_id
            scientific_prompt_version = request.prompt_version
            scientific_prompt_hash = request.prompt_hash
            request = replace(
                request,
                prompt_template_id=self.prompt_template_id,
                prompt_version=None,
                prompt_hash=None,
                metadata={
                    **request.metadata,
                    "legacy_operator_prompt_contract": True,
                    "scientific_use_allowed": False,
                    "m5_scientific_prompt_template_id": scientific_prompt_id,
                    "m5_scientific_prompt_version": scientific_prompt_version,
                    "m5_scientific_prompt_hash": scientific_prompt_hash,
                },
            )

        plan = request.content_plan
        plan_blocked = plan is not None and not plan.executable

        # M4 scientific runs must never generate through a blocked proposal plan.
        # The explicit deterministic test double can still exercise M3 state and
        # archive contracts without claiming scientific validity.
        test_only_bypass = bool(
            getattr(generator, "test_only_allow_blocked_plan", False)
        )

        if plan_blocked and not test_only_bypass:
            reasons = tuple(issue.code for issue in plan.issues if issue.blocking)
            response = GenerationResponse(
                content="",
                provider="content-planner",
                model="generation-skipped",
                model_version="m5-v1",
                parameters={},
                raw_metadata={
                    "generation_skipped": True,
                    "planning_status": plan.planning_status,
                },
                status="impossible",
            )
            validation = ContentValidationResult(
                accepted=False,
                reasons=reasons,
                metadata={
                    "planning_blocked": True,
                    "planning_issues": [issue.to_dict() for issue in plan.issues],
                },
                retryable=False,
                failure_details=tuple(
                    {"code": reason, "stage": "content_planning"} for reason in reasons
                ),
            )
            return ContentOperationResult(
                self.name, request, response, validation, (), max_attempts
            )

        if plan_blocked and test_only_bypass:
            request = replace(
                request,
                metadata={
                    **request.metadata,
                    "test_only_planning_bypass": True,
                    "scientific_use_allowed": False,
                },
            )

        attempts: list[ContentAttempt] = []
        current_request = request
        final_response: GenerationResponse | None = None
        final_validation: ContentValidationResult | None = None

        for attempt_index in range(1, max_attempts + 1):
            response = generator.generate(current_request)
            validation = validator.validate(current_request, response)
            attempts.append(ContentAttempt(attempt_index, current_request, response, validation))
            final_response = response
            final_validation = validation

            if validation.accepted:
                break
            if not validation.retryable:
                break
            if attempt_index >= max_attempts:
                break

            current_request = self._repair_request(
                current_request,
                response,
                validation,
                attempt_index=attempt_index + 1,
                base_seed=seed,
                prompt_registry=prompt_registry,
            )

        assert final_response is not None and final_validation is not None
        return ContentOperationResult(
            self.name,
            current_request,
            final_response,
            final_validation,
            tuple(attempts),
            max_attempts,
        )


__all__ = [
    "MAX_CONTENT_ATTEMPTS",
    "ContentAttempt",
    "ContentOperationResult",
    "ContentOperator",
    "BaseContentOperator",
]
