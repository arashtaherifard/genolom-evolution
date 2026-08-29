from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genolom_evolution.service.engine import Phase2Engine
from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator


class SmokeOntology:
    """Offline test double; never use for scientific results."""
    name = "smoke-test-ontology"

    def __init__(self, topics):
        self._topics = tuple(sorted(set(topics)))

    def resolve_topic(self, topic):
        return topic if topic in self._topics else None

    def undirected_distance(self, a, b):
        if a not in self._topics or b not in self._topics:
            return None
        return 0 if a == b else 1

    def ancestor_distance(self, a, b):
        return None

    def reference_topics(self):
        return self._topics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-cso", action="store_true", help="Use the real CSO ontology instead of the offline smoke double.")
    args = parser.parse_args()

    if args.with_cso:
        from genolom_evolution.ontology.cso_adapter import CSOOntologyAdapter
        ontology = CSOOntologyAdapter()
    else:
        # Get topics without creating a service session first.
        from genolom_evolution.dataio.generation0 import load_generation0
        pop = load_generation0(ROOT / "data" / "generation_0.xlsx")
        ontology = SmokeOntology(k for i in pop for k in i.genome.keywords)

    engine = Phase2Engine(
        ROOT,
        "configs/development.yaml",
        ontology=ontology,
        content_generator=DeterministicTestGenerator(),
        content_validator=AcceptingTestValidator(),
    )

    metrics = engine.compute_priority_metrics()
    session = engine.start_priority_session(seed=17)

    # Mutation path
    mutation_parent = "G0_LO_001"
    mutation = engine.session_apply_mutation(mutation_parent, force_rate=1.0)
    mutation_child = mutation.data["offspring"]["individual_id"] if mutation.ok and mutation.data.get("offspring") else None
    content = None
    if mutation_child:
        content = engine.session_apply_content_operator(mutation_child, "abstraction")

    end_generation = engine.session_end_generation() if content and content.ok else None

    # After one completed generation, G0 parents have age 1 and can satisfy the
    # development maturity_age=1 for crossover.
    engine.compute_priority_metrics()
    crossover = engine.session_apply_crossover("G0_LO_001", "G0_LO_002", force_rate=1.0)
    crossover_child = crossover.data["offspring"]["individual_id"] if crossover.ok and crossover.data.get("offspring") else None
    crossover_content = None
    if crossover_child:
        crossover_content = engine.session_apply_content_operator(crossover_child, "elaboration")

    out = {
        "warning": "SmokeOntology and deterministic content generator are test doubles unless --with-cso is used. Do not use this script's test-double results as paper evidence.",
        "metrics_ok": metrics.ok,
        "coverage": None if not metrics.ok else metrics.data["coverage"],
        "session": session.to_dict(),
        "mutation": mutation.to_dict(),
        "mutation_content": None if content is None else content.to_dict(),
        "generation_transition": None if end_generation is None else end_generation.to_dict(),
        "crossover": crossover.to_dict(),
        "crossover_content": None if crossover_content is None else crossover_content.to_dict(),
        "snapshot": engine.session_snapshot().to_dict(),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
