from dataclasses import replace

from genolom_evolution.content.grounding import GroundingContext
from genolom_evolution.content.operators.base import BaseContentOperator
from genolom_evolution.content.planning import (
    compile_proposal_content_plan,
    target_realized_direction_mismatches,
)
from genolom_evolution.content.proposal_rules import (
    ProposalRuleSet,
    RULE_PROPOSAL_DEFINED,
    RULE_UNSUPPORTED,
)
from genolom_evolution.content.testing import AcceptingTestValidator, DeterministicTestGenerator
from genolom_evolution.models.genome import GenoLOMGenome
from genolom_evolution.models.individual import Individual


def genome(**changes):
    base = GenoLOMGenome(
        interactivityType="Expositive",
        learningResourceType="Narrative Text",
        interactivityLevel="Low",
        semanticDensity="Medium",
        intendedEndUserRole="Learner",
        context="Higher Education",
        typicalAgeRange="18+",
        difficulty="Medium",
        typicalLearningTime=2.0,
        description="source",
        language="en",
        keywords=("topic",),
    )
    return replace(base, **changes)


def test_narrative_text_semantic_density_increase_compiles_appendix_a_pack():
    plan = compile_proposal_content_plan(
        genome(), genome(semanticDensity="Very High"), operator_name="abstraction"
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("Pack(2)",)
    assert plan.step_specs[0].origin == RULE_PROPOSAL_DEFINED
    assert plan.step_specs[0].proposal_reference == "Proposal Appendix A, p.87"


def test_narrative_text_semantic_density_decrease_is_expand_from_proposal_not_guess():
    plan = compile_proposal_content_plan(
        genome(semanticDensity="Very High"),
        genome(semanticDensity="Low"),
        operator_name="elaboration",
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("Expand(3)",)
    assert plan.step_specs[0].origin == RULE_PROPOSAL_DEFINED


def test_exercise_semantic_density_decrease_uses_unpack_not_generic_expand():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Exercise", semanticDensity="High"),
        genome(learningResourceType="Exercise", semanticDensity="Low"),
        operator_name="elaboration",
    )
    assert plan.executable
    assert plan.proposal_native_steps == (
        "Unpack(hints: text, voice, video, animation)",
    )


def test_hypertext_semantic_density_decrease_compiles_two_proposal_steps():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Hypertext Document", semanticDensity="High"),
        genome(learningResourceType="Hypertext Document", semanticDensity="Low"),
        operator_name="elaboration",
    )
    assert plan.executable
    assert plan.proposal_native_steps == (
        "Expand(2)",
        "Unpack(hints: text, voice, video, animation)",
    )


def test_diagram_semantic_density_increase_is_explicit_nop():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Diagram", semanticDensity="Low"),
        genome(learningResourceType="Diagram", semanticDensity="High"),
        operator_name="abstraction",
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("NOP",)


def test_exercise_difficulty_increase_compiles_cognitive_and_density_steps():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Exercise", difficulty="Easy"),
        genome(learningResourceType="Exercise", difficulty="Very Difficult"),
        operator_name="elaboration",
    )
    assert plan.proposal_native_steps == (
        "Cognitive_Level_up(3)",
        "sdIncrease(3)",
    )


def test_narrative_text_difficulty_increase_uses_only_sd_increase_per_appendix_a():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Narrative Text", difficulty="Easy"),
        genome(learningResourceType="Narrative Text", difficulty="Very Difficult"),
        operator_name="elaboration",
    )
    assert plan.proposal_native_steps == ("sdIncrease(3)",)


def test_diagram_interactivity_increase_compiles_specific_action_set():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Diagram", interactivityLevel="Low"),
        genome(learningResourceType="Diagram", interactivityLevel="High"),
        operator_name="elaboration",
    )
    assert plan.proposal_native_steps == (
        "Add_Actions(Navigation)",
        "Add_Actions(Click)",
        "Add_Actions(Animation)",
        "Add_Actions(Hotspots)",
        "Add_Actions(TextInput)",
    )


def test_question_interactivity_decrease_preserves_proposal_asymmetry():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Question", interactivityLevel="High"),
        genome(learningResourceType="Question", interactivityLevel="Low"),
        operator_name="elaboration",
    )
    assert plan.proposal_native_steps == (
        "Remove_Actions(Adv_Click)",
        "Add_Actions(Animation)",
        "Remove_Actions(Drag&Drop)",
        "Remove_Actions(Adv_Drag&Drop)",
        "Export2HTML()",
    )


def test_exercise_to_question_uses_appendix_b_same_as_rule():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Exercise"),
        genome(learningResourceType="Question"),
        operator_name="probing",
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("is_Same_as()",)
    assert plan.step_specs[0].proposal_reference == "Proposal Appendix B, pp.89-93"


def test_exercise_to_diagram_drop_rule_blocks_realization():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Exercise"),
        genome(learningResourceType="Diagram"),
        operator_name="probing",
    )
    assert not plan.executable
    assert plan.proposal_native_steps == ("Drop()",)
    issue = next(i for i in plan.issues if i.code == "appendix_b_drop_transition")
    assert issue.classification == RULE_PROPOSAL_DEFINED


def test_problem_statement_to_narrative_text_uses_converts_to():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Problem Statement"),
        genome(learningResourceType="Narrative Text"),
        operator_name="elaboration",
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("Converts_to()",)


def test_question_to_narrative_text_is_drop_not_conversion():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Question"),
        genome(learningResourceType="Narrative Text"),
        operator_name="elaboration",
    )
    assert not plan.executable
    assert plan.proposal_native_steps == ("Drop()",)


def test_source_type_without_appendix_b_rule_is_blocked_not_fabricated():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Narrative Text"),
        genome(learningResourceType="Question"),
        operator_name="probing",
    )
    assert not plan.executable
    assert plan.proposal_native_steps == ()
    issue = next(i for i in plan.issues if i.code == "appendix_b_transition_not_defined")
    assert issue.classification == RULE_UNSUPPORTED


def test_source_type_without_appendix_a_row_blocks_ordinal_realization():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Headline", semanticDensity="Medium"),
        genome(learningResourceType="Headline", semanticDensity="High"),
        operator_name="abstraction",
    )
    assert not plan.executable
    issue = next(
        i for i in plan.issues if i.code == "appendix_a_rule_not_defined_for_source_lrt"
    )
    assert issue.classification == RULE_UNSUPPORTED


def test_renderer_gap_is_separate_from_proposal_validity():
    plan = compile_proposal_content_plan(
        genome(learningResourceType="Exercise"),
        genome(learningResourceType="Slide"),
        operator_name="elaboration",
    )
    assert plan.proposal_native_steps == ("Converts_to()",)
    assert not plan.executable
    assert "UNSUPPORTED_REALIZATION" in {i.code for i in plan.issues}


def test_typical_learning_time_is_directional_constraint_not_density_alias():
    plan = compile_proposal_content_plan(
        genome(), genome(typicalLearningTime=4.0), operator_name="elaboration"
    )
    assert plan.executable
    assert plan.proposal_native_steps == ("NOP",)
    assert plan.directional_expectations[0].direction == "increase"

    realized_wrong = genome(typicalLearningTime=1.5)
    assert target_realized_direction_mismatches(plan, realized_wrong) == (
        "typicalLearningTime",
    )
    realized_ok = genome(typicalLearningTime=2.5)
    assert target_realized_direction_mismatches(plan, realized_ok) == ()


def test_fixed_trait_change_is_blocking():
    plan = compile_proposal_content_plan(
        genome(), genome(language="fa"), operator_name="elaboration"
    )
    assert not plan.executable
    assert "fixed_trait_change" in {i.code for i in plan.issues}


class CountingGenerator:
    provider_name = "counting"

    def __init__(self):
        self.calls = 0

    def generate(self, request):
        self.calls += 1
        raise AssertionError("blocked plans must not reach generation")


def test_blocked_plan_skips_generator_entirely():
    source = Individual(
        "LO_1", "source text", genome(learningResourceType="Exercise")
    )
    generator = CountingGenerator()
    result = BaseContentOperator().execute(
        source,
        genome(learningResourceType="Diagram"),
        generator=generator,
        validator=AcceptingTestValidator(),
    )
    assert result.accepted is False
    assert generator.calls == 0
    assert result.response.raw_metadata["generation_skipped"] is True


def test_default_grounding_context_is_parent_only_and_serialized():
    source = Individual(
        "LO_1", "trusted source text", genome(learningResourceType="Exercise")
    )
    request = BaseContentOperator().build_request(
        source,
        genome(learningResourceType="Question"),
    )
    assert isinstance(request.grounding_context, GroundingContext)
    assert request.grounding_context.mode == "grounded"
    assert request.grounding_context.source_ids == ("LO_1",)
    assert request.grounding_context.evidence[0].text == "trusted source text"


def test_m3_structural_planner_remains_backward_compatible():
    from genolom_evolution.content.planning import compile_structural_content_plan

    plan = compile_structural_content_plan(
        genome(), genome(semanticDensity="High"), operator_name="mutation"
    )
    assert plan.planning_stage == "m3_structural_only"
    assert plan.proposal_native_steps == ()
    assert plan.step_specs == ()
    assert plan.issues == ()
    assert plan.to_dict()["proposal_native_compilation"] == "deferred_to_milestone_4"


def test_interactivity_type_only_change_is_constraint_not_invented_operation():
    plan = compile_proposal_content_plan(
        genome(), genome(interactivityType="Mixed"), operator_name="elaboration"
    )
    assert plan.executable
    assert plan.proposal_native_steps == ()
    issue = next(i for i in plan.issues if i.field == "interactivityType")
    assert issue.code == "interactivity_type_target_constraint_only"
    assert issue.blocking is False


class CapturingGenerator:
    provider_name = "capture"

    def __init__(self):
        self.requests = []

    def generate(self, request):
        from genolom_evolution.content.generator import GenerationResponse

        self.requests.append(request)
        return GenerationResponse(
            content="generated candidate",
            provider=self.provider_name,
            model="deterministic-capture",
            model_version="test",
            parameters={},
            raw_metadata={"not_for_scientific_use": True},
        )


def test_executable_plan_reaches_generator_with_exact_proposal_plan_and_grounding():
    source = Individual("LO_1", "trusted source text", genome())
    generator = CapturingGenerator()
    result = BaseContentOperator().execute(
        source,
        genome(semanticDensity="High"),
        generator=generator,
        validator=AcceptingTestValidator(),
    )
    assert result.accepted is True
    assert len(generator.requests) == 1
    request = generator.requests[0]
    assert request.content_plan.planning_stage == "m4_proposal_exact_v2"
    assert request.content_plan.proposal_native_steps == ("Pack(1)",)
    assert request.grounding_context.mode == "grounded"
    assert request.grounding_context.source_ids == ("LO_1",)



def test_explicit_deterministic_test_double_preserves_m3_orchestration_on_blocked_plan():
    """Blocked proposal plans stay blocked scientifically but M3 test plumbing still runs.

    Headline has no Appendix-A row. A normal/scientific generator is therefore
    skipped, while the explicit deterministic test double may pass through so
    session/archive behavior can be tested independently of realization support.
    """
    source = Individual(
        "LO_TEST_COMPAT",
        "A heading-like source",
        genome(learningResourceType="Headline", semanticDensity="Medium"),
    )
    result = BaseContentOperator().execute(
        source,
        genome(learningResourceType="Headline", semanticDensity="High"),
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
    )
    assert result.accepted is True
    assert result.request.content_plan.executable is False
    assert result.request.metadata["test_only_planning_bypass"] is True
    assert result.request.metadata["scientific_use_allowed"] is False
    assert result.response.raw_metadata["not_for_scientific_use"] is True
