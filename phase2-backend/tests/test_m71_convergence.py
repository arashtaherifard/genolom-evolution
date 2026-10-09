from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.dataio.generation0 import load_generation0
from genolom_evolution.evaluation.convergence import (
    ConvergencePolicy,
    evaluate_convergence,
)
from genolom_evolution.experiments.genome_evolution import CompleteGenomeEvolutionRunner

ROOT = Path(__file__).resolve().parents[1]


class ExactKeywordOntology:
    name = "exact-keyword-test-ontology"

    def __init__(self, known):
        self.known = set(known)

    def resolve_topic(self, topic):
        value = str(topic).strip()
        return value if value in self.known else None

    def undirected_distance(self, a, b):
        a, b = self.resolve_topic(a), self.resolve_topic(b)
        if a is None or b is None:
            return None
        return 0 if a == b else 1

    def ancestor_distance(self, a, b):
        a, b = self.resolve_topic(a), self.resolve_topic(b)
        if a is None or b is None:
            return None
        return 0 if a == b else None

    def hierarchy_path(self, a, b):
        return (a,) if a == b and self.resolve_topic(a) is not None else None


def _row(generation, fitness, population, unique_ratio, recall):
    return {
        "generation": generation,
        "mean_micro_fitness": fitness,
        "population_size": population,
        "unique_genome_ratio": unique_ratio,
        "recall": recall,
    }


def test_frozen_convergence_rule_requires_all_four_conditions():
    policy = ConvergencePolicy(
        enabled=True,
        stop_on_convergence=True,
        minimum_generation=10,
        window_generations=5,
        mean_micro_fitness_range_max=0.01,
        population_relative_range_max=0.05,
        unique_genome_ratio_range_max=0.02,
        recall_range_max=0.02,
    )
    rows = [
        _row(6, 0.950, 1000, 0.20, 0.50),
        _row(7, 0.954, 1010, 0.19, 0.49),
        _row(8, 0.956, 1005, 0.19, 0.49),
        _row(9, 0.957, 1015, 0.19, 0.50),
        _row(10, 0.958, 1008, 0.19, 0.49),
    ]
    check = evaluate_convergence(rows, policy)
    assert check is not None
    assert check.converged
    assert check.window_start == 6
    assert check.window_end == 10

    drifting_recall = deepcopy(rows)
    drifting_recall[-1]["recall"] = 0.45
    check = evaluate_convergence(drifting_recall, policy)
    assert check is not None
    assert check.fitness_stable
    assert check.population_stable
    assert check.unique_genome_ratio_stable
    assert not check.recall_stable
    assert not check.converged


def test_runner_stops_on_convergence_when_enabled(tmp_path):
    generation0 = load_generation0(ROOT / "data" / "generation_0.xlsx")
    known = {keyword for item in generation0 for keyword in item.genome.keywords}
    ontology = ExactKeywordOntology(known)
    config = load_config(ROOT / "configs" / "genome_evolution_development.yaml")
    config["outputs"]["root"] = str(tmp_path)
    config["genome_evolution"]["attempt_budget"] = {
        "mode": "fixed", "value": 1, "minimum": 0, "maximum": None
    }
    config["evolution"]["convergence"] = {
        "enabled": True,
        "stop_on_convergence": True,
        "minimum_generation": 1,
        "window_generations": 2,
        "mean_micro_fitness_range_max": 999.0,
        "population_relative_range_max": 999.0,
        "unique_genome_ratio_range_max": 999.0,
        "recall_range_max": 999.0,
    }

    result = CompleteGenomeEvolutionRunner(config, ontology).run(
        ROOT, generation_count=5, seed=77, run_id="m71-stop-test"
    )

    assert result.completed_final_generation == 1
    assert result.requested_final_generation == 5
    assert result.stop_reason == "convergence"
    assert result.convergence_generation == 1
    run = Path(result.run_path)
    assert (run / "convergence/result.json").exists()
    assert (run / "metrics/convergence_windows.csv").exists()
