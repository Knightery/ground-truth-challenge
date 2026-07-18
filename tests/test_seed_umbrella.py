from classify import Verdict
from decide import dispose
from groundtruth.loader import load_seed
from groundtruth.model import GraphView


def _seed_view():
    return GraphView(load_seed())


def test_defined_factor_reversal_revises_child_not_umbrella():
    # A classifier may target the umbrella C3g; dispose must revise the mechanism child C3c,
    # because revising C3g directly is overwritten by the framework's min-propagation.
    prov = {"method_class": "defined_factor_perturbation"}
    res = dispose(Verdict(is_contradiction=True, target="C3g"), 10.0, prov, _seed_view(), "EV1")
    revised = [d.payload["claim_id"] for d in res.deltas if d.op == "revise_confidence"]
    scoped = [d.payload["claim_id"] for d in res.deltas if d.op == "set_scope"]
    assert revised == ["C3c"]
    assert scoped == ["C3c"]


def test_environmental_stress_reversal_revises_c3d():
    prov = {"method_class": "environmental_stress"}
    res = dispose(Verdict(is_contradiction=True, target="C3g"), 10.0, prov, _seed_view(), "EV1")
    revised = [d.payload["claim_id"] for d in res.deltas if d.op == "revise_confidence"]
    assert revised == ["C3d"]
