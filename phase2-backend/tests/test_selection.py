import random
from genolom_evolution.selection.fitness_proportionate import fitness_proportionate_probabilities, FitnessProportionateSelection
from genolom_evolution.selection.random_selection import RandomSelection

def test_probabilities_normalize():
    assert fitness_proportionate_probabilities([1,2,1]) == [0.25,0.5,0.25]

def test_zero_fitness_uniform_fallback():
    assert fitness_proportionate_probabilities([0,0]) == [0.5,0.5]

def test_selection_is_reproducible(generation0):
    for i, v in enumerate(generation0[:3], start=1): v.micro_fitness = float(i)
    s = FitnessProportionateSelection()
    a = s.sample_indices(generation0[:3], 8, random.Random(99))
    b = s.sample_indices(generation0[:3], 8, random.Random(99))
    assert a == b

def test_random_baseline_uniform(generation0):
    p = RandomSelection().probabilities(generation0[:4])
    assert p == [0.25]*4
