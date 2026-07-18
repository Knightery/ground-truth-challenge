"""Calibration sweeps for the GROUND TRUTH solution's evidence-weighting dial.

Extends eval/gradient.py's single-parameter `calibration_monotonicity` into four independent
provenance-dimension sweeps, a saturation check, a skepticism flip-point search, and a
retraction check -- all driven purely through `ingest_fn(item, view) -> IngestResult`.

HONESTY RULE: every property checked below is a RULE about the RELATIONSHIP between calls to
ingest_fn (non-decreasing, ordered-flip, zeroed-on-retraction) -- never a number read off our own
output and asserted against itself. We never call strength()/dispose()/classify() directly; the
only handle into the solution under test is the `ingest_fn` argument to run().

Reuses run_traced()/_dlo() from eval/gradient.py (copied here, per that module's own docstring:
"you may copy them"), so a single item's effect is measured by snapshotting EVERY claim's
confidence before/after and taking the claim with the largest |delta log-odds| -- never by
assuming in advance which claim id will move.

Usage:
  python eval/sweeps/calibration_sweeps.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))

from groundtruth.api import DeltaAPI                       # noqa: E402
from groundtruth.harness import MUTATING_OPS                # noqa: E402
from groundtruth.ingest import EvidenceItem, IngestFn        # noqa: E402
from groundtruth.model import GraphView, logit                # noqa: E402
from groundtruth.loader import load_seed                       # noqa: E402

# ---------------------------------------------------------------------------------------------
# Copied from eval/gradient.py. This is the shared measurement primitive for every sweep below:
# run one item, snapshot ALL claims before/after, report |delta log-odds| per claim that moved.
# ---------------------------------------------------------------------------------------------


def _dlo(old: float, new: float) -> float:
    """|change in log-odds| between two confidences."""
    return abs(logit(new) - logit(old))


def run_traced(stream, ingest_fn, graph):
    """Run the stream, snapshotting every claim's confidence before/after each item."""
    api = DeltaAPI(graph)
    recs = []
    for item in stream:
        api.set_active_evidence(item.id)
        before = {cid: graph.claims[cid].confidence for cid in graph.claims}
        public = EvidenceItem(item.id, "", item.body, item.provenance, item.era)
        result = ingest_fn(public, GraphView(graph))
        ops, attempted = [], False
        for d in result.deltas:
            if d.op in MUTATING_OPS:
                attempted = True
            api.apply(d)
            ops.append(d.op)
        after = {cid: graph.claims[cid].confidence for cid in graph.claims}
        moved = {cid: (before[cid], after[cid], round(_dlo(before[cid], after[cid]), 3))
                 for cid in after if abs(after[cid] - before.get(cid, after[cid])) > 1e-9}
        recs.append({"id": item.id, "ops": ops, "ood": bool(result.ood_flag),
                     "attempted_mutation": attempted, "moved": moved,
                     "rationale": result.rationale})
    return recs, list(api.violations)


def _biggest_move(rec) -> float:
    return max((m[2] for m in rec["moved"].values()), default=0.0)


# ---------------------------------------------------------------------------------------------
# Fixture: the one clean in-model contradiction named in the brief.
#   Fibroblast (potency 3) -> PluripotentStemCell (potency 1), a defined-factor reversal.
#   classify_geometric() flags this a contradiction targeting C3g (the umbrella claim -- the only
#   statement containing the word "return"); decide._resolve_target then routes a defined_factor
#   method_class onto C3g's mechanism child C3c, and revising C3c drags C3g down through
#   DeltaAPI._propagate_umbrella (umbrella = min over children). We never assume which claim id
#   absorbs the change -- run_traced() snapshots ALL claims and _biggest_move() picks it, exactly
#   per the brief's instruction to find the mover empirically rather than name it in advance.
# ---------------------------------------------------------------------------------------------
CONTRADICTION_BODY = ("A defined-factor intervention returned Fibroblast cells to the "
                      "PluripotentStemCell state, reproduced by independent groups.")

# A "strong baseline" provenance record: every dimension pinned strong except the one swept.
STRONG_BASELINE = {
    "independent_groups": "several",
    "replication_count": "several",
    "method_class": "defined_factor_perturbation",
    "method_directness": "direct",
    "effect_strength": "strong",
    "retraction_status": "none",
}

# Per-dimension thin -> thick ladders, exactly as given in the brief.
GROUPS_LEVELS = ["single", 1, "few", 2, "several", 4, "many", 8]
REPS_LEVELS = ["single", 1, "few", 2, "several", 4, "many", 8]
DIRECTNESS_LEVELS = ["inferred", "indirect", "direct"]
EFFECT_LEVELS = ["weak", "moderate", "strong"]

SWEEP_DIMS = {
    "independent_groups": GROUPS_LEVELS,
    "replication_count": REPS_LEVELS,
    "method_directness": DIRECTNESS_LEVELS,
    "effect_strength": EFFECT_LEVELS,
}


def _prov(dim: str, value) -> dict:
    """Strong baseline with a single dimension overridden -- isolates that dimension's effect."""
    p = dict(STRONG_BASELINE)
    p[dim] = value
    return p


def _fire(ingest_fn, prov: dict, item_id: str = "SWEEP"):
    """Run the fixed contradiction once against a FRESH seed graph; return the traced record.

    Fresh load_seed() per call so sweep points can never interact with each other (matches
    eval/gradient.py's calibration_monotonicity, which reloads the seed every iteration too).
    """
    graph = load_seed()
    stream = [EvidenceItem(item_id, "", CONTRADICTION_BODY, prov, "")]
    recs, violations = run_traced(stream, ingest_fn, graph)
    return recs[0], violations


def _is_nondecreasing(values, tol: float = 1e-9) -> bool:
    return all(values[i] >= values[i - 1] - tol for i in range(1, len(values)))


# ---------------------------------------------------------------------------------------------
# Sweep 1 + 2: multi-dimension monotonicity, and saturation at the strong end.
# ---------------------------------------------------------------------------------------------


def sweep_dimension(ingest_fn, dim: str, levels: list):
    """One provenance dimension swept thin -> thick, the rest pinned at STRONG_BASELINE.

    RULE under test: the |delta log-odds| of whichever claim moves most is NON-DECREASING as the
    swept dimension strengthens (levels are given thin-first, per the brief).
    """
    curve = []
    violations = []
    for lvl in levels:
        rec, viol = _fire(ingest_fn, _prov(dim, lvl))
        curve.append((lvl, _biggest_move(rec)))
        violations.extend(viol)
    mono = _is_nondecreasing([d for _, d in curve])
    return curve, mono, violations


def check_saturation(curve):
    """Descriptive finding, NOT a scored property: does the thickest level (index 8, e.g. 'many')
    move STRICTLY more than the 'several'/4 level? Reported as `saturates=True` when it does NOT
    -- i.e. the strong end of the ladder has no further resolution. A plateau here is expected
    fallout of strength()'s base=min(10, ...) cap, not a bug, so it is flagged, not penalized.
    """
    by_level = dict(curve)
    several, thick = by_level[4], by_level[8]
    strictly_more = thick > several + 1e-9
    return (not strictly_more), f"Δlo(=4)={several}  Δlo(=8)={thick}"


# ---------------------------------------------------------------------------------------------
# Sweep 3: skepticism flip-point.
# ---------------------------------------------------------------------------------------------


def _scale_index(i: int, n_from: int, n_to: int) -> int:
    """Map ladder index i in [0, n_from) onto [0, n_to), never decreasing as i increases."""
    return round(i * (n_to - 1) / (n_from - 1)) if n_from > 1 else 0


def flip_point_ladder() -> list:
    """A single thin -> thick ladder that advances ALL FOUR dimensions in lockstep.

    Each of GROUPS_LEVELS / REPS_LEVELS / DIRECTNESS_LEVELS / EFFECT_LEVELS is, by the brief's
    own framing, given thin-first. Walking all four with a shared, non-decreasing index therefore
    produces a provenance sequence that is thin -> thick on every axis at once. We do not call
    strength() to confirm this -- we only rely on each ladder being individually thin -> thick
    (given), then test the REAL ingest_fn's behavior against that ordering.
    """
    n = len(GROUPS_LEVELS)
    ladder = []
    for i in range(n):
        ladder.append({
            "independent_groups": GROUPS_LEVELS[i],
            "replication_count": REPS_LEVELS[i],
            "method_directness": DIRECTNESS_LEVELS[_scale_index(i, n, len(DIRECTNESS_LEVELS))],
            "effect_strength": EFFECT_LEVELS[_scale_index(i, n, len(EFFECT_LEVELS))],
            "method_class": "defined_factor_perturbation",
            "retraction_status": "none",
        })
    return ladder


def _settings_label(prov: dict) -> str:
    return (f"groups={prov['independent_groups']} reps={prov['replication_count']} "
            f"directness={prov['method_directness']} effect={prov['effect_strength']}")


def skepticism_flip_point(ingest_fn):
    """RULE under test: reading the ladder thin -> thick, behavior flips AT MOST ONCE from HOLD
    (nothing moved: a hold_pending or a no_op) to REVISE (some claim's confidence actually moved),
    and never flips back -- i.e. never revise at low strength then hold at higher strength.
    'REVISE' is defined as a claim actually moving in the snapshot (stronger evidence than
    matching on op name, since op names are the API's vocabulary, not its observed effect).
    """
    ladder = flip_point_ladder()
    curve = []  # (settings, dlo, is_revise)
    violations = []
    for prov in ladder:
        rec, viol = _fire(ingest_fn, prov)
        is_revise = bool(rec["moved"])
        curve.append((prov, _biggest_move(rec), is_revise))
        violations.extend(viol)

    revise_flags = [c[2] for c in curve]
    dlo_values = [c[1] for c in curve]
    never_flips_back = all(not (revise_flags[i - 1] and not revise_flags[i])
                            for i in range(1, len(revise_flags)))
    n_flips = sum(1 for i in range(1, len(revise_flags))
                  if revise_flags[i] and not revise_flags[i - 1])
    flips_at_most_once = n_flips <= 1
    dlo_nondecreasing = _is_nondecreasing(dlo_values)
    ok = never_flips_back and flips_at_most_once and dlo_nondecreasing

    flip_point = None
    for i in range(1, len(curve)):
        if curve[i][2] and not curve[i - 1][2]:
            flip_point = {"from_settings": curve[i - 1][0], "to_settings": curve[i][0],
                          "from_index": i - 1, "to_index": i}
            break
    if flip_point is None:
        if all(revise_flags):
            flip_point = "always REVISE across the whole ladder (never held)"
        elif not any(revise_flags):
            flip_point = "always HOLD across the whole ladder (never revised)"
        else:
            flip_point = "no clean single crossing (see never_flips_back/flips_at_most_once)"

    labeled_curve = [(_settings_label(s), dlo, rev) for s, dlo, rev in curve]
    return {"ok": ok, "never_flips_back": never_flips_back,
            "flips_at_most_once": flips_at_most_once, "dlo_nondecreasing": dlo_nondecreasing,
            "flip_point": flip_point, "curve": labeled_curve}, violations


# ---------------------------------------------------------------------------------------------
# Sweep 4: retraction zeroes the update.
# ---------------------------------------------------------------------------------------------

RETRACTION_REASONS = ["retracted", "methodology_flaw", "withdrawn"]


def check_retraction(ingest_fn):
    """RULE under test: otherwise-strong provenance, but retraction_status set to ANY reason
    string -> strength collapses -> no mutating op is emitted and no claim moves. Checked against
    several distinct reason strings so the property isn't accidentally keyed on one literal word.
    """
    results = []
    violations = []
    for reason in RETRACTION_REASONS:
        prov = dict(STRONG_BASELINE)
        prov["retraction_status"] = reason
        rec, viol = _fire(ingest_fn, prov)
        ok = (not rec["moved"]) and (not rec["attempted_mutation"])
        results.append({"reason": reason, "ok": ok, "ops": rec["ops"], "moved": rec["moved"]})
        violations.extend(viol)
    return all(r["ok"] for r in results), results, violations


# ---------------------------------------------------------------------------------------------
# Top-level contract
# ---------------------------------------------------------------------------------------------


def run(ingest_fn: IngestFn) -> dict:
    notes = []
    all_violations = []

    # 1) multi-dimension monotonicity
    monotonic = {}
    curves = {}
    for dim, levels in SWEEP_DIMS.items():
        curve, mono, viol = sweep_dimension(ingest_fn, dim, levels)
        monotonic[dim] = mono
        curves[dim] = curve
        all_violations.extend(viol)
        if not mono:
            notes.append(f"{dim}: NOT non-decreasing -- {curve}")

    # 2) saturation at the strong end (informational finding, not scored)
    saturates, sat_detail = check_saturation(curves["independent_groups"])
    notes.append(f"saturation independent_groups(=4 vs =8): {sat_detail}")
    reps_saturates, reps_sat_detail = check_saturation(curves["replication_count"])
    if reps_saturates:
        notes.append(f"replication_count ALSO saturates (=4 vs =8): {reps_sat_detail}")

    # 3) skepticism flip point
    flip_result, flip_viol = skepticism_flip_point(ingest_fn)
    all_violations.extend(flip_viol)
    notes.append(f"flip point: {flip_result['flip_point']}")
    if not flip_result["ok"]:
        notes.append(
            f"flip-point property failed: never_flips_back={flip_result['never_flips_back']} "
            f"flips_at_most_once={flip_result['flips_at_most_once']} "
            f"dlo_nondecreasing={flip_result['dlo_nondecreasing']}")

    # 4) retraction
    retraction_ok, retraction_detail, retr_viol = check_retraction(ingest_fn)
    all_violations.extend(retr_viol)
    if not retraction_ok:
        notes.append(f"retraction FAILED on: {[r for r in retraction_detail if not r['ok']]}")

    # ---- score: fraction of monotonicity + flip-ordering + retraction properties satisfied ----
    properties = dict(monotonic)
    properties["flip_ordering"] = flip_result["ok"]
    properties["retraction"] = retraction_ok
    score = sum(1 for v in properties.values() if v) / len(properties)

    if all_violations:
        # A structural DeltaAPI violation (unknown op / unattributed write) means a sweep point
        # could not be trusted to measure calibration at all -- this is a firewall bug, not a
        # calibration-shape issue, so it forces the score rather than silently averaging in.
        score = 0.0
        notes.append(f"score forced to 0.0: structural API violations observed: {all_violations}")

    return {
        "score": score,
        "monotonic": monotonic,
        "saturates": saturates,
        "flip_point": flip_result["flip_point"],
        "retraction_ok": retraction_ok,
        "curves": {**curves, "flip_ladder": flip_result["curve"], "retraction": retraction_detail},
        "notes": " | ".join(notes),
    }


if __name__ == "__main__":
    try:  # Windows consoles default to cp1252; force utf-8 output
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    # Offline run: force the geometric classify() fallback regardless of env, so this is
    # deterministic and doesn't require GT_API_KEY/GT_BASE_URL.
    saved = {k: os.environ.pop(k, None) for k in ("GT_API_KEY", "GT_BASE_URL")}
    try:
        import my_solution
        report = run(my_solution.ingest)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v

    print("=" * 72)
    print("CALIBRATION SWEEPS -- offline / geometric")
    print("=" * 72)
    for dim in SWEEP_DIMS:
        print(f"\n[{dim}]  monotonic={report['monotonic'][dim]}")
        for lvl, dlo in report["curves"][dim]:
            print(f"    {lvl!r:>10} -> Δlo={dlo}")

    print(f"\n[saturation]  saturates(independent_groups, =4 vs =8)={report['saturates']}")

    print("\n[skepticism flip-point]  thin -> thick")
    for label, dlo, is_revise in report["curves"]["flip_ladder"]:
        tag = "REVISE" if is_revise else "HOLD  "
        print(f"    {tag}  Δlo={dlo:<7.4f} {label}")
    print(f"    flip_point = {report['flip_point']}")

    print(f"\n[retraction]  retraction_ok={report['retraction_ok']}")
    for r in report["curves"]["retraction"]:
        print(f"    reason={r['reason']!r:<20} ok={r['ok']}  ops={r['ops']}")

    print("\n" + "-" * 72)
    print(f"SCORE: {report['score']:.3f}")
    print("-" * 72)
    print(f"notes: {report['notes']}")
