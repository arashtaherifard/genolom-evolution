from dataclasses import replace
from copy import deepcopy
import pytest

from genolom_evolution.fitness.dependence import calculate_dependence
from genolom_evolution.fitness.micro import calculate_micro_fitness
from genolom_evolution.evaluation.coverage import calculate_coverage


def test_dependence_is_canonical_name(toy_ontology):
    assert calculate_dependence(["a", "b", "c"], toy_ontology) == pytest.approx(2/3)


def test_micro_result_exposes_dependence_and_legacy_alias(toy_ontology):
    r = calculate_micro_fitness(["a", "b", "c"], toy_ontology)
    assert r.dependence == pytest.approx(2/3)
    assert r.coherence == r.dependence
    assert r.to_dict()["coherence"] == r.dependence


def test_coverage_span_and_threshold(generation0, toy_ontology):
    # Build two LOs covering a/b and b/c, so 3 of 4 reference nodes are covered.
    a = deepcopy(generation0[0])
    b = deepcopy(generation0[1])
    a.genome = replace(a.genome, keywords=("a", "b"))
    b.genome = replace(b.genome, keywords=("b", "c"))
    result = calculate_coverage([a, b], toy_ontology, coverage_threshold=2)
    assert result.coverage_span == pytest.approx(3/4)
    assert result.coverage_rate == pytest.approx(1/4)
    assert result.topic_resource_counts["b"] == 2


def test_coverage_counts_resources_not_duplicate_keywords(generation0, toy_ontology):
    x = deepcopy(generation0[2])
    x.genome = replace(x.genome, keywords=("a", "a", "b"))
    result = calculate_coverage([x], toy_ontology, coverage_threshold=1)
    assert result.topic_resource_counts == {"a": 1, "b": 1}


def test_coverage_threshold_must_be_positive(generation0, toy_ontology):
    with pytest.raises(ValueError):
        calculate_coverage(generation0[:1], toy_ontology, coverage_threshold=0)
