"""Run the whole red-team corpus through the current solution and print a BREAK REPORT.

Offline (geometric) path by default -- deterministic, CI-safe. Pass --llm to ALSO run the real
submission path (needs GT_API_KEY / GT_BASE_URL; nondeterministic, spends credits).

  python eval/redteam/run_all.py            # offline only
  python eval/redteam/run_all.py --llm      # offline + LLM

Writes eval/out/redteam.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _harness as H                                         # noqa: E402
from firewall_redteam import PAYLOADS                        # noqa: E402
from ood_redteam import ITEMS as OOD_ITEMS                   # noqa: E402
from calibration_redteam import ITEMS as CAL_ITEMS          # noqa: E402
from logic_probes import ITEMS as LOGIC_ITEMS               # noqa: E402
from stream_redteam import SCENARIOS                         # noqa: E402

BAR = "=" * 78


def _run_path(path: str) -> dict:
    logic = H.grade_calibration(LOGIC_ITEMS, path)      # canonical names -> reaches dispose()
    fw = H.grade_firewall(PAYLOADS)
    ood = H.grade_ood(OOD_ITEMS, path)
    cal = H.grade_calibration(CAL_ITEMS, path)
    stream = H.grade_stream(SCENARIOS)
    return {"logic": logic, "firewall": fw, "ood": ood, "calibration": cal, "stream": stream}


def _summ(results: dict) -> dict:
    fw_breaks = [r for r in results["firewall"] if r["break"]]
    ood_breaks = [r for r in results["ood"] if r["break"]]
    ood_known = [r for r in results["ood"] if r.get("flagged_but_known")]
    cal_breaks = [r for r in results["calibration"] if r["break"]]
    cal_known = [r for r in results["calibration"] if r.get("flagged_but_known")]
    stream_breaks = [r for r in results["stream"] if r["break"]]
    stream_review = [r for r in results["stream"] if r["kind"] == "needs-review"]
    return {"fw_breaks": fw_breaks, "ood_breaks": ood_breaks, "ood_known": ood_known,
            "cal_breaks": cal_breaks, "cal_known": cal_known,
            "stream_breaks": stream_breaks, "stream_review": stream_review}


def _print_report(path: str, results: dict) -> None:
    s = _summ(results)
    n = {k: len(results[k]) for k in ("logic", "firewall", "ood", "calibration", "stream")}
    logic_breaks = [r for r in results["logic"] if r["break"]]
    print(BAR)
    print(f"RED-TEAM BREAK REPORT  [{path}]   corpus: logic={n['logic']} fw={n['firewall']} "
          f"ood={n['ood']} cal={n['calibration']} stream={n['stream']}")
    print(BAR)

    print(f"\n[0] PATH-INDEPENDENT LOGIC DEFECTS  (reproduce under the LLM path too)   "
          f"breaks: {len(logic_breaks)}/{n['logic']}")
    for r in results["logic"]:
        tag = "XX" if r["break"] else ".."
        o = r["observed"]
        print(f"  {tag} {r['id']:22s} [{r['bucket']}]  expected={r['expected']} "
              f"observed={o['move_bucket']} (Δlo={o['biggest_move']}) ops={o['ops']}")
        if r["break"]:
            print(f"       {r['break_hypothesis']}")

    print(f"\n[1] FIREWALL  (any break = DISQUALIFYING)   breaks: {len(s['fw_breaks'])}/{n['firewall']}")
    for r in s["fw_breaks"]:
        d = r["detail"]
        why = []
        if d["invariance_fail_on"]:
            why.append(f"deltas changed under injection on {d['invariance_fail_on']}")
        if d["standalone_mutated_at"]:
            why.append(f"payload-alone mutated at {d['standalone_mutated_at']}")
        if d["violations"]:
            why.append(f"structural violation {d['violations']}")
        print(f"  XX {r['id']:22s} [{r['style']}]  {'; '.join(why)}")
    if not s["fw_breaks"]:
        print("  none -- firewall held across every payload/benign-body/tier.")

    print(f"\n[2] OOD  breaks (defects): {len(s['ood_breaks'])}/{n['ood']}   "
          f"(+{len(s['ood_known'])} documented offline-only misses, not defects)")
    for r in sorted(s["ood_breaks"], key=lambda r: r["bucket"] or ""):
        print(f"  XX {r['id']:26s} {r['bucket']:9s} expected_ood={r['expected_ood']} "
              f"got={r['got_ood']}  ops={r['ops']}")
        print(f"       rule: {r['rule']}")
    if not s["ood_breaks"]:
        print("  none that are true logic defects.")
    if s["ood_known"]:
        ids = ", ".join(f"{r['id'].split(':')[-1]}({r['bucket']})" for r in s["ood_known"][:12])
        print(f"  ~~ offline-recognition misses ({len(s['ood_known'])}): {ids}"
              + (" ..." if len(s["ood_known"]) > 12 else ""))
        print("     these no_op'd on naturally-phrased prose the geometric matcher can't tokenize;")
        print("     run --llm to see whether the real submission path catches them.")

    print(f"\n[3] CALIBRATION  breaks (defects): {len(s['cal_breaks'])}/{n['calibration']}   "
          f"(+{len(s['cal_known'])} offline-recognition misses)")
    for r in sorted(s["cal_breaks"], key=lambda r: r["expected"]):
        o = r["observed"]
        print(f"  XX {r['id']:26s} expected={r['expected']:12s} observed={o['move_bucket']} "
              f"(Δlo={o['biggest_move']}) ops={o['ops']}")
        print(f"       rule: {r['rule']}")
        print(f"       why-it-breaks: {r['break_hypothesis']}")
    if not s["cal_breaks"]:
        print("  none that are true logic defects.")
    if s["cal_known"]:
        ids = ", ".join(r["id"].split(":")[-1] for r in s["cal_known"][:12])
        print(f"  ~~ offline-recognition misses ({len(s['cal_known'])}): {ids}"
              + (" ..." if len(s["cal_known"]) > 12 else ""))

    print(f"\n[4] STREAM  hard breaks: {len(s['stream_breaks'])}/{n['stream']}   "
          f"({len(s['stream_review'])} scenarios need trajectory review)")
    for r in results["stream"]:
        tag = "XX" if r["break"] else ".."
        print(f"  {tag} {r['id']:26s} {r['description']}")
        if r["violations"]:
            print(f"       STRUCTURAL VIOLATION: {r['violations']}")
        traj = " -> ".join(str(st["snapshot"]) for st in r["steps"])
        print(f"       expected: {r['expected_sequence']}")
        print(f"       observed: {traj}")

    logic_breaks = [r for r in results["logic"] if r["break"]]
    total_defects = (len(logic_breaks) + len(s["fw_breaks"]) + len(s["ood_breaks"])
                     + len(s["cal_breaks"]) + len(s["stream_breaks"]))
    known = len(s["ood_known"]) + len(s["cal_known"])
    print("\n" + "-" * 78)
    print(f"TOTAL LOGIC-DEFECT BREAKS [{path}]: {total_defects}   "
          f"(logic {len(logic_breaks)}, firewall {len(s['fw_breaks'])}, ood {len(s['ood_breaks'])}, "
          f"calibration {len(s['cal_breaks'])}, stream {len(s['stream_breaks'])})")
    print(f"OFFLINE-RECOGNITION MISSES (not logic defects; LLM path expected to cover): {known}")
    print(BAR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="also run the real LLM submission path")
    ap.add_argument("--out", default="eval/out/redteam.json")
    args = ap.parse_args()

    report = {}
    with H.forced_offline():
        report["offline"] = _run_path("offline")
    _print_report("offline", report["offline"])

    if args.llm:
        if not H.llm_configured():
            print("\n[--llm] skipped: set GT_API_KEY and GT_BASE_URL first.")
        else:
            print()
            report["llm"] = _run_path("llm")
            _print_report("llm", report["llm"])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nfull per-item log -> {out}")


if __name__ == "__main__":
    main()
