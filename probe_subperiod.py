#!/usr/bin/env python3
# stability-trigger-envelope/probe_subperiod.py
#
# NC_023 probe -- work order 2026-10-02, item 3.
#
# QUESTION. envelope_window_frac is 0.25 of the forcing period, so the moving
# RMS runs over a quarter of a carrier cycle. A moving RMS over a window
# shorter than the carrier period is not stationary: on a pure sine it swings
# between roughly 0.43 and 0.90 of the amplitude across a quarter period. If
# two bodies start at different carrier phases, the first-exceedance index
# can move by up to a quarter period, and a SUB-PERIOD lead could read with
# the wrong sign. Every fixture in cases.py leads by zero or exactly one
# reversal, so the carrier phase at onset is identical on both bodies and the
# case is unreached. This file reaches it.
#
# WHAT THIS DOES. Sweeps the cab-first lead over sub-period values and, for
# each, sweeps the absolute carrier phase. Runs classify() unchanged. PRINTS
# the sign ESP-1 reads for every cell. Asserts NOTHING about the sign -- the
# sign is the result -- and changes no threshold. A control column holds the
# carrier phase AT ONSET equal on both bodies (the carrier referenced to the
# onset, as the sibling N4 fixtures do), where the lead should recover
# exactly whatever the window.
#
# READ THE OUTPUT AS: for each lead, how many of the phase sweep read the
# cab first (correct sign), how many read the trailer first (wrong sign),
# how many had no measurable lead. If the wrong-sign count is zero at every
# lead, NC_023's derivation did not reach this instrument and the 0.25
# window has a run behind it. If it is not zero, the defect is reached and a
# retune has something to stand on. Neither outcome is written down here in
# advance as the expected one.
#
# Standard library only. Parses under Python 3.9. Refuses --selftest.

from __future__ import annotations

import math
import os
import sys
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cases
import descent_record as dr

LEADS = (5, 10, 15, 20, 25, 33, 50, 75)          # samples; period is 100
PHASES = tuple(range(0, 100, 10))                  # absolute carrier phase, samples


def carrier(n: int, period: float, amp: float, onset_idx: int, rise: int,
            phase_samples: float, reference_to_onset: bool) -> List[float]:
    """cases.burst with the carrier phase exposed. reference_to_onset=True is
    the control: the carrier starts at the same phase on every body."""
    out = []
    for i in range(n):
        if i < onset_idx:
            level = 0.0
        else:
            k = (i - onset_idx) / float(rise)
            if k > 1.0:
                k = 1.0
            level = amp * k
        origin = onset_idx if reference_to_onset else 0
        out.append(level * math.sin(2.0 * math.pi * (i - origin - phase_samples)
                                    / period))
    return out


def one_cell(lead: int, phase: float, reference_to_onset: bool) -> Dict[str, object]:
    n, per, rate = cases.N, cases.PERIOD_SAMPLES, cases.RATE_HZ
    cab = dr.trace(0.0, rate, carrier(n, per, 1.00, 200, 40, phase, reference_to_onset))
    trl = dr.trace(0.0, rate, carrier(n, per, 0.15, 200 + lead, 40, phase, reference_to_onset))
    rec = cases._record(cab, trl, road_id="probe-subperiod")
    out = dr.classify(rec)
    lead_s: Optional[float] = out.get("onset_lead_s")
    if lead_s is None:
        sign = "NONE"
    elif lead_s > 0:
        sign = "CAB_FIRST"
    elif lead_s < 0:
        sign = "TRAILER_FIRST"
    else:
        sign = "ZERO"
    return {"lead": lead, "phase": phase, "verdict": out["verdict"],
            "lead_samples": None if lead_s is None else lead_s * rate,
            "sign": sign, "agrees": out.get("onset_agrees"),
            "cab_onset": out.get("cab_onset", {}).get("state"),
            "trl_onset": out.get("trailer_onset", {}).get("state")}


def sweep(reference_to_onset: bool) -> List[Dict[str, object]]:
    rows = []
    for lead in LEADS:
        for ph in PHASES:
            rows.append(one_cell(lead, ph, reference_to_onset))
    return rows


def summarise(rows: List[Dict[str, object]], label: str) -> List[str]:
    out = ["%s" % label,
           "  lead   CAB_FIRST  TRAILER_FIRST  NONE/ZERO   lead read (samples) min..max   verdicts"]
    for lead in LEADS:
        cells = [r for r in rows if r["lead"] == lead]
        c = sum(1 for r in cells if r["sign"] == "CAB_FIRST")
        t = sum(1 for r in cells if r["sign"] == "TRAILER_FIRST")
        z = len(cells) - c - t
        reads = [r["lead_samples"] for r in cells if r["lead_samples"] is not None]
        span = ("%+.1f..%+.1f" % (min(reads), max(reads))) if reads else "--"
        verdicts = sorted({r["verdict"] for r in cells})
        out.append("  %4d   %9d  %13d  %9d   %-28s  %s"
                   % (lead, c, t, z, span, ",".join(verdicts)))
    wrong = sum(1 for r in rows if r["sign"] == "TRAILER_FIRST")
    out.append("  wrong-sign cells: %d of %d" % (wrong, len(rows)))
    return out


def main() -> int:
    print("NC_023 sub-period lead probe -- stability-trigger-envelope")
    print("=" * 72)
    print("window: envelope_window_frac = %s of the forcing period (UNCHANGED)"
          % dr.threshold("envelope_window_frac"))
    print("period: %d samples; leads swept: %s; carrier phases swept: %s"
          % (int(cases.PERIOD_SAMPLES), LEADS, PHASES))
    print("the cab is constructed FIRST in every cell, so CAB_FIRST is the")
    print("correct sign and TRAILER_FIRST is the wrong one. Nothing below is")
    print("asserted; the counts are the result.")
    print()
    absolute = sweep(reference_to_onset=False)
    for line in summarise(absolute, "ARM A -- absolute-time carrier (cases.burst's convention; "
                                    "carrier phase at onset DIFFERS between bodies)"):
        print(line)
    print()
    control = sweep(reference_to_onset=True)
    for line in summarise(control, "ARM B -- control: carrier referenced to onset (carrier "
                                   "phase at onset EQUAL on both bodies)"):
        print(line)
    print()
    print("F10 as filed in cases.py (lead 10, absolute carrier, phase 0):")
    r = one_cell(10, 0.0, False)
    print("  verdict %s  sign %s  lead read %s samples  agrees %s  onsets cab=%s trailer=%s"
          % (r["verdict"], r["sign"],
             "--" if r["lead_samples"] is None else "%+.1f" % r["lead_samples"],
             r["agrees"], r["cab_onset"], r["trl_onset"]))
    print()
    print("thresholds in force (none changed by this probe):")
    for line in dr.threshold_report():
        print(line)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        print("probe_subperiod.py carries no checks: its output is a reading, "
              "not a pass. Run it bare.", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
