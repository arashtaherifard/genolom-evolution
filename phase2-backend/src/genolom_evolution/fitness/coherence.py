"""Backward-compatible alias.

Milestone 2 adopts the proposal/task-sheet term ``Dependence`` as the canonical
individual-level variable. Existing imports of ``calculate_coherence`` continue
to work and delegate to the same frozen V1 proxy.
"""
from .dependence import calculate_dependence


def calculate_coherence(keywords, ontology):
    return calculate_dependence(keywords, ontology)
