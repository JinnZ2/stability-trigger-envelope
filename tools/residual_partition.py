# tools/residual_partition.py
#
# N3 -- the residual is not noise.
#
# QUESTION
#   After the declared sources are removed, what is left, and what could it be?
#
# The return is UNPARTITIONED carrying the sources that WERE declared. That
# field is the point: a residual of 0.3 against four declared sources and a
# residual of 0.3 against none are different findings, and a bare number
# reports them the same way.
#
# WHAT IT REFUSES TO DO
#   It never scales a candidate and never subtracts one. Fitting a candidate's
#   magnitude to the residual makes any candidate consistent, which is the
#   move that turns an unexplained remainder into a confirmed mechanism
#   without a measurement. Candidates are admitted with a SIGN or a SHAPE
#   only, and candidate() refuses a magnitude field outright.
#
#   A consistent candidate is therefore never an attribution. It says the
#   residual runs the way that mechanism would run it, which several
#   mechanisms can do at once -- the tool reports all of them and ranks none.
#
# Standard library only. Parses under Python 3.9.

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Sequence

from typed import (load_threshold, mean, not_evaluable, threshold_report,
                   typed, unpartitioned)

#: what a candidate may predict about the residual. Sign or shape, never size.
PREDICTIONS = (
    "SIGN_POSITIVE",        # the residual runs above the declared sources
    "SIGN_NEGATIVE",        # below
    "MONOTONE_UP",          # the residual grows across the ordered samples
    "MONOTONE_DOWN",
    "SYMMETRIC_ABOUT_ZERO",  # centred, with both signs present
)

#: fields a candidate may not carry. Admitting any of these is admitting a
#: magnitude, and a magnitude is what would let the candidate be fitted.
FORBIDDEN_CANDIDATE_FIELDS = ("magnitude", "scale", "amplitude", "coefficient",
                              "weight", "size", "gain")


def candidate(name: str, predicts: str, requires: Sequence[str] = (),
              basis: str = "") -> Dict[str, object]:
    """An undeclared source that might account for some of the residual.

    requires names what the data must carry for the prediction to be testable
    at all; a candidate whose requirement is unmet returns not_testable rather
    than being scored against data that cannot address it.
    """
    if predicts not in PREDICTIONS:
        raise ValueError("prediction %r is outside the declared vocabulary %r"
                         % (predicts, PREDICTIONS))
    if not basis.strip():
        raise ValueError("a candidate must state the basis of its prediction; "
                         "a sign asserted from nothing is not a prediction")
    return {"name": name, "predicts": predicts, "requires": list(requires),
            "basis": basis}


def _reject_magnitude(**fields) -> None:
    for f in fields:
        if f.lower() in FORBIDDEN_CANDIDATE_FIELDS:
            raise ValueError(
                "field %r is a magnitude; this tool checks sign and shape only, "
                "because a fitted magnitude makes any candidate consistent" % f)


def partition(observed: Sequence[float],
              declared: Optional[Dict[str, Sequence[float]]] = None,
              candidates: Optional[Sequence[Dict[str, object]]] = None,
              available: Sequence[str] = (),
              sign_floor: Optional[float] = None) -> Dict[str, object]:
    """Remove the declared sources; type what is left; test each candidate.

    available names the variables the dataset actually carries, so a candidate
    requiring one it lacks is not_testable rather than silently unscored.
    """
    observed = list(observed)
    if not observed:
        return not_evaluable("no observations supplied")
    declared = dict(declared or {})
    candidates = list(candidates or [])
    if sign_floor is None:
        sign_floor = float(load_threshold("n3.sign_floor")["value"])

    for name, series in declared.items():
        if len(series) != len(observed):
            return not_evaluable(
                "declared source %r has %d points against %d observations"
                % (name, len(series), len(observed)))

    residual = []
    for i, y in enumerate(observed):
        residual.append(y - sum(declared[s][i] for s in declared))

    rows = [_test(c, residual, available, sign_floor) for c in candidates]

    result = unpartitioned(
        residual=mean([abs(r) for r in residual]),
        sources_declared=sorted(declared),
        residual_series=residual,
        residual_mean=mean(residual),
        n=len(observed),
        candidates=rows,
        consistent=[r["candidate"] for r in rows if r["verdict"] == "consistent"],
        sign_floor=sign_floor,
    )
    if not declared:
        result["note"] = ("no sources were declared, so the residual is the "
                          "whole observation; this is the loudest form of "
                          "UNPARTITIONED and not a small remainder")
    return result


def _sign(xs: Sequence[float], floor: float) -> str:
    m = mean(xs)
    if m is None:
        return "SIGN_UNRESOLVED"
    if abs(m) <= floor:
        return "SIGN_UNRESOLVED"
    return "SIGN_POSITIVE" if m > 0 else "SIGN_NEGATIVE"


def _test(c: Dict[str, object], residual: Sequence[float],
          available: Sequence[str], floor: float) -> Dict[str, object]:
    """One candidate against the residual. Returns a verdict and its reason.

    The residual is passed in and never modified; this function computes no
    scaled version of it and returns no fitted quantity.
    """
    missing = [r for r in c["requires"] if r not in available]
    if missing:
        return {"candidate": c["name"], "verdict": "not_testable",
                "predicts": c["predicts"],
                "reason": "the data does not carry %s" % ", ".join(missing)}

    p = c["predicts"]
    if p in ("SIGN_POSITIVE", "SIGN_NEGATIVE"):
        got = _sign(residual, floor)
        if got == "SIGN_UNRESOLVED":
            return {"candidate": c["name"], "verdict": "not_testable",
                    "predicts": p,
                    "reason": "mean residual is at or below the sign floor "
                              "(%g); no sign is resolved" % floor}
        return {"candidate": c["name"],
                "verdict": "consistent" if got == p else "inconsistent",
                "predicts": p, "observed": got,
                "reason": "residual sign is %s" % got}

    if p in ("MONOTONE_UP", "MONOTONE_DOWN"):
        if len(residual) < 3:
            return {"candidate": c["name"], "verdict": "not_testable",
                    "predicts": p,
                    "reason": "a shape over %d points is not a shape" % len(residual)}
        diffs = [residual[i + 1] - residual[i] for i in range(len(residual) - 1)]
        up = all(d > 0 for d in diffs)
        down = all(d < 0 for d in diffs)
        if not up and not down:
            return {"candidate": c["name"], "verdict": "inconsistent",
                    "predicts": p, "observed": "NOT_MONOTONE",
                    "reason": "the residual is not monotone in either direction"}
        got = "MONOTONE_UP" if up else "MONOTONE_DOWN"
        return {"candidate": c["name"],
                "verdict": "consistent" if got == p else "inconsistent",
                "predicts": p, "observed": got,
                "reason": "residual is %s" % got}

    # SYMMETRIC_ABOUT_ZERO
    if len(residual) < 3:
        return {"candidate": c["name"], "verdict": "not_testable",
                "predicts": p,
                "reason": "symmetry over %d points is not testable" % len(residual)}
    has_pos = any(r > 0 for r in residual)
    has_neg = any(r < 0 for r in residual)
    centred = abs(mean(residual)) <= floor or (
        abs(mean(residual)) < max(abs(r) for r in residual) / 2.0)
    ok = has_pos and has_neg and centred
    return {"candidate": c["name"],
            "verdict": "consistent" if ok else "inconsistent",
            "predicts": p,
            "observed": "both signs present" if (has_pos and has_neg)
                        else "one-signed",
            "reason": "both signs present and centred" if ok
                      else "the residual is one-signed or off-centre"}


# ---------------------------------------------------------------------------
# worked example -- text only, no data
# ---------------------------------------------------------------------------

WORKED_EXAMPLE = """\
WORKED EXAMPLE (no data; the shape of a case this tool is for)

A survey item whose "yes" carries two meanings that run opposite ways on the
outcome being modelled -- one reading raising the modelled risk, the other
lowering it -- and whose mix shifts across the period the survey covers.

The declared sources in the tenure curve are the ones the model names. The
residual is then not error: it is a candidate source with a SIGN prediction
attached, because a drifting mix of two oppositely-signed readings drags the
curve in a direction the declared sources do not account for.

What this tool would do with it, and what it would refuse:

  DO      admit `term_drift` as a candidate with a predicted sign, and report
          whether the residual runs that way
  DO      report it alongside every other candidate that predicts the same
          sign, ranking none of them
  REFUSE  fit a magnitude to the drift so that the residual is "explained"
  REFUSE  return the leftover as error, which would delete the candidate
          before it was written down

NOT RUN. No survey, no tenure curve and no coding of any item exists here, so
no verdict about term drift is produced anywhere in this folder.
"""


# ---------------------------------------------------------------------------
# fixtures -- CONSTRUCTED
# ---------------------------------------------------------------------------

def fixture_f1():
    """Residual matches the candidate's predicted sign -> consistent."""
    observed = [1.2, 1.4, 1.6, 1.8, 2.0]
    declared = {"declared_trend": [1.0, 1.2, 1.4, 1.6, 1.8]}
    cands = [candidate("upward_undeclared", "SIGN_POSITIVE",
                       basis="CONSTRUCTED: the fixture adds a constant +0.2")]
    return observed, declared, cands


def fixture_f2():
    """Residual runs opposite to the prediction -> inconsistent."""
    observed = [0.8, 1.0, 1.2, 1.4, 1.6]
    declared = {"declared_trend": [1.0, 1.2, 1.4, 1.6, 1.8]}
    cands = [candidate("upward_undeclared", "SIGN_POSITIVE",
                       basis="CONSTRUCTED: the same prediction against a "
                             "residual built to run the other way")]
    return observed, declared, cands


def fixture_f3():
    """No candidate listed -> UNPARTITIONED with an empty candidate table."""
    observed = [1.2, 1.4, 1.6, 1.8, 2.0]
    declared = {"declared_trend": [1.0, 1.2, 1.4, 1.6, 1.8]}
    return observed, declared, []


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def render(result: Dict[str, object]) -> List[str]:
    if result["kind"] == "NOT_EVALUABLE":
        return ["  NOT_EVALUABLE -- %s" % result["reason"]]
    out = ["  VERDICT: %s" % result["kind"]]
    out.append("  sources_declared: %s" % (result["sources_declared"] or "[] -- none"))
    out.append("  residual (mean |r|): %.6f   mean r: %+.6f   n=%d"
               % (result["residual"], result["residual_mean"], result["n"]))
    out.append("  residual series: %s"
               % [round(r, 6) for r in result["residual_series"]])
    if result.get("note"):
        out.append("  note: %s" % result["note"])
    if not result["candidates"]:
        out.append("  candidates: none listed. The residual is typed and")
        out.append("    unattributed; no candidate was ruled in or out, which")
        out.append("    is a different state from every candidate failing.")
        return out
    out.append("  candidates (no ranking; a consistent candidate is not an "
               "attribution):")
    for r in result["candidates"]:
        out.append("    %-22s predicts %-22s %-13s %s"
                   % (r["candidate"], r["predicts"], r["verdict"], r["reason"]))
    return out


def run_fixture() -> int:
    print("N3 residual_partition.py -- the residual is not noise")
    print("=" * 72)
    print()
    print(WORKED_EXAMPLE)
    for label, fx in (("F1 -- residual matches the predicted sign", fixture_f1),
                      ("F2 -- residual runs opposite the prediction", fixture_f2),
                      ("F3 -- no candidate listed", fixture_f3)):
        observed, declared, cands = fx()
        print(label)
        for line in render(partition(observed, declared, cands)):
            print(line)
        print()
    print("CONTRAST -- nothing declared at all. The residual is the whole")
    print("observation, and sources_declared says so.")
    for line in render(partition([1.2, 1.4, 1.6, 1.8, 2.0])):
        print(line)
    print()
    print("CONTRAST -- a candidate requiring a variable the data lacks.")
    print("not_testable, kept apart from inconsistent.")
    observed, declared, _ = fixture_f1()
    c = candidate("covariate_driven", "SIGN_POSITIVE", requires=["ambient_temp"],
                  basis="CONSTRUCTED: prediction conditioned on a covariate")
    for line in render(partition(observed, declared, [c], available=["time"])):
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

    # F1 / F2 / F3 return what the dispatch says they must
    o, d, c = fixture_f1()
    r1 = partition(o, d, c)
    ck(r1["kind"] == "UNPARTITIONED", "F1 returns UNPARTITIONED")
    ck(r1["candidates"][0]["verdict"] == "consistent", "F1 candidate is consistent")
    ck(r1["consistent"] == ["upward_undeclared"], "F1 lists the consistent candidate")
    ck(abs(r1["residual"] - 0.2) < 1e-9, "F1 residual is the constructed 0.2")

    o, d, c = fixture_f2()
    r2 = partition(o, d, c)
    ck(r2["kind"] == "UNPARTITIONED", "F2 returns UNPARTITIONED")
    ck(r2["candidates"][0]["verdict"] == "inconsistent", "F2 candidate is inconsistent")
    ck(r2["consistent"] == [], "F2 lists no consistent candidate")

    o, d, c = fixture_f3()
    r3 = partition(o, d, c)
    ck(r3["kind"] == "UNPARTITIONED", "F3 returns UNPARTITIONED")
    ck(r3["candidates"] == [], "F3 candidate table is empty")
    ck(r3["sources_declared"] == ["declared_trend"],
       "F3 still names the declared source")

    # the empty declaration is the loud case and says so
    empty = partition([1.0, 2.0, 3.0])
    ck(empty["sources_declared"] == [], "an empty declaration is recorded as empty")
    ck("whole observation" in empty["note"], "the empty declaration states its reading")
    ck(abs(empty["residual"] - 2.0) < 1e-9,
       "with nothing declared the residual is the observation itself")

    # not_testable is kept apart from inconsistent
    o, d, _ = fixture_f1()
    c_req = candidate("needs_covariate", "SIGN_POSITIVE", requires=["temp"],
                      basis="CONSTRUCTED")
    nt = partition(o, d, [c_req], available=["time"])
    ck(nt["candidates"][0]["verdict"] == "not_testable",
       "a missing requirement is not_testable")
    ck("does not carry" in nt["candidates"][0]["reason"], "the reason names the gap")
    ck(nt["consistent"] == [],
       "a not_testable candidate is not counted as consistent")
    ck(partition(o, d, [c_req], available=["temp"])["candidates"][0]["verdict"]
       == "consistent", "the same candidate is testable once the data carries it")

    # a shape needs enough points, and a short series says so rather than guessing
    short = partition([1.0, 1.1], {"s": [0.0, 0.0]},
                      [candidate("m", "MONOTONE_UP", basis="CONSTRUCTED")])
    ck(short["candidates"][0]["verdict"] == "not_testable",
       "a shape over two points is not testable")

    # monotone: direction is checked, not merely presence
    up = partition([1.0, 2.0, 4.0], {"s": [0.0, 0.0, 0.0]},
                   [candidate("m", "MONOTONE_UP", basis="CONSTRUCTED"),
                    candidate("d", "MONOTONE_DOWN", basis="CONSTRUCTED")])
    ck(up["candidates"][0]["verdict"] == "consistent", "MONOTONE_UP fires on a rise")
    ck(up["candidates"][1]["verdict"] == "inconsistent",
       "MONOTONE_DOWN does not fire on the same rise")
    flat = partition([1.0, 3.0, 2.0], {"s": [0.0, 0.0, 0.0]},
                     [candidate("m", "MONOTONE_UP", basis="CONSTRUCTED")])
    ck(flat["candidates"][0]["observed"] == "NOT_MONOTONE",
       "a non-monotone residual is reported as such")

    # symmetry
    sym = partition([-1.0, 0.0, 1.0], {"s": [0.0, 0.0, 0.0]},
                    [candidate("s", "SYMMETRIC_ABOUT_ZERO", basis="CONSTRUCTED")])
    ck(sym["candidates"][0]["verdict"] == "consistent", "a centred residual is symmetric")
    asym = partition([1.0, 2.0, 3.0], {"s": [0.0, 0.0, 0.0]},
                     [candidate("s", "SYMMETRIC_ABOUT_ZERO", basis="CONSTRUCTED")])
    ck(asym["candidates"][0]["verdict"] == "inconsistent",
       "a one-signed residual is not symmetric")

    # several candidates can be consistent at once and none is ranked
    both = partition([1.0, 2.0, 3.0], {"s": [0.0, 0.0, 0.0]},
                     [candidate("a", "SIGN_POSITIVE", basis="CONSTRUCTED"),
                      candidate("b", "MONOTONE_UP", basis="CONSTRUCTED")])
    ck(len(both["consistent"]) == 2, "two candidates are consistent at once")
    ck("consistent" in "\n".join(render(both)) and
       "rank" in "\n".join(render(both)).lower(),
       "the render states that a consistent candidate is not an attribution")

    # the residual does not move with the candidate list -- nothing is fitted
    a = partition(o, d, [])
    b = partition(o, d, [candidate("x", "SIGN_NEGATIVE", basis="CONSTRUCTED")])
    ck(a["residual_series"] == b["residual_series"],
       "the residual is identical with and without candidates; nothing is fitted")

    # magnitudes are refused at the boundary
    for field in ("magnitude", "scale", "coefficient", "gain"):
        try:
            _reject_magnitude(**{field: 1.0})
            ck(False, "a magnitude field was accepted: %s" % field)
        except ValueError:
            ck(True, "a %s field is refused" % field)
    try:
        candidate("x", "SIZE_LARGE", basis="CONSTRUCTED")
        ck(False, "an undeclared prediction was accepted")
    except ValueError:
        ck(True, "an undeclared prediction is refused")
    try:
        candidate("x", "SIGN_POSITIVE", basis="  ")
        ck(False, "a candidate with no basis was accepted")
    except ValueError:
        ck(True, "a candidate with no stated basis is refused")

    # mismatched lengths refuse rather than truncating
    bad = partition([1.0, 2.0], {"s": [0.0]})
    ck(bad["kind"] == "NOT_EVALUABLE", "a mismatched declared source refuses")
    ck(partition([])["kind"] == "NOT_EVALUABLE", "an empty observation refuses")

    # the worked example claims no verdict
    ck("NOT RUN" in WORKED_EXAMPLE, "the worked example is marked not run")
    ck("REFUSE" in WORKED_EXAMPLE, "the worked example states what is refused")

    text = "\n".join(render(r1))
    ck("noise" not in text.lower(), "the render does not return 'noise'")

    print("residual_partition.py: %d checks, 0 failed" % checks)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(run_fixture())
