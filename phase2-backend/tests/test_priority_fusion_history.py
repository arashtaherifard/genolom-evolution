from copy import deepcopy
import pytest

from genolom_evolution.evolution.fusion_defusion import (
    FusionDefusionThreshold,
    record_fusion_participation,
    record_defusion_participation,
)


def test_fusion_defusion_history_is_recorded(generation0):
    x = deepcopy(generation0[0])
    policy = FusionDefusionThreshold(minimum=0, maximum=2)
    record_fusion_participation(x, "f1", policy)
    record_defusion_participation(x, "d1", policy)
    assert x.fusion_count == 1
    assert x.defusion_count == 1
    assert x.fusion_history == ["f1"]
    assert x.defusion_history == ["d1"]


def test_fusion_threshold_blocks_above_max(generation0):
    x = deepcopy(generation0[0])
    policy = FusionDefusionThreshold(minimum=0, maximum=1)
    record_fusion_participation(x, "f1", policy)
    with pytest.raises(ValueError):
        record_fusion_participation(x, "f2", policy)


def test_positive_lower_threshold_is_reportable_not_deadlocking(generation0):
    x = deepcopy(generation0[0])
    policy = FusionDefusionThreshold(minimum=2, maximum=4)
    assert not policy.meets_minimum(x.fusion_count)
    assert policy.can_fuse(x)
