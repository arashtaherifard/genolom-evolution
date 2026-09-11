from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from ..models.genome import GenoLOMGenome
from ..evolution.operator_rules import (
    INTERACTIVITY_LEVELS,
    SEMANTIC_DENSITY_LEVELS,
    DIFFICULTY_LEVELS,
)

# Frozen V1 target↔realized exact-match traits.
CONTROLLED_CATEGORICAL_TRAITS = (
    "learningResourceType",
    "interactivityType",
    "interactivityLevel",
    "semanticDensity",
    "difficulty",
)

# Frozen traits that must remain fixed during content realization.
FIXED_TRAITS = (
    "intendedEndUserRole",
    "context",
    "typicalAgeRange",
    "language",
)

_ORDINAL_SCALES: dict[str, tuple[str, ...]] = {
    "interactivityLevel": INTERACTIVITY_LEVELS,
    "semanticDensity": SEMANTIC_DENSITY_LEVELS,
    "difficulty": DIFFICULTY_LEVELS,
}


@dataclass(frozen=True, slots=True)
class GeneChange:
    field: str
    source: Any
    target: Any
    direction: str
    ordinal_delta: int | None = None
    steps: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "source": list(self.source) if isinstance(self.source, tuple) else self.source,
            "target": list(self.target) if isinstance(self.target, tuple) else self.target,
            "direction": self.direction,
            "ordinal_delta": self.ordinal_delta,
            "steps": self.steps,
        }


@dataclass(frozen=True, slots=True)
class GenomeDiff:
    """Deterministic SourceGenome→TargetGenome difference.

    No model/LLM is involved. For ordinal genes ``steps`` is exactly the frozen
    V1 definition n = abs(target_index - source_index).
    """

    source_genome: GenoLOMGenome
    target_genome: GenoLOMGenome
    changes: tuple[GeneChange, ...]

    @classmethod
    def between(cls, source: GenoLOMGenome, target: GenoLOMGenome) -> "GenomeDiff":
        changes: list[GeneChange] = []
        for f in fields(GenoLOMGenome):
            name = f.name
            before = getattr(source, name)
            after = getattr(target, name)
            if before == after:
                continue

            scale = _ORDINAL_SCALES.get(name)
            if scale is not None and before in scale and after in scale:
                delta = scale.index(after) - scale.index(before)
                changes.append(
                    GeneChange(
                        field=name,
                        source=before,
                        target=after,
                        direction="increase" if delta > 0 else "decrease",
                        ordinal_delta=delta,
                        steps=abs(delta),
                    )
                )
                continue

            if name == "typicalLearningTime":
                delta = float(after) - float(before)
                direction = "increase" if delta > 0 else "decrease"
            else:
                direction = "changed"

            changes.append(
                GeneChange(
                    field=name,
                    source=before,
                    target=after,
                    direction=direction,
                )
            )
        return cls(source, target, tuple(changes))

    @property
    def changed_fields(self) -> tuple[str, ...]:
        return tuple(change.field for change in self.changes)

    def change_for(self, field_name: str) -> GeneChange | None:
        return next((change for change in self.changes if change.field == field_name), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_genome": self.source_genome.to_dict(),
            "target_genome": self.target_genome.to_dict(),
            "changed_fields": list(self.changed_fields),
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass(frozen=True, slots=True)
class ContentPlan:
    """Milestone-3 structural content plan.

    This records *what* changed and what the current realization must control.
    Mapping those changes to proposal-native Pack/Expand/Unpack/etc. operations
    is intentionally deferred to Milestone 4.
    """

    operator_name: str
    genome_diff: GenomeDiff
    controlled_traits: tuple[str, ...]
    fixed_trait_changes: tuple[str, ...]
    proposal_native_steps: tuple[str, ...] = ()
    planning_stage: str = "m3_structural_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_name": self.operator_name,
            "genome_diff": self.genome_diff.to_dict(),
            "controlled_traits": list(self.controlled_traits),
            "fixed_trait_changes": list(self.fixed_trait_changes),
            "proposal_native_steps": list(self.proposal_native_steps),
            "planning_stage": self.planning_stage,
            "proposal_native_compilation": "deferred_to_milestone_4",
        }


def compile_structural_content_plan(
    source_genome: GenoLOMGenome,
    target_genome: GenoLOMGenome,
    *,
    operator_name: str,
) -> ContentPlan:
    diff = GenomeDiff.between(source_genome, target_genome)
    changed = set(diff.changed_fields)
    controlled = tuple(
        field for field in CONTROLLED_CATEGORICAL_TRAITS if field in changed
    )
    fixed_changes = tuple(field for field in FIXED_TRAITS if field in changed)
    return ContentPlan(
        operator_name=operator_name,
        genome_diff=diff,
        controlled_traits=controlled,
        fixed_trait_changes=fixed_changes,
    )


def target_realized_mismatches(
    target_genome: GenoLOMGenome,
    realized_genome: GenoLOMGenome,
    *,
    controlled_traits: tuple[str, ...],
) -> tuple[str, ...]:
    """Return frozen V1 exact-match violations.

    Only categorical/ordinal traits controlled by this transformation are
    exact-matched. Fixed traits are always checked. Typical learning time is
    intentionally not exact-matched here.
    """

    checked = tuple(dict.fromkeys((*controlled_traits, *FIXED_TRAITS)))
    return tuple(
        field
        for field in checked
        if getattr(target_genome, field) != getattr(realized_genome, field)
    )


__all__ = [
    "CONTROLLED_CATEGORICAL_TRAITS",
    "FIXED_TRAITS",
    "GeneChange",
    "GenomeDiff",
    "ContentPlan",
    "compile_structural_content_plan",
    "target_realized_mismatches",
]
