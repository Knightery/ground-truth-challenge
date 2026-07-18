from classify import Verdict
from decide import dispose
from groundtruth.loader import load_practice_seed, load_seed
from groundtruth.model import GraphView


def _view():
    return GraphView(load_practice_seed())


def _seed_view():
    return GraphView(load_seed())


def _ops(res):
    return [d.op for d in res.deltas]


def test_axis_proposes_axis_and_flags():
    res = dispose(Verdict(is_axis=True), 0.0, {}, _view(), "EV1")
    assert _ops(res) == ["propose_axis"] and res.ood_flag is True


def test_regime_proposes_regime_and_flags():
    res = dispose(Verdict(is_regime=True), 0.0, {}, _view(), "EV1")
    assert _ops(res) == ["propose_regime"] and res.ood_flag is True


def test_strong_contradiction_revises_and_scopes():
    prov = {"method_class": "defined_factor_perturbation"}
    res = dispose(Verdict(is_contradiction=True, target="Q1"), 10.0, prov, _view(), "EV1")
    assert "revise_confidence" in _ops(res) and "set_scope" in _ops(res)
    assert res.ood_flag is False
    new = next(d.payload["new_confidence"] for d in res.deltas if d.op == "revise_confidence")
    assert new < 0.93


def test_thin_contradiction_holds_pending_no_mutation():
    res = dispose(Verdict(is_contradiction=True, target="Q1"), 2.0, {}, _view(), "EV1")
    assert _ops(res) == ["hold_pending"]
    # pending is keyed by the doubted claim so a later result can resolve it
    assert res.deltas[0].payload["claim_id"] == "Q1"


def test_resolved_pending_is_dropped_on_strong_result():
    # a prior tentative doubt about C4 is held pending; a later strong contradiction of C4 both
    # revises the claim AND drops the now-resolved pending cleanly.
    graph = load_seed()
    graph.pending["C4"] = {"note": "earlier unreplicated doubt", "evidence_id": "OLD"}
    view = GraphView(graph)
    res = dispose(Verdict(is_contradiction=True, target="C4"), 9.0,
                  {"method_class": "defined_factor_perturbation"}, view, "EV2")
    ops = _ops(res)
    assert "revise_confidence" in ops and "drop_claim" in ops
    assert any(d.op == "drop_claim" and d.payload["claim_id"] == "C4" for d in res.deltas)


def test_no_drop_when_target_not_pending():
    res = dispose(Verdict(is_contradiction=True, target="Q1"), 10.0, {}, _view(), "EV1")
    assert "drop_claim" not in _ops(res)


def test_all_false_is_no_op():
    res = dispose(Verdict(), 9.0, {}, _view(), "EV1")
    assert _ops(res) == ["no_op"]


def test_contradiction_with_missing_target_is_no_op():
    res = dispose(Verdict(is_contradiction=True, target="NOPE"), 9.0, {}, _view(), "EV1")
    assert _ops(res) == ["no_op"]


def test_strong_contradiction_without_method_class_has_no_scope():
    res = dispose(Verdict(is_contradiction=True, target="Q1"), 10.0, {}, _view(), "EV1")
    assert _ops(res) == ["revise_confidence"]


def test_support_strengthens_contested_claim():
    # C4 (contested, 0.45) has room to move; strong confirmation nudges it UP.
    res = dispose(Verdict(is_support=True, target="C4"), 9.0, {}, _seed_view(), "EV1")
    assert _ops(res) == ["revise_confidence"]
    assert res.deltas[0].payload["new_confidence"] > 0.45
    assert res.ood_flag is False


def test_support_of_near_certain_claim_is_no_op():
    # C5 (0.99) is already near-certain -> no material change on a confirmation.
    res = dispose(Verdict(is_support=True, target="C5"), 9.0, {}, _seed_view(), "EV1")
    assert _ops(res) == ["no_op"]


def test_thin_support_is_no_op():
    res = dispose(Verdict(is_support=True, target="C4"), 2.0, {}, _seed_view(), "EV1")
    assert _ops(res) == ["no_op"]


def test_support_of_umbrella_claim_is_no_op():
    # C3g is an umbrella (derived_from) -> min-propagation would clobber a direct up-move -> no_op.
    res = dispose(Verdict(is_support=True, target="C3g"), 9.0, {}, _seed_view(), "EV1")
    assert _ops(res) == ["no_op"]
