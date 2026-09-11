from copy import deepcopy
from dataclasses import replace

from genolom_evolution.content.planning import (
    GenomeDiff,
    compile_structural_content_plan,
)


def test_genome_diff_uses_frozen_ordinal_distance(generation0):
    source = deepcopy(generation0[0].genome)
    levels = ("Very Low", "Low", "Medium", "High", "Very High")
    source_index = levels.index(source.semanticDensity)
    target_index = source_index + 1 if source_index < len(levels) - 1 else source_index - 1
    target = replace(source, semanticDensity=levels[target_index])

    diff = GenomeDiff.between(source, target)
    change = diff.change_for("semanticDensity")

    assert change is not None
    assert change.steps == 1
    assert change.ordinal_delta == target_index - source_index
    assert change.direction == ("increase" if target_index > source_index else "decrease")


def test_m3_content_plan_is_structural_and_does_not_invent_m4_rules(generation0):
    source = deepcopy(generation0[0].genome)
    levels = ("Very Low", "Low", "Medium", "High", "Very High")
    source_index = levels.index(source.semanticDensity)
    target_index = source_index + 1 if source_index < len(levels) - 1 else source_index - 1
    target = replace(source, semanticDensity=levels[target_index])

    plan = compile_structural_content_plan(
        source,
        target,
        operator_name="abstraction",
    )

    assert plan.controlled_traits == ("semanticDensity",)
    assert plan.proposal_native_steps == ()
    assert plan.planning_stage == "m3_structural_only"
    assert plan.to_dict()["proposal_native_compilation"] == "deferred_to_milestone_4"
