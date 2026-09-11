from copy import deepcopy
from pathlib import Path

import pytest

from genolom_evolution.config import load_config
from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator
from genolom_evolution.evolution.fusion_defusion import fuse_genomes, recover_defusion_components
from genolom_evolution.evolution.session import PriorityEvolutionSession
from genolom_evolution.models.individual import Individual

ROOT = Path(__file__).resolve().parents[1]


def _session_with_compatible_pair(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    for parent in (a, b):
        parent.age = 1
        parent.micro_fitness = 1.0
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    return PriorityEvolutionSession([a, b], config, seed=31), a, b


def test_session_fusion_creates_pending_target_and_records_history(generation0):
    session, a, b = _session_with_compatible_pair(generation0)
    out = session.apply_fusion(a.individual_id, b.individual_id, binary_operator="AND")
    assert len(out.offspring) == 1
    child_id = out.offspring[0]["individual_id"]
    child = session.pending_offspring[child_id]
    assert child.created_by == "fusion"
    assert child.content_status == "pending_generation"
    assert child.target_genome is not None
    assert child.realized_genome is None
    assert child.extra["requires_structural_content_realizer"] is True
    assert a.fusion_count == b.fusion_count == child.fusion_count == 1
    assert set(session.lineage.parents[child_id]) == {a.individual_id, b.individual_id}


def test_generic_single_source_content_operator_cannot_fake_fusion_realization(generation0):
    session, a, b = _session_with_compatible_pair(generation0)
    out = session.apply_fusion(a.individual_id, b.individual_id, binary_operator="AND")
    child_id = out.offspring[0]["individual_id"]
    with pytest.raises(ValueError, match="dedicated structural content realizer"):
        session.apply_content_operator(
            child_id,
            operator_name="abstraction",
            generator=DeterministicTestGenerator(),
            validator=AcceptingTestValidator(),
        )


def test_session_fusion_failure_creates_no_child(generation0):
    session, a, b = _session_with_compatible_pair(generation0)
    out = session.apply_fusion(a.individual_id, b.individual_id, binary_operator="XOR")
    assert out.offspring == ()
    assert not out.operator_result["success"]
    assert not session.pending_offspring
    assert session.lineage.events[-1].event_type == "fusion_failed"


def test_session_fusion_threshold_is_enforced(generation0):
    session, a, b = _session_with_compatible_pair(generation0)
    session.config["evolution"]["fusion_defusion"]["threshold"]["maximum"] = 0
    with pytest.raises(ValueError, match="threshold"):
        session.apply_fusion(a.individual_id, b.individual_id, binary_operator="AND")


def test_defusion_recovers_stored_fusion_targets_only(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    fusion = fuse_genomes(a, b, binary_operator="AND")
    assert fusion.success and fusion.target_genome is not None
    fused = Individual(
        individual_id="G1_LO_FUSED",
        content="fused realized content",
        genome=fusion.target_genome,
        generation_created=1,
        parent_ids=(a.individual_id, b.individual_id),
        created_by="fusion",
        content_status="accepted",
        extra={"fusion_provenance": fusion.provenance},
    )
    result = recover_defusion_components(fused)
    assert result.success
    assert [c.source_parent_id for c in result.components] == [a.individual_id, b.individual_id]
    assert result.components[0].target_genome == a.genome
    assert result.components[1].target_genome == b.genome


def test_session_composition_and_decomposition_are_deterministic(generation0):
    session, a, b = _session_with_compatible_pair(generation0)
    composed = session.apply_composition(
        [a.individual_id, b.individual_id], roles=["explanation", "example"]
    )
    compound_id = composed.offspring[0]["individual_id"]
    compound = session.pending_offspring[compound_id]
    assert compound.content_status == "accepted"
    assert compound.extra["not_llm_rewritten"] is True

    # Promote accepted structural artifact into the active population.
    session.end_generation()
    compound = session._find(compound_id, include_pending=False)
    compound.micro_fitness = 1.0
    session.config["evolution"]["maturity_age"] = 0

    decomposed = session.apply_decomposition(compound_id)
    assert len(decomposed.offspring) == 2
    children = [session.pending_offspring[item["individual_id"]] for item in decomposed.offspring]
    assert [child.content for child in children] == [a.content, b.content]
    assert all(child.content_status == "accepted" for child in children)
    assert all(child.extra["not_llm_rewritten"] is True for child in children)
    assert all(session.lineage.parents[child.individual_id] == (compound_id,) for child in children)


def test_session_defusion_creates_pending_targets_from_stored_provenance(generation0):
    a, b = deepcopy(generation0[8]), deepcopy(generation0[48])
    fusion = fuse_genomes(a, b, binary_operator="AND")
    assert fusion.success and fusion.target_genome is not None
    fused = Individual(
        individual_id="G1_LO_FUSED_SESSION",
        content="realized fused content",
        genome=fusion.target_genome,
        generation_created=1,
        parent_ids=(a.individual_id, b.individual_id),
        created_by="fusion",
        content_status="accepted",
        extra={"fusion_provenance": fusion.provenance},
    )
    fused.age = 1
    fused.micro_fitness = 1.0
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    session = PriorityEvolutionSession([fused], config, seed=41)

    out = session.apply_defusion(fused.individual_id)
    assert len(out.offspring) == 2
    children = [session.pending_offspring[item["individual_id"]] for item in out.offspring]
    assert all(child.created_by == "defusion" for child in children)
    assert all(child.content_status == "pending_generation" for child in children)
    assert children[0].target_genome == a.genome
    assert children[1].target_genome == b.genome
    assert fused.defusion_count == 1
