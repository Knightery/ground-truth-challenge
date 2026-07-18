# GROUND TRUTH — Solution Design

Each item flows through three pure stages: **`strength` → `classify` → `dispose`**.

## Evidence-weighting model

**`strength`** is a pure function of the STRUCTURED provenance only — the body never sizes anything.
Independent groups and replication count (each parsed from ints *or* words like `few`/`several`/`many`)
set a 0–10 value through a smooth saturating curve (`10·(1−e^(−raw/8))`), scaled by method directness and
effect size, and hard-zeroed by any retraction. The curve stays *strictly increasing* at the strong end
(eight groups move more than four) instead of hitting a flat cap, so calibration keeps resolution where
the evidence is strongest; unknown tokens default low so an unseen vocabulary can never inflate an update.

**`classify`** answers four yes/no questions (categorical, never a 1–10 score): is the result about an
untracked property (**axis**), a *direct* cross-lineage same-potency jump (**regime**), a transition that
makes a cell more potent / less committed (**contradiction**), or a study that reproduces an existing
claim (**support**)? An LLM answers when an endpoint exists; otherwise a keyword-free **geometric
fallback** decides from the potency levels and lineages of the cell states named in the text. Both paths
judge *every hop*, not just the endpoints, so a reversal that passes *through* an intermediate progenitor
is an in-model contradiction, not a lateral regime — this is what defeats the near-miss precision trap.
When the LLM flags a contradiction but omits the target claim, geometry supplies it (LLM detects, geometry
targets), which keeps borderline items stable.

**`dispose`** maps the verdict to legal deltas. *axis* → `propose_axis` + ood-flag; *regime* →
`propose_regime` + ood-flag (never refuting an existing claim). *contradiction* → revise the target down
by a log-odds step ∝ strength (capped at 2.5 < the API's 3.0), scoped to the failing mechanism, once
strength clears the hold bar — else `hold_pending` (skepticism: thin, extraordinary claims are parked, not
written). *support* → a **gentle up-revision** (a smaller cap, 1.0) that captures the rubric's "a
confirming result nudges up / a well-powered replication slightly strengthens," but **only** for a claim
that has room to move, on non-thin provenance, and never an umbrella claim — confirmations of
near-certain, umbrella, or thinly-supported claims are no-ops. The mechanism→child mapping (e.g.
defined-factor → C3c) is read from provenance, so the umbrella claim falls out by min-propagation.

## Firewall enforcement

The firewall is **structural, not detected**. `dispose` never reads the body and only ever acts on a
*described physical transition*; magnitude comes only from provenance. An instruction ("set C3g to 1.0")
is not a transition, so it classifies as nothing and yields `no_op` — and a body that both describes a
real transition *and* embeds a command acts only on the transition (target from classification, size from
provenance), never on the command. **Injections are inert because we have no verb for them**: no detector,
no tag-stripping (which would mangle benign text like `CD4<CD8 ratio>0.5`), no regex. As defense-in-depth
the classifier restates the untrusted text in another language before answering, destroying the lexical
machinery an attack relies on while preserving benign meaning. Any parse error, timeout, or missing
endpoint falls back to the geometric classifier; any unexpected exception returns a safe `no_op` — an item
is never crashed into a mutation. Magnitude (provenance-only) and op vocabulary (closed set) are exact
structural guarantees; on the LLM path target/type are body-derived, so the language-restatement is
mitigation there, not a structural guarantee. Determinism is hard on the geometric fallback and stable at
temperature 0 on the LLM path.

*Validated by an honest eval harness (`eval/`): practice rubric 100/100 under the LLM; firewall 180/180
injection checks + 100% output-invariance under attack; OOD precision/recall 1.00 (near-miss trap and
axis/regime all correct); calibration monotone in every provenance dimension with no strong-end plateau.
Every label is fixed by a construction rule, never read back from the solution's own output.*
