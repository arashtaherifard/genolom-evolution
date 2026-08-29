import pytest
from genolom_evolution.fitness.cohesion import calculate_cohesion
from genolom_evolution.fitness.coherence import calculate_coherence
from genolom_evolution.fitness.micro import calculate_micro_fitness

def test_cohesion_empty_and_single(toy_ontology):
    assert calculate_cohesion([], toy_ontology) == 0
    assert calculate_cohesion(["a"], toy_ontology) == 1

def test_cohesion_pairwise_formula(toy_ontology):
    # distances: 1,2,1 -> scores 1,.5,1 -> mean 5/6
    assert calculate_cohesion(["a","b","c"], toy_ontology) == pytest.approx(5/6)

def test_coherence_formula(toy_ontology):
    # a:0, b:1, c:max(1/2,1)=1 => 2/3
    assert calculate_coherence(["a","b","c"], toy_ontology) == pytest.approx(2/3)

def test_micro_default_weights(toy_ontology):
    r = calculate_micro_fitness(["a","b","c"], toy_ontology)
    assert r.fitness == pytest.approx(0.5*(5/6) + 0.5*(2/3))

def test_micro_weights_must_sum_to_one(toy_ontology):
    with pytest.raises(ValueError):
        calculate_micro_fitness(["a"], toy_ontology, cohesion_weight=.7, coherence_weight=.7)
