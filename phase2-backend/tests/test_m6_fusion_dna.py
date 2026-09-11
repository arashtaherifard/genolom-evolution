from copy import deepcopy

from genolom_evolution.evolution.dna import (
    DNA_SCHEMA_VERSION,
    FusionBinaryOperator,
    encode_genome_dna,
)
from genolom_evolution.evolution.fusion_defusion import fuse_genomes
from genolom_evolution.models.genome import GenoLOMGenome


def _compatible_pair(generation0):
    a = deepcopy(generation0[8])   # G0_LO_009
    b = deepcopy(generation0[48])  # G0_LO_049
    assert a.genome.learningResourceType == b.genome.learningResourceType == "Narrative Text"
    assert a.genome.typicalLearningTime == b.genome.typicalLearningTime == 5.0
    return a, b


def test_table2_dna_encoding_has_expected_schema_and_width(generation0):
    a, _ = _compatible_pair(generation0)
    result = encode_genome_dna(a.genome)
    assert result.ok
    assert result.encoded is not None
    assert result.encoded.schema_version == DNA_SCHEMA_VERSION
    # 59 categorical one-hot bits + 7 age bits + 6 learning-time bits.
    assert len(result.encoded.bitstring) == 72
    assert set(result.encoded.bitstring) <= {"0", "1"}


def test_phase1_headline_maps_to_proposal_text_cell_without_rewriting_source(generation0):
    headline = deepcopy(generation0[0])
    assert headline.genome.learningResourceType == "Headline"
    assert headline.genome.typicalLearningTime == 0.1
    result = encode_genome_dna(headline.genome)
    assert result.ok
    assert headline.genome.learningResourceType == "Headline"  # Generation 0 stays frozen.
    normalized = [x.to_dict() for x in result.normalizations]
    assert {
        "field": "learningResourceType",
        "source_value": "Headline",
        "dna_value": "Narrative Text",
        "policy": "phase1_to_proposal_table2_lrt_adapter_v1",
    } in normalized
    assert {
        "field": "typicalLearningTime",
        "source_value": 0.1,
        "dna_value": 1.0,
        "policy": "fractional_minutes_to_nearest_proposal_minute_v1",
    } in normalized


def test_phase1_question_maps_to_table2_questionnaire_cell(generation0):
    question = deepcopy(generation0[64])
    assert question.genome.learningResourceType == "Question"
    result = encode_genome_dna(question.genome)
    assert result.ok
    assert any(
        x.field == "learningResourceType"
        and x.source_value == "Question"
        and x.dna_value == "Questionnaire"
        for x in result.normalizations
    )


def test_fractional_learning_time_is_quantized_in_minutes_not_rejected(generation0):
    x = deepcopy(generation0[0])
    x.genome = GenoLOMGenome.from_mapping(
        {**x.genome.to_dict(), "learningResourceType": "Narrative Text", "typicalLearningTime": 2.5}
    )
    result = encode_genome_dna(x.genome)
    assert result.ok
    assert any(
        item.field == "typicalLearningTime"
        and item.source_value == 2.5
        and item.dna_value == 3.0
        for item in result.normalizations
    )



def test_same_headline_parents_preserve_more_specific_phase1_type(generation0):
    a = deepcopy(generation0[0])
    b = deepcopy(generation0[2])
    assert a.genome.learningResourceType == b.genome.learningResourceType == "Headline"
    result = fuse_genomes(a, b, binary_operator="AND")
    assert result.success
    assert result.target_genome is not None
    assert result.target_genome.learningResourceType == "Headline"
    # Both 0.1-minute estimates are quantized to the same one-minute DNA code.
    assert result.target_genome.typicalLearningTime == 1.0


def test_same_question_parents_decode_to_current_question_label(generation0):
    a = deepcopy(generation0[64])
    b = deepcopy(generation0[137])
    # Align fields that would otherwise make AND invalid; this test isolates LRT aliasing.
    b.genome = GenoLOMGenome.from_mapping(
        {
            **a.genome.to_dict(),
            "description": b.genome.description,
            "keywords": b.genome.keywords,
            "typicalLearningTime": a.genome.typicalLearningTime,
        }
    )
    result = fuse_genomes(a, b, binary_operator="AND")
    assert result.success
    assert result.target_genome is not None
    assert result.target_genome.learningResourceType == "Question"

def test_and_fusion_of_compatible_parents_yields_valid_target(generation0):
    a, b = _compatible_pair(generation0)
    result = fuse_genomes(a, b, binary_operator="AND")
    assert result.success
    assert result.target_genome is not None
    assert result.target_genome.learningResourceType == "Narrative Text"
    assert result.target_genome.typicalAgeRange == "18+"
    assert result.target_genome.typicalLearningTime == 5.0
    assert result.parent_a_dna["bit_length"] == 72
    assert result.fused_dna["bit_length"] == 72
    # Keywords were excluded from bitwise DNA and retained as deterministic union.
    assert set(a.genome.keywords).issubset(result.target_genome.keywords)
    assert set(b.genome.keywords).issubset(result.target_genome.keywords)


def test_or_fusion_of_compatible_parents_yields_valid_target(generation0):
    a, b = _compatible_pair(generation0)
    result = fuse_genomes(a, b, binary_operator=FusionBinaryOperator.OR)
    assert result.success
    assert result.target_genome is not None


def test_xor_fusion_fails_invalid_one_hot_instead_of_llm_repair(generation0):
    a, b = _compatible_pair(generation0)
    result = fuse_genomes(a, b, binary_operator="XOR")
    assert not result.success
    assert result.target_genome is None
    assert any(reason["code"] == "invalid_one_hot_block" for reason in result.reasons)


def test_nand_fusion_fails_invalid_one_hot_instead_of_llm_repair(generation0):
    a, b = _compatible_pair(generation0)
    result = fuse_genomes(a, b, binary_operator="NAND")
    assert not result.success
    assert result.target_genome is None
    assert any(reason["code"] == "invalid_one_hot_block" for reason in result.reasons)


def test_different_one_hot_categories_make_and_fusion_invalid(generation0):
    a, b = _compatible_pair(generation0)
    b.genome = GenoLOMGenome.from_mapping(
        {**b.genome.to_dict(), "semanticDensity": "High"}
    )
    result = fuse_genomes(a, b, binary_operator="AND")
    assert not result.success
    assert any(
        reason["code"] == "invalid_one_hot_block" and reason["field"] == "semanticDensity"
        for reason in result.reasons
    )
