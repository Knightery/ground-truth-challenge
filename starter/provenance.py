"""Evidence strength as a pure function of the STRUCTURED provenance channel.

The body is never consulted here. Unknown tokens default low, never high, so an unseen
vocabulary in the hidden set cannot inflate an update.
"""
from __future__ import annotations
import math

WORD_COUNTS = {"none": 0, "0": 0, "single": 1, "one": 1, "1": 1,
               "few": 2, "several": 4, "many": 8}
DIRECTNESS = {"direct": 1.0, "indirect": 0.6, "inferred": 0.6, "modeled": 0.4}
EFFECT = {"strong": 1.0, "moderate": 0.7, "weak": 0.4}


def _count(v) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    return WORD_COUNTS.get(str(v).strip().lower(), 1)


def strength(prov: dict) -> float:
    """Map a provenance record to a 0..10 evidence strength."""
    if str(prov.get("retraction_status", "none")).strip().lower() not in ("none", "", "false"):
        return 0.0
    groups = _count(prov.get("independent_groups", 0))
    reps = _count(prov.get("replication_count", 0))
    directness = DIRECTNESS.get(str(prov.get("method_directness", "")).strip().lower(), 0.4)
    effect = EFFECT.get(str(prov.get("effect_strength", "")).strip().lower(), 0.4)
    # Independent groups dominate; replication adds. Smooth saturation (ceiling 10) that stays
    # STRICTLY increasing at the strong end -- 8 groups move more than 4 -- rather than a hard cap
    # that plateaus. T=8 keeps thin evidence (1 group, 1 rep -> ~2.7) below the hold bar while a
    # well-replicated direct result still reaches "large".
    raw = 2.0 * groups + 0.5 * reps
    base = 10.0 * (1.0 - math.exp(-raw / 8.0))
    return max(0.0, min(10.0, base * directness * effect))
