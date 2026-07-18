"""Terminal walkthrough for the GROUND TRUTH starter solution.

Run from the repository root:
    .venv/bin/python starter/demo.py --case PR02
    .venv/bin/python starter/demo.py --all

The runner deliberately sends each item through ``my_solution.ingest`` and the
provided Delta API, so the screen output reflects the same decision path that
the challenge harness evaluates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow the script to run directly from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from groundtruth.api import DeltaAPI
from groundtruth.loader import load_practice_seed, load_practice_stream
from groundtruth.model import GraphView

import my_solution


DEMO_CASES = ("PR02", "PR03", "PR04", "PR05", "PR06")


def _divider(title: str = "") -> None:
    print()
    print("=" * 72)
    if title:
        print(title)
        print("-" * 72)


def _claim_snapshot(graph, claim_id: str) -> dict | None:
    claim = graph.claims.get(claim_id)
    if claim is None:
        return None
    return {
        "confidence": claim.confidence,
        "scope": claim.scope,
        "status": claim.epistemic_status,
    }


def _show_graph_effect(graph, deltas) -> None:
    targets = {
        delta.payload["claim_id"]
        for delta in deltas
        if "claim_id" in delta.payload
    }
    if targets:
        print("\nGRAPH STATE AFTER VALIDATION")
        for target in sorted(targets):
            snapshot = _claim_snapshot(graph, target)
            if snapshot is not None:
                print(f"  {target}: {json.dumps(snapshot, sort_keys=True)}")
            elif target in graph.pending:
                print(f"  {target}: pending note = {graph.pending[target]['note']!r}")
    if graph.proposed_regimes:
        print(f"\nPROPOSED REGIMES: {', '.join(graph.proposed_regimes)}")
    if graph.proposed_axes:
        print(f"\nPROPOSED AXES: {', '.join(graph.proposed_axes)}")


def run_case(item_id: str) -> None:
    stream = {item.id: item for item in load_practice_stream()}
    item = stream[item_id]
    graph = load_practice_seed()
    api = DeltaAPI(graph)

    _divider(f"GROUND TRUTH DEMO — {item.id}")
    print("EVIDENCE BODY (untrusted)")
    print(f"  {item.body}")
    print("\nSTRUCTURED PROVENANCE (trusted)")
    print(json.dumps(item.provenance, indent=2, sort_keys=True))

    api.set_active_evidence(item.id)
    result = my_solution.ingest(item, GraphView(graph))

    print("\nOUR DECISION")
    print(f"  Rationale: {result.rationale}")
    print(f"  Decision confidence: {result.confidence:.2f}")
    print(f"  Out-of-distribution flag: {result.ood_flag}")
    print("\nPROPOSED DELTAS")
    for delta in result.deltas:
        print(f"  {delta.op}: {json.dumps(delta.payload, sort_keys=True)}")

    target_ids = [
        delta.payload["claim_id"]
        for delta in result.deltas
        if "claim_id" in delta.payload
    ]
    if target_ids:
        print("\nGRAPH STATE BEFORE VALIDATION")
        for target in sorted(set(target_ids)):
            snapshot = _claim_snapshot(graph, target)
            if snapshot is not None:
                print(f"  {target}: {json.dumps(snapshot, sort_keys=True)}")

    print("\nDELTA API VALIDATION")
    for delta in result.deltas:
        applied = api.apply(delta)
        outcome = "APPLIED" if applied.applied else "REJECTED"
        print(f"  {outcome}: {delta.op} — {applied.reason}")

    _show_graph_effect(graph, result.deltas)
    print("\nFIREWALL VIOLATIONS:", api.violations or "none")
    _divider("END DEMO")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show how the starter solution handles practice evidence."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", choices=DEMO_CASES, help="Practice evidence ID to demonstrate")
    group.add_argument("--all", action="store_true", help="Run all recommended demo cases")
    args = parser.parse_args()

    case_ids = DEMO_CASES if args.all else (args.case,)
    for item_id in case_ids:
        run_case(item_id)


if __name__ == "__main__":
    main()
