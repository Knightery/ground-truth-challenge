# Red-Team Findings

Generated adversarial corpus (84 label-honest items + 6 logic probes) run against the current
`starter/my_solution.py` via `eval/redteam/run_all.py`. Offline/geometric path. Re-run with `--llm`
to exercise the real submission path.

Two kinds of result, kept strictly separate:
- **Logic defect** — a flaw in the decision logic (strength / mechanism routing / umbrella
  propagation) that reproduces on BOTH paths, because it lives *after* classification.
- **Offline-recognition miss** — the geometric fallback's exact-token matcher didn't recognize a
  naturally-phrased cell-state name, so it `no_op`'d before any logic ran. Real brittleness, but the
  LLM path is designed to cover it; not counted as a logic defect.

## Confirmed logic defects (5) — reproduce under the LLM path

### D1. Umbrella-clobber: unmapped `method_class` erases a strong revision  (3 items: LOGIC:CLOBBER-01..03)
A terminal→pluripotent reversal backed by many independent groups, direct, strong evidence
(strength ≈ 9) should move belief a lot. When `method_class` is not one of the five hardcoded keys
in `decide.MECHANISM_CHILD` (`defined_factor`, `env_stress`/`environmental_stress`, `oocyte`,
`spontaneous`), `_resolve_target` returns the **umbrella claim C3g** unchanged. `dispose` revises
C3g directly to ~0.59, then `api._propagate_umbrella` immediately overwrites C3g back to
`min(children)` = 0.90 (children untouched). **Net move: 0.389 log-odds** vs **2.35** for identical
evidence with a mapped mechanism — a ~6× suppression driven purely by mechanism vocabulary. The
hidden judge set will use mechanism words the solution never hardcoded; those updates are silently
gutted. `provenance.strength`'s docstring promises unseen vocabulary "cannot inflate an update" — but
here unseen vocabulary *deflates* it to near-zero.

### D2. Hold-bar leak: a single independent group crosses the revise threshold  (2 items: LOGIC:HOLDBAR-01..02)
`strength(independent_groups=1, replication_count=2, direct, strong) = 3.13 > HOLD_BAR = 3.0`, so a
result from ONE lab (self-replicated twice) emits a `revise_confidence` instead of `hold_pending`.
The challenge explicitly says to hold a single-source result pending. Self-replication is counted the
same as independent replication in `raw = 2.0*groups + 0.5*reps`, so a lab replicating its own result
buys its way over the bar.

### Control (passes): LOGIC:CONTROL-01
Mapped mechanism + many groups + direct + strong → routes to child C3c → moves 2.35 (large), exactly
as it should. Confirms the harness discriminates rather than flagging everything.

### D3 (side-effect, minor): seed umbrella inconsistency
The seed sets C3g = 0.93 but `min(children)` = 0.90 (C3b). The first `revise_confidence` to ANY claim
triggers `_propagate_umbrella`, which "corrects" C3g from 0.93 → 0.90 as a side effect — even when the
revised claim (e.g. C1) has nothing to do with C3g's children. Observed in STREAM-08.

## Offline-recognition misses (31) — geometric fallback brittleness, LLM-path expected to cover
- OOD REGIME/AXIS: 24. Bodies use natural phrasing ("fibroblasts", "neuronal", "myocytes", plural
  "Neurons"/"PluripotentStemCells") that `classify._mentioned_states` (exact case-insensitive token
  match) doesn't recognize → <2 states seen → `no_op`. The existing `ood_battery.py` only ever used
  canonical singular names, so it never surfaced this. On the offline path this is a large silent
  recall hole.
- Calibration: 7, same cause (no_op before `dispose` runs).

## Firewall (0 breaks)
All 15 semantic injection payloads: appended to every benign body → byte-identical deltas; used alone
→ no mutating op; no structural violations. The structural firewall holds offline. NOTE: offline never
invokes the LLM, so this does NOT test whether the model *obeys* a semantic injection — run `--llm`
(and note the Greek-translation defense) for that.

## Stream (needs --llm for a real test)
All 8 ordered scenarios are essentially inert offline (same recognition wall), except STREAM-08 whose
precision-trap step uses canonical names and correctly moved C1. The scenarios (pending→resolve→drop,
contradict-then-reconfirm, anchoring drip, flip-flop, injection mid-stream, retraction-after-revision,
MIN-umbrella pinning, OOD triad) are wired and ready; run under the LLM path to adjudicate the
trajectories against each scenario's fixed `expected_sequence`.

## How to run
```
python eval/redteam/run_all.py          # offline, deterministic, CI-safe
python eval/redteam/run_all.py --llm    # + real submission path (GT_API_KEY/GT_BASE_URL)
```
Full per-item log: `eval/out/redteam.json`.
