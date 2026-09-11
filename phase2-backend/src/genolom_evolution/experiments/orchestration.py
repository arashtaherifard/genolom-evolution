from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from ..evolution.session import PriorityEvolutionSession
from ..tracking.run_store import RunStore


class GenerationStep(Protocol):
    """Experiment-supplied generation policy.

    M3 deliberately does not choose mutation/crossover/operator scheduling.
    The scientific run supplies that policy explicitly and reproducibly.
    """

    def __call__(
        self,
        session: PriorityEvolutionSession,
        generation: int,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class GenerationRunRecord:
    generation: int
    summary: dict[str, Any]
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "summary": self.summary,
            "snapshot": self.snapshot,
        }


def run_generations(
    session: PriorityEvolutionSession,
    *,
    generation_count: int,
    generation_step: GenerationStep | Callable[[PriorityEvolutionSession, int], None],
    store: RunStore | None = None,
) -> list[GenerationRunRecord]:
    """Run an explicit multi-generation schedule without inventing a policy."""

    if generation_count < 0:
        raise ValueError("generation_count must be >= 0")

    records: list[GenerationRunRecord] = []
    rejected_written = 0

    for _ in range(generation_count):
        next_generation = session.generation + 1
        generation_step(session, next_generation)
        summary = session.end_generation()
        snapshot = session.generation_snapshots[-1]

        if store is not None:
            store.write_generation_snapshot(next_generation, snapshot)
            for attempt in session.rejected_attempts[rejected_written:]:
                store.append_rejected_attempt(attempt)
            rejected_written = len(session.rejected_attempts)

        records.append(
            GenerationRunRecord(
                generation=next_generation,
                summary=summary,
                snapshot=snapshot,
            )
        )

    return records


__all__ = ["GenerationStep", "GenerationRunRecord", "run_generations"]
