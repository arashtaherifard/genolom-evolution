from pathlib import Path

from genolom_evolution.service.engine import Phase2Engine

ROOT = Path(__file__).resolve().parents[1]


def test_m6_capabilities_expose_structural_operators():
    engine = Phase2Engine(ROOT, "configs/development.yaml")
    caps = engine.capabilities()
    for name in ("fusion_execution", "defusion_execution", "composition", "decomposition"):
        assert name in caps["implemented"]
        assert name not in caps["deferred_but_hooked"]
    assert "fusion_defusion_content_realization_m5b" in caps["deferred_but_hooked"]
    assert caps["ui_contract_version"] == "1.2"
