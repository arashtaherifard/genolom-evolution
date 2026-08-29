from __future__ import annotations
from dataclasses import dataclass, asdict
from ..models.individual import Individual
from ..validation.genome_validator import validate_genome

MATURE_ONLY_OPERATORS = {
    "crossover", "fusion", "defusion", "composition", "decomposition"
}


@dataclass(frozen=True, slots=True)
class EligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]
    operator: str

    def to_dict(self) -> dict:
        return asdict(self)


def check_parent_eligibility(
    individual: Individual,
    *,
    operator: str,
    maturity_age: int | None = None,
    max_parent_participations_per_generation: int | None = None,
    require_fitness: bool = True,
) -> EligibilityResult:
    reasons: list[str] = []
    op = operator.strip().lower()

    if not individual.alive:
        reasons.append("not_alive")
    if validate_genome(individual.genome):
        reasons.append("invalid_genome")
    if require_fitness and individual.micro_fitness is None:
        reasons.append("fitness_missing")

    if op in MATURE_ONLY_OPERATORS and maturity_age is not None:
        if maturity_age < 0:
            raise ValueError("maturity_age must be >= 0")
        if individual.age < maturity_age:
            reasons.append("below_maturity_age")

    if max_parent_participations_per_generation is not None:
        if max_parent_participations_per_generation < 1:
            raise ValueError("max_parent_participations_per_generation must be >= 1")
        if individual.generation_participations >= max_parent_participations_per_generation:
            reasons.append("participation_limit_reached")

    return EligibilityResult(not reasons, tuple(reasons), op)
