from __future__ import annotations
from dataclasses import dataclass, asdict, replace
import random
from typing import Any

from ..models.genome import GenoLOMGenome
from ..models.individual import Individual
from ..validation.genome_validator import validate_genome
from ..validation.proposal_rules import ALLOWED_INTERACTIVITY_LEVELS, FORBIDDEN_SEMANTIC_DIFFICULTY
from .rates import rate_trigger
from .operator_rules import (
    SEMANTIC_DENSITY_LEVELS,
    DIFFICULTY_LEVELS,
    ResourceTransformAction,
    get_learning_resource_transition,
    crossover_interactivity_type,
    crossover_interactivity_level,
    crossover_semantic_density,
    crossover_difficulty,
)


@dataclass(frozen=True, slots=True)
class RepairAction:
    field: str
    before: Any
    after: Any
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CrossoverResult:
    parent_ids: tuple[str, str]
    attempted: bool
    applied: bool
    crossover_rate: float
    rate_draw: float
    base_parent_id: str
    target_genome: GenoLOMGenome
    repairs: tuple[RepairAction, ...]
    validation_issues: tuple[dict, ...]
    provisional_fields: tuple[str, ...]
    learning_resource_rule: str
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "parent_ids": list(self.parent_ids),
            "attempted": self.attempted,
            "applied": self.applied,
            "crossover_rate": self.crossover_rate,
            "rate_draw": self.rate_draw,
            "base_parent_id": self.base_parent_id,
            "target_genome": self.target_genome.to_dict(),
            "repairs": [r.to_dict() for r in self.repairs],
            "validation_issues": list(self.validation_issues),
            "provisional_fields": list(self.provisional_fields),
            "learning_resource_rule": self.learning_resource_rule,
            "reason": self.reason,
        }


def _choose_lrt(a: str, b: str, base: str) -> tuple[str, str]:
    if a == b:
        return a, "same_parent_type"

    a_to_b = get_learning_resource_transition(a, b)
    b_to_a = get_learning_resource_transition(b, a)
    if a_to_b is not None and a_to_b.action is not ResourceTransformAction.DROP:
        return b, f"appendix_b:{a}->{b}:{a_to_b.action.value}"
    if b_to_a is not None and b_to_a.action is not ResourceTransformAction.DROP:
        return a, f"appendix_b:{b}->{a}:{b_to_a.action.value}"

    # The proposal does not provide complete source-transition coverage. Keep a
    # real parent value rather than inventing a new transformation.
    return base, "conservative_parent_inheritance_no_explicit_rule"


def _repair_interactivity(genome: GenoLOMGenome) -> tuple[GenoLOMGenome, list[RepairAction]]:
    allowed = ALLOWED_INTERACTIVITY_LEVELS.get(genome.interactivityType)
    if not allowed or genome.interactivityLevel in allowed:
        return genome, []

    order = ["Very Low", "Low", "Medium", "High", "Very High"]
    current = order.index(genome.interactivityLevel)
    target = min(allowed, key=lambda x: (abs(order.index(x) - current), order.index(x)))
    return replace(genome, interactivityLevel=target), [
        RepairAction("interactivityLevel", genome.interactivityLevel, target,
                     "integrity_repair_for_interactivityType")
    ]


def _repair_semantic_difficulty(genome: GenoLOMGenome) -> tuple[GenoLOMGenome, list[RepairAction]]:
    pair = (genome.semanticDensity, genome.difficulty)
    if pair not in FORBIDDEN_SEMANTIC_DIFFICULTY:
        return genome, []

    s_idx = SEMANTIC_DENSITY_LEVELS.index(genome.semanticDensity)
    d_idx = DIFFICULTY_LEVELS.index(genome.difficulty)
    candidates: list[tuple[int, int, str, str]] = []
    for s in SEMANTIC_DENSITY_LEVELS:
        for d in DIFFICULTY_LEVELS:
            if (s, d) in FORBIDDEN_SEMANTIC_DIFFICULTY:
                continue
            distance = abs(SEMANTIC_DENSITY_LEVELS.index(s) - s_idx) + abs(DIFFICULTY_LEVELS.index(d) - d_idx)
            candidates.append((distance, SEMANTIC_DENSITY_LEVELS.index(s) + DIFFICULTY_LEVELS.index(d), s, d))
    _, _, s_new, d_new = min(candidates)
    repaired = replace(genome, semanticDensity=s_new, difficulty=d_new)
    repairs: list[RepairAction] = []
    if s_new != genome.semanticDensity:
        repairs.append(RepairAction("semanticDensity", genome.semanticDensity, s_new,
                                    "integrity_repair_for_forbidden_semantic_difficulty_pair"))
    if d_new != genome.difficulty:
        repairs.append(RepairAction("difficulty", genome.difficulty, d_new,
                                    "integrity_repair_for_forbidden_semantic_difficulty_pair"))
    return repaired, repairs


def crossover_individuals(
    parent_a: Individual,
    parent_b: Individual,
    *,
    rate: float,
    rng: random.Random,
) -> CrossoverResult:
    triggered, draw = rate_trigger(rate, rng)
    base_parent = rng.choice([parent_a, parent_b])
    if not triggered:
        return CrossoverResult(
            (parent_a.individual_id, parent_b.individual_id), True, False,
            float(rate), draw, base_parent.individual_id, base_parent.genome,
            (), (), (), "not_applied", "rate_not_triggered",
        )

    a, b = parent_a.genome, parent_b.genome
    lrt, lrt_rule = _choose_lrt(a.learningResourceType, b.learningResourceType, base_parent.genome.learningResourceType)

    raw = replace(
        base_parent.genome,
        interactivityType=crossover_interactivity_type(a.interactivityType, b.interactivityType),
        learningResourceType=lrt,
        interactivityLevel=crossover_interactivity_level(a.interactivityLevel, b.interactivityLevel),
        semanticDensity=crossover_semantic_density(a.semanticDensity, b.semanticDensity),
        difficulty=crossover_difficulty(a.difficulty, b.difficulty),
        # Non-Appendix-D genes remain inherited from a real parent in V1.
    )

    repaired, r1 = _repair_interactivity(raw)
    repaired, r2 = _repair_semantic_difficulty(repaired)
    issues = tuple(issue.to_dict() for issue in validate_genome(repaired))
    return CrossoverResult(
        (parent_a.individual_id, parent_b.individual_id), True, not issues,
        float(rate), draw, base_parent.individual_id, repaired,
        tuple(r1 + r2), issues, ("semanticDensity", "difficulty"), lrt_rule,
        None if not issues else "target_genome_invalid",
    )
