# tools/rerun_find_rate.py
#
# N2 -- one find, many misses.
#
# QUESTION
#   A result appeared in 1 run and not in k reruns. What does that bound?
#
# The measurand is the REPRODUCIBILITY OF THE FINDING PROCESS. It is not
# whether the find is real: a result found once and missed ten times is
# consistent with a real thing reached rarely and with an artifact reached
# once, and no count of runs separates those two. Stated here rather than in a
# footnote, because a rate printed beside a result invites being read as a
# confidence in the result.
#
# MISSES ARE BOUNDED INFORMATION, NOT DISCARD
#   Each miss records that the process did not reach the signal on that run,
#   under the conditions of that run. The tool keeps them as rows rather than
#   as a denominator only, because which runs missed and by which path is the
#   quantity a later reader needs and a bare k/n throws away.
#
# Standard library only. Parses under Python 3.9.

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Sequence

from typed import (clopper_pearson, fmt_interval, load_threshold,
                   not_evaluable, threshold_report, typed)

#: how a find was reached. ASSIGNED_PATH is the route the campaign was
#: designed around; SIDE_PATH is any other route the process happened to take.
PATHS = ("ASSIGNED_PATH", "SIDE_PATH", "NOT_APPLICABLE")


def run(run_id: str, found: bool, path: str = "NOT_APPLICABLE",
        note: str = "") -> Dict[str, object]:
    """One run of the campaign.

    A run that did not find anything carries path NOT_APPLICABLE -- the route
    a miss did not take is not a fact about the miss, and recording one would
    put a guess in the record.
    """
    if path not in PATHS:
        raise ValueError("path %r is outside the declared vocabulary %r" % (path, PATHS))
    if not found and path != "NOT_APPLICABLE":
        raise ValueError("a run that found nothing cannot declare a find path")
    if found and path == "NOT_APPLICABLE":
        raise ValueError("a find must declare ASSIGNED_PATH or SIDE_PATH")
    return {"run_id": run_id, "found": bool(found), "path": path, "note": note}


def score(runs: Sequence[Dict[str, object]],
          confidence: Optional[float] = None) -> Dict[str, object]:
    """Per-run find probability with an exact interval, plus the miss record.

    Returns SINGLE_FIND when exactly one run found the result. A single
    positive fixes a point estimate of 1/n and fixes almost nothing else; the
    typed return exists so the interval is not quietly read as a rate.
    """
    runs = list(runs)
    if not runs:
        return not_evaluable("no runs supplied; a rate has no denominator")
    if confidence is None:
        confidence = float(load_threshold("n2.confidence")["value"])

    n = len(runs)
    finds = [r for r in runs if r["found"]]
    misses = [r for r in runs if not r["found"]]
    k = len(finds)

    interval = clopper_pearson(k, n, confidence)

    side = [r for r in finds if r["path"] == "SIDE_PATH"]
    assigned = [r for r in finds if r["path"] == "ASSIGNED_PATH"]
    if k == 0:
        side_share: Optional[float] = None
        side_note = "no finds; a side-path share has no denominator"
    else:
        side_share = len(side) / k
        side_note = ""

    fields = dict(
        runs=n, finds=k, misses=len(misses),
        interval=interval,
        side_path_finds=len(side), assigned_path_finds=len(assigned),
        side_path_share=side_share, side_path_note=side_note,
        miss_record=[{"run_id": r["run_id"], "note": r["note"]} for r in misses],
        find_record=[{"run_id": r["run_id"], "path": r["path"], "note": r["note"]}
                     for r in finds],
    )
    if k == 1:
        return typed("SINGLE_FIND", k_runs=n, **fields)
    return typed("VALUE", quantity="per_run_find_probability", **fields)


def side_path_share(result: Dict[str, object]) -> Optional[float]:
    """Fraction of finds reached off the assigned path. None when there are no
    finds -- an empty numerator over an empty denominator is not a zero."""
    return result.get("side_path_share")


# ---------------------------------------------------------------------------
# fixture -- SECONDARY
# ---------------------------------------------------------------------------

FIXTURE_PROVENANCE = """\
SECONDARY. As reported: the finding appeared in the original campaign by a
SIDE PATH -- a route the campaign was not designed around -- and ten reruns of
the same campaign all missed it. The primary record is UNREAD here; the counts
below are the reported structure (1 find, 10 misses) and not a transcription
of any run log.

WHAT THE 1-OF-11 DOES NOT SAY, recorded so the interval is not over-read:

  * It does not say the find is wrong. A rarely-reached real result and a
    once-reached artifact produce the same 1/11.
  * It does not say the reruns were identical to the original. "The same
    campaign" is the report's phrase; whether the side path was reachable at
    all on the reruns is exactly the quantity that would separate a low rate
    from a closed route, and it is UNREAD.
  * The one find came off the SIDE path, so the ASSIGNED path is 0 for 11 --
    which is the sharper number of the two and is not the one the headline
    carries.
"""


def fixture_runs() -> List[Dict[str, object]]:
    rows = [run("original", True, "SIDE_PATH",
                "reached off the route the campaign was designed around")]
    for i in range(1, 11):
        rows.append(run("rerun_%02d" % i, False, "NOT_APPLICABLE",
                        "same campaign as reported; whether the side path was "
                        "reachable on this run is UNREAD"))
    return rows


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def render(result: Dict[str, object]) -> List[str]:
    out = []
    if result["kind"] == "NOT_EVALUABLE":
        return ["  NOT_EVALUABLE -- %s" % result["reason"]]
    out.append("  runs %d   finds %d   misses %d" %
               (result["runs"], result["finds"], result["misses"]))
    out.append("  per-run find probability: %s" % fmt_interval(result["interval"]))
    out.append("  VERDICT: %s" % result["kind"])
    if result["kind"] == "SINGLE_FIND":
        out.append("    one positive over %d runs. The point estimate is 1/%d "
                   "and the interval is" % (result["k_runs"], result["k_runs"]))
        out.append("    most of the unit line; this bounds the process, not "
                   "the result.")
    share = result["side_path_share"]
    if share is None:
        out.append("  side-path share of finds: None -- %s" % result["side_path_note"])
    else:
        out.append("  side-path share of finds: %.3f (%d of %d finds off the "
                   "assigned path)" % (share, result["side_path_finds"], result["finds"]))
    assigned_iv = clopper_pearson(result["assigned_path_finds"], result["runs"])
    out.append("  assigned-path find probability: %s" % fmt_interval(assigned_iv))
    out.append("  miss record (%d rows kept, not summed away):" % len(result["miss_record"]))
    for m in result["miss_record"][:3]:
        out.append("    %-12s %s" % (m["run_id"], m["note"]))
    if len(result["miss_record"]) > 3:
        out.append("    ... %d more, each carrying the same note"
                   % (len(result["miss_record"]) - 3))
    return out


def run_fixture() -> int:
    print("N2 rerun_find_rate.py -- one find, many misses")
    print("=" * 72)
    print()
    print(FIXTURE_PROVENANCE)
    res = score(fixture_runs())
    print("THE REPORTED CAMPAIGN")
    for line in render(res):
        print(line)
    print()
    print("CONTRAST -- the same 11 runs with the find on the ASSIGNED path.")
    print("The headline rate is identical; what moves is the second number.")
    alt = [run("original", True, "ASSIGNED_PATH", "assigned route")] + \
          [run("rerun_%02d" % i, False) for i in range(1, 11)]
    for line in render(score(alt)):
        print(line)
    print()
    print("CONTRAST -- zero finds in 11 runs. A different absence: the point")
    print("estimate is a measured zero and the side-path share is None,")
    print("because an empty numerator over an empty denominator is not 0.0.")
    for line in render(score([run("r%02d" % i, False) for i in range(11)])):
        print(line)
    print()
    print("thresholds in force:")
    for line in threshold_report():
        print(line)
    return 0


# ---------------------------------------------------------------------------

def _selftest() -> int:
    checks = 0

    def ck(cond, label):
        nonlocal checks
        checks += 1
        if not cond:
            raise AssertionError("FAILED: " + label)

    # SINGLE_FIND fires on exactly one find and not otherwise
    one = score(fixture_runs())
    ck(one["kind"] == "SINGLE_FIND", "one find over eleven returns SINGLE_FIND")
    ck(one["k_runs"] == 11, "SINGLE_FIND carries the run count")
    two = score([run("a", True, "SIDE_PATH"), run("b", True, "ASSIGNED_PATH"),
                 run("c", False)])
    ck(two["kind"] == "VALUE", "two finds is not SINGLE_FIND")
    none = score([run("a", False), run("b", False)])
    ck(none["kind"] == "VALUE", "zero finds is not SINGLE_FIND")

    # the 1-of-11 interval, checked against the closed forms
    iv = one["interval"]
    ck(abs(iv["point"] - 1.0 / 11.0) < 1e-12, "the point estimate is 1/11")
    ck(iv["lo"] < 0.01 and iv["hi"] > 0.40,
       "the 1-of-11 interval spans from under 1% to over 40%")
    ck(iv["hi"] - iv["lo"] > 0.39, "a single find bounds very little")

    # zero finds: a measured zero point, an interval that is not [0,1]
    zi = none["interval"]
    ck(zi["point"] == 0.0, "zero finds gives a point estimate of exactly 0")
    ck(zi["lo"] == 0.0 and zi["hi"] < 1.0,
       "a measured zero still carries an upper bound")

    # side-path share is None with no finds, never 0.0
    ck(side_path_share(none) is None,
       "the side-path share of no finds is None, not 0.0")
    ck("no denominator" in none["side_path_note"], "the None says why")
    ck(abs(side_path_share(one) - 1.0) < 1e-12,
       "the fixture's one find is entirely off the assigned path")
    ck(abs(side_path_share(two) - 0.5) < 1e-12, "a mixed pair gives 0.5")

    # the assigned-path number is the sharper one and is separately reachable
    ck(one["assigned_path_finds"] == 0,
       "the fixture's assigned path found nothing in eleven runs")
    ck(clopper_pearson(0, 11)["hi"] < clopper_pearson(1, 11)["hi"],
       "the assigned-path bound is tighter than the headline bound")

    # misses are kept as rows, not collapsed to a count
    ck(len(one["miss_record"]) == 10, "every miss is kept as a row")
    ck(all("run_id" in m for m in one["miss_record"]), "each miss names its run")
    ck(len(one["find_record"]) == 1 and one["find_record"][0]["path"] == "SIDE_PATH",
       "the find record carries the path")

    # the path vocabulary is closed and coherent
    try:
        run("x", True, "LUCK")
        ck(False, "run() accepted an undeclared path")
    except ValueError:
        ck(True, "run() refuses an undeclared path")
    try:
        run("x", False, "SIDE_PATH")
        ck(False, "run() accepted a path on a miss")
    except ValueError:
        ck(True, "run() refuses a find path on a run that found nothing")
    try:
        run("x", True)
        ck(False, "run() accepted a find with no path")
    except ValueError:
        ck(True, "run() refuses a find that declares no path")

    # an empty campaign refuses rather than returning a rate
    ck(score([])["kind"] == "NOT_EVALUABLE", "no runs refuses")
    ck("denominator" in score([])["reason"], "the refusal names what it lacks")

    # the fixture records what it cannot establish
    ck("SECONDARY" in FIXTURE_PROVENANCE, "the fixture is marked SECONDARY")
    ck("UNREAD" in FIXTURE_PROVENANCE, "the fixture records the unread primary")
    ck("does not say the find is wrong" in FIXTURE_PROVENANCE,
       "the fixture refuses the reading it would most invite")

    # the render does not return the word the shared rule forbids
    text = "\n".join(render(one))
    ck("noise" not in text.lower(), "the render does not return 'noise'")
    ck("bounds the process, not" in text,
       "the SINGLE_FIND render states what it bounds")

    print("rerun_find_rate.py: %d checks, 0 failed" % checks)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(run_fixture())
