from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LearnerStudyObservation:
    anonymous_participant_id: str
    condition_id: str
    pretest_score: float | None
    posttest_score: float | None
    completion_time_seconds: float | None = None
