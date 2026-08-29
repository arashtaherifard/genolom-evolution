from pathlib import Path
import pytest
from genolom_evolution.dataio.generation0 import load_generation0

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session")
def generation0():
    return load_generation0(ROOT / "data" / "generation_0.xlsx")

class ToyOntology:
    name = "toy"
    def __init__(self):
        self.undirected = {("a","b"):1, ("a","c"):2, ("b","c"):1}
        self.ancestor = {("a","b"):1, ("a","c"):2, ("b","c"):1}
    def resolve_topic(self, topic): return topic if topic in {"a","b","c","d"} else None
    def undirected_distance(self, a, b):
        if a == b: return 0
        return self.undirected.get((a,b), self.undirected.get((b,a)))
    def ancestor_distance(self, a, d): return self.ancestor.get((a,d))
    def reference_topics(self): return ("a", "b", "c", "d")

@pytest.fixture
def toy_ontology(): return ToyOntology()
