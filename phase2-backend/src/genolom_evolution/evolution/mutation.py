from __future__ import annotations
from dataclasses import dataclass, asdict, replace
import random
from typing import Any

from ..models.genome import GenoLOMGenome
from ..models.individual import Individual
from ..validation.genome_validator import validate_genome
from .rates import rate_trigger
from .operator_rules import (
    INTERACTIVITY_LEVELS,
    SEMANTIC_DENSITY_LEVELS,
    DIFFICULTY_LEVELS,
    ResourceTransformAction,
    get_learning_resource_transition,
    valid_learning_resource_mutation_targets,
    interactivity_level_mutation_action,
    semantic_density_mutation_action,
    difficulty_mutation_action,
)


@dataclass(frozen=True, slots=True)
class MutationOption:
    gene: str
    old_value: Any
    new_value: Any
    action: str
    requires_content_conversion: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MutationResult:
    parent_id: str
    attempted: bool
    applied: bool
    mutation_rate: float
    rate_draw: float
    option: MutationOption | None
    target_genome: GenoLOMGenome
    validation_issues: tuple[dict, ...]
    reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "parent_id": self.parent_id,
            "attempted": self.attempted,
            "applied": self.applied,
            "mutation_rate": self.mutation_rate,
            "rate_draw": self.rate_draw,
            "option": None if self.option is None else self.option.to_dict(),
            "target_genome": self.target_genome.to_dict(),
            "validation_issues": list(self.validation_issues),
            "reason": self.reason,
        }


def _neighbor_values(value: str, levels: tuple[str, ...]) -> list[str]:
    idx = levels.index(value)
    out: list[str] = []
    if idx > 0:
        out.append(levels[idx - 1])
    if idx + 1 < len(levels):
        out.append(levels[idx + 1])
    return out


def _candidate(genome: GenoLOMGenome, gene: str, value: Any) -> GenoLOMGenome:
    return replace(genome, **{gene: value})


def viable_mutation_options(genome: GenoLOMGenome) -> list[MutationOption]:
    """Enumerate only proposal-rule mutations that leave a valid target genome.

    We do not invent mutation behavior for GenoLOM genes that the proposal does
    not operationalize in Appendices B/C. In particular, unsupported
    learningResourceType source classes simply contribute no LRT mutation.
    """
    options: list[MutationOption] = []

    for target in valid_learning_resource_mutation_targets(genome.learningResourceType):
        transition = get_learning_resource_transition(genome.learningResourceType, target)
        if transition is None or transition.action is ResourceTransformAction.DROP:
            continue
        candidate = _candidate(genome, "learningResourceType", target)
        if not validate_genome(candidate):
            options.append(MutationOption(
                "learningResourceType", genome.learningResourceType, target,
                transition.action.value, transition.requires_content_conversion,
            ))

    for target in _neighbor_values(genome.interactivityLevel, INTERACTIVITY_LEVELS):
        candidate = _candidate(genome, "interactivityLevel", target)
        if not validate_genome(candidate):
            options.append(MutationOption(
                "interactivityLevel", genome.interactivityLevel, target,
                interactivity_level_mutation_action(genome.interactivityLevel, target),
            ))

    for target in _neighbor_values(genome.semanticDensity, SEMANTIC_DENSITY_LEVELS):
        candidate = _candidate(genome, "semanticDensity", target)
        if not validate_genome(candidate):
            options.append(MutationOption(
                "semanticDensity", genome.semanticDensity, target,
                semantic_density_mutation_action(genome.semanticDensity, target),
            ))

    for target in _neighbor_values(genome.difficulty, DIFFICULTY_LEVELS):
        candidate = _candidate(genome, "difficulty", target)
        if not validate_genome(candidate):
            options.append(MutationOption(
                "difficulty", genome.difficulty, target,
                difficulty_mutation_action(genome.difficulty, target),
            ))

    return options


def mutate_individual(parent: Individual, *, rate: float, rng: random.Random) -> MutationResult:
    triggered, draw = rate_trigger(rate, rng)
    if not triggered:
        return MutationResult(
            parent.individual_id, True, False, float(rate), draw, None,
            parent.genome, (), "rate_not_triggered",
        )

    options = viable_mutation_options(parent.genome)
    if not options:
        return MutationResult(
            parent.individual_id, True, False, float(rate), draw, None,
            parent.genome, (), "no_viable_mutation",
        )

    option = rng.choice(options)
    target = _candidate(parent.genome, option.gene, option.new_value)
    issues = tuple(issue.to_dict() for issue in validate_genome(target))
    return MutationResult(
        parent.individual_id, True, not issues, float(rate), draw, option,
        target, issues, None if not issues else "target_genome_invalid",
    )
