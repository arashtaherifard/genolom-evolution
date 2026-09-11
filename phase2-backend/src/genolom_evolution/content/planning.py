from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from ..models.genome import GenoLOMGenome
from ..evolution.operator_rules import (
    INTERACTIVITY_LEVELS,
    SEMANTIC_DENSITY_LEVELS,
    DIFFICULTY_LEVELS,
)
from .proposal_rules import (
    APPENDIX_A_REFERENCE,
    APPENDIX_B_REFERENCE,
    DEFAULT_PROPOSAL_RULES,
    OperationTemplate,
    ProposalRuleSet,
    RULE_PROPOSAL_DEFINED,
    RULE_OPERATIONALIZATION,
    RULE_UNSUPPORTED,
    RULE_DEFERRED,
)

# Frozen V1 target<->realized exact-match traits.
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
    """Deterministic SourceGenome->TargetGenome difference.

    No model/LLM is involved. For ordinal genes ``steps`` is exactly the frozen
    V1 definition n = abs(target_index - source_index), matching Appendix C.
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
class ProposalStep:
    """One deterministic low-level realization instruction."""

    operation: str
    field: str | None = None
    n: int | None = None
    source: Any = None
    target: Any = None
    origin: str = RULE_PROPOSAL_DEFINED
    argument: str | None = None
    proposal_reference: str | None = None

    @property
    def label(self) -> str:
        if self.n is not None:
            return f"{self.operation}({self.n})"
        if self.argument is not None:
            return f"{self.operation}({self.argument})"
        return (
            f"{self.operation}()"
            if self.operation in {"Export2HTML", "Drop", "is_Same_as", "Converts_to"}
            else self.operation
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "label": self.label,
            "field": self.field,
            "n": self.n,
            "argument": self.argument,
            "source": self.source,
            "target": self.target,
            "origin": self.origin,
            "proposal_reference": self.proposal_reference,
        }


@dataclass(frozen=True, slots=True)
class PlanningIssue:
    """A visible scientific/implementation limitation discovered while planning."""

    code: str
    field: str | None
    message: str
    classification: str
    blocking: bool = True
    proposal_reference: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "classification": self.classification,
            "blocking": self.blocking,
            "proposal_reference": self.proposal_reference,
        }


@dataclass(frozen=True, slots=True)
class DirectionalExpectation:
    """A non-exact validation constraint such as typicalLearningTime direction."""

    field: str
    direction: str
    source_value: float
    target_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "direction": self.direction,
            "source_value": self.source_value,
            "target_value": self.target_value,
        }


@dataclass(frozen=True, slots=True)
class ContentPlan:
    """Deterministic Source->Target realization plan.

    The first six fields preserve the Milestone-3 structural-plan contract.
    Milestone 4 appends proposal-native steps, visible planning issues, and
    directional constraints without changing the evolutionary TargetGenome.
    """

    operator_name: str
    genome_diff: GenomeDiff
    controlled_traits: tuple[str, ...]
    fixed_trait_changes: tuple[str, ...]
    proposal_native_steps: tuple[str, ...] = ()
    planning_stage: str = "m3_structural_only"

    # M4 additions are appended for backward-compatible construction.
    step_specs: tuple[ProposalStep, ...] = ()
    issues: tuple[PlanningIssue, ...] = ()
    directional_expectations: tuple[DirectionalExpectation, ...] = ()

    @property
    def executable(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    @property
    def planning_status(self) -> str:
        return "ready" if self.executable else "blocked"

    def to_dict(self) -> dict[str, Any]:
        data = {
            "operator_name": self.operator_name,
            "genome_diff": self.genome_diff.to_dict(),
            "controlled_traits": list(self.controlled_traits),
            "fixed_trait_changes": list(self.fixed_trait_changes),
            "proposal_native_steps": list(self.proposal_native_steps),
            "planning_stage": self.planning_stage,
            "planning_status": self.planning_status,
            "executable": self.executable,
            "step_specs": [step.to_dict() for step in self.step_specs],
            "issues": [issue.to_dict() for issue in self.issues],
            "directional_expectations": [
                item.to_dict() for item in self.directional_expectations
            ],
        }
        if self.planning_stage == "m3_structural_only":
            data["proposal_native_compilation"] = "deferred_to_milestone_4"
        else:
            data["proposal_native_compilation"] = "compiled_from_proposal_appendices"
        return data


def compile_structural_content_plan(
    source_genome: GenoLOMGenome,
    target_genome: GenoLOMGenome,
    *,
    operator_name: str,
) -> ContentPlan:
    """Preserve the Milestone-3 structural planner for compatibility."""

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


def _append_template_steps(
    steps: list[ProposalStep],
    templates: tuple[OperationTemplate, ...],
    *,
    field: str,
    change: GeneChange,
) -> None:
    for template in templates:
        steps.append(
            ProposalStep(
                operation=template.operation,
                field=field,
                n=change.steps if template.uses_n else None,
                source=change.source,
                target=change.target,
                origin=template.origin,
                argument=template.argument,
                proposal_reference=template.proposal_reference,
            )
        )


def _append_appendix_a_family(
    *,
    rules: ProposalRuleSet,
    source_resource_type: str,
    action_family: str,
    field: str,
    change: GeneChange,
    steps: list[ProposalStep],
    issues: list[PlanningIssue],
) -> None:
    templates = rules.content_operations_for(source_resource_type, action_family)
    if templates is None:
        issues.append(
            PlanningIssue(
                code="appendix_a_rule_not_defined_for_source_lrt",
                field=field,
                message=(
                    f"Appendix A does not define {action_family} for source "
                    f"learningResourceType {source_resource_type!r}; realization is "
                    "blocked rather than inventing an operation."
                ),
                classification=RULE_UNSUPPORTED,
                blocking=True,
                proposal_reference=APPENDIX_A_REFERENCE,
            )
        )
        return
    _append_template_steps(steps, templates, field=field, change=change)


def compile_proposal_content_plan(
    source_genome: GenoLOMGenome,
    target_genome: GenoLOMGenome,
    *,
    operator_name: str,
    rules: ProposalRuleSet | None = None,
) -> ContentPlan:
    """Compile Source->Target metadata changes from the proposal tables.

    Appendix A supplies source-LRT-specific content operations, Appendix B
    supplies LearningResourceType transitions, and Appendix C determines the
    ordinal direction/distance represented by GenomeDiff. Undefined proposal
    rules are blocking; this compiler never fills a scientific gap with an LLM
    or a guessed transition.
    """

    rules = DEFAULT_PROPOSAL_RULES if rules is None else rules
    structural = compile_structural_content_plan(
        source_genome, target_genome, operator_name=operator_name
    )
    diff = structural.genome_diff
    steps: list[ProposalStep] = []
    issues: list[PlanningIssue] = []
    expectations: list[DirectionalExpectation] = []

    for field in structural.fixed_trait_changes:
        issues.append(
            PlanningIssue(
                code="fixed_trait_change",
                field=field,
                message=f"Fixed trait {field} must not change during content realization.",
                classification=RULE_PROPOSAL_DEFINED,
            )
        )

    source_lrt = source_genome.learningResourceType

    # Appendix A: interactivityLevel, semanticDensity, difficulty operations are
    # source-learningResourceType dependent. Do not reduce the table to a
    # generic Add/Remove/Pack/Expand mapping.
    level_change = diff.change_for("interactivityLevel")
    if level_change is not None:
        _append_appendix_a_family(
            rules=rules,
            source_resource_type=source_lrt,
            action_family=(
                "ilIncrease" if level_change.direction == "increase" else "ilDecrease"
            ),
            field="interactivityLevel",
            change=level_change,
            steps=steps,
            issues=issues,
        )

    density_change = diff.change_for("semanticDensity")
    if density_change is not None:
        _append_appendix_a_family(
            rules=rules,
            source_resource_type=source_lrt,
            action_family=(
                "sdIncrease" if density_change.direction == "increase" else "sdDecrease"
            ),
            field="semanticDensity",
            change=density_change,
            steps=steps,
            issues=issues,
        )

    difficulty_change = diff.change_for("difficulty")
    if difficulty_change is not None:
        _append_appendix_a_family(
            rules=rules,
            source_resource_type=source_lrt,
            action_family=(
                "diffIncrease"
                if difficulty_change.direction == "increase"
                else "diffDecrease"
            ),
            field="difficulty",
            change=difficulty_change,
            steps=steps,
            issues=issues,
        )

    # The proposal tables do not define a standalone content operation for an
    # interactivityType-only mutation. Keep it as a target constraint; do not
    # invent a transformation. Appendix C groups interactivity-level rows by
    # Expositive/Mixed/Active but gives ilIncrease/ilDecrease actions.
    type_change = diff.change_for("interactivityType")
    if type_change is not None:
        rule = rules.interactivity_type_rule(type_change.source, type_change.target)
        if rule is not None:
            steps.append(
                ProposalStep(
                    operation=rule.operation,
                    field=type_change.field,
                    source=type_change.source,
                    target=type_change.target,
                    origin=rule.origin,
                )
            )
        else:
            issues.append(
                PlanningIssue(
                    code="interactivity_type_target_constraint_only",
                    field="interactivityType",
                    message=(
                        "Appendices A-C do not specify a standalone low-level content "
                        "operation for this interactivityType change; the target remains "
                        "a controlled metadata constraint."
                    ),
                    classification=RULE_DEFERRED,
                    blocking=False,
                )
            )

    # Appendix B: exact source->target LearningResourceType rule.
    resource_change = diff.change_for("learningResourceType")
    if resource_change is not None:
        rule = rules.resource_type_rule(resource_change.source, resource_change.target)
        if rule is None:
            issues.append(
                PlanningIssue(
                    code="appendix_b_transition_not_defined",
                    field="learningResourceType",
                    message=(
                        f"Appendix B does not define a LearningResourceType transition "
                        f"from {resource_change.source!r} to {resource_change.target!r}. "
                        "Realization is blocked rather than inventing a conversion."
                    ),
                    classification=RULE_UNSUPPORTED,
                    blocking=True,
                    proposal_reference=APPENDIX_B_REFERENCE,
                )
            )
        else:
            steps.append(
                ProposalStep(
                    operation=rule.operation,
                    field=resource_change.field,
                    source=resource_change.source,
                    target=resource_change.target,
                    origin=rule.origin,
                    argument=None,
                    proposal_reference=rule.proposal_reference,
                )
            )
            if rule.blocks_realization:
                issues.append(
                    PlanningIssue(
                        code="appendix_b_drop_transition",
                        field="learningResourceType",
                        message=(
                            f"Appendix B marks {resource_change.source!r} -> "
                            f"{resource_change.target!r} as Drop()/not convertible."
                        ),
                        classification=RULE_PROPOSAL_DEFINED,
                        blocking=True,
                        proposal_reference=rule.proposal_reference,
                    )
                )

    time_change = diff.change_for("typicalLearningTime")
    if time_change is not None:
        # Frozen V1: learning time is not exact-matched and is not treated as
        # semantic density/length. Only direction consistency is required when
        # a target explicitly expects an increase/decrease.
        expectations.append(
            DirectionalExpectation(
                field="typicalLearningTime",
                direction=time_change.direction,
                source_value=float(time_change.source),
                target_value=float(time_change.target),
            )
        )

    # Implementation capability gate. This does not redefine the proposal; it
    # prevents a text generator from pretending to have produced an artifact.
    if target_genome.learningResourceType in rules.unsupported_resource_types:
        issues.append(
            PlanningIssue(
                code="UNSUPPORTED_REALIZATION",
                field="learningResourceType",
                message=(
                    f"Phase-2 V1 has no artifact renderer for learningResourceType "
                    f"{target_genome.learningResourceType!r}."
                ),
                classification=RULE_OPERATIONALIZATION,
                blocking=True,
            )
        )

    # Description is generated content and keywords are re-extracted later;
    # neither gets a synthetic proposal operation.
    actionable_changed_fields = {
        change.field
        for change in diff.changes
        if change.field not in {"description", "keywords", "typicalLearningTime"}
    }
    if not steps and not issues and not actionable_changed_fields:
        steps.append(
            ProposalStep(
                operation="NOP",
                origin=RULE_PROPOSAL_DEFINED,
                proposal_reference=APPENDIX_A_REFERENCE,
            )
        )

    return ContentPlan(
        operator_name=operator_name,
        genome_diff=diff,
        controlled_traits=structural.controlled_traits,
        fixed_trait_changes=structural.fixed_trait_changes,
        proposal_native_steps=tuple(step.label for step in steps),
        planning_stage="m4_proposal_exact_v2",
        step_specs=tuple(steps),
        issues=tuple(issues),
        directional_expectations=tuple(expectations),
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


def target_realized_direction_mismatches(
    content_plan: ContentPlan,
    realized_genome: GenoLOMGenome,
) -> tuple[str, ...]:
    """Return direction-consistency violations for non-exact M4 constraints."""

    mismatches: list[str] = []
    for expectation in content_plan.directional_expectations:
        if expectation.field != "typicalLearningTime":
            continue
        realized_value = float(getattr(realized_genome, expectation.field))
        if (
            expectation.direction == "increase"
            and realized_value <= expectation.source_value
        ):
            mismatches.append(expectation.field)
        elif (
            expectation.direction == "decrease"
            and realized_value >= expectation.source_value
        ):
            mismatches.append(expectation.field)
    return tuple(mismatches)


__all__ = [
    "CONTROLLED_CATEGORICAL_TRAITS",
    "FIXED_TRAITS",
    "GeneChange",
    "GenomeDiff",
    "ProposalStep",
    "PlanningIssue",
    "DirectionalExpectation",
    "ContentPlan",
    "compile_structural_content_plan",
    "compile_proposal_content_plan",
    "target_realized_mismatches",
    "target_realized_direction_mismatches",
]
