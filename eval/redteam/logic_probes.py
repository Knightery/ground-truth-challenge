"""Path-INDEPENDENT logic probes -- the real prizes.

Unlike the generated corpus (whose naturally-phrased bodies mostly no_op on the offline geometric
classifier's exact-token matcher), these use CANONICAL singular state names so the contradiction is
recognized on BOTH paths and execution reaches decide.dispose(). The break then lives in the
decision logic itself (strength / mechanism routing / umbrella min-propagation), so it reproduces
under the LLM path too -- it is not offline-recognition brittleness.

Every expected_behavior is fixed from the challenge's own principle (thin single-source holds;
well-replicated multi-group direct+strong moves a LOT; retraction zeroes) BEFORE running, never
back-filled from the solution. grade_calibration measures the actual confidence trajectory.
"""

_STRONG = dict(method_directness="direct", effect_strength="strong", retraction_status="none")

ITEMS = [
    # --- UMBRELLA-CLOBBER: strong evidence, unmapped method_class -> dispose targets the C3g
    # umbrella directly -> _propagate_umbrella overwrites the revision back to min(children) ->
    # a ~6x smaller net update than the identical evidence under a mapped mechanism. -------------
    {"id": "LOGIC:CLOBBER-01", "bucket": "umbrella_clobber_unmapped_mechanism",
     "body": "A small-molecule cocktail returned Fibroblast cells to the PluripotentStemCell state, "
             "reproduced by many independent groups.",
     "provenance": {"independent_groups": "many", "replication_count": "many",
                    "method_class": "small_molecule_cocktail", **_STRONG},
     "expected_behavior": "revise_large",
     "rule": "Fibroblast(3)->PluripotentStemCell(1) is an in-model reversal contradicting C3g ('by ANY "
             "mechanism'); many groups x many reps direct+strong => strength ~9.2, far above HOLD_BAR. A "
             "calibrated agent moves belief a LOT regardless of the method name being outside C3a-d.",
     "break_hypothesis": "method_class 'small_molecule_cocktail' matches no MECHANISM_CHILD key, so dispose "
                         "revises C3g DIRECTLY; _propagate_umbrella then resets C3g to min(children) (0.90), "
                         "erasing all but ~0.39 log-odds. Identical evidence with method_class "
                         "'defined_factor_perturbation' moves ~2.35. Path-independent (post-classify)."},
    {"id": "LOGIC:CLOBBER-02", "bucket": "umbrella_clobber_unmapped_mechanism",
     "body": "CRISPR activation of endogenous pluripotency loci reprogrammed Neuron cells into the "
             "PluripotentStemCell state, reproduced by many independent groups.",
     "provenance": {"independent_groups": "many", "replication_count": "several",
                    "method_class": "crispr_activation", **_STRONG},
     "expected_behavior": "revise_large",
     "rule": "Neuron(3)->PluripotentStemCell(1): in-model reversal on C3g; many groups direct+strong => "
             "strength ~8.9 >> HOLD_BAR. Overwhelming evidence => large move.",
     "break_hypothesis": "'crispr_activation' is unmapped -> C3g revised directly -> umbrella min-propagation "
                         "clobbers it back to 0.90. Net move tiny."},
    {"id": "LOGIC:CLOBBER-03", "bucket": "umbrella_clobber_unmapped_mechanism",
     "body": "A Sendai-virus reprogramming protocol returned IntestinalEpithelialCell cells to the "
             "PluripotentStemCell state, reproduced by many independent groups.",
     "provenance": {"independent_groups": "many", "replication_count": "many",
                    "method_class": "sendai_virus_reprogramming", **_STRONG},
     "expected_behavior": "revise_large",
     "rule": "IntestinalEpithelialCell(3)->PluripotentStemCell(1): in-model reversal on C3g; strength ~9.2 "
             ">> HOLD_BAR => large move.",
     "break_hypothesis": "Unmapped mechanism -> C3g direct revision -> umbrella clobber -> near-zero net move."},

    # --- HOLD-BAR LEAK: a SINGLE independent group that self-replicated crosses strength 3.0 and the
    # solution emits a mutation, where a calibrated agent holds a single-source result pending. ----
    {"id": "LOGIC:HOLDBAR-01", "bucket": "single_group_crosses_bar",
     "body": "A defined-factor intervention returned Fibroblast cells to the PluripotentStemCell state.",
     "provenance": {"independent_groups": 1, "replication_count": 2,
                    "method_class": "defined_factor_perturbation", **_STRONG},
     "expected_behavior": "hold",
     "rule": "ONE independent group (self-replicated twice) is a single-source result; the challenge says "
             "hold a single-source result pending. strength=3.13 sits just over HOLD_BAR=3.0 only because "
             "self-replication is counted the same as independent replication.",
     "break_hypothesis": "strength(1 group,2 reps,direct,strong)=3.13 > 3.0 -> dispose emits "
                         "revise_confidence off a single independent group instead of hold_pending."},
    {"id": "LOGIC:HOLDBAR-02", "bucket": "single_group_crosses_bar",
     "body": "An environmental-stress protocol returned Neuron cells to the PluripotentStemCell state.",
     "provenance": {"independent_groups": 1, "replication_count": 3,
                    "method_class": "environmental_stress", **_STRONG},
     "expected_behavior": "hold",
     "rule": "One independent group, self-replicated three times: still single-source => hold pending. "
             "strength=3.44 > HOLD_BAR only via self-replication counting.",
     "break_hypothesis": "Solution revises off one group because reps push strength past the bar."},

    # --- CONTROL (NOT a break): mapped mechanism, well-replicated multi-group -> must move large.
    # Present so the report demonstrably discriminates rather than flagging everything. -----------
    {"id": "LOGIC:CONTROL-01", "bucket": "control_should_pass",
     "body": "A defined-factor intervention returned Fibroblast cells to the PluripotentStemCell state, "
             "reproduced by many independent groups.",
     "provenance": {"independent_groups": "many", "replication_count": "many",
                    "method_class": "defined_factor_perturbation", **_STRONG},
     "expected_behavior": "revise_large",
     "rule": "Mapped mechanism (defined_factor -> child C3c), many groups direct+strong: the canonical "
             "well-replicated contradiction. Routes to C3c and moves ~2.35 log-odds -> large. Should PASS.",
     "break_hypothesis": "(control) if this fails, the harness over-flags; it should be a clean large move."},
]
