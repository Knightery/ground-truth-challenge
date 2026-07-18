"""The dispose layer: Verdict + structured provenance -> legal Deltas.

The ONLY module that emits a mutation, and it never reads item.body. Magnitude is a pure
function of provenance, so no text can size or authorize a change.
"""
from __future__ import annotations

from groundtruth.deltas import Delta, no_op
from groundtruth.ingest import IngestResult
from groundtruth.model import logit as _logit, sigmoid as _sigmoid
from classify import Verdict

HOLD_BAR = 3.0
CAP_SAFE = 2.5   # < api CAP_LOGODDS (3.0)

MECHANISM_CHILD = {
    "defined_factor": "C3c",
    "environmental_stress": "C3d",
    "env_stress": "C3d",
    "oocyte": "C3b",
    "spontaneous": "C3a",
}


def _resolve_target(target, prov, view):
    """Prefer the mechanism-specific child of an umbrella claim, so the revision is not erased by
    the framework's min-propagation from unchanged children."""
    claim = view.get_claim(target)
    if claim is None or not claim.derived_from:
        return target
    method = str(prov.get("method_class", "")).lower()
    for key, child in MECHANISM_CHILD.items():
        if key in method and child in claim.derived_from and view.get_claim(child) is not None:
            return child
    return target


def _revised(old: float, s: float) -> float:
    frac = max(0.0, min(1.0, (s - HOLD_BAR) / (10.0 - HOLD_BAR)))
    return round(min(max(_sigmoid(_logit(old) - CAP_SAFE * frac), 0.01), 0.99), 3)


def dispose(v: Verdict, s: float, prov: dict, view, evidence_id: str) -> IngestResult:
    if v.is_axis:
        return IngestResult([Delta("propose_axis", evidence_id, {"axis": "identity_preserving_property"})],
                            "out-of-model axis", 0.7, True)
    if v.is_regime:
        return IngestResult([Delta("propose_regime", evidence_id, {"regime": "lateral_conversion"})],
                            "out-of-model regime (lateral)", 0.7, True)
    if v.is_contradiction and v.target and view.get_claim(v.target) is not None:
        if s < HOLD_BAR:
            return IngestResult([Delta("hold_pending", evidence_id,
                                       {"claim_id": evidence_id, "note": f"unreplicated contradiction of {v.target}"})],
                                "thin/extraordinary; held pending", 0.6, False)
        target = _resolve_target(v.target, prov, view)
        old = view.get_claim(target).confidence
        new = _revised(old, s)
        deltas = [Delta("revise_confidence", evidence_id, {"claim_id": target, "new_confidence": new})]
        method = str(prov.get("method_class", "")).strip()
        if method:
            deltas.append(Delta("set_scope", evidence_id, {"claim_id": target,
                                                           "scope": {"refuted_under": method}}))
        return IngestResult(deltas, f"in-model contradiction; {target} {old}->{new}", 0.85, False)
    return IngestResult([no_op(evidence_id)], "no grounded change", 0.6, False)
