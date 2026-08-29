from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genolom_evolution.config import load_config
from genolom_evolution.experiments.runner import ExperimentRunner


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--with-ontology", action="store_true")
    args = parser.parse_args()

    config = load_config(ROOT / args.config)
    ontology = None
    if args.with_ontology:
        from genolom_evolution.ontology.cso_adapter import CSOOntologyAdapter
        ontology = CSOOntologyAdapter()

    result = ExperimentRunner(config, ontology=ontology).initial_analysis(ROOT)
    summary = {k: v for k, v in result.items() if k != "population"}
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
