from __future__ import annotations

import hashlib


def derive_event_seed(
    run_seed: int,
    generation: int,
    individual_id: str,
    operator: str,
    purpose: str,
) -> int:
    """Stable event-specific seed independent of Python's randomized hash()."""

    payload = "\x1f".join(
        [str(run_seed), str(generation), str(individual_id), str(operator), str(purpose)]
    ).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    # 64 bits is ample for random.Random while remaining JSON-friendly.
    return int.from_bytes(digest[:8], "big", signed=False)


__all__ = ["derive_event_seed"]
