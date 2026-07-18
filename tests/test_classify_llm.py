import json
from classify import classify, _parse_verdict
from groundtruth.loader import load_practice_seed
from groundtruth.model import GraphView


def _view():
    return GraphView(load_practice_seed())


def test_parse_reads_booleans_and_target():
    v = _parse_verdict(json.dumps({"is_contradiction": True, "target": "Q2"}))
    assert v.is_contradiction is True and v.target == "Q2"


def test_parse_returns_none_on_garbage():
    assert _parse_verdict("not json") is None


def test_classify_uses_injected_completion_for_pr06_case():
    def fake(system, user):
        return json.dumps({"is_axis": False, "is_regime": False,
                           "is_contradiction": True, "target": "Q2"})
    v = classify("MidState reverted to a less-committed state within the same lineage",
                 _view(), complete=fake)
    assert v.is_contradiction is True and v.target == "Q2"


def test_classify_falls_back_when_completion_raises():
    def boom(system, user):
        raise RuntimeError("endpoint down")
    v = classify("A defined intervention returned LeafA cells to the SourceState.",
                 _view(), complete=boom)
    assert v.is_contradiction is True  # geometric fallback still resolves PR02-style
