from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(frozen=True, slots=True)
class EvolutionEvent:
    event_type: str
    generation: int
    individual_ids: tuple[str, ...] = ()
    parent_ids: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["individual_ids"] = list(self.individual_ids)
        data["parent_ids"] = list(self.parent_ids)
        return data
