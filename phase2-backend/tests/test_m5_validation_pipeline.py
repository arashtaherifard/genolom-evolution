from dataclasses import replace

from genolom_evolution.content.annotation import MetadataAnnotation
from genolom_evolution.content.generator import GenerationResponse
from genolom_evolution.content.judging import (
    CONTRADICTED,
    CONTRADICTION,
    NLIResult,
)
from genolom_evolution.content.operators import AbstractionOperator
from genolom_evolution.content.testing import (
    ConstantTopicSimilarity,
    DeterministicTestAnnotator,
    EntailingTestNLI,
    SupportedTestJudge,
)
from genolom_evolution.content.validation_pipeline import (
    ScientificContentValidator,
    TopicSimilarityCalibration,
)
from genolom_evolution.models.genome import GenoLOMGenome
from genolom_evolution.models.individual import Individual


def genome(**changes):
    base = dict(
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
    base.update(changes)
    return GenoLOMGenome(**base)


def request_for(target=None):
    source_g = genome()
    source = Individual("G0_LO_001", "Computer science studies computation.", source_g)
    return AbstractionOperator().build_request(source, target or source_g, seed=99)


def response(content="Computer science studies computation."):
    return GenerationResponse(
        content=content,
        provider="test",
        model="test",
        raw_metadata={"not_for_scientific_use": True},
        status="ok",
    )


def validator(annotation_genome=None, *, topic_score=0.95, nli=None, judge=None, self_judge=None):
    g = annotation_genome or genome()
    return ScientificContentValidator(
        annotator=DeterministicTestAnnotator(g),
        topic_similarity=ConstantTopicSimilarity(topic_score),
        topic_calibration=TopicSimilarityCalibration(0.8, "pilot-v1"),
        nli_analyzer=nli or EntailingTestNLI(),
        independent_judge=judge or SupportedTestJudge(),
        self_judge=self_judge,
    )


def test_scientific_pipeline_accepts_only_after_all_ordered_gates_pass():
    result = validator().validate(request_for(), response())
    assert result.accepted is True
    assert result.realized_genome is not None
    assert result.genome_agreement == 1.0
    assert result.faithfulness == 0.95
    assert result.factuality == 1.0
    assert result.metadata["gating_strategy"] == "ordered_gates_no_weighted_average"
    # Critical: serialized blind annotation request has no target.
    assert "target_genome" not in result.metadata["annotation_request"]


def test_target_realized_mismatch_is_retryable_and_not_silently_promoted():
    target = genome(semanticDensity="High")
    # Blind annotator independently observes Medium, not the target High.
    result = validator(genome(semanticDensity="Medium")).validate(
        request_for(target), response()
    )
    assert result.accepted is False
    assert result.retryable is True
    assert "target_realized_mismatch:semanticDensity" in result.reasons
    assert result.realized_genome.semanticDensity == "Medium"


class _ContradictingNLI:
    name = "contradicting-test-nli"

    def evaluate(self, evidence, claim):
        return NLIResult(label=CONTRADICTION, score=1.0, model="test")


def test_nli_contradiction_is_a_gate_not_a_weighted_score():
    result = validator(nli=_ContradictingNLI()).validate(request_for(), response())
    assert result.accepted is False
    assert "nli_contradiction" in result.reasons
    assert "nli_contradiction" in result.hallucination_flags


def test_self_judge_is_diagnostic_only_and_cannot_reject():
    result = validator(
        self_judge=SupportedTestJudge(label=CONTRADICTED)
    ).validate(request_for(), response())
    assert result.accepted is True
    assert result.metadata["self_judge_diagnostic"]["overall_label"] == CONTRADICTED


def test_topic_threshold_must_come_from_frozen_pilot_calibration():
    try:
        TopicSimilarityCalibration(0.8, "", frozen=True)
    except ValueError:
        pass
    else:
        raise AssertionError("missing pilot_set_id must fail")

    try:
        TopicSimilarityCalibration(0.8, "pilot", frozen=False)
    except ValueError:
        pass
    else:
        raise AssertionError("unfrozen threshold must fail")


def test_generator_impossible_is_terminal_not_retried():
    result = validator().validate(
        request_for(),
        GenerationResponse(
            content="",
            provider="test",
            model="test",
            status="impossible",
        ),
    )
    assert result.accepted is False
    assert result.retryable is False
    assert result.reasons == ("generator_impossible",)
