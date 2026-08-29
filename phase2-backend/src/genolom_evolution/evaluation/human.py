from __future__ import annotations
from dataclasses import dataclass, asdict


@dataclass(frozen=True, slots=True)
class HumanEvaluationItem:
    item_id: str
    individual_id: str
    blinded_condition: str
    content: str


@dataclass(frozen=True, slots=True)
class HumanRatingRecord:
    evaluator_id: str
    item_id: str
    dimension: str
    score: float
    notes: str = ""

    def to_dict(self):
        return asdict(self)
