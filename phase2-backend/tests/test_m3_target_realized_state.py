from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.evolution.session import PriorityEvolutionSession
from genolom_evolution.content.testing import (
    DeterministicTestGenerator,
    AcceptingTestValidator,
)

ROOT = Path(__file__).resolve().parents[1]


def _session(generation0, toy_ontology):
    pop = [deepcopy(x) for x in generation0[:8]]
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    session = PriorityEvolutionSession(pop, config, seed=11)
    session.compute_micro_fitness(toy_ontology)
    return session


def test_pending_offspring_keeps_target_separate_from_realized(generation0, toy_ontology):
    session = _session(generation0, toy_ontology)
    parent = session.population[0]
    result = session.apply_mutation(parent.individual_id, force_rate=1.0)
    child_id = result.offspring["individual_id"]
    child = session.pending_offspring[child_id]

    assert child.target_genome is not None
    assert child.realized_genome is None
    assert child.genome == parent.genome


def test_accepted_test_content_promotes_explicit_realized_genome(generation0, toy_ontology):
    session = _session(generation0, toy_ontology)
    parent = session.population[0]
    result = session.apply_mutation(parent.individual_id, force_rate=1.0)
    child_id = result.offspring["individual_id"]

    output = session.apply_content_operator(
        child_id,
        operator_name="abstraction",
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
    )
    child = session.pending_offspring[child_id]

    assert output["acceptance"]["accepted"] is True
    assert child.realized_genome == child.target_genome
    assert child.genome == child.realized_genome
    assert child.extra["content_operation"]["validation"]["metadata"]["not_for_scientific_use"] is True
