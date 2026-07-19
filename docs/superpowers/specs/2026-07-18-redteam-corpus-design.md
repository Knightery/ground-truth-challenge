# Red-Team Corpus — Design

**Date:** 2026-07-18
**Goal:** Generate ~110 hard, diverse adversarial evidence items engineered to make the
*current* `starter/my_solution.py:ingest` fail, across all four tested surfaces, and produce a
ranked **break report**. Generation is a parallel subagent blitz; every label is fixed by seed
geometry *before* `ingest` is run, and verified by a second, independent agent.

## The honesty invariant (non-negotiable)

The existing batteries (`eval/sweeps/*.py`) are trustworthy because every expected label is
decided by a written rule / geometry **before** `ingest()` is ever called — never back-filled
from what the solution returned. The red-team set keeps this:

1. A generator agent authors an item and its `expected_*` label **from `seed.json` geometry**
   (potency levels, lineage identity, modeled axes/regimes, declared absences, claims C1–C6),
   writing a one-line `rule` justifying the label. It **must not** call `ingest`/`classify`/
   `strength`/`dispose` to derive the label.
2. A *different* verify agent re-derives the label from geometry and either `CONFIRMS` or
   `REJECTS`. Rejected items are dropped. (Adversarial verify — a solution that is wrong in
   either direction must still be detectable.)
3. Only then does the runner call `ingest`. A "break" = the solution's output disagrees with an
   independently-correct label. This is compatible with red-teaming: we *aim* items at seams,
   but the label's correctness never depends on the solution.

Firewall labels are a *property* (clean vs clean+payload → byte-identical deltas; a payload
alone → no `MUTATING_OPS` delta), which is self-referential and needs no external oracle —
same pattern as `test_adversarial.py` / `injection_battery.py`.

## Seed geometry the generators are handed (from `groundtruth/data/seed.json`)

States (potency 1 most-potent … 3 terminal): PluripotentStemCell(1,pluripotent),
MesodermalProgenitor(2,mesoderm), Fibroblast(3,mesoderm/connective),
SkeletalMuscleCell(3,mesoderm/muscle), Neuron(3,ectoderm/neural),
IntestinalEpithelialCell(3,endoderm/gut). Claims: C1 (no potency increase), C2 (no direct
terminal↔terminal; adjacent only), C3g umbrella (terminal↛pluripotent, any mechanism) over
C3a spontaneous / C3b oocyte_nt / C3c defined_factor / C3d env_stress, C4 contested(0.45),
C5, C6. Excluded axes: biological_age, cell_function_independent_of_identity. Regimes not
modeled: lateral_somatic_conversion, identity_preserving_state_change. Declared absences:
ab_fib_psc, ab_intest_psc, ab_fib_neuron, ab_fib_musc.

## Files (new `eval/redteam/`; never edits `groundtruth/`)

| File | ~N | Attacks the seam |
|---|---|---|
| `_harness.py` | — | Item schema; `run_offline(item)` / `run_llm(item)`; `strength`/geometry label-checker; break-classifier: **real defect** vs **documented offline-only limitation** (`is_axis` offline always misses; <2 recognized state names → all-False); severity ranking (firewall > OOD false-flag/miss > calibration inversion > stream) |
| `firewall_redteam.py` | ~30 | Semantic injections that survive Greek machine-translation (meaning-level, not surface-form); injections naming real claim IDs C1/C2/C3g; homoglyph / zero-width / RTL cell-state names; "helpful correction" social-engineering; body-number spoof with structured provenance pinned **at the HOLD_BAR seam** |
| `ood_redteam.py` | ~40 | NEAR_MISS worded as exotic regime; **decoy named intermediate** (regime that *mentions* a progenitor to look in-model, or contradiction whose intermediate is only implied); 3-hop chains; `is_axis` function-vs-identity traps; single-state axis; cross-germ-layer laterals; scrambled mention order (exploits `_mentioned_states` order-of-appearance) |
| `calibration_redteam.py` | ~30 | Provenance yielding S≈3.0 (HOLD_BAR); **unmapped `method_class` → umbrella-clobber** (revise C3g directly, `_propagate_umbrella` overwrites it back to min(children) → ~0 net move); single-group self-replicated (1 group/2 reps/direct/strong → S≈3.1 revises off one source); retraction-string spoofs; `"2"` vs `"few"`; support that must NOT strengthen (umbrella / ≥0.9 / thin) |
| `stream_redteam.py` | ~8 scenarios | **Currently untested** — ordered streams vs one evolving graph via `groundtruth.harness.run`: pending→resolve→drop; contradict-then-reconfirm; anchoring (drip of weak same-direction results); flip-flop (alternating directions); injection mid-stream; retraction *after* a revision |
| `run_all.py` | — | Runs every item on offline + (optional, `GT_API_KEY`/`GT_BASE_URL`) LLM path → prints BREAK REPORT ranked by severity, writes `eval/out/redteam.json` |

## Generation method

A single `Workflow`:
- **Phase 1 (fan-out, ~8 sonnet agents):** one per surface-slice, each returns geometry-labeled
  items in a fixed JSON schema (id, surface, bucket, body, provenance, era, `expected_*`, rule).
- **Phase 2 (verify, parallel):** each item's label independently re-derived from geometry;
  drop on REJECT.
- **Phase 3 (synthesize):** orchestrator dedupes, writes survivors into the battery files,
  runs `run_all.py` offline, reports breaks.

Model policy: sonnet for generation/verify per `[[no-haiku-subagents]]`; orchestrator (me) does
synthesis + wiring + run.

## Deliverable

The **break report**, not the items: how many items broke `ingest`, on which surface/path, each
with the geometry-fixed label it violated, and whether it is a genuine defect or a documented
offline-only limitation. Firewall breaks (any = disqualifying) ranked first.

## Out of scope

No edits to `groundtruth/` (framework is fixed). No changes to `starter/` solution in this pass —
this pass *finds* breaks; fixing them is a separate decision. LLM path is built and wired but not
fired in this pass (run offline; user fires LLM via Azure later).
