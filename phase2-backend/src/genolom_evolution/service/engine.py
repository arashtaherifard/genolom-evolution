from __future__ import annotations
from pathlib import Path
import random

from ..config import load_config
from ..dataio.generation0 import load_generation0
from ..dataio.manifest import load_manifest, verify_manifest_dataset
from ..validation.genome_validator import validate_genome
from ..evaluation.independent import evaluate_population
from ..evaluation.coverage import calculate_coverage
from ..fitness.micro import calculate_micro_fitness
from ..evolution.eligibility import check_parent_eligibility
from ..evolution.mutation import mutate_individual
from ..evolution.crossover import crossover_individuals
from ..evolution.fusion_defusion import FusionDefusionThreshold
from ..evolution.session import PriorityEvolutionSession
from ..content.operators import AbstractionOperator, ElaborationOperator, ProbingOperator
from .dto import ServiceResult


class Phase2Engine:
    """Stable, JSON-serializable backend boundary intended for Phase 3 UI/API.

    Core evolution modules remain UI-independent. This facade exposes query,
    preview, and stateful session operations without leaking internal classes to
    the presentation layer.
    """

    def __init__(
        self,
        project_root: str | Path,
        config_path: str | Path = "configs/default.yaml",
        *,
        ontology=None,
        content_generator=None,
        content_validator=None,
    ):
        self.project_root = Path(project_root).resolve()
        self.config = load_config(self.project_root / config_path)
        self.ontology = ontology
        self.content_generator = content_generator
        self.content_validator = content_validator
        self._population = None
        self._session: PriorityEvolutionSession | None = None

    def capabilities(self) -> dict:
        return {
            "phase": 2,
            "milestone": "priority-blue-rows",
            "implemented": [
                "generation0_loading",
                "dataset_checksum",
                "proposal_validation",
                "cohesion",
                "dependence_proxy",
                "micro_fitness",
                "coverage_span",
                "coverage_threshold",
                "coverage_rate_dependency",
                "parent_eligibility",
                "maturity_age_dependency",
                "fitness_proportionate_selection",
                "random_selection_baseline",
                "mutation_rules",
                "mutation_rate",
                "mutation_execution",
                "crossover_rules",
                "crossover_rate",
                "crossover_execution",
                "target_genome_validation",
                "offspring_creation",
                "abstraction_operator",
                "elaboration_operator",
                "probing_operator",
                "age",
                "longevity_chance",
                "perish",
                "fusion_history",
                "defusion_history",
                "fusion_defusion_threshold",
                "fusion_execution",
                "defusion_execution",
                "composition",
                "decomposition",
                "operator_events",
                "lineage",
                "immutable_run_store",
            ],
            "deferred_but_hooked": [
                "fusion_defusion_content_realization_m5b",
                "unstructured_multimedia_decomposition",
                "expert_metric_validation",
                "held_out_chapters",
                "additional_textbooks",
                "additional_domains_ontologies",
                "expert_content_evaluation",
                "inter_rater_reliability",
                "learner_study",
            ],
            "ui_contract_version": "1.2",
        }

    def _load(self):
        if self._population is None:
            path = self.project_root / self.config["dataset"]["path"]
            self._population = load_generation0(path)
        return self._population

    def _get_ontology(self):
        if self.ontology is None:
            from ..ontology.cso_adapter import CSOOntologyAdapter
            self.ontology = CSOOntologyAdapter(
                root_topic=self.config.get("coverage", {}).get("reference_root", "computer science")
            )
        return self.ontology

    def _get_individual_obj(self, individual_id: str):
        for individual in self._load():
            if individual.individual_id == individual_id:
                return individual
        return None

    def dataset_info(self) -> ServiceResult:
        manifest_path = self.project_root / self.config["dataset"]["manifest"]
        dataset_path = self.project_root / self.config["dataset"]["path"]
        manifest = load_manifest(manifest_path)
        return ServiceResult(True, {
            "manifest": manifest,
            "checksum_ok": verify_manifest_dataset(manifest_path, dataset_path),
        })

    def preflight(self) -> ServiceResult:
        population = self._load()
        invalid = []
        for i in population:
            issues = validate_genome(i.genome)
            if issues:
                invalid.append({"individual_id": i.individual_id, "issues": [x.to_dict() for x in issues]})
        return ServiceResult(True, {
            "population_size": len(population),
            "invalid_individual_count": len(invalid),
            "invalid_individuals": invalid,
            "evaluation": evaluate_population(population),
        })

    def population_summary(self) -> ServiceResult:
        return ServiceResult(True, evaluate_population(self._load()))

    def get_individual(self, individual_id: str) -> ServiceResult:
        individual = self._get_individual_obj(individual_id)
        if individual is not None:
            return ServiceResult(True, individual.to_dict())
        if self._session is not None and individual_id in self._session.pending_offspring:
            return ServiceResult(True, self._session.pending_offspring[individual_id].to_dict())
        return ServiceResult(False, None, ({"code": "not_found", "message": f"Unknown individual {individual_id}"},))

    def compute_priority_metrics(self) -> ServiceResult:
        try:
            ontology = self._get_ontology()
            fcfg = self.config["micro_fitness"]
            dependence_weight = fcfg.get("dependence_weight", fcfg.get("coherence_weight", 0.5))
            rows = []
            for individual in self._load():
                r = calculate_micro_fitness(
                    individual.genome.keywords,
                    ontology,
                    cohesion_weight=float(fcfg["cohesion_weight"]),
                    dependence_weight=float(dependence_weight),
                )
                individual.cohesion = r.cohesion
                individual.dependence = r.dependence
                individual.micro_fitness = r.fitness
                rows.append({"individual_id": individual.individual_id, **r.to_dict()})
            coverage = calculate_coverage(
                self._load(), ontology,
                coverage_threshold=int(self.config.get("coverage", {}).get("threshold", 1)),
            )
            return ServiceResult(True, {
                "individual_metrics": rows,
                "coverage": coverage.to_dict(),
            })
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "metric_error", "message": str(exc)},))

    def eligibility(self, individual_id: str, operator: str) -> ServiceResult:
        individual = self._get_individual_obj(individual_id)
        if individual is None:
            return ServiceResult(False, None, ({"code": "not_found", "message": f"Unknown individual {individual_id}"},))
        ecfg = self.config.get("evolution", {})
        result = check_parent_eligibility(
            individual,
            operator=operator,
            maturity_age=ecfg.get("maturity_age"),
            max_parent_participations_per_generation=ecfg.get("max_parent_participations_per_generation"),
        )
        return ServiceResult(True, result.to_dict())

    def preview_mutation(self, individual_id: str, *, rate: float = 1.0, seed: int | None = None) -> ServiceResult:
        individual = self._get_individual_obj(individual_id)
        if individual is None:
            return ServiceResult(False, None, ({"code": "not_found", "message": f"Unknown individual {individual_id}"},))
        result = mutate_individual(individual, rate=rate, rng=random.Random(self.config["reproducibility"]["seed"] if seed is None else seed))
        return ServiceResult(True, result.to_dict())

    def preview_crossover(self, parent_a_id: str, parent_b_id: str, *, rate: float = 1.0, seed: int | None = None) -> ServiceResult:
        a = self._get_individual_obj(parent_a_id)
        b = self._get_individual_obj(parent_b_id)
        if a is None or b is None:
            missing = [x for x, obj in ((parent_a_id, a), (parent_b_id, b)) if obj is None]
            return ServiceResult(False, None, ({"code": "not_found", "message": f"Unknown parent(s): {missing}"},))
        result = crossover_individuals(a, b, rate=rate, rng=random.Random(self.config["reproducibility"]["seed"] if seed is None else seed))
        return ServiceResult(True, result.to_dict())

    def fusion_defusion_status(self, individual_id: str) -> ServiceResult:
        individual = self._get_individual_obj(individual_id)
        if individual is None:
            return ServiceResult(False, None, ({"code": "not_found", "message": f"Unknown individual {individual_id}"},))
        threshold_cfg = self.config.get("evolution", {}).get("fusion_defusion", {}).get("threshold", {})
        policy = FusionDefusionThreshold(
            minimum=int(threshold_cfg.get("minimum", 0)),
            maximum=None if threshold_cfg.get("maximum") is None else int(threshold_cfg["maximum"]),
        )
        return ServiceResult(True, {
            "individual_id": individual_id,
            "fusion_history": list(individual.fusion_history),
            "defusion_history": list(individual.defusion_history),
            "fusion_count": individual.fusion_count,
            "defusion_count": individual.defusion_count,
            "threshold": policy.to_dict(),
            "can_fuse": policy.can_fuse(individual),
            "can_defuse": policy.can_defuse(individual),
            "note": "M6 executes proposal-traceable Fusion targets and provenance-based V1 Defusion. Real Fusion/Defusion content realization remains deferred to M5B.",
        })

    def content_operator_contracts(self) -> ServiceResult:
        operators = [AbstractionOperator(), ElaborationOperator(), ProbingOperator()]
        return ServiceResult(True, [
            {
                "name": op.name,
                "prompt_template_id": op.prompt_template_id,
                "instruction": op.instruction,
                "requires_generator": True,
                "requires_validator": True,
            }
            for op in operators
        ])

    def start_priority_session(self, *, seed: int | None = None) -> ServiceResult:
        # Session uses the loaded population objects intentionally so the UI can
        # observe changes through the same service facade.
        self._session = PriorityEvolutionSession(self._load(), self.config, seed=seed)
        return ServiceResult(True, {
            "seed": self._session.seed,
            "generation": self._session.generation,
            "population_size": len(self._session.population),
        })

    def session_apply_mutation(self, parent_id: str, *, force_rate: float | None = None) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(True, self._session.apply_mutation(parent_id, force_rate=force_rate).to_dict())
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "mutation_error", "message": str(exc)},))

    def session_apply_crossover(self, parent_a_id: str, parent_b_id: str, *, force_rate: float | None = None) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(True, self._session.apply_crossover(parent_a_id, parent_b_id, force_rate=force_rate).to_dict())
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "crossover_error", "message": str(exc)},))

    def session_apply_fusion(
        self,
        parent_a_id: str,
        parent_b_id: str,
        *,
        binary_operator: str = "AND",
    ) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(
                True,
                self._session.apply_fusion(
                    parent_a_id, parent_b_id, binary_operator=binary_operator
                ).to_dict(),
            )
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "fusion_error", "message": str(exc)},))

    def session_apply_defusion(self, fused_id: str) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(True, self._session.apply_defusion(fused_id).to_dict())
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "defusion_error", "message": str(exc)},))

    def session_apply_composition(
        self,
        parent_ids: list[str] | tuple[str, ...],
        *,
        roles: list[str] | tuple[str, ...] | None = None,
    ) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(
                True,
                self._session.apply_composition(parent_ids, roles=roles).to_dict(),
            )
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "composition_error", "message": str(exc)},))

    def session_apply_decomposition(self, compound_id: str) -> ServiceResult:
        if self._session is None:
            self.start_priority_session()
        try:
            return ServiceResult(
                True, self._session.apply_decomposition(compound_id).to_dict()
            )
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "decomposition_error", "message": str(exc)},))

    def session_lineage(self, individual_id: str) -> ServiceResult:
        if self._session is None:
            return ServiceResult(False, None, ({"code": "session_not_started", "message": "Start a priority session first."},))
        return ServiceResult(True, self._session.lineage_for(individual_id))
    def session_apply_content_operator(self, child_id: str, operator_name: str, *, seed: int | None = None) -> ServiceResult:
        if self._session is None:
            return ServiceResult(False, None, ({"code": "session_not_started", "message": "Start a priority session first."},))
        if self.content_generator is None or self.content_validator is None:
            return ServiceResult(False, None, ({
                "code": "content_backend_not_configured",
                "message": "A ContentGenerator and ContentValidator must be injected into the backend service before content execution.",
            },))
        try:
            data = self._session.apply_content_operator(
                child_id,
                operator_name=operator_name,
                generator=self.content_generator,
                validator=self.content_validator,
                seed=seed,
            )
            return ServiceResult(True, data)
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "content_operator_error", "message": str(exc)},))

    def session_snapshot(self) -> ServiceResult:
        if self._session is None:
            return ServiceResult(False, None, ({"code": "session_not_started", "message": "Start a priority session first."},))
        return ServiceResult(True, self._session.snapshot())

    def session_end_generation(self) -> ServiceResult:
        if self._session is None:
            return ServiceResult(False, None, ({"code": "session_not_started", "message": "Start a priority session first."},))
        try:
            return ServiceResult(True, self._session.end_generation())
        except Exception as exc:
            return ServiceResult(False, None, ({"code": "generation_transition_error", "message": str(exc)},))

