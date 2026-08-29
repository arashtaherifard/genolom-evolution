from dataclasses import replace
from genolom_evolution.validation.genome_validator import validate_genome

def test_all_generation0_genomes_are_valid(generation0):
    assert all(not validate_genome(i.genome) for i in generation0)

def test_fixed_age_mismatch_is_rejected(generation0):
    g = replace(generation0[0].genome, typicalAgeRange="18-22")
    assert any(i.code == "fixed_metadata_mismatch" for i in validate_genome(g))

def test_interactivity_mismatch_is_rejected(generation0):
    g = replace(generation0[0].genome, interactivityType="Expositive", interactivityLevel="Medium")
    assert any(i.code == "interactivity_constraint" for i in validate_genome(g))

def test_forbidden_semantic_difficulty_is_rejected(generation0):
    g = replace(generation0[0].genome, semanticDensity="Very High", difficulty="Very Easy")
    assert any(i.code == "forbidden_semantic_difficulty" for i in validate_genome(g))
