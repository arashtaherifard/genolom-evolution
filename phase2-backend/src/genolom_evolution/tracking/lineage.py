from __future__ import annotations
from collections import defaultdict
from .events import EvolutionEvent


class LineageTracker:
    def __init__(self):
        self.events: list[EvolutionEvent] = []
        self.parents: dict[str, tuple[str, ...]] = {}
        self.children: dict[str, list[str]] = defaultdict(list)

    def record(self, event: EvolutionEvent) -> None:
        self.events.append(event)
        for child in event.individual_ids:
            if event.parent_ids:
                self.parents[child] = event.parent_ids
                for parent in event.parent_ids:
                    if child not in self.children[parent]:
                        self.children[parent].append(child)

    def ancestors_of(self, individual_id: str) -> set[str]:
        out: set[str] = set()
        stack = list(self.parents.get(individual_id, ()))
        while stack:
            node = stack.pop()
            if node in out:
                continue
            out.add(node)
            stack.extend(self.parents.get(node, ()))
        return out

    def to_dict(self) -> dict:
        return {
            "parents": {k: list(v) for k, v in self.parents.items()},
            "children": {k: list(v) for k, v in self.children.items()},
            "events": [e.to_dict() for e in self.events],
        }
