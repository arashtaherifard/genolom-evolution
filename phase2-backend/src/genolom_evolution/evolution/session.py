from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import random
from typing import Any, Sequence

from ..content.operators import get_content_operator
from ..fitness.micro import calculate_micro_fitness
from ..models.individual import Individual
from ..selection.parent_pool import select_parents, ParentSelectionResult
from ..tracking.events import EvolutionEvent
from ..tracking.lineage import LineageTracker
from ..validation.config_validator import validate_mutation_runtime_config, validate_crossover_runtime_config, validate_lifecycle_runtime_config
from .crossover import crossover_individuals, CrossoverResult
from .eligibility import check_parent_eligibility
from .lifecycle import (
    LongevityPolicy, initialize_longevity, age_survivors,
    update_longevity_end_of_generation, apply_perish, reset_generation_state,
)
from .mutation import mutate_individual, MutationResult
from .offspring import OffspringIdAllocator, create_offspring


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


class PriorityEvolutionSession:
    """Stateful Phase-2 session behind the UI/service layer.

    The session implements the priority (blue-row) genetic workflow while
    keeping content generation/provider-specific behavior injected through
    interfaces. No UI dependency exists here.
    """

    def __init__(self, population: Sequence[Individual], config: dict, *, seed: int | None = None):
        self.population: list[Individual] = list(population)
        self.pending_offspring: dict[str, Individual] = {}
        self.config = config
        self.seed = int(config.get("reproducibility", {}).get("seed", 42) if seed is None else seed)
        self.rng = random.Random(self.seed)
        self.generation = max((i.generation_created for i in self.population), default=0)
        self.allocator = OffspringIdAllocator(self.generation + 1)
        self.lineage = LineageTracker()
        self.successful_parent_participations: Counter[str] = Counter()

    def _find(self, individual_id: str, *, include_pending: bool = True) -> Individual:
        for individual in self.population:
            if individual.individual_id == individual_id:
                return individual
        if include_pending and individual_id in self.pending_offspring:
            return self.pending_offspring[individual_id]
        raise KeyError(individual_id)

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
            max_parent_participations_per_generation=ecfg.get("max_parent_participations_per_generation"),
        ).to_dict()

    def select(self, *, operator: str, count: int) -> ParentSelectionResult:
        ecfg = self.config["evolution"]
        scfg = self.config["selection"]
        return select_parents(
            self.population,
            operator=operator,
            count=count,
            rng=self.rng,
            strategy=scfg.get("strategy", "fitness_proportionate"),
            maturity_age=ecfg.get("maturity_age"),
            max_parent_participations_per_generation=ecfg.get("max_parent_participations_per_generation"),
            repeated_parent_selection=bool(scfg.get("repeated_parent_selection", True)),
        )

    def apply_mutation(self, parent_id: str, *, force_rate: float | None = None) -> AppliedOperatorResult:
        if force_rate is None:
            validate_mutation_runtime_config(self.config)
        parent = self._find(parent_id, include_pending=False)
        eligibility = self.eligibility(parent_id, operator="mutation")
        if not eligibility["eligible"]:
            raise ValueError(f"Parent {parent_id} is not eligible for mutation: {eligibility['reasons']}")
        rate = float(self.config["evolution"]["mutation"]["rate"] if force_rate is None else force_rate)
        result: MutationResult = mutate_individual(parent, rate=rate, rng=self.rng)
        parent.generation_participations += 1
        if not result.applied:
            event = EvolutionEvent(
                event_type="mutation_not_applied",
                generation=self.generation + 1,
                parent_ids=(parent_id,),
                payload=result.to_dict(),
            )
            self.lineage.record(event)
            return AppliedOperatorResult("mutation", result.to_dict(), None, event.to_dict())

        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=(parent_id,),
            created_by="mutation",
            target_genome=result.target_genome,
            content=parent.content,
            content_status="pending_generation",
            source_type=parent.source_type,
            source_page=parent.source_page,
            source_row_id=parent.source_row_id,
        )
        child.extra.update({
            "source_parent_id": parent_id,
            "genetic_operator": "mutation",
            "mutation": result.to_dict(),
        })
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="mutation",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=(parent_id,),
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        return AppliedOperatorResult("mutation", result.to_dict(), child.to_dict(), event.to_dict())

    def apply_crossover(self, parent_a_id: str, parent_b_id: str, *, force_rate: float | None = None) -> AppliedOperatorResult:
        if force_rate is None:
            validate_crossover_runtime_config(self.config)
        if parent_a_id == parent_b_id:
            raise ValueError("Crossover requires two distinct parent individuals.")
        a = self._find(parent_a_id, include_pending=False)
        b = self._find(parent_b_id, include_pending=False)
        for parent in (a, b):
            e = self.eligibility(parent.individual_id, operator="crossover")
            if not e["eligible"]:
                raise ValueError(f"Parent {parent.individual_id} is not eligible for crossover: {e['reasons']}")
        rate = float(self.config["evolution"]["crossover"]["rate"] if force_rate is None else force_rate)
        result: CrossoverResult = crossover_individuals(a, b, rate=rate, rng=self.rng)
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
            return AppliedOperatorResult("crossover", result.to_dict(), None, event.to_dict())

        base = self._find(result.base_parent_id, include_pending=False)
        child = create_offspring(
            allocator=self.allocator,
            generation=self.generation + 1,
            parent_ids=(parent_a_id, parent_b_id),
            created_by="crossover",
            target_genome=result.target_genome,
            content=base.content,
            content_status="pending_generation",
            source_type=base.source_type,
            source_page=base.source_page,
            source_row_id=base.source_row_id,
        )
        child.extra.update({
            "source_parent_id": base.individual_id,
            "genetic_operator": "crossover",
            "crossover": result.to_dict(),
        })
        self.pending_offspring[child.individual_id] = child
        event = EvolutionEvent(
            event_type="crossover",
            generation=self.generation + 1,
            individual_ids=(child.individual_id,),
            parent_ids=(parent_a_id, parent_b_id),
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        return AppliedOperatorResult("crossover", result.to_dict(), child.to_dict(), event.to_dict())

    def apply_content_operator(self, child_id: str, *, operator_name: str, generator, validator, seed: int | None = None) -> dict[str, Any]:
        child = self._find(child_id, include_pending=True)
        if child_id not in self.pending_offspring:
            raise ValueError("Content operators can only finalize pending offspring in this milestone.")
        source_id = str(child.extra.get("source_parent_id") or "")
        source = self._find(source_id, include_pending=False)
        operator = get_content_operator(operator_name)
        result = operator.execute(
            source,
            child.genome,
            generator=generator,
            validator=validator,
            seed=self.seed if seed is None else seed,
        )
        event_type = "content_accepted" if result.accepted else "content_rejected"
        if result.accepted:
            child.content = result.response.content
            child.content_status = "accepted"
            for parent_id in child.parent_ids:
                self.successful_parent_participations[parent_id] += 1
        else:
            child.content_status = "rejected"
        event = EvolutionEvent(
            event_type=event_type,
            generation=self.generation + 1,
            individual_ids=(child_id,),
            parent_ids=child.parent_ids,
            payload=result.to_dict(),
        )
        self.lineage.record(event)
        return {"result": result.to_dict(), "offspring": child.to_dict(), "event": event.to_dict()}

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
            c.individual_id for c in self.pending_offspring.values()
            if c.content_status == "pending_generation"
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
        accepted = [c for c in self.pending_offspring.values() if c.content_status == "accepted"]
        rejected = [c for c in self.pending_offspring.values() if c.content_status == "rejected"]
        initialize_longevity(accepted, policy)
        self.population.extend(accepted)

        completed_generation = self.generation + 1
        self.generation = completed_generation
        self.pending_offspring = {}
        self.successful_parent_participations.clear()
        reset_generation_state(self.population)
        self.allocator = OffspringIdAllocator(self.generation + 1)

        return {
            "completed_generation": completed_generation,
            "accepted_offspring_count": len(accepted),
            "rejected_offspring_count": len(rejected),
            "perished_count": len(perish_events),
            "alive_population_size": sum(1 for i in self.population if i.alive),
            "longevity_events": [e.to_dict() for e in longevity_events],
            "perish_events": [e.to_dict() for e in perish_events],
        }

    def lineage_for(self, individual_id: str) -> dict[str, Any]:
        return {
            "individual_id": individual_id,
            "parents": list(self.lineage.parents.get(individual_id, ())),
            "children": list(self.lineage.children.get(individual_id, ())),
            "ancestors": sorted(self.lineage.ancestors_of(individual_id)),
            "events": [e.to_dict() for e in self.lineage.events if individual_id in e.individual_ids or individual_id in e.parent_ids],
        }

    def snapshot(self) -> dict[str, Any]:
        """Serializable state for UI refreshes and immutable run artifacts."""
        return {
            "seed": self.seed,
            "generation": self.generation,
            "population": [i.to_dict() for i in self.population],
            "pending_offspring": [i.to_dict() for i in self.pending_offspring.values()],
            "successful_parent_participations": dict(self.successful_parent_participations),
            "lineage": self.lineage.to_dict(),
        }
