from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum


INTERACTIVITY_TYPES = ("Active", "Expositive", "Mixed")
INTERACTIVITY_LEVELS = ("Very Low", "Low", "Medium", "High", "Very High")
SEMANTIC_DENSITY_LEVELS = ("Very Low", "Low", "Medium", "High", "Very High")
DIFFICULTY_LEVELS = ("Very Easy", "Easy", "Medium", "Difficult", "Very Difficult")

LEARNING_RESOURCE_TYPES = (
    "Headline", "Narrative Text", "Figure", "Diagram", "Graph", "Table",
    "Slide", "Question", "Exercise", "Problem Statement", "Self-Assessment",
    "Exam", "Experiment", "Simulation", "Video Clip", "Hypertext Document",
    "Formula", "Lecture", "Questionnaire", "Authoring Tool",
)

# Proposal Table 3.
INTERACTIVITY_TYPE_ALLOWED_LEVELS = {
    "Expositive": ("Very Low",),
    "Mixed": ("Low",),
    "Active": ("Medium", "High", "Very High"),
}

# Six red/impossible Table-3 combinations.
IMPOSSIBLE_SEMANTIC_DENSITY_DIFFICULTY = {
    ("Very Low", "Difficult"),
    ("Very Low", "Very Difficult"),
    ("Low", "Very Difficult"),
    ("High", "Very Easy"),
    ("Very High", "Very Easy"),
    ("Very High", "Easy"),
}

TABLE3_FIXED_EXPERIMENT_METADATA = {
    "intendedEndUserRole": "Learner",
    "context": "Higher Education",
    "typicalAgeRange": "18+",
}


# ---------------- Appendix B ----------------

APPENDIX_B_SUPPORTED_SOURCES = ("Exercise", "Question", "Problem Statement")

APPENDIX_B_TARGETS = (
    "Exercise", "Question", "Problem Statement", "Self-Assessment", "Exam",
    "Diagram", "Figure", "Graph", "Slide", "Table", "Narrative Text",
    "Video Clip", "Hypertext Document",
)


class ResourceTransformAction(StrEnum):
    UNCHANGED = "unchanged"
    SAME_AS = "is_same_as"
    DROP = "drop"
    CONVERTS_TO = "converts_to"


@dataclass(frozen=True, slots=True)
class ResourceTransition:
    source: str
    target: str
    action: ResourceTransformAction

    @property
    def is_convertible(self) -> bool:
        return self.action is not ResourceTransformAction.DROP

    @property
    def requires_content_conversion(self) -> bool:
        return self.action is ResourceTransformAction.CONVERTS_TO


_U = ResourceTransformAction.UNCHANGED
_S = ResourceTransformAction.SAME_AS
_D = ResourceTransformAction.DROP
_C = ResourceTransformAction.CONVERTS_TO

LEARNING_RESOURCE_TRANSITIONS = {
    "Exercise": {
        "Exercise": _U, "Question": _S, "Problem Statement": _S,
        "Self-Assessment": _S, "Exam": _S,
        "Diagram": _D, "Figure": _D, "Graph": _D,
        "Slide": _C, "Table": _D, "Narrative Text": _C,
        "Video Clip": _C, "Hypertext Document": _C,
    },
    "Question": {
        "Exercise": _S, "Question": _U, "Problem Statement": _D,
        "Self-Assessment": _S, "Exam": _S,
        "Diagram": _D, "Figure": _D, "Graph": _D,
        "Slide": _C, "Table": _D, "Narrative Text": _D,
        "Video Clip": _C, "Hypertext Document": _C,
    },
    "Problem Statement": {
        "Exercise": _S, "Question": _D, "Problem Statement": _U,
        "Self-Assessment": _S, "Exam": _S,
        "Diagram": _D, "Figure": _D, "Graph": _D,
        "Slide": _C, "Table": _D, "Narrative Text": _C,
        "Video Clip": _C, "Hypertext Document": _C,
    },
}

AUXILIARY_CONTENT_RULES = {
    "Question": ("Drop(Index)",),
    "Problem Statement": ("Drop(Index)",),
}


def get_learning_resource_transition(source: str, target: str):
    action = LEARNING_RESOURCE_TRANSITIONS.get(source, {}).get(target)
    return None if action is None else ResourceTransition(source, target, action)


def valid_learning_resource_mutation_targets(
    source: str,
    *,
    include_unchanged: bool = False,
) -> tuple[str, ...]:
    rules = LEARNING_RESOURCE_TRANSITIONS.get(source)
    if rules is None:
        return ()

    targets = []
    for target, action in rules.items():
        if action is ResourceTransformAction.DROP:
            continue
        if not include_unchanged and action is ResourceTransformAction.UNCHANGED:
            continue
        targets.append(target)
    return tuple(targets)


# ---------------- Appendix C ----------------

def ordinal_mutation_action(
    before: str,
    after: str,
    *,
    levels: tuple[str, ...],
    prefix: str,
) -> str:
    index = {value: i for i, value in enumerate(levels)}
    if before not in index:
        raise ValueError(f"Unknown source value: {before!r}")
    if after not in index:
        raise ValueError(f"Unknown target value: {after!r}")

    delta = index[after] - index[before]
    if delta > 0:
        return f"{prefix}Increase({delta})"
    if delta < 0:
        return f"{prefix}Decrease({abs(delta)})"
    return f"{prefix}NoChange()"


def interactivity_level_mutation_action(before: str, after: str) -> str:
    return ordinal_mutation_action(
        before, after, levels=INTERACTIVITY_LEVELS, prefix="il"
    )


def semantic_density_mutation_action(before: str, after: str) -> str:
    return ordinal_mutation_action(
        before, after, levels=SEMANTIC_DENSITY_LEVELS, prefix="sd"
    )


def difficulty_mutation_action(before: str, after: str) -> str:
    return ordinal_mutation_action(
        before, after, levels=DIFFICULTY_LEVELS, prefix="diff"
    )


# ---------------- Appendix D ----------------

INTERACTIVITY_TYPE_CROSSOVER = {
    ("Active", "Active"): "Active",
    ("Active", "Expositive"): "Mixed",
    ("Active", "Mixed"): "Mixed",
    ("Expositive", "Active"): "Mixed",
    ("Expositive", "Expositive"): "Expositive",
    ("Expositive", "Mixed"): "Mixed",
    ("Mixed", "Active"): "Mixed",
    ("Mixed", "Expositive"): "Mixed",
    ("Mixed", "Mixed"): "Mixed",
}


def _ordinal_max_matrix(levels: tuple[str, ...]):
    index = {value: i for i, value in enumerate(levels)}
    return {
        (a, b): levels[max(index[a], index[b])]
        for a in levels
        for b in levels
    }


def _symmetric_matrix(upper):
    result = dict(upper)
    for (a, b), value in list(upper.items()):
        result[(b, a)] = value
    return result


INTERACTIVITY_LEVEL_CROSSOVER = _ordinal_max_matrix(INTERACTIVITY_LEVELS)

SEMANTIC_DENSITY_CROSSOVER = _symmetric_matrix({
    ("Very Low", "Very Low"): "Very Low",
    ("Very Low", "Low"): "Very Low",
    ("Very Low", "Medium"): "Very Low",
    ("Very Low", "High"): "Very Low",
    ("Very Low", "Very High"): "Very Low",
    ("Low", "Low"): "Very Low",
    ("Low", "Medium"): "Low",
    ("Low", "High"): "Low",
    ("Low", "Very High"): "Low",
    ("Medium", "Medium"): "Low",
    ("Medium", "High"): "Medium",
    ("Medium", "Very High"): "Medium",
    ("High", "High"): "Medium",
    ("High", "Very High"): "High",
    ("Very High", "Very High"): "High",
})

DIFFICULTY_CROSSOVER = _ordinal_max_matrix(DIFFICULTY_LEVELS)

RECOMPUTE_AFTER_CONTENT_GENERATION = {
    "semanticDensity": True,
    "difficulty": True,
}


def crossover_interactivity_type(a: str, b: str) -> str:
    return INTERACTIVITY_TYPE_CROSSOVER[(a, b)]


def crossover_interactivity_level(a: str, b: str) -> str:
    return INTERACTIVITY_LEVEL_CROSSOVER[(a, b)]


def crossover_semantic_density(a: str, b: str) -> str:
    return SEMANTIC_DENSITY_CROSSOVER[(a, b)]


def crossover_difficulty(a: str, b: str) -> str:
    return DIFFICULTY_CROSSOVER[(a, b)]
