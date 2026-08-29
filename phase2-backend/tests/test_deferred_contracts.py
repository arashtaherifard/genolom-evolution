from genolom_evolution.evaluation.human import HumanRatingRecord
from genolom_evolution.evaluation.learner import LearnerStudyObservation

def test_human_rating_contract():
    r = HumanRatingRecord("expert-1","item-1","cohesion",4.0)
    assert r.to_dict()["dimension"] == "cohesion"

def test_learner_study_contract_is_decoupled():
    o = LearnerStudyObservation("anon-1","control",10,14,120)
    assert o.posttest_score == 14
