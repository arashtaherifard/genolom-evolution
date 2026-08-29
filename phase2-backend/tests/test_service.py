from pathlib import Path
import json
from genolom_evolution.service.engine import Phase2Engine

ROOT = Path(__file__).resolve().parents[1]

def test_service_is_ui_serializable():
    engine = Phase2Engine(ROOT)
    result = engine.preflight().to_dict()
    json.dumps(result)
    assert result["ok"] is True
    assert result["data"]["population_size"] == 298
    assert result["data"]["invalid_individual_count"] == 0

def test_service_unknown_individual_is_structured_error():
    engine = Phase2Engine(ROOT)
    result = engine.get_individual("nope").to_dict()
    assert result["ok"] is False
    assert result["errors"][0]["code"] == "not_found"
