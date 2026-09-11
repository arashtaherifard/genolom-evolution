from genolom_evolution.experiments.seeding import derive_event_seed


def test_event_seed_is_stable_and_purpose_separated():
    a = derive_event_seed(42, 3, "G3_LO_0001", "abstraction", "content_realization")
    b = derive_event_seed(42, 3, "G3_LO_0001", "abstraction", "content_realization")
    c = derive_event_seed(42, 3, "G3_LO_0001", "abstraction", "validation")

    assert a == b
    assert a != c
