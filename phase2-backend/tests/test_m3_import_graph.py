def test_m3_content_and_evolution_public_imports_do_not_cycle():
    # Regression test for the M3 planning -> evolution.operator_rules import.
    from genolom_evolution.content.testing import (
        AcceptingTestValidator,
        DeterministicTestGenerator,
    )
    from genolom_evolution.evolution import (
        AppliedOperatorResult,
        PriorityEvolutionSession,
    )

    assert DeterministicTestGenerator is not None
    assert AcceptingTestValidator is not None
    assert PriorityEvolutionSession is not None
    assert AppliedOperatorResult is not None
