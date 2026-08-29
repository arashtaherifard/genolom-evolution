from __future__ import annotations
from dataclasses import dataclass, asdict
from ..models.individual import Individual


@dataclass(frozen=True, slots=True)
class FusionDefusionThreshold:
    """Allowed operation-count interval for Fusion/Defusion history.

    The updated priority scope requires the histories and threshold to be
    operational. Actual Fusion/Defusion genome transformations remain a later
    operator milestone because their non-blue rule rows/matrices are not yet
    frozen. This policy can already gate and record those future operations.
    """
    minimum: int = 0
    maximum: int | None = None

    def __post_init__(self):
        if self.minimum < 0:
            raise ValueError("minimum must be >= 0")
        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("maximum must be >= minimum")

    def allows_another(self, count: int) -> bool:
        """Whether another operation can be applied before the upper limit.

        ``minimum`` is retained as the lower threshold reported by the proposal;
        it is not used to block the first operation (which would make a positive
        minimum unreachable). Consumers can separately inspect whether the lower
        threshold has been reached.
        """
        return self.maximum is None or count < self.maximum

    def meets_minimum(self, count: int) -> bool:
        return count >= self.minimum

    def can_fuse(self, individual: Individual) -> bool:
        return self.allows_another(individual.fusion_count)

    def can_defuse(self, individual: Individual) -> bool:
        return self.allows_another(individual.defusion_count)

    def to_dict(self) -> dict:
        return asdict(self)


def record_fusion_participation(individual: Individual, event_id: str, threshold: FusionDefusionThreshold) -> None:
    if not threshold.can_fuse(individual):
        raise ValueError("Fusion threshold does not allow another fusion participation.")
    individual.record_fusion(event_id)


def record_defusion_participation(individual: Individual, event_id: str, threshold: FusionDefusionThreshold) -> None:
    if not threshold.can_defuse(individual):
        raise ValueError("Defusion threshold does not allow another defusion participation.")
    individual.record_defusion(event_id)
