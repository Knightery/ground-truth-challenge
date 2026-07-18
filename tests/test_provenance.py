from provenance import strength, _count


def test_count_handles_ints_and_words():
    assert _count(4) == 4
    assert _count("many") == 8
    assert _count("several") == 4
    assert _count("few") == 2
    assert _count(1) == 1
    assert _count("none") == 0
    assert _count("unseen-token") == 1  # conservative default


def test_strong_replicated_direct_is_high():
    prov = {"independent_groups": 4, "replication_count": "many",
            "method_directness": "direct", "effect_strength": "strong",
            "retraction_status": "none"}
    assert strength(prov) >= 8.0


def test_single_unreplicated_is_below_hold_bar():
    prov = {"independent_groups": 1, "replication_count": 1,
            "method_directness": "direct", "effect_strength": "strong",
            "retraction_status": "none"}
    assert strength(prov) < 3.0


def test_moderate_several_is_actionable():
    prov = {"independent_groups": "several", "replication_count": "several",
            "method_directness": "direct", "effect_strength": "moderate",
            "retraction_status": "none"}
    assert strength(prov) >= 3.0


def test_retraction_zeroes_strength():
    prov = {"independent_groups": 4, "replication_count": "many",
            "method_directness": "direct", "effect_strength": "strong",
            "retraction_status": "retracted"}
    assert strength(prov) == 0.0
