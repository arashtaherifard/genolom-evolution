from copy import deepcopy

from genolom_evolution.evolution.composition import (
    COMPOUND_FORMAT_VERSION,
    compose_individuals,
    recover_composition_components,
)
from genolom_evolution.models.individual import Individual


def test_composition_preserves_component_content_and_boundaries(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    result = compose_individuals([a, b], roles=["explanation", "example"])
    assert result.content.startswith(f"[{COMPOUND_FORMAT_VERSION}]")
    assert len(result.components) == 2
    for component in result.components:
        assert (
            result.content[component.rendered_content_start:component.rendered_content_end]
            == component.content
        )
    assert result.components[0].content in result.content
    assert result.components[1].content in result.content
    assert result.provenance["our_operationalization"][-1] == "no LLM rewriting"


def test_composition_uses_source_row_order_when_safely_available(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[9])
    # Force same source identity and reverse selection order.
    a.source_type = b.source_type = "chapter"
    a.source_page = b.source_page = "1"
    a.source_row_id = "9"
    b.source_row_id = "10"
    result = compose_individuals([b, a])
    assert [c.source_parent_id for c in result.components] == [a.individual_id, b.individual_id]


def test_composition_falls_back_to_selection_order_when_source_order_not_comparable(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    result = compose_individuals([b, a])
    assert [c.source_parent_id for c in result.components] == [b.individual_id, a.individual_id]


def test_composition_requires_distinct_multiple_parents(generation0):
    import pytest

    a = deepcopy(generation0[8])
    with pytest.raises(ValueError, match="at least two"):
        compose_individuals([a])
    with pytest.raises(ValueError, match="distinct"):
        compose_individuals([a, a])


def test_decomposition_rejects_non_composition_parent(generation0):
    result = recover_composition_components(deepcopy(generation0[8]))
    assert not result.success
    assert result.reasons == ("not_composition_derived",)


def test_decomposition_recovers_exact_stored_components(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    composition = compose_individuals([a, b])
    compound = Individual(
        individual_id="G1_LO_TEST",
        content=composition.content,
        genome=composition.container_genome,
        generation_created=1,
        parent_ids=(a.individual_id, b.individual_id),
        created_by="composition",
        content_status="accepted",
        extra={"composition": composition.to_dict()},
    )
    result = recover_composition_components(compound)
    assert result.success
    assert [c.content for c in result.components] == [c.content for c in composition.components]
    assert [c.genome for c in result.components] == [c.genome for c in composition.components]
