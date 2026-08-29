from .base import ContentOperationResult, ContentOperator, BaseContentOperator
from .abstraction import AbstractionOperator
from .elaboration import ElaborationOperator
from .probing import ProbingOperator


def get_content_operator(name: str):
    key = name.strip().lower()
    mapping = {
        "abstraction": AbstractionOperator,
        "elaboration": ElaborationOperator,
        "probing": ProbingOperator,
    }
    if key not in mapping:
        raise ValueError(f"Unknown content operator: {name}")
    return mapping[key]()


__all__ = [
    "ContentOperationResult", "ContentOperator", "BaseContentOperator",
    "AbstractionOperator", "ElaborationOperator", "ProbingOperator",
    "get_content_operator",
]
