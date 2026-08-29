import pytest
from genolom_evolution.tracking.run_store import RunStore

def test_run_store_refuses_overwrite(tmp_path):
    s = RunStore(tmp_path, run_id="test-run")
    s.write_json_once("a.json", {"x":1})
    with pytest.raises(FileExistsError):
        s.write_json_once("a.json", {"x":2})
