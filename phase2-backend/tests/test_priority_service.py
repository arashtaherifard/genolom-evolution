from pathlib import Path
import json

from genolom_evolution.service.engine import Phase2Engine

ROOT = Path(__file__).resolve().parents[1]


def test_service_capabilities_expose_priority_rows():
    engine = Phase2Engine(ROOT)
    caps = engine.capabilities()
    required = {
        "mutation_execution", "crossover_execution", "parent_eligibility",
        "abstraction_operator", "elaboration_operator", "probing_operator",
        "longevity_chance", "age", "perish", "fusion_history",
        "defusion_history", "coverage_span", "coverage_threshold",
    }
    assert required.issubset(set(caps["implemented"]))


def test_service_mutation_preview_is_serializable():
    engine = Phase2Engine(ROOT)
    result = engine.preview_mutation("G0_LO_001", rate=1.0, seed=1).to_dict()
    json.dumps(result)
    assert result["ok"] is True
    assert result["data"]["target_genome"]


def test_service_content_operator_contracts_are_ui_ready():
    engine = Phase2Engine(ROOT)
    result = engine.content_operator_contracts().to_dict()
    json.dumps(result)
    assert result["ok"] is True
    assert {x["name"] for x in result["data"]} == {"abstraction", "elaboration", "probing"}


def test_service_fusion_status_is_serializable():
    engine = Phase2Engine(ROOT)
    result = engine.fusion_defusion_status("G0_LO_001").to_dict()
    json.dumps(result)
    assert result["ok"] is True
    assert result["data"]["fusion_count"] == 0
