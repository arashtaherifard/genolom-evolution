from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator
from genolom_evolution.content.validators import ContentValidationResult
from genolom_evolution.evolution.session import PriorityEvolutionSession

ROOT = Path(__file__).resolve().parents[1]


class RejectingTestValidator:
    name = "rejecting-test-validator"

    def validate(self, request, response):
        return ContentValidationResult(
            accepted=False,
            reasons=("synthetic_reject",),
            metadata={"not_for_scientific_use": True},
        )


def _session(generation0, toy_ontology):
    pop = [deepcopy(x) for x in generation0[:8]]
    config = load_config(ROOT / "configs" / "development.yaml")
    config["evolution"]["maturity_age"] = 0
    session = PriorityEvolutionSession(pop, config, seed=19)
    session.compute_micro_fitness(toy_ontology)
    return session


def test_archive_library_and_rejected_attempts_are_distinct(generation0, toy_ontology):
    session = _session(generation0, toy_ontology)
    parent = session.population[0]

    accepted_result = session.apply_mutation(parent.individual_id, force_rate=1.0)
    accepted_id = accepted_result.offspring["individual_id"]
    session.apply_content_operator(
        accepted_id,
        operator_name="abstraction",
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
    )

    rejected_result = session.apply_mutation(parent.individual_id, force_rate=1.0)
    rejected_id = rejected_result.offspring["individual_id"]
    session.apply_content_operator(
        rejected_id,
        operator_name="abstraction",
        generator=DeterministicTestGenerator(),
        validator=RejectingTestValidator(),
    )

    summary = session.end_generation()

    assert accepted_id in session.variant_library
    assert accepted_id in session.historical_archive
    assert rejected_id not in session.variant_library
    assert rejected_id not in session.historical_archive
    assert any(x["offspring"]["individual_id"] == rejected_id for x in session.rejected_attempts)
    assert summary["accepted_offspring_count"] == 1
    assert summary["rejected_offspring_count"] == 1
    assert len(session.generation_snapshots) == 1

    snapshot = session.snapshot()
    assert "active_population" in snapshot
    assert "historical_archive" in snapshot
    assert "variant_library" in snapshot
    assert "rejected_attempts" in snapshot
    assert "generation_snapshots" in snapshot
