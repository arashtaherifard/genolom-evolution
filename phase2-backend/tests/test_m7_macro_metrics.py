from genolom_evolution.evaluation.macro import calculate_generation_macro_metrics
from genolom_evolution.evaluation.reference import ReferenceConceptSet
from genolom_evolution.models.genome import GenoLOMGenome
from genolom_evolution.models.individual import Individual


class HierarchyOntology:
    name = "hierarchy-test"
    parents = {
        "ml": "ai",
        "nn": "ml",
        "rl": "ml",
        "db": "cs",
        "ai": "cs",
    }

    def resolve_topic(self, topic):
        value = str(topic).strip().lower()
        return value if value in {"cs", "ai", "ml", "nn", "rl", "db"} else None

    def ancestor_distance(self, ancestor, descendant):
        ancestor = self.resolve_topic(ancestor)
        descendant = self.resolve_topic(descendant)
        if ancestor is None or descendant is None:
            return None
        if ancestor == descendant:
            return 0
        current = descendant
        distance = 0
        while current in self.parents:
            current = self.parents[current]
            distance += 1
            if current == ancestor:
                return distance
        return None

    def hierarchy_path(self, ancestor, descendant):
        distance = self.ancestor_distance(ancestor, descendant)
        if distance is None:
            return None
        if distance == 0:
            return (self.resolve_topic(ancestor),)
        rev = [self.resolve_topic(descendant)]
        current = rev[0]
        while current != self.resolve_topic(ancestor):
            current = self.parents[current]
            rev.append(current)
        return tuple(reversed(rev))

    def undirected_distance(self, a, b):
        if self.resolve_topic(a) is None or self.resolve_topic(b) is None:
            return None
        if self.resolve_topic(a) == self.resolve_topic(b):
            return 0
        return 1


def genome(keywords):
    return GenoLOMGenome(
        interactivityType="Expositive",
        learningResourceType="Narrative Text",
        interactivityLevel="Very Low",
        semanticDensity="Medium",
        intendedEndUserRole="Learner",
        context="Higher Education",
        typicalAgeRange="18+",
        difficulty="Medium",
        typicalLearningTime=2.0,
        description="test",
        language="English (en)",
        keywords=tuple(keywords),
    )


def ind(identifier, keywords):
    return Individual(identifier, "", genome(keywords))


def test_macro_metrics_follow_frozen_definitions():
    ontology = HierarchyOntology()
    reference = ReferenceConceptSet(
        topics=("ai", "ml", "nn", "rl", "db"),
        unresolved_generation0_keywords=(),
        ontology_name=ontology.name,
    )
    population = [
        ind("A", ["ml", "nn"]),
        ind("B", ["ml", "rl"]),
        ind("C", ["db", "unknown"]),
    ]
    result = calculate_generation_macro_metrics(
        population, ontology, reference, generation=3, coverage_thresholds=(1, 2, 3)
    )

    # 6 LO-level keyword occurrences; 5 cover at least one reference node.
    assert result.keyword_occurrence_count == 6
    assert result.coherent_keyword_occurrence_count == 5
    assert result.coherency_rate == 5 / 6

    # Direct reference coverage: ml, nn, rl, db = 4/5.
    assert result.coverage_span == 4 / 5
    assert result.recall == result.coverage_span
    assert result.coverage_rates[1] == result.recall
    assert result.coverage_rates[2] == 1 / 5  # only ml appears in two distinct LOs
    assert result.coverage_rates[3] == 0.0

    rank = {entry.resolved_topic: entry.coverage_count for entry in result.coherency_rank}
    assert rank["ml"] == 3  # ml + nn + rl within T_ref
    assert rank["nn"] == 1
    assert rank["db"] == 1

    # ml/nn/rl form one ancestor-descendant component; db is separate.
    assert result.precision_component_count == 2
    assert result.precision_subgraph_node_count == 4
    assert result.precision == 0.75
    assert 0.0 < result.generation_f1 < 1.0
