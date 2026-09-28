from __future__ import annotations

"""Proposal-native learning-resource compatibility matrices.

Figure 14 (Metamorphosis Matrix) is a directed eligibility matrix: a row
resource type may transform to a checked column resource type.  Figure 15
(Composition Matrix) marks every listed pair as composable.

These tables answer only *whether* a genome-level transition/composition is
eligible.  Appendix-B content rules answer *how* a supported content
realization should be performed later; the absence of an Appendix-B rule does
not invalidate a Figure-14-allowed target genome.
"""

METAMORPHOSIS_RESOURCE_TYPES: tuple[str, ...] = (
    "Simulation",
    "Question",
    "Exercise",
    "Problem Statement",
    "Experiment",
    "Exam",
    "Self-Assessment",
    "Video Clip",
    "Hypertext Document",
    "Diagram",
    "Figure",
    "Graph",
    "Slide",
    "Table",
    "Headline",
    "Narrative Text",
    "Formula",
)

# Proposal Figure 14, transcribed as directed checked cells.
_METAMORPHOSIS_ALLOWED: dict[str, tuple[str, ...]] = {
    "Simulation": ("Simulation", "Experiment", "Video Clip", "Slide"),
    "Question": ("Question", "Exam", "Self-Assessment"),
    "Exercise": ("Question", "Exercise", "Experiment", "Exam", "Self-Assessment"),
    "Problem Statement": ("Problem Statement",),
    "Experiment": ("Simulation", "Exercise", "Experiment", "Self-Assessment"),
    "Exam": ("Question", "Exercise", "Exam"),
    "Self-Assessment": ("Question", "Self-Assessment"),
    "Video Clip": ("Simulation", "Video Clip"),
    "Hypertext Document": (
        "Problem Statement",
        "Exam",
        "Hypertext Document",
        "Headline",
        "Narrative Text",
    ),
    "Diagram": ("Experiment", "Diagram", "Figure", "Graph", "Table"),
    "Figure": ("Experiment", "Diagram", "Figure", "Graph"),
    "Graph": ("Experiment", "Video Clip", "Diagram", "Figure", "Graph"),
    "Slide": ("Simulation", "Video Clip", "Slide"),
    "Table": ("Experiment", "Table"),
    "Headline": ("Hypertext Document", "Headline"),
    "Narrative Text": ("Problem Statement", "Hypertext Document", "Narrative Text"),
    "Formula": ("Exercise", "Formula"),
}

METAMORPHOSIS_MATRIX: dict[str, dict[str, bool]] = {
    source: {
        target: target in _METAMORPHOSIS_ALLOWED[source]
        for target in METAMORPHOSIS_RESOURCE_TYPES
    }
    for source in METAMORPHOSIS_RESOURCE_TYPES
}


def is_metamorphosis_allowed(source: str, target: str) -> bool:
    """Return the exact Figure-14 eligibility decision.

    Resource types not shown in Figure 14 are deliberately unsupported rather
    than guessed.
    """

    return bool(METAMORPHOSIS_MATRIX.get(str(source), {}).get(str(target), False))


def metamorphosis_targets(source: str, *, include_identity: bool = False) -> tuple[str, ...]:
    row = METAMORPHOSIS_MATRIX.get(str(source))
    if row is None:
        return ()
    return tuple(
        target
        for target in METAMORPHOSIS_RESOURCE_TYPES
        if row[target] and (include_identity or target != source)
    )


# Proposal Figure 15: every displayed pair is checked.  We still materialize
# the matrix explicitly so provenance/tests remain tied to the proposal table
# rather than a hidden unconditional ``return True``.
COMPOSITION_MATRIX: dict[str, dict[str, bool]] = {
    source: {target: True for target in METAMORPHOSIS_RESOURCE_TYPES}
    for source in METAMORPHOSIS_RESOURCE_TYPES
}


def is_composition_allowed(resource_a: str, resource_b: str) -> bool:
    return bool(COMPOSITION_MATRIX.get(str(resource_a), {}).get(str(resource_b), False))


def are_composition_parents_compatible(resource_types: tuple[str, ...] | list[str]) -> bool:
    values = tuple(str(value) for value in resource_types)
    if len(values) < 2:
        return False
    for index, left in enumerate(values):
        for right in values[index + 1 :]:
            if not is_composition_allowed(left, right):
                return False
            if not is_composition_allowed(right, left):
                return False
    return True


__all__ = [
    "METAMORPHOSIS_RESOURCE_TYPES",
    "METAMORPHOSIS_MATRIX",
    "COMPOSITION_MATRIX",
    "is_metamorphosis_allowed",
    "metamorphosis_targets",
    "is_composition_allowed",
    "are_composition_parents_compatible",
]
