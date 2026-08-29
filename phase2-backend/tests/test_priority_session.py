from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.evolution.session import PriorityEvolutionSession
from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator

ROOT = Path(__file__).resolve().parents[1]


def _session(generation0, toy_ontology):
    pop = [deepcopy(x) for x in generation0[:8]]
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    s = PriorityEvolutionSession(pop, config, seed=11)
    s.compute_micro_fitness(toy_ontology)
    return s


def test_session_mutation_creates_pending_offspring_and_lineage(generation0, toy_ontology):
    s = _session(generation0, toy_ontology)
    parent = s.population[0]
    r = s.apply_mutation(parent.individual_id, force_rate=1.0)
    assert r.offspring is not None
    child_id = r.offspring["individual_id"]
    assert child_id in s.pending_offspring
    assert s.pending_offspring[child_id].content_status == "pending_generation"
    assert parent.individual_id in s.lineage.ancestors_of(child_id)


def test_session_content_acceptance_marks_viable_and_rewards_parent(generation0, toy_ontology):
    s = _session(generation0, toy_ontology)
    parent = s.population[0]
    r = s.apply_mutation(parent.individual_id, force_rate=1.0)
    child_id = r.offspring["individual_id"]
    out = s.apply_content_operator(
        child_id,
        operator_name="abstraction",
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
    )
    assert out["offspring"]["content_status"] == "accepted"
    assert s.successful_parent_participations[parent.individual_id] == 1
    summary = s.end_generation()
    assert summary["accepted_offspring_count"] == 1
    assert any(x.individual_id == child_id for x in s.population)


def test_session_crossover_creates_two_parent_lineage(generation0, toy_ontology):
    s = _session(generation0, toy_ontology)
    a, b = s.population[0], s.population[1]
    r = s.apply_crossover(a.individual_id, b.individual_id, force_rate=1.0)
    assert r.offspring is not None
    child_id = r.offspring["individual_id"]
    assert set(s.lineage.parents[child_id]) == {a.individual_id, b.individual_id}


def test_generation_transition_rejects_unvalidated_pending_offspring(generation0, toy_ontology):
    import pytest
    s = _session(generation0, toy_ontology)
    parent = s.population[0]
    r = s.apply_mutation(parent.individual_id, force_rate=1.0)
    assert r.offspring is not None
    with pytest.raises(ValueError, match="pending content validation"):
        s.end_generation()


def test_session_rejects_same_parent_crossover(generation0, toy_ontology):
    import pytest
    s = _session(generation0, toy_ontology)
    p = s.population[0]
    with pytest.raises(ValueError, match="distinct"):
        s.apply_crossover(p.individual_id, p.individual_id, force_rate=1.0)
