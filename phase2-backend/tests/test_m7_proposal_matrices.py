from genolom_evolution.evolution.proposal_matrices import (
    METAMORPHOSIS_RESOURCE_TYPES,
    is_metamorphosis_allowed,
    metamorphosis_targets,
    is_composition_allowed,
    are_composition_parents_compatible,
)


def test_figure14_selected_directed_cells_match_proposal():
    assert is_metamorphosis_allowed("Simulation", "Video Clip")
    assert is_metamorphosis_allowed("Narrative Text", "Problem Statement")
    assert is_metamorphosis_allowed("Headline", "Hypertext Document")
    assert is_metamorphosis_allowed("Diagram", "Table")
    assert not is_metamorphosis_allowed("Narrative Text", "Question")
    assert not is_metamorphosis_allowed("Problem Statement", "Narrative Text")
    assert not is_metamorphosis_allowed("Question", "Exercise")


def test_figure14_unknown_types_are_not_invented():
    assert not is_metamorphosis_allowed("Lecture", "Narrative Text")
    assert metamorphosis_targets("Authoring Tool") == ()


def test_figure15_all_displayed_pairs_are_composable():
    for left in METAMORPHOSIS_RESOURCE_TYPES:
        for right in METAMORPHOSIS_RESOURCE_TYPES:
            assert is_composition_allowed(left, right)
    assert are_composition_parents_compatible(
        ["Narrative Text", "Figure", "Question"]
    )
    assert not are_composition_parents_compatible(["Narrative Text", "Lecture"])
