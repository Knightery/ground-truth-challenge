from classify import classify_geometric
from groundtruth.loader import load_practice_seed, load_practice_stream
from groundtruth.model import GraphView


def _items():
    return {i.id: i for i in load_practice_stream()}


def _view():
    return GraphView(load_practice_seed())


def test_pr02_reversal_is_contradiction_targeting_q1():
    v = classify_geometric(_items()["PR02"].body, _view())
    assert v.is_contradiction is True
    assert v.is_regime is False
    assert v.target == "Q1"


def test_pr05_lateral_is_regime_not_contradiction():
    v = classify_geometric(_items()["PR05"].body, _view())
    assert v.is_regime is True
    assert v.is_contradiction is False


def test_pr01_confirm_is_all_false():
    v = classify_geometric(_items()["PR01"].body, _view())
    assert (v.is_axis, v.is_regime, v.is_contradiction) == (False, False, False)


def test_pr04_injection_describes_no_transition():
    v = classify_geometric(_items()["PR04"].body, _view())
    assert (v.is_axis, v.is_regime, v.is_contradiction) == (False, False, False)


def test_pr06_single_named_state_is_unresolved_offline():
    # Documented limitation: geometry needs two named states; PR06 names only one.
    v = classify_geometric(_items()["PR06"].body, _view())
    assert v.is_contradiction is False
