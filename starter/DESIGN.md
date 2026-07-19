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
target claim, decided in two layers, both anchored on **canonical cell-state names** drawn from the
graph (matched with light plural/suffix lemmatization so `Fibroblasts`, `Neurons`,
`MesodermalProgenitor-like` resolve to their state):

* **Geometry (≥2 named states).** Reason from potency levels and lineage identity along the *whole*
  path. Any hop to a lower potency number is a potency **increase** → in-model `is_contradiction`,
  even when the cells later re-differentiate (this defeats the near-miss precision trap: a reversal
  that visits a real intermediate is in-model, not a lateral regime). A **direct** same-potency,
  cross-lineage jump with no differing-potency intermediate is an out-of-model `is_regime`.
* **Prose fallback (1 named state), sentence-scoped.** Geometry needs two names, but some real items
  name one state and paraphrase the destination (e.g. PR06: *“MidState … reverted to a
  less-committed state … then re-specialized”*). For each sentence containing a canonical name we
  read potency **direction** from a small, domain-grounded lexicon: a non-negated reversal /
  dedifferentiation cue → `is_contradiction`; an explicit *identity-preserving* statement plus an
  **excluded-axis** property (age / senescence / firing rate / metabolism, per `axes_excluded`) →
  `is_axis`. Negation (`never reverted`, `no dedifferentiation`) suppresses a false contradiction.

## 3. State Resolution & Mutations (`dispose`)

* **Skepticism gate.** A contradiction with $S <$ `HOLD_BAR` (3.0) emits `hold_pending`, not a write;
  a later strong result on the same claim resolves and drops it.
* **Calibrated moves.** Confirmed contradictions update in bounded log-odds capped below the API
  ceiling ($\text{Cap}=2.5$). Confirmations of a claim with room nudge gently ($\text{Cap}=1.0$);
  confirmations of near-certain or umbrella claims are `no_op`.
* **Umbrella protection.** Revisions target the mechanism-specific child (or the current MIN child)
  so the parent settles via the framework’s min-over-children propagation instead of being clobbered.

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

Verified offline against the practice sandbox (6/6, PR06 resolved as an in-model revision) and an
84-item adversarial red-team corpus: **firewall 0/15 breaks** (standalone + byte-exact invariance
across benign bodies × provenance tiers), **0 logic-defect breaks** across OOD, calibration, and
stream scenarios.
