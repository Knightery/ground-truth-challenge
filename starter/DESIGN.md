# GROUND TRUTH — Solution Design

Each item runs through `classify` → `strength` → `dispose`.

`classify` reads the untrusted body and decides *what kind* of change is described.
`strength` reads only structured provenance and decides *how much* to move.
`dispose` turns those two answers into legal `Delta`s and never sees the body.
That split is the firewall: text can neither size nor authorize a write.

---

## Evidence weighting (`strength`)

Provenance only. Counts go through
$S = 10\,(1-e^{-raw/8})\cdot\text{directness}\cdot\text{effect}$ with
$raw = 2.0\,groups + 0.5\,reps$. Eight groups still move more than four; unknown
tokens (`"a handful"`, `"couple"`) default low, never high. Any active
`retraction_status` forces $S = 0$.

## Classification (`classify`)

Four predicates (`is_axis`, `is_regime`, `is_contradiction`, `is_support`), a
target claim, and (for reversals) a mechanism. Everything is anchored on the
graph’s cell-state names.

**Finding states.** Exact/plural tokens (`Fibroblasts`) plus a small alias
lexicon keyed to the six seed identities (`neuronal` → Neuron, `myotube` →
SkeletalMuscleCell, `pluripotent`/`iPSC` → PluripotentStemCell, plus a few
specific markers like `myosin heavy chain` / `intestinal organoid`). Aliases stay
narrow on purpose — a bare `progenitor` would invent intermediates and wreck OOD
precision. A name that only appears in an absence clause (“no stage expressed
pluripotency”) is dropped; negation is movement-verb-aware so “no genetic
manipulation *drove* X back to PSC” still keeps X and PSC.

**Geometry (≥2 states, whole body).** Walk the named path. A hop to a lower
potency number is a potency increase → in-model contradiction, even if the cells
later re-differentiate (that’s the near-miss trap: visiting a real intermediate
is in-model, not a lateral regime). Same-potency, cross-lineage, no intervening
different-potency state, asserted conversion, and no “through an intermediate”
hint → out-of-model regime.

**Prose fallback (1 state, sentence-scoped).** For items like PR06 that name one
state and paraphrase the destination: a non-negated reversal cue → contradiction;
identity preserved plus an excluded-axis property (age, function, firing rate,
…) → axis.

**Support.** “Found zero reversion … cells remained terminal,” naming a terminal
state and exactly one mechanism → support on that child.

Negation is tight on cues (`rather than reprogramming` denies; a distant `no`
does not; `factor-free` is not negation). Denial that *suppresses* a geometric
drop is judged only in the sentence that names both endpoints, so an appended
injection sentence cannot flip a real verdict.

## Mutations (`dispose`)

- Contradiction with $S < 3$ → `hold_pending` (keyed by claim). A later strong
  result on the same claim revises and drops the pending note.
- Strong contradiction → bounded log-odds drop (cap 2.5). Terminal→pluripotent
  hits the C3g family; other potency increases hit C1. Child choice prefers the
  mechanism read from the transition sentence, then `method_class`, then the
  current min child (so min-propagation actually moves the umbrella).
- Support of a dented non-umbrella child → gentle nudge (cap 1.0). Near-certain,
  umbrella-level, or thin confirmations → `no_op`.
- Axis / regime → `propose_axis` / `propose_regime`, no claim rewrite.

## Firewall

No denylist. Structure does the work:

1. `dispose` never reads `body`.
2. Classification needs a real cell-state name in the same sentence as its cue —
   instruction-only text names none, so it classifies all-false → `no_op`, alone
   or appended.
3. Numbers in prose are ignored; only structured provenance feeds `strength`.
4. Exceptions → `no_op`. Deterministic, standard library.
