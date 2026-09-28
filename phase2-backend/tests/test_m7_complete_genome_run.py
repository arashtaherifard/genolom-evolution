from copy import deepcopy
from pathlib import Path

from genolom_evolution.config import load_config
from genolom_evolution.dataio.generation0 import load_generation0
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


def test_complete_runner_exports_generations_archive_library_and_lineage(tmp_path):
    generation0 = load_generation0(ROOT / "data" / "generation_0.xlsx")
    known = {keyword for item in generation0 for keyword in item.genome.keywords}
    ontology = ExactKeywordOntology(known)
    config = load_config(ROOT / "configs" / "genome_evolution_development.yaml")
    config["outputs"]["root"] = str(tmp_path)
    config["genome_evolution"]["attempt_budget"] = {
        "mode": "fixed", "value": 8, "minimum": 0, "maximum": None
    }
    config["genome_evolution"]["operator_weights"] = {
        "mutation": 0.5,
        "crossover": 0.5,
        "fusion": 0.0,
        "defusion": 0.0,
        "composition": 0.0,
        "decomposition": 0.0,
    }
    config["evolution"]["mutation"]["rate"] = 1.0
    config["evolution"]["crossover"]["rate"] = 1.0
    config["evolution"]["maturity_age"] = 0
    config["evolution"]["longevity"]["initial_chance"] = 20.0

    result = CompleteGenomeEvolutionRunner(config, ontology).run(
        ROOT, generation_count=2, seed=77, run_id="m7-test"
    )
    run = Path(result.run_path)
    assert result.completed_final_generation == 2
    assert not result.extinct
    assert (run / "generations/generation_0000.json").exists()
    assert (run / "generations/generation_0001.json").exists()
    assert (run / "generations/generation_0002.json").exists()
    assert (run / "final_generation.jsonl").exists()
    assert (run / "archive/genome_archive.jsonl").exists()
    assert (run / "library/genome_library.jsonl").exists()
    assert (run / "lineage/nodes.csv").exists()
    assert (run / "lineage/edges.csv").exists()
    assert (run / "lineage/lineage.graphml").exists()
    assert (run / "metrics/generation_metrics.csv").exists()
    assert (run / "metrics/coherency_rank.csv").exists()
    assert (run / "logs/evolution_events.jsonl").exists()
    assert (run / "checksums.json").exists()
