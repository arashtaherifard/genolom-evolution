from copy import deepcopy

from genolom_evolution.content.operators import (
    AbstractionOperator, ElaborationOperator, ProbingOperator,
)
from genolom_evolution.content.testing import DeterministicTestGenerator, AcceptingTestValidator


def _execute(operator, source):
    return operator.execute(
        source,
        source.genome,
        generator=DeterministicTestGenerator(),
        validator=AcceptingTestValidator(),
        seed=123,
    )


def test_abstraction_operator_contract(generation0):
    source = deepcopy(generation0[0])
    r = _execute(AbstractionOperator(), source)
    assert r.accepted
    assert r.request.operator_name == "abstraction"
    assert r.response.content.startswith("[ABSTRACTED]")


def test_elaboration_operator_contract(generation0):
    source = deepcopy(generation0[0])
    r = _execute(ElaborationOperator(), source)
    assert r.accepted
    assert r.request.prompt_template_id == "elaboration-v1"


def test_probing_operator_contract(generation0):
    source = deepcopy(generation0[0])
    r = _execute(ProbingOperator(), source)
    assert r.accepted
    assert "PROBING" in r.response.content


def test_test_generator_marks_itself_not_for_scientific_use(generation0):
    source = deepcopy(generation0[0])
    r = _execute(AbstractionOperator(), source)
    assert r.response.raw_metadata["not_for_scientific_use"] is True
