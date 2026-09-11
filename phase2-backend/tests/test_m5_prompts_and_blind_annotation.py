from dataclasses import replace

from genolom_evolution.content.annotation import (
    build_blind_annotation_request,
    reconcile_realized_genome,
    MetadataAnnotation,
)
from genolom_evolution.content.prompts import (
    DEFAULT_PROMPT_REGISTRY,
    GENOLOM_CONTENT_GENERATOR_GROUNDED_V1,
    GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1,
    GENOLOM_REALIZED_GENOME_ANNOTATOR_V1,
    GENOLOM_CLAIM_JUDGE_V1,
    GENOLOM_CONTENT_REPAIR_V1,
    GENOLOM_DIRECT_LLM_BASELINE_V1,
)
from genolom_evolution.models.genome import GenoLOMGenome


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


def test_frozen_prompt_registry_contains_all_six_required_templates():
    expected = {
        GENOLOM_CONTENT_GENERATOR_GROUNDED_V1,
        GENOLOM_CONTENT_GENERATOR_PARAMETRIC_V1,
        GENOLOM_REALIZED_GENOME_ANNOTATOR_V1,
        GENOLOM_CLAIM_JUDGE_V1,
        GENOLOM_CONTENT_REPAIR_V1,
        GENOLOM_DIRECT_LLM_BASELINE_V1,
    }
    registry = DEFAULT_PROMPT_REGISTRY.to_dict()
    assert set(registry) == expected
    for item in registry.values():
        assert item["prompt_version"] == "1"
        assert len(item["prompt_hash"]) == 64
        assert item["origin"] == "OUR_OPERATIONALIZATION"


def test_blind_annotation_request_structurally_has_no_target_genome():
    request = build_blind_annotation_request(
        "Computer science studies computation.", source_id="G0_LO_001"
    )
    assert not hasattr(request, "target_genome")
    payload = request.to_prompt_payload()
    assert "target_genome" not in payload
    assert "target" not in str(payload).lower()
    assert request.prompt_template_id == GENOLOM_REALIZED_GENOME_ANNOTATOR_V1


def test_realized_keywords_are_reextracted_not_copied_from_source_or_target():
    source = genome(keywords=("old-source-keyword",))
    annotation = MetadataAnnotation(
        learningResourceType="Narrative Text",
        interactivityType="Expositive",
        interactivityLevel="Low",
        semanticDensity="Medium",
        difficulty="Medium",
        typicalLearningTime=2.0,
        provider="test",
        model="test",
    )
    request = build_blind_annotation_request(
        "Algorithms organize computational procedures and algorithms solve problems.",
        source_id="G0_LO_001",
    )
    realized, _ = reconcile_realized_genome(
        source_genome=source,
        candidate_content=request.candidate_content,
        annotation=annotation,
        deterministic_features=request.deterministic_features,
    )
    assert "old-source-keyword" not in realized.keywords
    assert "algorithms" in realized.keywords


def test_direct_llm_baseline_request_contains_no_evolutionary_target():
    from genolom_evolution.content.generator import build_direct_baseline_request
    request = build_direct_baseline_request(
        "Computer science studies computation.", source_id="G0_LO_001", seed=5
    )
    assert not hasattr(request, "target_genome")
    assert "target_genome" not in request.to_prompt_payload()
    assert request.prompt_template_id == GENOLOM_DIRECT_LLM_BASELINE_V1


def test_local_llm_annotator_prompt_never_contains_target_genome():
    from genolom_evolution.content.annotation import LocalLLMAnnotator
    from genolom_evolution.content.testing import RecordingLocalBackend

    backend = RecordingLocalBackend([
        {
            "learningResourceType": "Narrative Text",
            "interactivityType": "Expositive",
            "interactivityLevel": "Low",
            "semanticDensity": "Medium",
            "difficulty": "Medium",
            "typicalLearningTime": 2.0,
        }
    ])
    request = build_blind_annotation_request(
        "Computer science studies computation.", source_id="G0_LO_001"
    )
    annotation = LocalLLMAnnotator(backend).annotate(request)
    assert annotation.learningResourceType == "Narrative Text"
    assert "target_genome" not in backend.prompts[0]
