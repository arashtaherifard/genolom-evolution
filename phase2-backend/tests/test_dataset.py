from pathlib import Path
from genolom_evolution.dataio.manifest import verify_manifest_dataset

ROOT = Path(__file__).resolve().parents[1]

def test_generation0_has_298_individuals(generation0):
    assert len(generation0) == 298

def test_generation0_ids_are_stable(generation0):
    assert generation0[0].individual_id == "G0_LO_001"
    assert generation0[-1].individual_id == "G0_LO_298"

def test_dataset_checksum_matches_manifest():
    assert verify_manifest_dataset(ROOT/"data/dataset_manifest.json", ROOT/"data/generation_0.xlsx")
