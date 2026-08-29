from __future__ import annotations
from dataclasses import dataclass
import random


@dataclass(slots=True)
class RunContext:
    seed: int

    def __post_init__(self):
        self.rng = random.Random(self.seed)
