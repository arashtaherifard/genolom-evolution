#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from genolom_evolution.config import load_config
from genolom_evolution.experiments.genome_evolution import CompleteGenomeEvolutionRunner
from genolom_evolution.ontology.cso_adapter import CSOOntologyAdapter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete content-independent GenoLOM genome evolution from "
            "frozen Generation 0 to the requested final generation."
        )
    )
    parser.add_argument(
        "--config",
        default="configs/genome_evolution_development.yaml",
        help="Config path relative to phase2-backend (default: development genome evolution config).",
    )
    parser.add_argument("--generations", type=int, default=None, help="Override max generations.")
    parser.add_argument("--seed", type=int, default=None, help="Override run seed.")
    parser.add_argument("--run-id", default=None, help="Optional explicit immutable output run id.")
    parser.add_argument(
        "--root-topic",
        default=None,
        help="Override the CSO adapter root topic (not the frozen T_ref definition).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = ROOT / args.config
    config = load_config(config_path)

    root_topic = args.root_topic or config.get("coverage", {}).get("reference_root", "computer science")
    try:
        ontology = CSOOntologyAdapter(root_topic=root_topic)
    except Exception as exc:
        print("ERROR: could not initialize CSO ontology.", file=sys.stderr)
        print(
            "Install requirements first (`python -m pip install -r requirements.txt`) "
            "and ensure cso-classifier can load its ontology resources.",
            file=sys.stderr,
        )
        print(f"Underlying error: {exc}", file=sys.stderr)
        return 2

    runner = CompleteGenomeEvolutionRunner(config, ontology)
    result = runner.run(
        ROOT,
        generation_count=args.generations,
        seed=args.seed,
        run_id=args.run_id,
    )

    print("GENOME EVOLUTION COMPLETE")
    print(f"Run: {result.run_id}")
    print(f"Output: {result.run_path}")
    print(
        f"Generation: {result.completed_final_generation}/"
        f"{result.requested_final_generation}"
    )
    print(f"Final active population: {result.final_population_size}")
    print(f"Historical archive individuals: {result.archive_size}")
    print(f"Unique genome variants: {result.unique_genome_count}")
    print(f"Extinct: {result.extinct}")
    return 0 if not result.extinct else 3


if __name__ == "__main__":
    raise SystemExit(main())
