from dataclasses import replace

from genolom_evolution.content.generator import LocalLLMGenerator
from genolom_evolution.content.grounding import GroundingContext
from genolom_evolution.content.operators import AbstractionOperator
from genolom_evolution.content.prompts import (
    GENOLOM_CONTENT_GENERATOR_GROUNDED_V1,
    GENOLOM_CONTENT_REPAIR_V1,
)
from genolom_evolution.content.testing import RecordingLocalBackend
from genolom_evolution.content.validators import ContentValidationResult
from genolom_evolution.models.genome import GenoLOMGenome
from genolom_evolution.models.individual import Individual


def genome():
    return GenoLOMGenome(
        interactivityType="Expositive",
        learningResourceType="Narrative Text",
        interactivityLevel="Low",
        semanticDensity="Medium",
        intendedEndUserRole="Learner",
        context="Higher Education",
        typicalAgeRange="18+",
        difficulty="Medium",
        typicalLearningTime=2.0,
        description="Computer science studies computation.",
        language="English (en)",
        keywords=("computer science",),
    )


def source_individual():
    g = genome()
    return Individual("G0_LO_001", "Computer science studies computation.", g)


def test_local_generator_parses_strict_structured_json_and_logs_prompt_identity():
    backend = RecordingLocalBackend([
        {"status": "ok", "content": "Computer science studies computation.", "added_claims": [], "notes": []}
    ])
    generator = LocalLLMGenerator(backend)
    request = AbstractionOperator().build_request(source_individual(), genome(), seed=7)
    response = generator.generate(request)
    assert response.status == "ok"
    assert response.content.startswith("Computer science")
    assert response.raw_metadata["prompt_template_id"] == GENOLOM_CONTENT_GENERATOR_GROUNDED_V1
    assert response.raw_metadata["prompt_hash"] == request.prompt_hash
    assert "target_genome" in backend.prompts[0]  # generator intentionally sees target


def test_grounded_generator_cannot_return_added_claims():
    backend = RecordingLocalBackend([
        {"status": "ok", "content": "New content.", "added_claims": ["New fact"], "notes": []}
    ])
    generator = LocalLLMGenerator(backend)
    response = generator.generate(
        AbstractionOperator().build_request(source_individual(), genome(), seed=7)
    )
    assert response.status == "malformed"


class _RetryingValidator:
    name = "retrying-test-validator"

    def __init__(self, target):
        self.calls = 0
        self.target = target

    def validate(self, request, response):
        self.calls += 1
        if self.calls < 3:
            return ContentValidationResult(
                accepted=False,
                reasons=(f"repair_me_{self.calls}",),
                retryable=True,
                failure_details=(
                    {"code": f"repair_me_{self.calls}", "stage": "test"},
                ),
            )
        return ContentValidationResult(
            accepted=True,
            reasons=(),
            realized_genome=self.target,
        )


def test_frozen_retry_policy_is_three_attempts_with_repair_prompt_and_deterministic_seeds():
    backend = RecordingLocalBackend([
        {"status": "ok", "content": "Attempt one content.", "added_claims": [], "notes": []},
        {"status": "ok", "content": "Attempt two content.", "added_claims": [], "notes": []},
        {"status": "ok", "content": "Computer science studies computation.", "added_claims": [], "notes": []},
    ])
    generator = LocalLLMGenerator(backend)
    target = genome()
    result = AbstractionOperator().execute(
        source_individual(),
        target,
        generator=generator,
        validator=_RetryingValidator(target),
        seed=1234,
    )
    assert result.accepted is True
    assert len(result.attempts) == 3
    assert result.attempts[0].request.prompt_template_id == GENOLOM_CONTENT_GENERATOR_GROUNDED_V1
    assert result.attempts[1].request.prompt_template_id == GENOLOM_CONTENT_REPAIR_V1
    assert result.attempts[2].request.prompt_template_id == GENOLOM_CONTENT_REPAIR_V1
    assert result.attempts[1].request.validator_feedback[0]["code"] == "repair_me_1"
    assert result.attempts[1].request.previous_candidate_content == "Attempt one content."
    assert len(set(backend.seeds)) == 3
    assert result.to_dict()["attempt_count"] == 3


class _AlwaysRetryValidator:
    name = "always-retry-test-validator"
    def validate(self, request, response):
        return ContentValidationResult(
            accepted=False,
            reasons=("still_invalid",),
            retryable=True,
            failure_details=({"code": "still_invalid", "stage": "test"},),
        )


def test_retry_loop_never_exceeds_frozen_three_attempt_maximum():
    backend = RecordingLocalBackend([
        {"status": "ok", "content": "one", "added_claims": [], "notes": []},
        {"status": "ok", "content": "two", "added_claims": [], "notes": []},
        {"status": "ok", "content": "three", "added_claims": [], "notes": []},
    ])
    result = AbstractionOperator().execute(
        source_individual(), genome(),
        generator=LocalLLMGenerator(backend),
        validator=_AlwaysRetryValidator(),
        seed=44,
    )
    assert result.accepted is False
    assert len(result.attempts) == 3
    assert result.retries_exhausted is True
    assert result.to_dict()["retries_exhausted"] is True


def test_deterministic_test_generator_preserves_legacy_operator_prompt_contract():
    from genolom_evolution.content.operators import ElaborationOperator
    from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator

    result = ElaborationOperator().execute(
        source_individual(),
        genome(),
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
        seed=17,
    )
    assert result.accepted is True
    assert result.request.prompt_template_id == "elaboration-v1"
    assert result.request.prompt_version is None
    assert result.request.prompt_hash is None
    assert result.request.metadata["legacy_operator_prompt_contract"] is True
    assert result.request.metadata["scientific_use_allowed"] is False
    assert (
        result.request.metadata["m5_scientific_prompt_template_id"]
        == GENOLOM_CONTENT_GENERATOR_GROUNDED_V1
    )


def test_local_llm_execution_still_uses_frozen_m5_prompt_identity():
    from genolom_evolution.content.testing import AcceptingTestValidator

    backend = RecordingLocalBackend([
        {"status": "ok", "content": "Computer science studies computation.", "added_claims": [], "notes": []}
    ])
    result = AbstractionOperator().execute(
        source_individual(),
        genome(),
        generator=LocalLLMGenerator(backend),
        validator=AcceptingTestValidator(),
        seed=18,
    )
    # The real/local-LLM path must remain on the registered M5 scientific prompt.
    assert result.attempts[0].request.prompt_template_id == GENOLOM_CONTENT_GENERATOR_GROUNDED_V1
    assert result.attempts[0].request.prompt_version == "1"
    assert result.attempts[0].request.prompt_hash is not None
