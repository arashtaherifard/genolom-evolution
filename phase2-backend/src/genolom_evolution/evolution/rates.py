from __future__ import annotations
import random


def validate_rate(rate: float) -> float:
    rate = float(rate)
    if not 0.0 <= rate <= 1.0:
        raise ValueError("Operator rate must be between 0 and 1 inclusive.")
    return rate


def rate_trigger(rate: float, rng: random.Random) -> tuple[bool, float]:
    rate = validate_rate(rate)
    draw = rng.random()
    return draw < rate, draw
