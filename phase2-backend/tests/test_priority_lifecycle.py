from copy import deepcopy

from genolom_evolution.evolution.lifecycle import (
    LongevityPolicy, initialize_longevity, update_longevity_end_of_generation,
    apply_perish, age_survivors,
)


def test_longevity_initialization_reward_and_penalty(generation0):
    pop = [deepcopy(x) for x in generation0[:2]]
    policy = LongevityPolicy(3.0, 1.0, 1.0, 0.0)
    initialize_longevity(pop, policy)
    assert [x.longevity_chance for x in pop] == [3.0, 3.0]
    update_longevity_end_of_generation(
        pop,
        successful_parent_participations={pop[0].individual_id: 2},
        policy=policy,
    )
    assert pop[0].longevity_chance == 5.0
    assert pop[0].reproduction_count == 2
    assert pop[1].longevity_chance == 2.0


def test_perish_removes_at_or_below_threshold(generation0):
    pop = [deepcopy(generation0[0]), deepcopy(generation0[1])]
    pop[0].longevity_chance = 0.0
    pop[1].longevity_chance = 0.1
    events = apply_perish(pop, threshold=0.0, generation=1)
    assert not pop[0].alive
    assert pop[1].alive
    assert len(events) == 1
    assert events[0].event_type == "perish"


def test_age_counts_survived_generations(generation0):
    pop = [deepcopy(generation0[0]), deepcopy(generation0[1])]
    pop[1].alive = False
    age_survivors(pop)
    assert pop[0].age == 1
    assert pop[1].age == 0
