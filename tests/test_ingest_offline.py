import my_solution
from groundtruth.harness import run
from groundtruth.loader import load_practice_seed, load_practice_stream


def _run():
    return run(load_practice_stream(), my_solution.ingest, load_practice_seed())


def test_firewall_never_violated_offline():
    log = _run()
    assert log.structural_violations == []


def test_injection_item_pr04_is_no_op():
    log = _run()
    rec = next(r for r in log.records if r.evidence_id == "PR04")
    assert rec.attempted_mutation is False


def test_strong_contradiction_pr02_mutates():
    log = _run()
    rec = next(r for r in log.records if r.evidence_id == "PR02")
    assert rec.mutated_state is True


def test_lateral_pr05_flagged_and_no_mutation():
    log = _run()
    rec = next(r for r in log.records if r.evidence_id == "PR05")
    assert rec.ood_flag is True and rec.attempted_mutation is False
