# GROUND TRUTH — Solution Design

## Evidence-weighting model
Each item is `strength → classify → dispose`. **strength** is a pure function of the STRUCTURED
provenance: independent groups and replication set a 0–10 value, scaled by method directness and
effect size, zeroed by retraction; unknown tokens default low. It is the only thing that sizes a
change — the body never sizes anything. **classify** answers three yes/no questions (categorical,
never a 1–10 score): is this about an untracked property (axis), a direct cross-lineage same-potency
jump (regime), or a transition that contradicts a claim? An LLM answers them when an endpoint exists;
otherwise a keyword-free geometric fallback decides from the potency and lineage of the cell states
named in the text. **dispose** maps the verdict: axis→propose_axis+flag, regime→propose_regime+flag,
contradiction→revise the target (a log-odds step ∝ strength, capped at 2.5 < the API's 3.0, scoped to
the failing mechanism) when strength clears the hold bar, else hold_pending. The mechanism→child claim
(e.g. defined-factor→C3c) is read from provenance, so the umbrella claim falls out by min-propagation.

## Firewall enforcement
The firewall is **structural, not detected**. dispose never reads the body and only ever acts on a
*described physical transition*; magnitude comes only from provenance. An instruction ("set Q1 to 1.0")
is not a transition, so it classifies as nothing and yields no_op — and a body that both describes a
real transition and embeds a command acts only on the transition (target from classification, size from
provenance), never on the command. Injections are inert because we have no verb for them: no detector,
no tag-stripping (which would mangle benign text like "CD4<CD8 ratio>0.5"), no regex. As defense-in-depth
the classifier restates the untrusted text in another language before answering, destroying the lexical
machinery an attack relies on while preserving benign meaning. Determinism: temperature 0 + pure
strength/dispose; any parse error, timeout, or missing endpoint falls back to the geometric classifier,
and any unexpected exception returns a safe no_op — an item is never crashed into a mutation. The structural guarantee is exact for magnitude (provenance-only) and op vocabulary (closed set); on the LLM path the target/type are body-derived, so the language-restatement is mitigation for target selection, not a structural guarantee. Determinism is hard-guaranteed on the geometric fallback; the LLM path runs at temperature 0 (stable, not bit-exact).
