from __future__ import annotations

from typing import NewType

from .genome import GenoLOMGenome

# Semantic/typing roles only.  At runtime the payload remains a GenoLOMGenome so
# existing validation and serialization code stays compatible.
TargetGenome = NewType("TargetGenome", GenoLOMGenome)
RealizedGenome = NewType("RealizedGenome", GenoLOMGenome)

__all__ = ["TargetGenome", "RealizedGenome"]
