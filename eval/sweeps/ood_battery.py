"""OOD battery: precision/recall harness for the out-of-model detection axis.

`gradient.py`'s OOD term is one line inside a bigger rubric, scored on 2 hidden items
(PR05/PR06-style). This sweep is a dedicated, LABEL-HONEST battery of >=4 items per
bucket, run directly over the REAL seed (groundtruth/data/seed.json), so ood_flag
precision and recall are separately measurable instead of folded into one number.

THE HONESTY RULE. Every `ood_expected` below is fixed by the GEOMETRY of the transition
described -- real-seed potency_level / lineage_identity, cross-checked against
domain.axes_modeled / axes_excluded / regimes_not_modeled -- decided in the comment
right above the item, BEFORE this file is ever executed. We never call ingest() and
then back-fill a label from what it returned; that would make the eval unable to
detect a solution that is wrong in either direction.

Real seed geometry (groundtruth/data/seed.json), potency_level 0=totipotent..3=terminal:
    PluripotentStemCell   1  pluripotent
    MesodermalProgenitor  2  mesoderm
    Fibroblast            3  mesoderm/connective
    SkeletalMuscleCell    3  mesoderm/muscle
    Neuron                3  ectoderm/neural
    IntestinalEpithelialCell  3  endoderm/gut
domain.axes_modeled = [potency, lineage_identity]
domain.axes_excluded = [biological_age, cell_function_independent_of_identity]
domain.regimes_not_modeled = [lateral_somatic_conversion, identity_preserving_state_change]
Relevant claims: C1 "transitions do not increase potency", C2 "no direct transition
between distinct terminal identities; only adjacent steps", C3g "a terminal cell
cannot return to pluripotency (any mechanism)" (umbrella over C3a spontaneous /
C3b oocyte NT / C3c defined-factor / C3d environmental stress).

Three buckets, each >=4 items:
  NEAR_MISS  ood_expected=False. An in-model contradiction worded to sound exotic: a
             move ALONG the modeled potency axis, either within one lineage branch
             (terminal -> its own progenitor, or vice versa) or straight to/from the
             pluripotent root -- which is exactly what C1/C3a-d/C3g already model.
             Must NOT come back ood_flag=True. This is the precision trap: a solution
             that flags every reversal as OOD "wins" recall on REGIME/AXIS while
             quietly failing every NEAR_MISS, which is why precision is reported
             separately and near_miss_flagged is called out by name.
  REGIME     ood_expected=True (propose_regime). A genuine lateral conversion the
             graph cannot express: terminal -> terminal, DIFFERENT lineage, no
             intermediate progenitor mentioned -- domain.regimes_not_modeled:
             lateral_somatic_conversion. Must come back ood_flag=True and must NOT be
             quietly absorbed as an in-model contradiction (no revise_confidence).
  AXIS       ood_expected=True (propose_axis). An EXCLUDED axis (biological_age or
             cell_function_independent_of_identity) with cell identity unchanged.
             The offline geometric fallback (starter/classify.py:classify_geometric)
             has no notion of is_axis at all -- it only ever sets is_contradiction /
             is_regime from potency_level and lineage_identity -- so offline these are
             EXPECTED to score as recall misses. That is not a bug in this battery; it
             is the reason Task 5 (the LLM classify path) exists. Run with
             GT_API_KEY/GT_BASE_URL set (and re-import my_solution) to see them caught.

Usage:
  python eval/sweeps/ood_battery.py     # offline (geometric fallback), deterministic
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:                                   # Windows consoles default to cp1252; force utf-8 output
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]        # eval/sweeps/ood_battery.py -> repo root
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "starter"))

from groundtruth.api import DeltaAPI          # noqa: E402
from groundtruth.ingest import EvidenceItem, IngestFn, IngestResult   # noqa: E402
from groundtruth.model import GraphView       # noqa: E402
from groundtruth.loader import load_seed      # noqa: E402


def _prov(**overrides: Any) -> dict:
    """A realistic, well-formed provenance record (see starter/provenance.py:strength),
    with sane defaults so each item only needs to override what makes it distinctive.
    Strength/HOLD_BAR/revise-vs-hold only ever governs the NEAR_MISS bucket's ops; it
    never influences ood_flag (dispose() branches on is_axis/is_regime before it ever
    looks at strength), so it is not part of what makes any label correct here.
    """
    base = dict(replication_count="several", independent_groups="several",
                method_class="defined_factor_perturbation", method_directness="direct",
                effect_strength="strong", retraction_status="none")
    base.update(overrides)
    return base


# =============================================================================
# ITEMS -- every `ood_expected` is decided here, from geometry, before any run.
# =============================================================================
ITEMS: list[dict[str, Any]] = []

# ---- NEAR_MISS: in-model contradictions that sound exotic ---------------------
# RULE (NM01): Fibroblast(3,mesoderm/connective) -> MesodermalProgenitor(2,mesoderm).
# potency_level DECREASES in number (3->2) = potency INCREASES biologically, one
# adjacent step, staying inside the mesoderm branch -> contradicts C1 ("transitions
# do not increase potency"). Along the modeled potency axis, in-model -> NOT ood.
ITEMS.append(dict(
    id="NM01", bucket="NEAR_MISS", ood_expected=False,
    rule="Fibroblast(3,mesoderm/connective)->MesodermalProgenitor(2,mesoderm): one "
         "adjacent potency-axis step backward within the mesoderm branch; contradicts "
         "C1, in-model.",
    body=("Under acute metabolic stress in culture, Fibroblast cells lost their "
          "connective-tissue markers and reverted toward a less-committed "
          "MesodermalProgenitor state before the culture was fixed for analysis."),
    provenance=_prov(independent_groups="single", replication_count="single",
                      method_class="environmental_stress", effect_strength="moderate"),
))

# RULE (NM02): SkeletalMuscleCell(3,mesoderm/muscle) -> MesodermalProgenitor(2,mesoderm).
# Same shape as NM01 from the other mesoderm terminal: one adjacent backward step,
# same broad lineage branch -> contradicts C1, in-model -> NOT ood.
ITEMS.append(dict(
    id="NM02", bucket="NEAR_MISS", ood_expected=False,
    rule="SkeletalMuscleCell(3,mesoderm/muscle)->MesodermalProgenitor(2,mesoderm): one "
         "adjacent potency-axis step backward within the mesoderm branch; contradicts "
         "C1, in-model.",
    body=("In a subset of long-term cultures, SkeletalMuscleCell cells spontaneously "
          "dedifferentiated, regressing to a MesodermalProgenitor-like state without "
          "any added factors."),
    provenance=_prov(independent_groups="few", replication_count="several",
                      method_class="spontaneous_reversion", effect_strength="strong"),
))

# RULE (NM03): Fibroblast(3,mesoderm/connective) -> PluripotentStemCell(1,pluripotent).
# A full reversion of a TERMINAL cell to the pluripotent root by a defined-factor
# mechanism is not an unmodeled regime -- it is *precisely* what C3c / the C3g
# umbrella already model ("a terminal cell cannot return to pluripotency"). Sounds
# like the most dramatic possible claim; geometrically it is the canonical in-model
# contradiction -> NOT ood.
ITEMS.append(dict(
    id="NM03", bucket="NEAR_MISS", ood_expected=False,
    rule="Fibroblast(3,mesoderm/connective)->PluripotentStemCell(1,pluripotent) via a "
         "defined-factor mechanism: exactly the transition C3c/C3g already model; "
         "in-model contradiction, NOT a new regime.",
    body=("A defined four-factor cocktail reprogrammed Fibroblast cells all the way "
          "back to the PluripotentStemCell state, confirmed by marker panel and "
          "teratoma assay."),
    provenance=_prov(independent_groups="several", replication_count="many",
                      method_class="defined_factor_perturbation", effect_strength="strong"),
))

# RULE (NM04): Neuron(3,ectoderm/neural) -> PluripotentStemCell(1,pluripotent) via
# oocyte nuclear transfer. Same shape as NM03 via the C3b mechanism child instead of
# C3c: a terminal cell returning to the pluripotent root is the modeled claim family
# C3a-d/C3g, regardless of which terminal lineage it started in -> in-model -> NOT ood.
ITEMS.append(dict(
    id="NM04", bucket="NEAR_MISS", ood_expected=False,
    rule="Neuron(3,ectoderm/neural)->PluripotentStemCell(1,pluripotent) via oocyte "
         "nuclear transfer: the C3b/C3g transition; in-model contradiction, NOT a new "
         "regime.",
    body=("Nuclear transfer into enucleated oocytes reset Neuron cell nuclei to the "
          "PluripotentStemCell state, generating cloned blastocysts."),
    provenance=_prov(independent_groups="few", replication_count="few",
                      method_class="oocyte_nuclear_transfer", effect_strength="strong"),
))

# RULE (NM05): IntestinalEpithelialCell(3,endoderm/gut) -> PluripotentStemCell(1,
# pluripotent) via environmental stress. Same C3d/C3g shape as NM03/NM04 from the
# third germ layer -> in-model -> NOT ood. (Weak provenance here, so dispose() should
# hold rather than revise -- that does not change the ood_flag expectation, only ops.)
ITEMS.append(dict(
    id="NM05", bucket="NEAR_MISS", ood_expected=False,
    rule="IntestinalEpithelialCell(3,endoderm/gut)->PluripotentStemCell(1,pluripotent) "
         "via environmental stress: the C3d/C3g transition; in-model contradiction, NOT "
         "a new regime (thin provenance -> expect hold, not revise, but still NOT ood).",
    body=("A brief low-pH environmental stress protocol was reported to convert "
          "IntestinalEpithelialCell cells into the PluripotentStemCell state within "
          "days."),
    provenance=_prov(independent_groups="single", replication_count="few",
                      method_class="environmental_stress", effect_strength="moderate"),
))

# RULE (NM06): Fibroblast(3,mesoderm/connective) -> MesodermalProgenitor(2,mesoderm)
# -> SkeletalMuscleCell(3,mesoderm/muscle), WITH the intermediate progenitor named.
# Two adjacent-level hops, neither skipping a step: (1) terminal -> its own progenitor
# (a C1-contradicting reversal, same as NM01/NM02), then (2) that progenitor -> a
# sibling terminal in the SAME mesoderm branch (ordinary forward differentiation,
# contradicts nothing). This is NOT "lateral_somatic_conversion" -- that regime is
# defined by a DIRECT terminal-to-terminal jump that skips the intermediate (see the
# REGIME bucket below and the ab_fib_musc/ab_fib_neuron absences in seed.json); here
# the intermediate is explicitly visited, so C2 ("only adjacent steps") is satisfied
# throughout -> in-model -> NOT ood. Included specifically because a same-potency,
# different-lineage-STRING pair of ENDPOINTS (Fibroblast vs SkeletalMuscleCell) is
# exactly the shape a naive first/last-state heuristic mistakes for a lateral regime
# -- this is the precision trap the battery exists to catch.
ITEMS.append(dict(
    id="NM06", bucket="NEAR_MISS", ood_expected=False,
    rule="Fibroblast(3)->MesodermalProgenitor(2)->SkeletalMuscleCell(3), intermediate "
         "progenitor explicitly visited: two adjacent in-model hops (a C1 reversal then "
         "ordinary re-differentiation), never skips a step -> NOT lateral conversion, "
         "NOT ood. Endpoints alone (Fibroblast, SkeletalMuscleCell) look same-potency "
         "+ different-lineage, which is why a last-two-states-only heuristic is prone "
         "to misread this one as a regime.",
    body=("Under a transient reprogramming pulse, Fibroblast cells first regressed to "
          "a MesodermalProgenitor state and then, once the pulse was withdrawn, "
          "differentiated onward into SkeletalMuscleCell cells."),
    provenance=_prov(independent_groups="several", replication_count="several",
                      method_class="defined_factor_perturbation", effect_strength="strong"),
))

# ---- REGIME: genuine lateral conversions, no intermediate mentioned -----------
# RULE (RG01-RG05, shared): each body names exactly two potency_level==3 (terminal)
# states with DIFFERENT lineage_identity, converted DIRECTLY into one another with no
# progenitor mentioned in between. That is domain.regimes_not_modeled:
# lateral_somatic_conversion -- the graph has no edge type for it (only a declared
# *absence*, e.g. ab_fib_neuron / ab_fib_musc in seed.json) -> ood_expected=True, and
# it must surface as propose_regime, never as a revised/refuted claim (there is no
# existing claim that predicted this specific lateral jump to "refute").
ITEMS.append(dict(
    id="RG01", bucket="REGIME", ood_expected=True,
    rule="Fibroblast(3,mesoderm/connective)->Neuron(3,ectoderm/neural) direct, no "
         "intermediate: lateral_somatic_conversion, unmodeled -> ood (matches the "
         "declared absence ab_fib_neuron in seed.json).",
    body=("A single defined factor converted Fibroblast cells directly into Neuron "
          "cells in one step, without passing through any progenitor state."),
    provenance=_prov(method_class="single_factor_transdifferentiation"),
))

ITEMS.append(dict(
    id="RG02", bucket="REGIME", ood_expected=True,
    rule="Fibroblast(3,mesoderm/connective)->SkeletalMuscleCell(3,mesoderm/muscle) "
         "direct, no intermediate: lateral_somatic_conversion, unmodeled -> ood "
         "(matches the declared absence ab_fib_musc in seed.json).",
    body=("Fibroblast cells were directly transdifferentiated into SkeletalMuscleCell "
          "cells by forced expression of a single factor, with no intermediate "
          "progenitor stage detected."),
    provenance=_prov(method_class="direct_transdifferentiation"),
))

ITEMS.append(dict(
    id="RG03", bucket="REGIME", ood_expected=True,
    rule="Neuron(3,ectoderm/neural)->IntestinalEpithelialCell(3,endoderm/gut) direct, "
         "no intermediate: cross-germ-layer lateral conversion, unmodeled -> ood.",
    body=("Neuron cells were converted directly into IntestinalEpithelialCell cells by "
          "a defined transcription-factor cocktail, bypassing any intermediate "
          "state."),
    provenance=_prov(method_class="defined_factor_perturbation"),
))

ITEMS.append(dict(
    id="RG04", bucket="REGIME", ood_expected=True,
    rule="IntestinalEpithelialCell(3,endoderm/gut)->SkeletalMuscleCell(3,mesoderm/"
         "muscle) direct, no intermediate: cross-germ-layer lateral conversion, "
         "unmodeled -> ood.",
    body=("IntestinalEpithelialCell cells were directly converted into "
          "SkeletalMuscleCell cells in a single step, with no progenitor intermediate "
          "observed."),
    provenance=_prov(method_class="small_molecule_reprogramming"),
))

ITEMS.append(dict(
    id="RG05", bucket="REGIME", ood_expected=True,
    rule="SkeletalMuscleCell(3,mesoderm/muscle)->Neuron(3,ectoderm/neural) direct, no "
         "intermediate: cross-germ-layer lateral conversion, unmodeled -> ood.",
    body=("A single-step protocol directly converted SkeletalMuscleCell cells into "
          "Neuron cells without transitioning through any progenitor state."),
    provenance=_prov(method_class="direct_lineage_conversion"),
))

# ---- AXIS: excluded axis, identity unchanged -----------------------------------
# RULE (AX01-AX05, shared): each body names ONE cell state, unchanged at the start
# and end of the sentence, and varies a property NOT in domain.axes_modeled
# (biological_age or cell_function_independent_of_identity) -> ood_expected=True
# (propose_axis). NOTE: starter/classify.py:classify_geometric never sets is_axis --
# it only derives is_contradiction/is_regime from potency_level/lineage_identity of
# >=2 mentioned states -- so with exactly one state mentioned it always returns all-
# False, and these are EXPECTED to come back ood_flag=False (a recall miss) on the
# offline/geometric path. That gap is real and is exactly what the LLM classify path
# (Task 5, is_axis question) exists to close; it is not a labeling error in this
# battery.
ITEMS.append(dict(
    id="AX01", bucket="AXIS", ood_expected=True,
    rule="Neuron: age-related function reversed, identity unchanged (same state named "
         "at both ends) -> biological_age / cell_function_independent_of_identity, "
         "both excluded axes -> ood. Offline geometric fallback has no is_axis path -> "
         "expected miss.",
    body=("Aged Neuron cells regained youthful electrophysiological firing patterns "
          "after treatment, while remaining Neuron cells throughout; cell identity "
          "was unchanged."),
    provenance=_prov(method_class="functional_electrophysiology_assay",
                      effect_strength="moderate"),
))

ITEMS.append(dict(
    id="AX02", bucket="AXIS", ood_expected=True,
    rule="Fibroblast: biological_age (senescence, proliferative capacity), identity "
         "unchanged -> excluded axis -> ood. Offline geometric fallback has no is_axis "
         "path -> expected miss.",
    body=("Fibroblast cells senesced and lost proliferative capacity with advancing "
          "biological age, but retained Fibroblast identity throughout; no change in "
          "lineage or potency was observed."),
    provenance=_prov(method_class="aging_cohort_observation", effect_strength="moderate"),
))

ITEMS.append(dict(
    id="AX03", bucket="AXIS", ood_expected=True,
    rule="SkeletalMuscleCell: cell_function_independent_of_identity (contractile "
         "force), identity unchanged -> excluded axis -> ood. Offline geometric "
         "fallback has no is_axis path -> expected miss.",
    body=("SkeletalMuscleCell cells showed markedly improved contractile force after "
          "treatment, yet remained SkeletalMuscleCell in every identity marker; "
          "function changed but identity did not."),
    provenance=_prov(method_class="contractile_force_assay"),
))

ITEMS.append(dict(
    id="AX04", bucket="AXIS", ood_expected=True,
    rule="IntestinalEpithelialCell: cell_function_independent_of_identity (nutrient "
         "absorption), identity unchanged -> excluded axis -> ood. Offline geometric "
         "fallback has no is_axis path -> expected miss.",
    body=("IntestinalEpithelialCell cells exhibited enhanced nutrient-absorption "
          "activity while continuing to express all canonical IntestinalEpithelialCell "
          "identity markers; no shift in developmental identity was observed."),
    provenance=_prov(method_class="nutrient_absorption_assay"),
))

ITEMS.append(dict(
    id="AX05", bucket="AXIS", ood_expected=True,
    rule="MesodermalProgenitor: biological_age (telomere attrition, senescence "
         "markers), identity and potency unchanged -> excluded axis -> ood. Offline "
         "geometric fallback has no is_axis path -> expected miss.",
    body=("MesodermalProgenitor cells cultured long-term accumulated hallmark aging "
          "changes such as telomere attrition, without any change to their "
          "MesodermalProgenitor identity or potency."),
    provenance=_prov(method_class="senescence_marker_panel", effect_strength="weak"),
))


# =============================================================================
# Harness -- adapted from eval/gradient.py:run_traced(). Each item runs against its
# own fresh copy of the REAL seed (load_seed()) rather than one shared/mutating graph:
# these are independent probes, not a narrative stream, and dispose()'s branch on
# is_axis/is_regime never reads claim confidence, so per-item isolation changes
# nothing about ood_flag while making every result order-independent and reproducible
# in isolation (e.g. `python -c` on a single item would match this run exactly).
# =============================================================================

def _run_item(spec: dict[str, Any], ingest_fn: IngestFn) -> dict[str, Any]:
    graph = load_seed()
    api = DeltaAPI(graph)
    api.set_active_evidence(spec["id"])
    # tag is hidden from the contestant at judging time, same as harness.py/run_traced
    item = EvidenceItem(spec["id"], "", spec["body"], spec["provenance"], "")
    try:
        result = ingest_fn(item, GraphView(graph))
    except Exception as exc:                     # a broken contestant must not sink the sweep
        result = IngestResult([], f"battery caught an exception: {exc!r}", 0.0, False)

    ops: list[str] = []
    for d in result.deltas:
        api.apply(d)
        ops.append(d.op)

    ood_got = bool(result.ood_flag)
    return {
        "id": spec["id"],
        "bucket": spec["bucket"],
        "ood_expected": spec["ood_expected"],
        "ood_got": ood_got,
        "ops": ops,
        "correct": ood_got == spec["ood_expected"],
        "rule": spec["rule"],
        "rationale": result.rationale,
        "violations": list(api.violations),
    }


def run(ingest_fn: IngestFn) -> dict[str, Any]:
    """Run the full battery through `ingest_fn` and score ood_flag as a binary
    classifier against the geometry-fixed labels in ITEMS. Deterministic: fixed
    items, fixed provenance, fresh seed graph per item, no randomness anywhere.
    """
    per_item = [_run_item(spec, ingest_fn) for spec in ITEMS]

    tp = sum(1 for r in per_item if r["ood_expected"] and r["ood_got"])
    fp = sum(1 for r in per_item if not r["ood_expected"] and r["ood_got"])
    fn = sum(1 for r in per_item if r["ood_expected"] and not r["ood_got"])
    tn = sum(1 for r in per_item if not r["ood_expected"] and not r["ood_got"])

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    near_miss = [r for r in per_item if r["bucket"] == "NEAR_MISS"]
    near_miss_flagged_ids = [r["id"] for r in near_miss if r["ood_got"]]

    regime = [r for r in per_item if r["bucket"] == "REGIME"]
    regime_missed_ids = [r["id"] for r in regime if not r["ood_got"]]
    regime_revised_ids = [r["id"] for r in regime if "revise_confidence" in r["ops"]]

    axis = [r for r in per_item if r["bucket"] == "AXIS"]
    axis_missed_ids = [r["id"] for r in axis if not r["ood_got"]]

    violations = [v for r in per_item for v in r["violations"]]

    notes_lines = [
        f"buckets: NEAR_MISS={len(near_miss)} REGIME={len(regime)} AXIS={len(axis)} "
        f"(n={len(per_item)})",
        f"confusion over ood_flag: tp={tp} fp={fp} fn={fn} tn={tn}",
        "NEAR_MISS wrongly flagged ood (false positives, the precision trap): "
        + (", ".join(near_miss_flagged_ids) if near_miss_flagged_ids else "none"),
        "REGIME missed (should have been ood, was not): "
        + (", ".join(regime_missed_ids) if regime_missed_ids else "none"),
        "REGIME wrongly revised a claim instead of proposing a regime: "
        + (", ".join(regime_revised_ids) if regime_revised_ids else "none"),
        "AXIS missed (should have been ood, was not): "
        + (", ".join(axis_missed_ids) if axis_missed_ids else "none")
        + " -- EXPECTED on the offline geometric fallback (starter/classify.py has no "
          "is_axis path); needs the LLM classify path (GT_API_KEY/GT_BASE_URL) to catch.",
    ]
    if violations:
        notes_lines.append(f"STRUCTURAL FIREWALL VIOLATIONS: {violations}")
    notes = "\n".join(notes_lines)

    return {
        "score": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "near_miss_flagged": len(near_miss_flagged_ids),
        "n": len(per_item),
        "per_item": per_item,
        "notes": notes,
    }


def _print_report(result: dict[str, Any], label: str) -> None:
    print("=" * 72)
    print(f"OOD battery - precision/recall sweep  [{label}]")
    print("=" * 72)
    print(f"n={result['n']}   precision={result['precision']:.3f}   "
          f"recall={result['recall']:.3f}   f1/score={result['f1']:.3f}")
    print(f"near_miss_flagged={result['near_miss_flagged']} "
          f"(NEAR_MISS items wrongly flagged ood; must be 0 for a precise solution)")
    print("-" * 72)
    print(f"{'id':6s} {'bucket':10s} {'expect':7s} {'got':7s} {'ok':4s} ops")
    for r in result["per_item"]:
        print(f"{r['id']:6s} {r['bucket']:10s} {str(r['ood_expected']):7s} "
              f"{str(r['ood_got']):7s} {'OK' if r['correct'] else 'XX':4s} {r['ops']}")
    print("-" * 72)
    print(result["notes"])
    print("=" * 72)


if __name__ == "__main__":
    import os

    # Force the offline/geometric path regardless of the ambient environment, so this
    # number is stable and CI-safe (same convention as eval/gradient.py main()).
    saved = {k: os.environ.pop(k, None) for k in ("GT_API_KEY", "GT_BASE_URL")}
    try:
        import my_solution
        outcome = run(my_solution.ingest)
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v

    _print_report(outcome, "offline / geometric")
