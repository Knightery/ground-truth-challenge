"""GROUND TRUTH solution: classify -> strength -> dispose (fully offline, no network / no LLM).

strength() sizes any change from the STRUCTURED provenance; classify() reads the body only to say
what KIND of transition is described (deterministic, canonical-name-anchored, sentence-scoped);
dispose() maps that to legal Deltas and never reads the body. Injections are inert by construction:
a classification requires a real cell-state name in the same sentence as its cue, and magnitude comes
only from structured provenance -- so instruction text can neither trigger nor size a mutation.
"""
from __future__ import annotations
import os
import sys

# Make helper modules importable under every loader the framework uses.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from groundtruth.ingest import EvidenceItem, IngestResult   # noqa: E402
from groundtruth.model import GraphView                     # noqa: E402
from provenance import strength                             # noqa: E402
from classify import classify                               # noqa: E402
from decide import dispose                                  # noqa: E402


def ingest(item: EvidenceItem, view: GraphView) -> IngestResult:
    try:
        v = classify(item.body, view)
        s = strength(item.provenance)
        return dispose(v, s, item.provenance, view, item.id)
    except Exception:
        from groundtruth.deltas import no_op
        return IngestResult([no_op(item.id)], "error; safe no-op", 0.0, False)
