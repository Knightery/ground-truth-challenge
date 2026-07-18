"""Classify one evidence item into a Verdict.

classify() uses an LLM when an endpoint is configured (Task 5) and otherwise a deterministic,
keyword-free GEOMETRIC fallback: it reads the cell-state names present in the body and decides
from graph geometry (potency direction, lineage identity). It stays safe (all-false -> no_op)
on anything it cannot judge.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


@dataclass
class Verdict:
    is_axis: bool = False           # changed property is one the graph does not track
    is_regime: bool = False         # lateral: direct same-potency cross-lineage conversion
    is_contradiction: bool = False  # a transition contradicting an existing claim (reversal)
    target: str | None = None       # the existing claim id it bears on


def _mentioned_states(body: str, view) -> list:
    out, seen = [], set()
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9]+", body):
        cs = view.cell_state(m.group(0))
        if cs is not None and cs.name not in seen:
            seen.add(cs.name)
            out.append(cs)
    return out


def _find_claim(view, *needles) -> str | None:
    for cid in view.list_claim_ids():
        st = (view.get_claim(cid).statement or "").lower()
        if all(n in st for n in needles):
            return cid
    return None


def _pick_target(states: list, prov: dict, view) -> str | None:
    if any(s.potency_level <= 1 for s in states):          # a return toward the most-potent state
        method = str(prov.get("method_class", "")).lower()
        for key, child in (("defined_factor", "C3c"), ("environmental_stress", "C3d"),
                           ("env_stress", "C3d"), ("oocyte", "C3b"), ("spontaneous", "C3a")):
            if key in method and view.get_claim(child) is not None:
                return child
        t = _find_claim(view, "return") or _find_claim(view, "cannot", "source")
        if t:
            return t
    return _find_claim(view, "potency") or (view.list_claim_ids()[0] if view.list_claim_ids() else None)


def classify_geometric(body: str, view) -> Verdict:
    v = Verdict()
    states = _mentioned_states(body, view)
    if len(states) >= 2:
        origin, dest = states[0], states[-1]
        if dest.potency_level < origin.potency_level:
            v.is_contradiction = True
            v.target = _pick_target(states, {}, view)
        elif (dest.potency_level == origin.potency_level
              and dest.lineage_identity != origin.lineage_identity):
            v.is_regime = True
    return v


def classify(body: str, view, complete=None) -> Verdict:
    # The LLM path is added in Task 5; geometric is authoritative until then.
    return classify_geometric(body, view)
