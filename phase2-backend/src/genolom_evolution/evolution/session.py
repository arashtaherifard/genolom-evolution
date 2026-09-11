from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import random
from typing import Any, Sequence

from ..content.operators import get_content_operator
from ..content.planning import (
    target_realized_mismatches,
    target_realized_direction_mismatches,
)
from ..experiments.seeding import derive_event_seed
from ..fitness.micro import calculate_micro_fitness
from ..models.individual import Individual
from ..models.genome_roles import RealizedGenome
from ..selection.parent_pool import select_parents, ParentSelectionResult
from ..tracking.events import EvolutionEvent
from ..tracking.lineage import LineageTracker
from ..validation.config_validator import (
    validate_mutation_runtime_config,
    validate_crossover_runtime_config,
    validate_lifecycle_runtime_config,
)
from .crossover import crossover_individuals, CrossoverResult
from .eligibility import check_parent_eligibility
from .lifecycle import (
    LongevityPolicy,
    initialize_longevity,
    age_survivors,
    update_longevity_end_of_generation,
    apply_perish,
    reset_generation_state,
)
from .mutation import mutate_individual, MutationResult
from .offspring import OffspringIdAllocator, create_offspring
from .dna import FusionBinaryOperator
from .fusion_defusion import (
    FusionDefusionThreshold,
    fuse_genomes,
    recover_defusion_components,
    record_fusion_participation,
    record_defusion_participation,
)
from .composition import compose_individuals, recover_composition_components


@dataclass(frozen=True, slots=True)
class AppliedOperatorResult:
    operator: str
    operator_result: dict[str, Any]
    offspring: dict[str, Any] | None
    event: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator": self.operator,
            "operator_result": self.operator_result,
            "offspring": self.offspring,
            "event": self.event,
        }


@dataclass(frozen=True, slots=True)
class AppliedStructuralOperatorResult:
    operator: str
    operator_result: dict[str, Any]
    offspring: tuple[dict[str, Any], ...]
    event: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator": self.operator,
            "operator_result": self.operator_result,
            "offspring": [dict(item) for item in self.offspring],
            "event": self.event,
        }


class PriorityEvolutionSession:
    """Stateful Phase-2 session behind the UI/service layer.

    M3 keeps the existing priority genetic workflow but adds explicit separation
    between evolutionary intent (target genome) and realized artifact metadata,
    plus generation snapshots, archive/library state and rejected-attempt logs.

    Provider-specific generation remains injected through interfaces. No UI
    dependency exists here.
    """

    def __init__(self, population: Sequence[Individual], config: dict, *, seed: int | None = None):
        self.population: list[Individual] = list(population)
        self.pending_offspring: dict[str, Individual] = {}
        self.config = config
        self.seed = int(config.get("reproducibility", {}).get("seed", 42) if seed is None else seed)

        # Evolutionary randomness remains independent of content randomness.
        self.evolution_rng = random.Random(self.seed)
        self.rng = self.evolution_rng  # backward-compatible alias

        self.generation = max((i.generation_created for i in self.population), default=0)
        self.allocator = OffspringIdAllocator(self.generation + 1)
        self.lineage = LineageTracker()
        self.successful_parent_participations: Counter[str] = Counter()

        # Distinct M3 state surfaces.
        self.historical_archive: dict[str, dict[str, Any]] = {
            i.individual_id: deepcopy(i.to_dict()) for i in self.population
        }
        self.variant_library: dict[str, dict[str, Any]] = {
            i.individual_id: deepcopy(i.to_dict())
            for i in self.population
            if i.generation_created > 0 and i.content_status == "accepted"
        }
        self.rejected_attempts: list[dict[str, Any]] = []
        self.generation_snapshots: list[dict[str, Any]] = []

    @property
    def active_population(self) -> list[Individual]:
        return [
            individual
            for individual in self.population
            if individual.alive and individual.content_status == "accepted"
        ]

    def _find(self, individual_id: str, *, include_pending: bool = True) -> Individual:
        for individual in self.population:
            if individual.individual_id == individual_id:
                return individual
        if include_pending and individual_id in self.pending_offspring:
            return self.pending_offspring[individual_id]
        raise KeyError(individual_id)

    def _content_seed(self, child_id: str, operator_name: str) -> int:
        return derive_event_seed(
            self.seed,
            self.generation + 1,
            child_id,
            operator_name,
            "content_realization",
        )

    def compute_micro_fitness(self, ontology) -> dict[str, dict[str, float]]:
        cfg = self.config["micro_fitness"]
        dependence_weight = cfg.get("dependence_weight", cfg.get("coherence_weight", 0.5))
        out: dict[str, dict[str, float]] = {}
        for individual in self.population:
            if not individual.alive or individual.content_status != "accepted":
                continue
            result = calculate_micro_fitness(
                individual.genome.keywords,
                ontology,
                cohesion_weight=float(cfg["cohesion_weight"]),
                dependence_weight=float(dependence_weight),
            )
            individual.cohesion = result.cohesion
            individual.dependence = result.dependence
            individual.micro_fitness = result.fitness
            out[individual.individual_id] = result.to_dict()
        return out

    def eligibility(self, individual_id: str, *, operator: str) -> dict[str, Any]:
        individual = self._find(individual_id, include_pending=False)
        ecfg = self.config.get("evolution", {})
        return check_parent_eligibility(
            individual,
            operator=operator,
            maturity_age=ecfg.get("maturity_age"),
            max_parent_participations_per_generation=ecfg.get(
                "max_parent_participations_per_generation"
            ),
        ).to_dict()

    def select(self, *, operator: str, count: int) -> ParentSelectionResult:
        ecfg = self.config["evolution"]
        scfg = self.config["selection"]
        return select_parents(
            self.population,
            operator=operator,
            count=count,
            rng=self.evolution_rng,
            strategy=scfg.get("strategy", "fitness_proportionate"),
            maturity_age=ecfg.get("maturity_age"),
            max_parent_participations_per_generation=ecfg.get(
                "max_parent_participations_per_generation"
            ),
            repeated_parent_selection=bool(scfg.get("repeated_parent_selection", True)),
        )

    def apply_mutation(self, parent_id: str, *, force_rate: float | None = None) -> AppliedOperatorResult:
        if force_rate is None:
            validate_mutation_runtime_config(self.config)
        parent = self._find(parent_id, include_pending=False)
        eligibility = self.eligibility(parent_id, operator="mutation")
        if not eligibility["eligible"]:
            raise ValueError(
                f"Parent {parent_id} is not eligible for mutation: {eligibility['reasons']}"
            )
        rate = float(
            self.config["evolution"]["mutation"]["rate"]
            if force_rate is None
            else force_rate
        )
        result: MutationResult = mutate_individual(
            parent,
            rate=rate,
            rng=self.evolution_rng,
        )
        parent.generation_participations += 1
        if not result.applied:
            event = EvolutionEvent(
                event_type="mutation_not_applied",
                generation=self.generation + 1,
                parent_ids=(parent_id,),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedOperatorResult(
                "mutation", result.to_dict(), None, event.to_dict()
            )

        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=(parent_id,),
            created_by="mutation",
            target_genome=result.target_genome,
            source_genome=parent.genome,
            content=parent.content,
            content_status="pending_generation",
            source_type=parent.source_type,
            source_page=parent.source_page,
            source_row_id=parent.source_row_id,
        )
        child.extra.update(
            {
                "source_parent_id": parent_id,
                "genetic_operator": "mutation",
                "mutation": result.to_dict(),
            }
        )
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="mutation",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=(parent_id,),
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        return AppliedOperatorResult(
            "mutation", result.to_dict(), child.to_dict(), event.to_dict()
        )

    def apply_crossover(
        self,
        parent_a_id: str,
        parent_b_id: str,
        *,
        force_rate: float | None = None,
    ) -> AppliedOperatorResult:
        if force_rate is None:
            validate_crossover_runtime_config(self.config)
        if parent_a_id == parent_b_id:
            raise ValueError("Crossover requires two distinct parent individuals.")
        a = self._find(parent_a_id, include_pending=False)
        b = self._find(parent_b_id, include_pending=False)
        for parent in (a, b):
            eligibility = self.eligibility(parent.individual_id, operator="crossover")
            if not eligibility["eligible"]:
                raise ValueError(
                    f"Parent {parent.individual_id} is not eligible for crossover: "
                    f"{eligibility['reasons']}"
                )
        rate = float(
            self.config["evolution"]["crossover"]["rate"]
            if force_rate is None
            else force_rate
        )
        result: CrossoverResult = crossover_individuals(
            a,
            b,
            rate=rate,
            rng=self.evolution_rng,
        )
        a.generation_participations += 1
        b.generation_participations += 1
        if not result.applied:
            event = EvolutionEvent(
                event_type="crossover_not_applied",
                generation=self.generation + 1,
                parent_ids=(parent_a_id, parent_b_id),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedOperatorResult(
                "crossover", result.to_dict(), None, event.to_dict()
            )

        base = self._find(result.base_parent_id, include_pending=False)
        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=(parent_a_id, parent_b_id),
            created_by="crossover",
            target_genome=result.target_genome,
            source_genome=base.genome,
            content=base.content,
            content_status="pending_generation",
            source_type=base.source_type,
            source_page=base.source_page,
            source_row_id=base.source_row_id,
        )
        child.extra.update(
            {
                "source_parent_id": base.individual_id,
                "genetic_operator": "crossover",
                "crossover": result.to_dict(),
            }
        )
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="crossover",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=(parent_a_id, parent_b_id),
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        return AppliedOperatorResult(
            "crossover", result.to_dict(), child.to_dict(), event.to_dict()
        )

    def _fusion_defusion_policy(self) -> FusionDefusionThreshold:
        threshold_cfg = (
            self.config.get("evolution", {})
            .get("fusion_defusion", {})
            .get("threshold", {})
        )
        return FusionDefusionThreshold(
            minimum=int(threshold_cfg.get("minimum", 0)),
            maximum=(
                None
                if threshold_cfg.get("maximum") is None
                else int(threshold_cfg["maximum"])
            ),
        )

    def apply_fusion(
        self,
        parent_a_id: str,
        parent_b_id: str,
        *,
        binary_operator: str | FusionBinaryOperator = FusionBinaryOperator.AND,
    ) -> AppliedStructuralOperatorResult:
        if parent_a_id == parent_b_id:
            raise ValueError("Fusion requires two distinct parent individuals.")
        a = self._find(parent_a_id, include_pending=False)
        b = self._find(parent_b_id, include_pending=False)
        for parent in (a, b):
            eligibility = self.eligibility(parent.individual_id, operator="fusion")
            if not eligibility["eligible"]:
                raise ValueError(
                    f"Parent {parent.individual_id} is not eligible for fusion: "
                    f"{eligibility['reasons']}"
                )

        policy = self._fusion_defusion_policy()
        if not policy.can_fuse(a) or not policy.can_fuse(b):
            raise ValueError("Fusion threshold does not allow another fusion participation.")

        a.generation_participations += 1
        b.generation_participations += 1
        result = fuse_genomes(a, b, binary_operator=binary_operator)
        if not result.success or result.target_genome is None:
            event = EvolutionEvent(
                event_type="fusion_failed",
                generation=self.generation + 1,
                parent_ids=(parent_a_id, parent_b_id),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedStructuralOperatorResult(
                "fusion", result.to_dict(), (), event.to_dict()
            )

        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=(parent_a_id, parent_b_id),
            created_by="fusion",
            target_genome=result.target_genome,
            source_genome=a.genome,
            content=a.content,
            content_status="pending_generation",
        )
        child.extra.update(
            {
                "structural_operator": "fusion",
                "source_parent_ids": [parent_a_id, parent_b_id],
                "fusion": result.to_dict(),
                "fusion_provenance": deepcopy(result.provenance or {}),
                "requires_structural_content_realizer": True,
            }
        )
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="fusion_target_created",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=(parent_a_id, parent_b_id),
            payload=result.to_dict(),
        )
        record_fusion_participation(a, event.event_id, policy)
        record_fusion_participation(b, event.event_id, policy)
        record_fusion_participation(child, event.event_id, policy)
        self.lineage.record(event)
        return AppliedStructuralOperatorResult(
            "fusion", result.to_dict(), (child.to_dict(),), event.to_dict()
        )

    def apply_defusion(self, fused_id: str) -> AppliedStructuralOperatorResult:
        fused = self._find(fused_id, include_pending=False)
        eligibility = self.eligibility(fused_id, operator="defusion")
        if not eligibility["eligible"]:
            raise ValueError(
                f"Parent {fused_id} is not eligible for defusion: {eligibility['reasons']}"
            )
        policy = self._fusion_defusion_policy()
        if not policy.can_defuse(fused):
            raise ValueError("Defusion threshold does not allow another defusion participation.")

        result = recover_defusion_components(fused)
        fused.generation_participations += 1
        if not result.success:
            event = EvolutionEvent(
                event_type="defusion_failed",
                generation=self.generation + 1,
                parent_ids=(fused_id,),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedStructuralOperatorResult(
                "defusion", result.to_dict(), (), event.to_dict()
            )

        children: list[Individual] = []
        for component in result.components:
            child = create_offspring(
                allocator=self.allocator,
                generation=self.generation + 1,
                parent_ids=(fused_id,),
                created_by="defusion",
                target_genome=component.target_genome,
                source_genome=fused.genome,
                content=fused.content,
                content_status="pending_generation",
                source_type=component.source_metadata.get("source_type", ""),
                source_page=component.source_metadata.get("source_page", ""),
                source_row_id=component.source_metadata.get("source_row_id", ""),
            )
            child.extra.update(
                {
                    "structural_operator": "defusion",
                    "source_parent_id": fused_id,
                    "recovered_source_parent_id": component.source_parent_id,
                    "defusion_component": component.to_dict(),
                    "defusion_provenance": deepcopy(result.provenance),
                    "requires_structural_content_realizer": True,
                }
            )
            self.pending_offspring[child.individual_id] = child
            children.append(child)

        event = EvolutionEvent(
            event_type="defusion_targets_created",
            generation=self.generation + 1,
            individual_ids=tuple(child.individual_id for child in children),
            parent_ids=(fused_id,),
            payload=result.to_dict(),
        )
        record_defusion_participation(fused, event.event_id, policy)
        for child in children:
            record_defusion_participation(child, event.event_id, policy)
        self.lineage.record(event)
        return AppliedStructuralOperatorResult(
            "defusion",
            result.to_dict(),
            tuple(child.to_dict() for child in children),
            event.to_dict(),
        )

    def apply_composition(
        self,
        parent_ids: Sequence[str],
        *,
        roles: Sequence[str] | None = None,
    ) -> AppliedStructuralOperatorResult:
        if len(parent_ids) < 2:
            raise ValueError("Composition requires at least two parent individuals.")
        if len(set(parent_ids)) != len(parent_ids):
            raise ValueError("Composition requires distinct parent individuals.")
        parents = [self._find(parent_id, include_pending=False) for parent_id in parent_ids]
        for parent in parents:
            eligibility = self.eligibility(parent.individual_id, operator="composition")
            if not eligibility["eligible"]:
                raise ValueError(
                    f"Parent {parent.individual_id} is not eligible for composition: "
                    f"{eligibility['reasons']}"
                )

        for parent in parents:
            parent.generation_participations += 1
        result = compose_individuals(parents, roles=roles)
        ordered_parent_ids = tuple(result.provenance["parent_ids"])
        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=ordered_parent_ids,
            created_by="composition",
            target_genome=result.container_genome,
            source_genome=result.container_genome,
            content=result.content,
            content_status="accepted",
        )
        child.extra.update(
            {
                "structural_operator": "composition",
                "compound": True,
                "composition": result.to_dict(),
                "container_genome_policy": "first_ordered_component_inheritance_v1_nonsemantic",
                "not_llm_rewritten": True,
            }
        )
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="composition",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=ordered_parent_ids,
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        for parent_id in ordered_parent_ids:
            self.successful_parent_participations[parent_id] += 1
        return AppliedStructuralOperatorResult(
            "composition", result.to_dict(), (child.to_dict(),), event.to_dict()
        )

    def apply_decomposition(self, compound_id: str) -> AppliedStructuralOperatorResult:
        compound = self._find(compound_id, include_pending=False)
        eligibility = self.eligibility(compound_id, operator="decomposition")
        if not eligibility["eligible"]:
            raise ValueError(
                f"Parent {compound_id} is not eligible for decomposition: {eligibility['reasons']}"
            )
        result = recover_composition_components(compound)
        compound.generation_participations += 1
        if not result.success:
            event = EvolutionEvent(
                event_type="decomposition_failed",
                generation=self.generation + 1,
                parent_ids=(compound_id,),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedStructuralOperatorResult(
                "decomposition", result.to_dict(), (), event.to_dict()
            )

        children: list[Individual] = []
        for component in result.components:
            child = create_offspring(
                allocator=self.allocator,
                generation=self.generation + 1,
                parent_ids=(compound_id,),
                created_by="decomposition",
                target_genome=component.genome,
                source_genome=component.genome,
                content=component.content,
                content_status="accepted",
                source_type=component.source_type,
                source_page=component.source_page,
                source_row_id=component.source_row_id,
            )
            child.extra.update(
                {
                    "structural_operator": "decomposition",
                    "decomposed_from": compound_id,
                    "original_component": component.to_dict(),
                    "original_source_parent_id": component.source_parent_id,
                    "not_llm_rewritten": True,
                }
            )
            self.pending_offspring[child.individual_id] = child
            children.append(child)

        event = EvolutionEvent(
            event_type="decomposition",
            generation=self.generation + 1,
            individual_ids=tuple(child.individual_id for child in children),
            parent_ids=(compound_id,),
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        self.successful_parent_participations[compound_id] += 1
        return AppliedStructuralOperatorResult(
            "decomposition",
            result.to_dict(),
            tuple(child.to_dict() for child in children),
            event.to_dict(),
        )

    def apply_content_operator(
        self,
        child_id: str,
        *,
        operator_name: str,
        generator,
        validator,
        seed: int | None = None,
        grounding_context=None,
        planning_rules=None,
        prompt_registry=None,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        child = self._find(child_id, include_pending=True)
        if child_id not in self.pending_offspring:
            raise ValueError(
                "Content operators can only finalize pending offspring in this milestone."
            )
        if child.created_by in {"fusion", "defusion"}:
            raise ValueError(
                "Fusion/Defusion offspring require the dedicated structural content "
                "realizer planned for the deferred real-model M5B stage; generic "
                "single-source content operators must not fake this realization."
            )

        source_id = str(child.extra.get("source_parent_id") or "")
        source = self._find(source_id, include_pending=False)
        operator = get_content_operator(operator_name)

        # Controlled refactor: M3 session-produced offspring always have an
        # explicit target_genome. Fallback only supports legacy callers that
        # manually constructed a pending child.
        target_genome = (
            child.genome if child.target_genome is None else child.target_genome
        )
        content_seed = self._content_seed(child_id, operator_name) if seed is None else seed
        execute_kwargs = {
            "generator": generator,
            "validator": validator,
            "seed": content_seed,
            "grounding_context": grounding_context,
            "planning_rules": planning_rules,
            "generation_info": {
                "run_seed": self.seed,
                "generation": self.generation + 1,
                "child_id": child_id,
                "operator": operator_name,
            },
            "max_attempts": max_attempts,
        }
        if prompt_registry is not None:
            execute_kwargs["prompt_registry"] = prompt_registry
        result = operator.execute(source, target_genome, **execute_kwargs)

        realized = result.validation.realized_genome
        rejection_reasons: list[str] = []

        if not result.accepted:
            rejection_reasons.extend(result.validation.reasons)
            if getattr(result, "retries_exhausted", False):
                rejection_reasons.append("max_content_attempts_exhausted")

        if result.accepted and realized is None:
            rejection_reasons.append("missing_realized_genome")

        if result.accepted and realized is not None:
            content_plan = result.request.content_plan
            controlled_traits = (
                () if content_plan is None else content_plan.controlled_traits
            )
            mismatches = target_realized_mismatches(
                target_genome,
                realized,
                controlled_traits=controlled_traits,
            )
            rejection_reasons.extend(
                f"target_realized_mismatch:{field}" for field in mismatches
            )
            if content_plan is not None:
                direction_mismatches = target_realized_direction_mismatches(
                    content_plan, realized
                )
                rejection_reasons.extend(
                    f"target_realized_direction_mismatch:{field}"
                    for field in direction_mismatches
                )

        session_accepted = bool(result.accepted and not rejection_reasons)
        event_type = "content_accepted" if session_accepted else "content_rejected"

        child.extra["content_seed"] = content_seed
        child.extra["content_operation"] = result.to_dict()

        if session_accepted:
            child.content = result.response.content
            child.realized_genome = RealizedGenome(realized)
            child.genome = realized
            child.content_status = "accepted"
            for parent_id in child.parent_ids:
                self.successful_parent_participations[parent_id] += 1
        else:
            if realized is not None:
                child.realized_genome = RealizedGenome(realized)
            child.content_status = "rejected"
            child.extra["content_rejection_reasons"] = list(rejection_reasons)

        acceptance = {
            "accepted": session_accepted,
            "validator_accepted": result.accepted,
            "reasons": rejection_reasons,
        }
        event = EvolutionEvent(
            event_type=event_type,
            generation=self.generation + 1,
            individual_ids=(child_id,),
            parent_ids=child.parent_ids,
            payload={**result.to_dict(), "session_acceptance": acceptance},
        )
        self.lineage.record(event)
        return {
            "result": result.to_dict(),
            "acceptance": acceptance,
            "offspring": child.to_dict(),
            "event": event.to_dict(),
        }

    def _capture_generation_snapshot(
        self,
        *,
        completed_generation: int,
        accepted: list[Individual],
        rejected: list[Individual],
        longevity_events: list[EvolutionEvent],
        perish_events: list[EvolutionEvent],
    ) -> dict[str, Any]:
        return {
            "snapshot_version": "m3-v1",
            "run_seed": self.seed,
            "completed_generation": completed_generation,
            "active_population": [deepcopy(i.to_dict()) for i in self.active_population],
            # Legacy/all-accepted population includes perished historical members.
            "population": [deepcopy(i.to_dict()) for i in self.population],
            "accepted_offspring_ids": [i.individual_id for i in accepted],
            "rejected_attempt_ids": [i.individual_id for i in rejected],
            "longevity_events": [e.to_dict() for e in longevity_events],
            "perish_events": [e.to_dict() for e in perish_events],
            "archive_ids": sorted(self.historical_archive),
            "variant_library_ids": sorted(self.variant_library),
            "rejected_attempt_count": len(self.rejected_attempts),
            "lineage": self.lineage.to_dict(),
        }

    def end_generation(self) -> dict[str, Any]:
        validate_lifecycle_runtime_config(self.config)
        ecfg = self.config["evolution"]
        lcfg = ecfg["longevity"]
        policy = LongevityPolicy(
            initial_chance=float(lcfg["initial_chance"]),
            reproduction_reward=float(lcfg["reproduction_reward"]),
            inactivity_penalty=float(lcfg["inactivity_penalty"]),
            perish_threshold=float(ecfg.get("perish", {}).get("threshold", 0.0)),
        )
        initialize_longevity(self.population, policy)

        unresolved = [
            child.individual_id
            for child in self.pending_offspring.values()
            if child.content_status == "pending_generation"
        ]
        if unresolved:
            raise ValueError(
                "Cannot end generation while offspring are pending content validation: "
                + ", ".join(unresolved[:10])
            )

        longevity_events = update_longevity_end_of_generation(
            self.population,
            successful_parent_participations=self.successful_parent_participations,
            policy=policy,
            generation=self.generation + 1,
        )
        for event in longevity_events:
            self.lineage.record(event)

        perish_events = apply_perish(
            self.population,
            threshold=policy.perish_threshold,
            generation=self.generation + 1,
        )
        for event in perish_events:
            self.lineage.record(event)

        age_survivors(self.population)

        accepted = [
            child
            for child in self.pending_offspring.values()
            if child.content_status == "accepted"
        ]
        rejected = [
            child
            for child in self.pending_offspring.values()
            if child.content_status == "rejected"
        ]
        initialize_longevity(accepted, policy)
        self.population.extend(accepted)

        completed_generation = self.generation + 1
        self.generation = completed_generation

        # Accepted artifacts belong to history, and evolved accepted variants
        # belong to the usable variant library. Rejected attempts are log-only.
        for individual in self.population:
            self.historical_archive[individual.individual_id] = deepcopy(
                individual.to_dict()
            )
        for individual in accepted:
            self.variant_library[individual.individual_id] = deepcopy(
                individual.to_dict()
            )
        for individual in rejected:
            self.rejected_attempts.append(
                {
                    "generation": completed_generation,
                    "offspring": deepcopy(individual.to_dict()),
                }
            )

        self.pending_offspring = {}
        self.successful_parent_participations.clear()
        reset_generation_state(self.population)
        self.allocator = OffspringIdAllocator(self.generation + 1)

        snapshot = self._capture_generation_snapshot(
            completed_generation=completed_generation,
            accepted=accepted,
            rejected=rejected,
            longevity_events=longevity_events,
            perish_events=perish_events,
        )
        self.generation_snapshots.append(snapshot)

        return {
            "completed_generation": completed_generation,
            "accepted_offspring_count": len(accepted),
            "rejected_offspring_count": len(rejected),
            "perished_count": len(perish_events),
            "alive_population_size": len(self.active_population),
            "archive_size": len(self.historical_archive),
            "variant_library_size": len(self.variant_library),
            "rejected_attempt_count": len(self.rejected_attempts),
            "generation_snapshot_index": len(self.generation_snapshots) - 1,
            "longevity_events": [e.to_dict() for e in longevity_events],
            "perish_events": [e.to_dict() for e in perish_events],
        }

    def lineage_for(self, individual_id: str) -> dict[str, Any]:
        return {
            "individual_id": individual_id,
            "parents": list(self.lineage.parents.get(individual_id, ())),
            "children": list(self.lineage.children.get(individual_id, ())),
            "ancestors": sorted(self.lineage.ancestors_of(individual_id)),
            "events": [
                event.to_dict()
                for event in self.lineage.events
                if individual_id in event.individual_ids
                or individual_id in event.parent_ids
            ],
        }

    def snapshot(self) -> dict[str, Any]:
        """Serializable state for UI refreshes and immutable run artifacts."""
        return {
            "seed": self.seed,
            "generation": self.generation,
            # Existing key retained for backward compatibility.
            "population": [i.to_dict() for i in self.population],
            "active_population": [i.to_dict() for i in self.active_population],
            "pending_offspring": [
                i.to_dict() for i in self.pending_offspring.values()
            ],
            "historical_archive": [
                deepcopy(self.historical_archive[k])
                for k in sorted(self.historical_archive)
            ],
            "variant_library": [
                deepcopy(self.variant_library[k]) for k in sorted(self.variant_library)
            ],
            "rejected_attempts": deepcopy(self.rejected_attempts),
            "generation_snapshots": deepcopy(self.generation_snapshots),
            "successful_parent_participations": dict(
                self.successful_parent_participations
            ),
            "lineage": self.lineage.to_dict(),
        }
