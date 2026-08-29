from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from ..dataio.generation0 import load_generation0
from ..dataio.manifest import load_manifest, verify_manifest_dataset
from ..validation.genome_validator import validate_genome
from ..evaluation.independent import evaluate_population
from ..evaluation.coverage import calculate_coverage
from ..fitness.micro import calculate_micro_fitness
from ..selection.fitness_proportionate import FitnessProportionateSelection
from ..selection.random_selection import RandomSelection
from ..tracking.run_store import RunStore


class ExperimentRunner:
    def __init__(self, config: dict, ontology=None):
        self.config = deepcopy(config)
        self.ontology = ontology

    def initial_analysis(self, project_root: str | Path) -> dict:
        root = Path(project_root)
        dataset = root / self.config["dataset"]["path"]
        manifest_path = root / self.config["dataset"]["manifest"]
        manifest = load_manifest(manifest_path)
        checksum_ok = verify_manifest_dataset(manifest_path, dataset)
        population = load_generation0(dataset)
        issues = {i.individual_id: [x.to_dict() for x in validate_genome(i.genome)] for i in population}
        issues = {k: v for k, v in issues.items() if v}

        coverage = None
        if self.ontology is not None:
            fcfg = self.config["micro_fitness"]
            dependence_weight = fcfg.get("dependence_weight", fcfg.get("coherence_weight", 0.5))
            for individual in population:
                result = calculate_micro_fitness(
                    individual.genome.keywords,
                    self.ontology,
                    cohesion_weight=float(fcfg["cohesion_weight"]),
                    dependence_weight=float(dependence_weight),
                )
                individual.cohesion = result.cohesion
                individual.dependence = result.dependence
                individual.micro_fitness = result.fitness

            strategy_name = self.config["selection"]["strategy"]
            strategy = RandomSelection() if strategy_name == "random" else FitnessProportionateSelection()
            probs = strategy.probabilities(population)
            for individual, prob in zip(population, probs):
                individual.selection_probability = prob

            if hasattr(self.ontology, "reference_topics"):
                coverage = calculate_coverage(
                    population,
                    self.ontology,
                    coverage_threshold=int(self.config.get("coverage", {}).get("threshold", 1)),
                ).to_dict()

        return {
            "dataset": manifest,
            "checksum_ok": checksum_ok,
            "population_size": len(population),
            "validation_issue_count": sum(len(v) for v in issues.values()),
            "invalid_individual_count": len(issues),
            "validation_issues": issues,
            "independent_evaluation": evaluate_population(population),
            "micro_fitness_computed": self.ontology is not None,
            "coverage": coverage,
            "population": population,
        }

    def persist_initial_analysis(self, project_root: str | Path) -> Path:
        result = self.initial_analysis(project_root)
        root = Path(project_root)
        store = RunStore(root / self.config["outputs"]["root"])
        serializable = {k: v for k, v in result.items() if k != "population"}
        store.write_json_once("config_snapshot.json", self.config)
        store.write_json_once("initial_analysis.json", serializable)
        return store.path
