from genolom_evolution.tracking.events import EvolutionEvent
from genolom_evolution.tracking.lineage import LineageTracker

def test_lineage_recovers_ancestors():
    t = LineageTracker()
    t.record(EvolutionEvent("mutation", 1, ("c1",), ("p0",)))
    t.record(EvolutionEvent("crossover", 2, ("c2",), ("c1","p1")))
    assert t.ancestors_of("c2") == {"c1","p0","p1"}
