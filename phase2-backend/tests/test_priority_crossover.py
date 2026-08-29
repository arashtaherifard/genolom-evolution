from copy import deepcopy
from dataclasses import replace
import random

from genolom_evolution.evolution.crossover import crossover_individuals
from genolom_evolution.validation.genome_validator import validate_genome


def test_crossover_rate_zero_inherits_real_parent(generation0):
    a, b = deepcopy(generation0[0]), deepcopy(generation0[1])
    r = crossover_individuals(a, b, rate=0.0, rng=random.Random(3))
    assert not r.applied
    assert r.target_genome in {a.genome, b.genome}


def test_crossover_rate_one_produces_valid_target(generation0):
    a, b = deepcopy(generation0[0]), deepcopy(generation0[20])
    r = crossover_individuals(a, b, rate=1.0, rng=random.Random(3))
    assert r.applied
    assert not validate_genome(r.target_genome)
    assert r.provisional_fields == ("semanticDensity", "difficulty")


def test_crossover_repairs_interactivity_integrity(generation0):
    a = deepcopy(generation0[0])
    b = deepcopy(generation0[1])
    a.genome = replace(a.genome, interactivityType="Active", interactivityLevel="Medium", semanticDensity="Medium", difficulty="Medium")
    b.genome = replace(b.genome, interactivityType="Expositive", interactivityLevel="Very Low", semanticDensity="Low", difficulty="Easy")
    assert not validate_genome(a.genome)
    assert not validate_genome(b.genome)
    r = crossover_individuals(a, b, rate=1.0, rng=random.Random(1))
    assert r.target_genome.interactivityType == "Mixed"
    assert r.target_genome.interactivityLevel == "Low"
    assert any(x.field == "interactivityLevel" for x in r.repairs)
    assert not validate_genome(r.target_genome)


def test_crossover_does_not_invent_unknown_lrt_rule(generation0):
    a, b = deepcopy(generation0[0]), deepcopy(generation0[1])
    a.genome = replace(a.genome, learningResourceType="Headline")
    b.genome = replace(b.genome, learningResourceType="Figure")
    r = crossover_individuals(a, b, rate=1.0, rng=random.Random(2))
    assert r.target_genome.learningResourceType in {"Headline", "Figure"}
    assert "conservative_parent_inheritance" in r.learning_resource_rule
