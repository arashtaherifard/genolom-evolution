from __future__ import annotations

"""Configurable automatic generation scheduling for genome-only evolution.

The proposal defines the operators, but not a single final scheduling
probability/budget.  This module therefore keeps scheduling explicit and fully
config-driven.  Development values are smoke-test values only; final values are
chosen by the staged calibration protocol.
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from ..models.individual import Individual
from ..tracking.events import EvolutionEvent
from .eligibility import check_parent_eligibility


SUPPORTED_OPERATORS = (
    "mutation",
    "crossover",
    "fusion",
    "defusion",
    "composition",
    "decomposition",
)


@dataclass(frozen=True, slots=True)
class GenerationPolicyResult:
    generation: int
    requested_attempts: int
    attempted_by_operator: dict[str, int]
    successful_by_operator: dict[str, int]
    offspring_by_operator: dict[str, int]
    skipped_by_operator: dict[str, int]
    failure_reasons: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "requested_attempts": self.requested_attempts,
            "attempted_by_operator": dict(sorted(self.attempted_by_operator.items())),
            "successful_by_operator": dict(sorted(self.successful_by_operator.items())),
            "offspring_by_operator": dict(sorted(self.offspring_by_operator.items())),
            "skipped_by_operator": dict(sorted(self.skipped_by_operator.items())),
            "failure_reasons": dict(sorted(self.failure_reasons.items())),
        }


def _weighted_choice(rng, weights: dict[str, float]) -> str:
    names = [name for name in SUPPORTED_OPERATORS if float(weights.get(name, 0.0)) > 0]
    if not names:
        raise ValueError("At least one positive operator weight is required.")
    values = [float(weights[name]) for name in names]
    return rng.choices(names, weights=values, k=1)[0]


def _eligible_special(session, operator: str, *, created_by: str) -> list[Individual]:
    ecfg = session.config.get("evolution", {})
    return [
        individual
        for individual in session.active_population
        if individual.created_by == created_by
        and check_parent_eligibility(
            individual,
            operator=operator,
            maturity_age=ecfg.get("maturity_age"),
            max_parent_participations_per_generation=ecfg.get(
                "max_parent_participations_per_generation"
            ),
        ).eligible
    ]


def _fitness_weighted_pick(session, candidates: Iterable[Individual]) -> Individual:
    values = list(candidates)
    if not values:
        raise ValueError("No eligible candidates.")
    strategy = str(session.config.get("selection", {}).get("strategy", "fitness_proportionate"))
    if strategy in {"random", "uniform"}:
        return session.evolution_rng.choice(values)
    weights = [max(0.0, float(item.micro_fitness or 0.0)) for item in values]
    if sum(weights) <= 0:
        return session.evolution_rng.choice(values)
    return session.evolution_rng.choices(values, weights=weights, k=1)[0]


class GenomeGenerationPolicy:
    """Execute one complete, content-independent evolutionary generation."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def attempt_budget(self, active_population_size: int) -> int:
        pcfg = self.config.get("genome_evolution", {}).get("attempt_budget", {})
        mode = str(pcfg.get("mode", "active_population"))
        if mode == "fixed":
            value = int(pcfg.get("value", 0))
        elif mode == "active_population":
            multiplier = float(pcfg.get("multiplier", 1.0))
            value = int(round(active_population_size * multiplier))
        else:
            raise ValueError(f"Unknown genome_evolution.attempt_budget.mode: {mode!r}")
        minimum = int(pcfg.get("minimum", 0))
        maximum = pcfg.get("maximum")
        value = max(minimum, value)
        if maximum is not None:
            value = min(value, int(maximum))
        return max(0, value)

    def run(self, session, generation: int) -> GenerationPolicyResult:
        if not session.genome_only_mode:
            raise ValueError("GenomeGenerationPolicy requires evolution.genome_only_mode=true")
        cfg = self.config.get("genome_evolution", {})
        weights = {str(k): float(v) for k, v in cfg.get("operator_weights", {}).items()}
        attempts = self.attempt_budget(len(session.active_population))
        composition_parent_count = int(cfg.get("composition_parent_count", 2))
        if composition_parent_count < 2:
            raise ValueError("composition_parent_count must be >= 2")
        fusion_ops = tuple(str(x) for x in cfg.get("fusion_binary_operators", ["AND"]))
        if not fusion_ops:
            raise ValueError("fusion_binary_operators must not be empty")

        attempted: Counter[str] = Counter()
        successful: Counter[str] = Counter()
        offspring_counts: Counter[str] = Counter()
        skipped: Counter[str] = Counter()
        failures: Counter[str] = Counter()

        for attempt_index in range(1, attempts + 1):
            operator = _weighted_choice(session.evolution_rng, weights)
            attempted[operator] += 1
            selected_ids: tuple[str, ...] = ()
            try:
                if operator == "mutation":
                    selection = session.select(operator="mutation", count=1)
                    selected_ids = selection.selected_ids
                    result = session.apply_mutation(selected_ids[0])
                    child_count = 0 if result.offspring is None else 1

                elif operator == "crossover":
                    selection = session.select(operator="crossover", count=2)
                    selected_ids = selection.selected_ids
                    result = session.apply_crossover(*selected_ids)
                    child_count = 0 if result.offspring is None else 1

                elif operator == "fusion":
                    selection = session.select(operator="fusion", count=2)
                    selected_ids = selection.selected_ids
                    binary_operator = session.evolution_rng.choice(fusion_ops)
                    result = session.apply_fusion(
                        selected_ids[0], selected_ids[1], binary_operator=binary_operator
                    )
                    child_count = len(result.offspring)

                elif operator == "defusion":
                    candidates = _eligible_special(session, "defusion", created_by="fusion")
                    if not candidates:
                        skipped[operator] += 1
                        failures["no_eligible_defusion_parent"] += 1
                        continue
                    parent = _fitness_weighted_pick(session, candidates)
                    selected_ids = (parent.individual_id,)
                    result = session.apply_defusion(parent.individual_id)
                    child_count = len(result.offspring)

                elif operator == "composition":
                    selection = session.select(
                        operator="composition", count=composition_parent_count
                    )
                    selected_ids = selection.selected_ids
                    result = session.apply_composition(selected_ids)
                    child_count = len(result.offspring)

                elif operator == "decomposition":
                    candidates = _eligible_special(
                        session, "decomposition", created_by="composition"
                    )
                    if not candidates:
                        skipped[operator] += 1
                        failures["no_eligible_decomposition_parent"] += 1
                        continue
                    parent = _fitness_weighted_pick(session, candidates)
                    selected_ids = (parent.individual_id,)
                    result = session.apply_decomposition(parent.individual_id)
                    child_count = len(result.offspring)

                else:  # pragma: no cover - protected by SUPPORTED_OPERATORS
                    raise ValueError(operator)

                if child_count:
                    successful[operator] += 1
                    offspring_counts[operator] += child_count
                else:
                    failures[f"{operator}_no_offspring"] += 1

                session.lineage.record(
                    EvolutionEvent(
                        event_type="operator_schedule_attempt",
                        generation=generation,
                        parent_ids=selected_ids,
                        payload={
                            "attempt_index": attempt_index,
                            "operator": operator,
                            "offspring_count": child_count,
                            "status": "success" if child_count else "no_offspring",
                        },
                    )
                )
            except (ValueError, KeyError) as exc:
                # In stochastic evolutionary scheduling, an operator may become
                # temporarily unavailable because maturity/participation limits
                # changed earlier in the same generation.  Record and continue;
                # never silently substitute another scientific rule.
                skipped[operator] += 1
                failures[f"{operator}:{type(exc).__name__}:{str(exc)}"] += 1
                session.lineage.record(
                    EvolutionEvent(
                        event_type="operator_schedule_skipped",
                        generation=generation,
                        parent_ids=selected_ids,
                        payload={
                            "attempt_index": attempt_index,
                            "operator": operator,
                            "reason": str(exc),
                        },
                    )
                )

        return GenerationPolicyResult(
            generation=generation,
            requested_attempts=attempts,
            attempted_by_operator=dict(attempted),
            successful_by_operator=dict(successful),
            offspring_by_operator=dict(offspring_counts),
            skipped_by_operator=dict(skipped),
            failure_reasons=dict(failures),
        )


__all__ = ["SUPPORTED_OPERATORS", "GenerationPolicyResult", "GenomeGenerationPolicy"]
