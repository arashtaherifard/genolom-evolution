from copy import deepcopy
import random
import pytest

from genolom_evolution.evolution.eligibility import check_parent_eligibility
from genolom_evolution.selection.parent_pool import select_parents


def test_crossover_respects_maturity_age(generation0):
    x = deepcopy(generation0[0])
    x.micro_fitness = 0.5
    x.age = 0
    r = check_parent_eligibility(x, operator="crossover", maturity_age=1)
    assert not r.eligible
    assert "below_maturity_age" in r.reasons
    x.age = 1
    assert check_parent_eligibility(x, operator="crossover", maturity_age=1).eligible


def test_mutation_does_not_require_maturity_age(generation0):
    x = deepcopy(generation0[0])
    x.micro_fitness = 0.5
    x.age = 0
    assert check_parent_eligibility(x, operator="mutation", maturity_age=100).eligible


def test_eligibility_checks_participation_limit(generation0):
    x = deepcopy(generation0[0])
    x.micro_fitness = 0.5
    x.generation_participations = 2
    r = check_parent_eligibility(
        x, operator="mutation", max_parent_participations_per_generation=2
    )
    assert not r.eligible
    assert "participation_limit_reached" in r.reasons


def test_parent_selection_uses_only_eligible(generation0):
    pop = [deepcopy(x) for x in generation0[:3]]
    for i, x in enumerate(pop, start=1):
        x.micro_fitness = float(i)
    pop[0].alive = False
    r = select_parents(
        pop,
        operator="mutation",
        count=10,
        rng=random.Random(7),
        strategy="fitness_proportionate",
    )
    assert pop[0].individual_id not in r.eligible_ids
    assert set(r.selected_ids).issubset({pop[1].individual_id, pop[2].individual_id})


def test_random_selection_baseline_is_available(generation0):
    pop = [deepcopy(x) for x in generation0[:2]]
    for x in pop:
        x.micro_fitness = 1.0
    r = select_parents(pop, operator="mutation", count=4, rng=random.Random(1), strategy="random")
    assert r.strategy == "random"
    assert set(r.probabilities.values()) == {0.5}


def test_selection_exposes_descending_fitness_rank(generation0):
    pop = [deepcopy(x) for x in generation0[:3]]
    values = [0.2, 0.9, 0.5]
    for x, f in zip(pop, values):
        x.micro_fitness = f
    r = select_parents(pop, operator="mutation", count=1, rng=random.Random(4))
    assert r.ranked_eligible_ids == (pop[1].individual_id, pop[2].individual_id, pop[0].individual_id)
    assert list(r.fitnesses.values()) == [0.9, 0.5, 0.2]


def test_crossover_selection_pair_is_distinct_even_when_repeated_selection_enabled(generation0):
    pop = [deepcopy(x) for x in generation0[:3]]
    for x in pop:
        x.micro_fitness = 1.0
        x.age = 2
    r = select_parents(
        pop, operator="crossover", count=2, rng=random.Random(9),
        maturity_age=1, repeated_parent_selection=True,
    )
    assert len(set(r.selected_ids)) == 2
