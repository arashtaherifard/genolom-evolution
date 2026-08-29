from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True, slots=True)
class ServiceResult:
    ok: bool
    data: Any = None
    errors: tuple[dict, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)
