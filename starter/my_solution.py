"""GROUND TRUTH solution: strength -> classify -> dispose.

strength() sizes any change from the STRUCTURED provenance; classify() (one LLM call, or a
geometric fallback) says what the evidence is; dispose() maps that to legal Deltas and never
reads the body. Injections are inert by construction: we only act on a described transition.
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
