from genolom_evolution.evaluation.diversity import population_diversity, shannon_entropy

def test_entropy_zero_for_identical_values():
    assert shannon_entropy(["x","x","x"]) == 0

def test_generation0_diversity_is_nontrivial(generation0):
    d = population_diversity(generation0)
    assert d["population_size"] == 298
    assert d["unique_keyword_count"] > 0
    assert 0 < d["unique_genome_ratio"] <= 1
