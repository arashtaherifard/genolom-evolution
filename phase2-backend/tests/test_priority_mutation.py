from copy import deepcopy
import random

from genolom_evolution.evolution.mutation import mutate_individual, viable_mutation_options
from genolom_evolution.validation.genome_validator import validate_genome


def test_mutation_rate_zero_does_not_apply(generation0):
    parent = deepcopy(generation0[0])
    r = mutate_individual(parent, rate=0.0, rng=random.Random(1))
    assert not r.applied
    assert r.reason == "rate_not_triggered"


def test_mutation_rate_one_produces_valid_target_when_options_exist(generation0):
    parent = deepcopy(generation0[0])
    assert viable_mutation_options(parent.genome)
    r = mutate_individual(parent, rate=1.0, rng=random.Random(2))
    assert r.applied
    assert r.option is not None
    assert not validate_genome(r.target_genome)
    assert r.option.old_value != r.option.new_value


def test_mutation_is_reproducible(generation0):
    parent = deepcopy(generation0[0])
    a = mutate_individual(parent, rate=1.0, rng=random.Random(99)).to_dict()
    b = mutate_individual(parent, rate=1.0, rng=random.Random(99)).to_dict()
    assert a == b


def test_unsupported_lrt_source_does_not_invent_lrt_transition(generation0):
    parent = deepcopy(generation0[0])
    assert parent.genome.learningResourceType == "Headline"
    options = viable_mutation_options(parent.genome)
    assert all(o.gene != "learningResourceType" for o in options)
