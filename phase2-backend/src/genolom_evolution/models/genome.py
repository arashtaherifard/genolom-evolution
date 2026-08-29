from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable


def _keywords(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = value.splitlines()
    elif isinstance(value, Iterable):
        items = list(value)
    else:
        items = [value]
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return tuple(out)


@dataclass(frozen=True, slots=True)
class GenoLOMGenome:
    interactivityType: str
    learningResourceType: str
    interactivityLevel: str
    semanticDensity: str
    intendedEndUserRole: str
    context: str
    typicalAgeRange: str
    difficulty: str
    typicalLearningTime: float
    description: str
    language: str
    keywords: tuple[str, ...]

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "GenoLOMGenome":
        return cls(
            interactivityType=str(row.get("interactivityType", "")).strip(),
            learningResourceType=str(row.get("learningResourceType", "")).strip(),
            interactivityLevel=str(row.get("interactivityLevel", "")).strip(),
            semanticDensity=str(row.get("semanticDensity", "")).strip(),
            intendedEndUserRole=str(row.get("intendedEndUserRole", "")).strip(),
            context=str(row.get("context", "")).strip(),
            typicalAgeRange=str(row.get("typicalAgeRange", "")).strip(),
            difficulty=str(row.get("difficulty", "")).strip(),
            typicalLearningTime=float(row.get("typicalLearningTime") or 0.0),
            description=str(row.get("description", "")).strip(),
            language=str(row.get("language", "")).strip(),
            keywords=_keywords(row.get("keywords")),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["keywords"] = list(self.keywords)
        return data

    def signature(self) -> tuple[Any, ...]:
        return (
            self.interactivityType,
            self.learningResourceType,
            self.interactivityLevel,
            self.semanticDensity,
            self.intendedEndUserRole,
            self.context,
            self.typicalAgeRange,
            self.difficulty,
            round(self.typicalLearningTime, 6),
            self.language,
            self.keywords,
        )
