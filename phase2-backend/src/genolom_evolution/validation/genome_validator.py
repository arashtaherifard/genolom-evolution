from __future__ import annotations
from dataclasses import dataclass
from ..models.genome import GenoLOMGenome
from .proposal_rules import (
    INTERACTIVITY_TYPES, INTERACTIVITY_LEVELS, SEMANTIC_DENSITIES, DIFFICULTIES,
    LEARNING_RESOURCE_TYPES, FIXED_METADATA, ALLOWED_INTERACTIVITY_LEVELS,
    FORBIDDEN_SEMANTIC_DIFFICULTY,
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}


def validate_genome(genome: GenoLOMGenome) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def vocab(field: str, value: str, allowed: set[str]) -> None:
        if value not in allowed:
            issues.append(ValidationIssue("invalid_vocabulary", field, f"{value!r} is not allowed."))

    vocab("interactivityType", genome.interactivityType, INTERACTIVITY_TYPES)
    vocab("learningResourceType", genome.learningResourceType, LEARNING_RESOURCE_TYPES)
    vocab("interactivityLevel", genome.interactivityLevel, INTERACTIVITY_LEVELS)
    vocab("semanticDensity", genome.semanticDensity, SEMANTIC_DENSITIES)
    vocab("difficulty", genome.difficulty, DIFFICULTIES)

    for field, expected in FIXED_METADATA.items():
        actual = getattr(genome, field)
        if actual != expected:
            issues.append(ValidationIssue("fixed_metadata_mismatch", field, f"Expected {expected!r}; got {actual!r}."))

    allowed_levels = ALLOWED_INTERACTIVITY_LEVELS.get(genome.interactivityType)
    if allowed_levels is not None and genome.interactivityLevel not in allowed_levels:
        issues.append(ValidationIssue(
            "interactivity_constraint",
            "interactivityLevel",
            f"{genome.interactivityType} requires one of {sorted(allowed_levels)}; got {genome.interactivityLevel!r}.",
        ))

    if (genome.semanticDensity, genome.difficulty) in FORBIDDEN_SEMANTIC_DIFFICULTY:
        issues.append(ValidationIssue(
            "forbidden_semantic_difficulty",
            "semanticDensity,difficulty",
            f"Forbidden pair: {genome.semanticDensity} + {genome.difficulty}.",
        ))

    if genome.typicalLearningTime < 0:
        issues.append(ValidationIssue("negative_learning_time", "typicalLearningTime", "Learning time cannot be negative."))
    if not genome.description:
        issues.append(ValidationIssue("missing_value", "description", "Description is required."))
    if not genome.language:
        issues.append(ValidationIssue("missing_value", "language", "Language is required."))

    return issues
