from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.evolution.session import PriorityEvolutionSession

ROOT = Path(__file__).resolve().parents[1]


def test_genome_only_mutation_enters_population_without_content(generation0, toy_ontology):
    config = load_config(ROOT / "configs" / "genome_evolution_development.yaml")
    config["evolution"]["maturity_age"] = 0
    config["evolution"]["mutation"]["rate"] = 1.0
    config["evolution"]["longevity"]["initial_chance"] = 10.0
    parent = deepcopy(generation0[0])
    session = PriorityEvolutionSession([parent], config, seed=12)
    session.compute_micro_fitness(toy_ontology)

    # Parent 0 is a Headline; Figure 14 now makes Hypertext Document a valid
    # genetic metamorphosis target even though Appendix B has no realization rule.
    result = session.apply_mutation(parent.individual_id, force_rate=1.0)
    assert result.offspring is not None
    child_id = result.offspring["individual_id"]
    child = session.pending_offspring[child_id]
    assert child.content_status == "unrealized"
    assert child.content == ""
    assert child.realized_genome is None
    assert child.genome == child.target_genome

    session.end_generation()
    assert any(item.individual_id == child_id for item in session.active_population)
