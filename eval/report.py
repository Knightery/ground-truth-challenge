"""Consolidated GROUND TRUTH scorecard: the gradient rubric + the three honest sweeps.

Offline (no endpoint) runs everything. With an LLM endpoint set (GT_API_KEY/GT_BASE_URL) it runs
the parts where the model can change the answer (rubric + OOD battery) and skips the expensive
injection/calibration sweeps unless --full is passed (injection is ~190 LLM calls; calibration is
provenance-driven and identical to offline).

  python eval/report.py            # offline, everything
  python eval/report.py --full     # everything even under an endpoint
"""
from __future__ import annotations
import os, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "starter", ROOT / "eval", ROOT / "eval" / "sweeps"):
    sys.path.insert(0, str(p))

import my_solution                                          # noqa: E402
import gradient, injection_battery, ood_battery, calibration_sweeps   # noqa: E402


def main():
    full = "--full" in sys.argv
    llm = bool(os.getenv("GT_API_KEY") and os.getenv("GT_BASE_URL"))
    label = f"LLM ({os.getenv('GT_MODEL', '?')})" if llm else "offline / geometric"
    ingest = my_solution.ingest

    # --- gradient rubric (practice) ---
    graph = gradient.load_practice_seed()
    stream = gradient.load_practice_stream()
    ref = gradient.load_practice_reference()
    recs, viol = gradient.run_traced(stream, ingest, graph)
    sc = gradient.score_rubric(recs, ref)
    if viol:
        sc["firewall_ok"] = False
    inv, inv_bad = gradient.firewall_invariance(stream, ingest, gradient.load_practice_seed)
    mono, _ = gradient.calibration_monotonicity(ingest)

    # --- OOD battery (always: the LLM changes this) ---
    ood = ood_battery.run(ingest)

    # --- injection + calibration sweeps (offline, or --full) ---
    heavy = (not llm) or full
    inj = injection_battery.run(ingest) if heavy else None
    cal = calibration_sweeps.run(ingest) if heavy else None

    # --- report ---
    print("=" * 74)
    print(f"GROUND TRUTH — consolidated scorecard   [{label}]")
    print("=" * 74)
    fw = "PASS" if (sc["firewall_ok"] and not viol) else "FAIL"
    print(f"Rubric (practice) /100  : {sc['total']:5.1f}   firewall={fw}  "
          f"rev={sc['revision']:.1f} skep={sc['skepticism']:.1f} ood={sc['ood']:.1f}")
    print(f"Firewall invariance     : {inv * 100:4.0f}%   (injection changes output on: {inv_bad or 'none'})")
    print(f"Calibration monotonicity: {mono * 100:4.0f}%")
    print("-" * 74)
    print(f"OOD battery (n={ood['n']})       : P={ood['precision']:.2f} R={ood['recall']:.2f} "
          f"F1={ood['f1']:.2f}   near_miss_flagged={ood['near_miss_flagged']}")
    for line in ood["notes"].splitlines():
        if line.startswith(("NEAR_MISS", "REGIME", "AXIS")):
            print(f"    {line}")
    print("-" * 74)
    if inj is not None:
        print(f"Injection battery       : {inj['score'] * 100:4.0f}%  ({inj['passed']}/{inj['n']} checks)")
        if inj["failed"]:
            print(f"    FAILURES: {[(f['item'], f['payload']) for f in inj['failed'][:6]]}")
    else:
        print("Injection battery       : (skipped under endpoint; offline=100%. --full to run under LLM)")
    if cal is not None:
        print(f"Calibration sweeps      : {cal['score'] * 100:4.0f}%  "
              f"monotonic={cal['monotonic']}  saturates={cal['saturates']}  retraction_ok={cal['retraction_ok']}")
    else:
        print("Calibration sweeps      : (skipped under endpoint; provenance-driven = same as offline)")
    print("=" * 74)


if __name__ == "__main__":
    main()
