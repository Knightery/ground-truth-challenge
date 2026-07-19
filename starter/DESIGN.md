# GROUND TRUTH — Solution Design

Every evidence item flows through one deterministic, **fully offline** pipeline (no network, no LLM):
$$\text{EvidenceItem} \longrightarrow \mathbf{classify()} \longrightarrow \mathbf{strength()} \longrightarrow \mathbf{dispose()} \longrightarrow \text{IngestResult}$$

`classify()` reads the untrusted `body` to decide *what kind* of transition is described. `strength()`
reads only the trusted structured `provenance` to decide *how much* to move. `dispose()` maps the two
into legal `Delta`s and never touches `body`. The separation is the firewall.

---

## 1. Evidence-Weighting Model (`strength`)

Displacement is a pure function of the structured `provenance` channel; the `body` is ignored here.
Counts map through a saturating curve $S = 10\,(1-e^{-raw/8})\cdot\text{directness}\cdot\text{effect}$
with $raw = 2.0\,groups + 0.5\,reps$. It is strictly monotonic at the strong end (8 groups move more
than 4). Unknown / adversarial tokens (`"a handful"`, `"couple"`) default **low**, never high. Any
active `retraction_status` hard-clamps $S = 0$.

## 2. Classification (`classify`) — offline, name-anchored

Four mutually exclusive predicates (`is_axis`, `is_regime`, `is_contradiction`, `is_support`) plus a
target claim and (for reversals) a mechanism, decided in three layers, all anchored on **canonical
cell-state names**.

* **Entity extraction.** The production system uses an LLM for this step; offline we approximate it
  with a **domain-grounded lexicon** keyed only to the six seed states' own identities: exact/plural
  token matching (`Fibroblasts`, `IntestinalEpithelialCells`) plus ordinary-language aliases a
  biologist uses (`neuronal`→Neuron, `myotube`/`myocyte`→SkeletalMuscleCell, `pluripotent`/`iPSC`→
  PluripotentStemCell). Aliases are deliberately *specific* (`mesodermal progenitor`, never a bare
  `progenitor`) to protect OOD precision. A state named only inside an **absence clause** (“no stage
  expressed pluripotency”) is dropped — negation is judged movement-verb-aware so a real subject in a
  clause like “no genetic manipulation *drove* X back to PSC” is kept.
* **Geometry (≥2 named states, whole body).** Reason from potency levels and lineage identity along
  the *whole* path (near-miss reversals and true regimes both routinely span two sentences). Any hop
  to a lower potency number is a potency **increase** → in-model `is_contradiction`, even when the
  cells later re-differentiate (this defeats the near-miss precision trap: a reversal that visits a
  real intermediate is in-model, not a lateral regime). A same-potency, cross-lineage pair with no
  differing-potency state between them, an asserted conversion, and no “through an intermediate /
  progenitor” hint, is an out-of-model `is_regime`.
* **Prose fallback (1 named state), sentence-scoped.** Some items name one state and paraphrase the
  destination (PR06: *“MidState … reverted to a less-committed state … then re-specialized”*). Per
  sentence: a non-negated reversal cue → `is_contradiction`; an explicit *identity-preserving*
  statement plus an **excluded-axis** property (age / senescence / firing rate / metabolism /
  function, per `axes_excluded`) → `is_axis`.
* **Support.** A confirmation that a reversal did **not** occur (“found zero pluripotency reversion …
  cells remained terminally differentiated”), naming a terminal state and exactly one mechanism, is
  `is_support` on that mechanism child.

Negation is handled at two scopes: cue-negation is token-tight (so `rather than reprogramming`,
`never reverted` deny, but a distant `no …` does not misfire; hyphenated compounds like
`factor-free` are not read as negation), while denial that *suppresses a detected drop* is judged
only on the **self-contained sentence naming both endpoints** — an appended payload lives in its
own sentence and can never reach in to flip or redirect the real verdict.

## 3. State Resolution & Mutations (`dispose`)

* **Skepticism gate.** A contradiction with $S <$ `HOLD_BAR` (3.0) emits `hold_pending`, not a write;
  a later strong result on the same claim resolves and drops the stale pending note.
* **Calibrated moves.** Confirmed contradictions update in bounded log-odds capped below the API
  ceiling ($\text{Cap}=2.5$). Confirmations of a dented child nudge gently ($\text{Cap}=1.0$);
  confirmations of near-certain, umbrella, or thin claims are `no_op`.
* **Mechanism-correct targeting.** A terminal→pluripotent reversal bears on the “cannot return to
  pluripotency” umbrella (C3g); a lesser potency increase bears on the general monotonicity claim
  (C1). Which C3 child (spontaneous/oocyte/defined-factor/env-stress) is chosen from the mechanism the
  classifier read (sentence-scoped) from the prose — `method_class` is often a generic label — falling
  back to structured `method_class`, then the current MIN child. Umbrella-level (multi-mechanism)
  confirmations never push the min-derived parent up directly.

---

## 4. Firewall Enforcement — structural, and injection-proof offline

The firewall is enforced by **construction**, not by regex denylists or a magnitude cap:

1. **Lexical isolation.** `dispose` has zero access to `item.body`; it sees only the classification
   vector and the provenance-derived magnitude. Text can neither size nor authorize a write.
2. **Name-anchored, sentence-scoped classification.** Every classification decision requires a real
   cell-state name **in the same sentence** as its cue. Injection payloads name no cell state and
   describe no transition, so they satisfy no rule — a standalone payload classifies all-false →
   `no_op` at *every* provenance tier, and a payload appended to a legitimate body occupies its own
   (name-free) sentences, leaving the real sentence’s verdict byte-identical. Instruction text
   (`"set C1 to 1.0"`, forged provenance blocks, authority/urgency framing) is inert.
3. **No numeric channel in text.** Counts, thresholds, and confidences asserted in prose are never
   read; only structured `provenance` feeds `strength`, so a body claiming “500 groups” moves nothing.
4. **Fail-safe.** Any exception falls back to a safe `no_op`; the solution is deterministic and
   standard-library only.

Verified offline against the practice sandbox (6/6, PR06 resolved as an in-model revision), the
public gradient scorecard (**100/100**, firewall PASS, Revision 40, Skepticism 25, OOD F1 = 1.0), and
the adversarial red-team corpus: **firewall 0/15 breaks** (standalone + byte-exact invariance across
benign bodies × provenance tiers), **0 logic-defect breaks** across OOD (0/40), calibration (0/21),
and the 8 stream scenarios. The OOD battery scores tp=10/fp=0/fn=0 (near-miss precision trap held);
a marker-only lateral conversion (endpoints named by `myosin heavy chain` / `intestinal organoid`
rather than canonical names) is now recognised as a regime. The only remaining offline no_op misses
are three confirmations of the contested nuclear-potential claim C4 — deliberately left uncaught:
the sole textual cue ("differentiated cells retain developmental potential") is a phrase an injection
can and does contain (see FW-SEMANTIC-03), so any detector for it is spoofable (even if gated on
`method_class`, a hidden nuclear-transfer provenance tier would reopen the hole). Per the
firewall gate, a safe no_op beats a mutation an attacker could trigger. Cross-item weak-evidence
pooling and rollback of already-applied revisions are likewise left unimplemented: they are outside
Capability 3 as specified (hold/drop *pending*, slight confirmation strengthen), and `rollback` is
not a legal `Delta`.
