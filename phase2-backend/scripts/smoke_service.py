from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genolom_evolution.service.engine import Phase2Engine

engine = Phase2Engine(ROOT)
print(json.dumps({
    "capabilities": engine.capabilities(),
    "dataset": engine.dataset_info().to_dict(),
    "preflight": engine.preflight().to_dict(),
    "sample_individual": engine.get_individual("G0_LO_001").to_dict(),
}, indent=2, ensure_ascii=False))
