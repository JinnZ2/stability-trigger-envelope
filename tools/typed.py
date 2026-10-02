# tools/typed.py
#
# Shared primitives for the four instruments in this directory. One copy, four
# importers: a duplicated threshold loader that drifts is the defect the
# provenance file exists to prevent.
#
# THE SHARED RULE, enforced here rather than described:
#
#   "noise" is never a return value. What is left after the declared sources
#   are removed is returned as a TYPED RESIDUAL carrying its provenance, or as
#   a TYPED ABSENCE carrying its reason. A bare float, a bare zero and a bare
#   None are all refused at the boundary.
#
# Absence states are kept apart on purpose. UNSEARCHED is not ABSENT_MEASURED;
# a channel that was never sampled and a channel sampled at zero call for
# different next actions, and collapsing them reports a silence as a finding.
#
# Standard library only. Parses under Python 3.9.

from __future__ import annotations

import math
import os
from typing import Dict, List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
THRESHOLD_FILE = os.path.join(HERE, "thresholds.txt")
PROVENANCE_FILE = os.path.join(HERE, "threshold_provenance.txt")


# ---------------------------------------------------------------------------
# typed returns
# ---------------------------------------------------------------------------

#: every typed return carries one of these in its "kind" field.
KINDS = (
    "VALUE",                 # a measured quantity, with its provenance
    "UNPARTITIONED",         # a residual survives after declared sources
    "CHANNEL_LOSS",          # detection lost between the data and the reader
    "SINGLE_FIND",           # one positive over k runs; bounds, not a rate
    "NOT_EVALUABLE",         # the input cannot answer the question asked
    "UNSEARCHED",            # not looked for. NOT a measured zero.
    "ABSENT_MEASURED",       # looked for, not there. NOT the same as UNSEARCHED.
    # N4 two_body_source. Widened deliberately: the first build of N4 was
    # refused by this tuple, which is the tuple doing its job. These three are
    # verdicts about WHICH BODY a signal sits on, not degrees of one scale,
    # and nothing orders them.
    "SOURCE_A_MODE",         # a mode of the body the sensor is mounted on
    "SOURCE_B",              # sourced on the body at risk
    "TRAILER_CHANNEL_ABSENT",  # the at-risk body carries no channel at all
)


class TypedError(ValueError):
    """Raised at the boundary when an untyped or unprovenanced value is passed."""


def typed(kind: str, **fields) -> Dict[str, object]:
    """Build a typed return. Refuses a kind outside the declared vocabulary."""
    if kind not in KINDS:
        raise TypedError(
            "kind %r is outside the declared vocabulary %r; widen KINDS "
            "deliberately or use NOT_EVALUABLE" % (kind, KINDS)
        )
    out: Dict[str, object] = {"kind": kind}
    out.update(fields)
    return out


def not_evaluable(reason: str, **fields) -> Dict[str, object]:
    """A refusal that names what it lacks. Never returns a number."""
    if not reason or not reason.strip():
        raise TypedError("NOT_EVALUABLE requires a stated reason")
    return typed("NOT_EVALUABLE", reason=reason, **fields)


def unpartitioned(residual: float, sources_declared: Sequence[str],
                  **fields) -> Dict[str, object]:
    """What is left after the declared sources. Carries which sources those were.

    An empty declaration is legal and is the loudest form of this return: it
    says the whole observation is unpartitioned, which is a different statement
    from a small residual against four declared sources.
    """
    return typed("UNPARTITIONED", residual=residual,
                 sources_declared=list(sources_declared), **fields)


# ---------------------------------------------------------------------------
# exact binomial interval (Clopper-Pearson), standard library
# ---------------------------------------------------------------------------

def _binom_tail_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p). Exact sum, no approximation."""
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i))
    return min(1.0, total)


def _binom_tail_le(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    if k >= n:
        return 1.0
    if k < 0:
        return 0.0
    total = 0.0
    for i in range(0, k + 1):
        total += math.comb(n, i) * (p ** i) * ((1.0 - p) ** (n - i))
    return min(1.0, total)


def _bisect(fn, target: float, lo: float, hi: float, iters: int = 200) -> float:
    """Monotone bisection. Used instead of an incomplete-beta inverse so the
    whole interval is standard library and auditable by hand."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fn(mid) > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def clopper_pearson(k: int, n: int, confidence: float = 0.95
                    ) -> Dict[str, object]:
    """Exact two-sided binomial interval for k successes in n attempts.

    Returns a typed value, never a bare tuple. n == 0 is NOT_EVALUABLE with the
    reason stated -- it is not an interval of [0, 1] and it is not a rate of
    zero, and reporting either would put an unattempted channel on the same
    scale as an attempted one.
    """
    if n < 0 or k < 0:
        return not_evaluable("negative count", k=k, n=n)
    if k > n:
        return not_evaluable("successes exceed attempts", k=k, n=n)
    if n == 0:
        return not_evaluable("no attempts; a rate has no denominator",
                             k=k, n=n)
    alpha = 1.0 - confidence
    point = k / n
    if k == 0:
        lo = 0.0
    else:
        lo = _bisect(lambda p: _binom_tail_ge(k, n, p), alpha / 2.0, 0.0, 1.0)
    if k == n:
        hi = 1.0
    else:
        hi = _bisect(lambda p: 1.0 - _binom_tail_le(k, n, p),
                     1.0 - alpha / 2.0, 0.0, 1.0)
    return typed("VALUE", quantity="rate", point=point, lo=lo, hi=hi,
                 k=k, n=n, confidence=confidence, method="clopper_pearson_exact")


def intervals_overlap(a: Dict[str, object], b: Dict[str, object]) -> Optional[bool]:
    """True/False when both are VALUE intervals; None when either is not.

    None is the absence of a comparison, never a False. Two intervals one of
    which does not exist have not been shown to overlap and have not been shown
    to be disjoint.
    """
    if a.get("kind") != "VALUE" or b.get("kind") != "VALUE":
        return None
    return not (a["hi"] < b["lo"] or b["hi"] < a["lo"])


def wholly_below(a: Dict[str, object], b: Dict[str, object]) -> Optional[bool]:
    """True when interval a sits wholly below interval b."""
    if a.get("kind") != "VALUE" or b.get("kind") != "VALUE":
        return None
    return a["hi"] < b["lo"]


# ---------------------------------------------------------------------------
# thresholds
# ---------------------------------------------------------------------------

def _parse_threshold_file(path: str) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 3)
            if len(parts) < 3:
                raise TypedError("malformed threshold row: %r" % line)
            key, value, status = parts[0], parts[1], parts[2]
            basis = parts[3] if len(parts) > 3 else ""
            rows[key] = {"value": value, "status": status, "basis": basis}
    return rows


def _provenanced_keys(path: str) -> Dict[str, str]:
    """key -> most recent value recorded in the append-only provenance file."""
    seen: Dict[str, str] = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 4)
            if len(parts) < 4:
                continue
            seen[parts[1]] = parts[2]
    return seen


def load_threshold(key: str) -> Dict[str, object]:
    """Read one threshold as a typed value carrying its status and provenance.

    A key present in thresholds.txt with no row in threshold_provenance.txt
    loads with provenanced=False rather than raising: the tool still runs, and
    every render prints the unprovenanced set, so the gap is visible in the
    output rather than at import time in somebody else's traceback.
    """
    rows = _parse_threshold_file(THRESHOLD_FILE)
    if key not in rows:
        return not_evaluable("threshold %r is not declared in thresholds.txt" % key)
    row = rows[key]
    prov = _provenanced_keys(PROVENANCE_FILE)
    provenanced = key in prov and prov[key] == row["value"]
    raw = row["value"]
    if "," in raw:
        parsed: object = [float(x) for x in raw.split(",")]
    else:
        try:
            parsed = float(raw)
        except ValueError:
            parsed = raw
    return typed("VALUE", quantity="threshold", key=key, value=parsed,
                 raw=raw, status=row["status"], basis=row["basis"],
                 provenanced=provenanced)


def threshold_report() -> List[str]:
    """One line per declared threshold. Printed by every tool, by convention:
    a PLACEHOLDER that never appears in an output is a stipulation nobody can
    see they are relying on."""
    rows = _parse_threshold_file(THRESHOLD_FILE)
    prov = _provenanced_keys(PROVENANCE_FILE)
    out = []
    for key in sorted(rows):
        row = rows[key]
        ok = "provenanced" if prov.get(key) == row["value"] else "UNPROVENANCED"
        out.append("  %-28s %-18s %-12s %s" % (key, row["value"], row["status"], ok))
    return out


# ---------------------------------------------------------------------------
# small helpers shared by more than one tool
# ---------------------------------------------------------------------------

def mean(xs: Sequence[float]) -> Optional[float]:
    """None on an empty sequence. Never 0.0 -- an empty channel has no mean,
    and a mean of zero is a measurement."""
    xs = list(xs)
    if not xs:
        return None
    return sum(xs) / len(xs)


def rms(xs: Sequence[float]) -> Optional[float]:
    xs = list(xs)
    if not xs:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def fmt_interval(v: Dict[str, object]) -> str:
    if v.get("kind") != "VALUE":
        return "%s(%s)" % (v.get("kind"), v.get("reason", ""))
    return "%.4f [%.4f, %.4f]  (%d/%d)" % (v["point"], v["lo"], v["hi"],
                                           v["k"], v["n"])


# ---------------------------------------------------------------------------

def _selftest() -> int:
    checks = 0

    def ck(cond, label):
        nonlocal checks
        checks += 1
        if not cond:
            raise AssertionError("FAILED: " + label)

    # typed vocabulary is closed
    try:
        typed("NOISE", x=1)
        ck(False, "typed() accepted a kind outside KINDS")
    except TypedError:
        ck(True, "typed() refuses an undeclared kind")
    ck(typed("VALUE", x=1)["kind"] == "VALUE", "typed() builds a VALUE")

    # NOT_EVALUABLE requires a reason
    try:
        not_evaluable("")
        ck(False, "not_evaluable accepted an empty reason")
    except TypedError:
        ck(True, "not_evaluable refuses an empty reason")

    # UNSEARCHED and ABSENT_MEASURED are separate members
    ck("UNSEARCHED" in KINDS and "ABSENT_MEASURED" in KINDS,
       "the two absence states are both declared")
    ck(typed("UNSEARCHED")["kind"] != typed("ABSENT_MEASURED")["kind"],
       "the two absence states do not collapse")

    # Clopper-Pearson against values that can be checked by hand.
    # k=0,n=10: lower bound is exactly 0; upper solves (1-p)^10 = 0.025.
    v = clopper_pearson(0, 10)
    ck(v["kind"] == "VALUE", "CP returns a VALUE for 0/10")
    ck(abs(v["lo"] - 0.0) < 1e-12, "CP lower bound at k=0 is exactly 0")
    ck(abs(v["hi"] - (1.0 - 0.025 ** 0.1)) < 1e-9,
       "CP upper bound at k=0 matches the closed form")
    # k=n=10: upper bound exactly 1; lower solves p^10 = 0.025.
    v = clopper_pearson(10, 10)
    ck(abs(v["hi"] - 1.0) < 1e-12, "CP upper bound at k=n is exactly 1")
    ck(abs(v["lo"] - 0.025 ** 0.1) < 1e-9,
       "CP lower bound at k=n matches the closed form")
    # symmetry: the interval for k/n mirrors that for (n-k)/n
    a = clopper_pearson(3, 10)
    b = clopper_pearson(7, 10)
    ck(abs(a["lo"] - (1.0 - b["hi"])) < 1e-9, "CP interval is symmetric (lo)")
    ck(abs(a["hi"] - (1.0 - b["lo"])) < 1e-9, "CP interval is symmetric (hi)")
    ck(a["lo"] <= a["point"] <= a["hi"], "CP interval contains the point")
    # a wider interval at the same rate when n is smaller -- the property the
    # N1 denominator sweep turns on
    small = clopper_pearson(3, 10)
    large = clopper_pearson(30, 100)
    ck((large["hi"] - large["lo"]) < (small["hi"] - small["lo"]),
       "CP interval narrows with n at fixed rate")

    # n == 0 is a refusal, not [0, 1] and not a rate of zero
    z = clopper_pearson(0, 0)
    ck(z["kind"] == "NOT_EVALUABLE", "CP refuses a zero denominator")
    ck("denominator" in z["reason"], "the refusal names what it lacks")
    ck(clopper_pearson(3, 2)["kind"] == "NOT_EVALUABLE",
       "CP refuses k > n")

    # overlap comparisons return None rather than False when one side is absent
    ck(intervals_overlap(a, z) is None, "overlap is None against a refusal")
    ck(wholly_below(a, z) is None, "wholly_below is None against a refusal")
    lowv, highv = clopper_pearson(1, 100), clopper_pearson(99, 100)
    ck(wholly_below(lowv, highv) is True, "wholly_below fires on disjoint intervals")
    ck(intervals_overlap(lowv, highv) is False, "overlap is False on disjoint intervals")
    ck(intervals_overlap(a, clopper_pearson(4, 10)) is True,
       "overlap is True on overlapping intervals")

    # thresholds load with their status and provenance
    t = load_threshold("n4.amplitude_ratio_hi")
    ck(t["kind"] == "VALUE" and t["value"] == 3.0, "threshold loads its value")
    ck(t["status"] == "PLACEHOLDER", "threshold carries its status")
    ck(t["provenanced"] is True, "threshold is matched in the provenance file")
    ck(load_threshold("n1.denominator_sweep")["value"] == [10, 25, 50, 100, 250],
       "a list-valued threshold parses")
    ck(load_threshold("nope.missing")["kind"] == "NOT_EVALUABLE",
       "an undeclared threshold refuses rather than defaulting")
    ck(len(threshold_report()) == len(_parse_threshold_file(THRESHOLD_FILE)),
       "every declared threshold is reported (count read from the file, not "
       "stored here -- a stored count is a second place for it to drift)")
    ck(all("UNPROVENANCED" not in ln for ln in threshold_report()),
       "no declared threshold is unprovenanced today")

    # mean/rms return None on empty rather than 0.0
    ck(mean([]) is None, "mean of an empty channel is None, not 0.0")
    ck(rms([]) is None, "rms of an empty channel is None, not 0.0")
    ck(mean([1.0, 3.0]) == 2.0, "mean computes")
    ck(abs(rms([1.0, -1.0]) - 1.0) < 1e-12, "rms computes")

    print("typed.py: %d checks, 0 failed" % checks)
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    print(__doc__ or "")
    print("thresholds in force:")
    for line in threshold_report():
        print(line)
