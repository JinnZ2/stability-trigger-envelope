# tools/channel_loss.py
#
# N1 -- what the reading channel removed.
#
# QUESTION
#   How much detection is lost to the channel between the data and the reader,
#   versus the reader itself?
#
# The reading is a property of the PAIR (reader, channel). A drop between a
# direct channel and a mediated one is attributable to the channel only when
# the reader is held fixed across them; the tool refuses to compare two
# channels read by different readers rather than reporting a loss that is
# partly a reader difference.
#
# WHAT IT DOES NOT DO
#   It does not say whether a detection is correct. A channel that hands the
#   reader less of the data will also hand it fewer chances to be wrong, and
#   nothing here separates those.
#
# Standard library only. Parses under Python 3.9.

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Sequence

from typed import (clopper_pearson, fmt_interval, intervals_overlap,
                   load_threshold, not_evaluable, threshold_report, typed,
                   wholly_below)


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def channel(name: str, attempts: int, detections: int, reader: str = "UNDECLARED",
            counts: str = "MEASURED", note: str = "") -> Dict[str, object]:
    """One channel's record.

    counts is one of:
      MEASURED                  attempts and detections were counted
      RECONSTRUCTED_FROM_PERCENT  a rate was published and the counts were
                                  rebuilt against an assumed denominator; the
                                  interval is then a property of that assumption
      UNSEARCHED                this channel was not run
    """
    if counts not in ("MEASURED", "RECONSTRUCTED_FROM_PERCENT", "UNSEARCHED"):
        raise ValueError("counts %r is outside the declared vocabulary" % counts)
    return {"name": name, "attempts": attempts, "detections": detections,
            "reader": reader, "counts": counts, "note": note}


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------

def detection_rate(ch: Dict[str, object], confidence: Optional[float] = None
                   ) -> Dict[str, object]:
    """Exact binomial interval for one channel, carrying its counts provenance."""
    if ch["counts"] == "UNSEARCHED":
        return typed("UNSEARCHED", channel=ch["name"],
                     reason="channel declared not run; this is not a rate of zero")
    if confidence is None:
        t = load_threshold("n1.confidence")
        confidence = float(t["value"])
    v = clopper_pearson(int(ch["detections"]), int(ch["attempts"]), confidence)
    if v["kind"] != "VALUE":
        return v
    v["channel"] = ch["name"]
    v["reader"] = ch["reader"]
    v["counts"] = ch["counts"]
    return v


def compare(direct: Dict[str, object], mediated: Dict[str, object],
            confidence: Optional[float] = None) -> Dict[str, object]:
    """Direct against mediated, with the reader held fixed.

    Returns CHANNEL_LOSS when the mediated interval sits wholly below the
    direct interval. Overlapping intervals return a VALUE carrying the point
    loss and the statement that the intervals overlap -- which is not a finding
    of no loss, and the render says so.
    """
    a = detection_rate(direct, confidence)
    b = detection_rate(mediated, confidence)
    for side, v in (("direct", a), ("mediated", b)):
        if v["kind"] == "UNSEARCHED":
            return typed("UNSEARCHED", side=side, channel=v["channel"],
                         reason=v["reason"])
        if v["kind"] != "VALUE":
            return not_evaluable("%s channel: %s" % (side, v.get("reason")),
                                 direct=a, mediated=b)

    if direct["reader"] != mediated["reader"]:
        return not_evaluable(
            "readers differ (%r vs %r); a rate difference across two readers is "
            "not a property of the channel" % (direct["reader"], mediated["reader"]),
            direct=a, mediated=b)

    loss = a["point"] - b["point"]
    below = wholly_below(b, a)
    overlap = intervals_overlap(a, b)
    reconstructed = [v["channel"] for v in (a, b)
                     if v["counts"] == "RECONSTRUCTED_FROM_PERCENT"]

    if below:
        return typed("CHANNEL_LOSS", channel=mediated["name"],
                     direct=a, mediated=b, loss_point=loss,
                     loss_lo=a["lo"] - b["hi"], loss_hi=a["hi"] - b["lo"],
                     intervals_overlap=overlap,
                     reconstructed_channels=reconstructed,
                     reader=direct["reader"])
    return typed("VALUE", quantity="channel_comparison", channel=mediated["name"],
                 direct=a, mediated=b, loss_point=loss,
                 loss_lo=a["lo"] - b["hi"], loss_hi=a["hi"] - b["lo"],
                 intervals_overlap=overlap,
                 reconstructed_channels=reconstructed,
                 reader=direct["reader"],
                 note="intervals overlap; a loss is not established at this n. "
                      "This is not a finding of no loss.")


def _reconstruct_count(rate: float, n: int) -> int:
    """Rebuild a count from a published rate at an assumed denominator.

    [CHOICE 1] The tie rule is round-half-UP, stated because Python's built-in
    round() is round-half-to-EVEN: at n=5 a published 90% gives 4.5, which the
    built-in sends to 4 (rate 0.80) and this sends to 5 (rate 1.00). A tie rule
    that alternates direction with the parity of the denominator is a second
    reconstruction artifact sitting inside the first, and neither is visible in
    the output unless it is named.

    The realized rate is reported beside the published one by the sweep,
    because a small denominator cannot represent an arbitrary percentage and
    the POINT estimate moves as well as the interval.
    """
    import math as _m
    return int(_m.floor(rate * n + 0.5))


def denominator_sweep(direct_rate: float, mediated_rate: float,
                      denominators: Optional[Sequence[float]] = None,
                      confidence: Optional[float] = None) -> List[Dict[str, object]]:
    """Run the comparison at several assumed denominators.

    This exists because a source that publishes only percentages fixes the
    point estimates and fixes nothing about the interval. The verdict can move
    from CHANNEL_LOSS to overlapping across the sweep with no change in the
    published numbers, and where it does, the verdict is a property of the
    assumption rather than of the report.
    """
    if denominators is None:
        denominators = load_threshold("n1.denominator_sweep")["value"]
    rows = []
    for n in denominators:
        n = int(n)
        ka, kb = _reconstruct_count(direct_rate, n), _reconstruct_count(mediated_rate, n)
        a = channel("direct", n, ka, reader="same",
                    counts="RECONSTRUCTED_FROM_PERCENT")
        b = channel("mediated", n, kb, reader="same",
                    counts="RECONSTRUCTED_FROM_PERCENT")
        rows.append({"n": n,
                     "realized_direct": ka / n,
                     "realized_mediated": kb / n,
                     "reconstruction_error": abs((ka / n - kb / n)
                                                 - (direct_rate - mediated_rate)),
                     "result": compare(a, b, confidence)})
    return rows


# ---------------------------------------------------------------------------
# fixture -- SECONDARY, RECONSTRUCTED_FROM_PERCENT
# ---------------------------------------------------------------------------

FIXTURE_PROVENANCE = """\
SECONDARY. A press report of a preprint, read at the level of reported
percentages. The preprint itself is UNREAD here -- this environment's network
policy refuses the host -- so no count in this fixture was taken from the
paper.

  preprint: "Autonomous AI agents discover reverse transcriptases with
             tandem repeat arrays"
  as reported: models given the DNA directly described the array in >= 90% of
               attempts; with files and tools, as low as 32%
  stated cause: the model often did not read enough raw DNA to see a full
                repeat

TWO THINGS THE FIXTURE CANNOT CARRY, both recorded rather than papered over:

  1. The real counts are UNREAD. Every count below is reconstructed against
     an assumed denominator declared in thresholds.txt, and the interval is a
     property of that assumption, not of the report. The sweep is printed for
     exactly this reason.

  2. ">= 90%" is a BOUND and "as low as 32%" is a BOUND, and they are bounds
     in opposite directions. Read as points they overstate the direct channel
     and overstate the loss. The fixture reads them as points because that is
     what a point estimate needs, and says here that doing so is the most
     favourable reading of the gap available from the report.
"""


def fixture_channels(attempts: Optional[int] = None):
    if attempts is None:
        attempts = int(load_threshold("n1.reconstructed_attempts")["value"])
    direct = channel("direct_dna", attempts, _reconstruct_count(0.90, attempts),
                     reader="same_model_family",
                     counts="RECONSTRUCTED_FROM_PERCENT",
                     note="reported as >= 90%; read as a point, which is the "
                          "most favourable reading for the direct channel")
    mediated = channel("files_and_tools", attempts, _reconstruct_count(0.32, attempts),
                       reader="same_model_family",
                       counts="RECONSTRUCTED_FROM_PERCENT",
                       note="reported as 'as low as 32%'; read as a point, "
                            "which is the most favourable reading for the gap")
    return direct, mediated


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def render(result: Dict[str, object]) -> List[str]:
    out = []
    if result["kind"] in ("UNSEARCHED", "NOT_EVALUABLE"):
        out.append("  %s -- %s" % (result["kind"], result.get("reason")))
        return out
    a, b = result["direct"], result["mediated"]
    out.append("  reader held fixed: %s" % result["reader"])
    out.append("  direct   %-18s %s  [%s]" % (a["channel"], fmt_interval(a), a["counts"]))
    out.append("  mediated %-18s %s  [%s]" % (b["channel"], fmt_interval(b), b["counts"]))
    out.append("  loss (direct - mediated)  point %.4f   interval [%.4f, %.4f]"
               % (result["loss_point"], result["loss_lo"], result["loss_hi"]))
    out.append("  intervals overlap: %s" % result["intervals_overlap"])
    out.append("  VERDICT: %s" % result["kind"])
    if result["kind"] == "VALUE":
        out.append("  note: %s" % result["note"])
    if result["reconstructed_channels"]:
        out.append("  RECONSTRUCTED_FROM_PERCENT: %s -- the interval is a "
                   "property of the assumed denominator"
                   % ", ".join(result["reconstructed_channels"]))
    return out


def run_fixture() -> int:
    print("N1 channel_loss.py -- what the reading channel removed")
    print("=" * 72)
    print()
    print(FIXTURE_PROVENANCE)
    n = int(load_threshold("n1.reconstructed_attempts")["value"])
    direct, mediated = fixture_channels(n)
    print("AT THE ASSUMED DENOMINATOR (n = %d per channel, PLACEHOLDER)" % n)
    for line in render(compare(direct, mediated)):
        print(line)
    print()
    print("DENOMINATOR SWEEP -- the same two published percentages, read at")
    print("five assumed denominators. The verdict moves across the sweep with")
    print("no change in the published numbers, and at the small end the point")
    print("estimate moves as well, because an integer count over a small")
    print("denominator cannot represent an arbitrary percentage.")
    print()
    print("     n   realized rates   point loss   direct interval   mediated interval  verdict")
    for row in denominator_sweep(0.90, 0.32):
        r = row["result"]
        if r["kind"] in ("NOT_EVALUABLE", "UNSEARCHED"):
            print("  %4d   %s" % (row["n"], r["kind"]))
            continue
        a, b = r["direct"], r["mediated"]
        print("  %4d   %.2f / %.2f      %.4f       [%.3f, %.3f]     [%.3f, %.3f]    %s"
              % (row["n"], row["realized_direct"], row["realized_mediated"],
                 r["loss_point"], a["lo"], a["hi"], b["lo"], b["hi"], r["kind"]))
    print()
    print("  published point loss is 0.90 - 0.32 = 0.5800. Where the realized")
    print("  rates differ from the published ones, the denominator cannot")
    print("  represent the percentage and the POINT moves as well as the")
    print("  interval -- a second reconstruction artifact, reported not hidden.")
    print()
    print("UNSEARCHED CHANNEL -- an absence, never a rate of zero")
    unread = channel("preprint_counts", 0, 0, reader="same_model_family",
                     counts="UNSEARCHED",
                     note="the preprint is not reachable from this environment")
    for line in render(compare(direct, unread)):
        print(line)
    print()
    print("READER NOT HELD FIXED -- refused rather than attributed")
    other = channel("files_and_tools", n, _reconstruct_count(0.32, n),
                    reader="a_different_model", counts="RECONSTRUCTED_FROM_PERCENT")
    for line in render(compare(direct, other)):
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

    # a clean channel loss fires
    a = channel("direct", 100, 90, reader="r")
    b = channel("mediated", 100, 32, reader="r")
    r = compare(a, b)
    ck(r["kind"] == "CHANNEL_LOSS", "a disjoint pair returns CHANNEL_LOSS")
    ck(abs(r["loss_point"] - 0.58) < 1e-12, "point loss is the rate difference")
    ck(r["intervals_overlap"] is False, "the intervals are disjoint")
    ck(r["loss_lo"] < r["loss_point"] < r["loss_hi"], "the loss carries an interval")

    # the same two rates at a small n do NOT fire -- the sweep's whole point
    small_a = channel("direct", 5, 5, reader="r", counts="RECONSTRUCTED_FROM_PERCENT")
    small_b = channel("mediated", 5, 2, reader="r", counts="RECONSTRUCTED_FROM_PERCENT")
    rs = compare(small_a, small_b)
    ck(rs["kind"] == "VALUE", "overlapping intervals do not return CHANNEL_LOSS")
    ck(rs["intervals_overlap"] is True, "the small-n intervals overlap")
    ck("not a finding of no loss" in rs["note"],
       "the overlapping return refuses to be read as no loss")
    ck(rs["reconstructed_channels"] == ["direct", "mediated"],
       "reconstructed channels are named in the return")

    # equal channels: no loss, and it is still not a CHANNEL_LOSS
    eq = compare(channel("d", 100, 50, reader="r"), channel("m", 100, 50, reader="r"))
    ck(eq["kind"] == "VALUE" and abs(eq["loss_point"]) < 1e-12,
       "equal channels give zero point loss and no verdict")

    # a MEDIATED channel above DIRECT does not fire either -- one direction only
    up = compare(channel("d", 100, 32, reader="r"), channel("m", 100, 90, reader="r"))
    ck(up["kind"] == "VALUE" and up["loss_point"] < 0,
       "a mediated channel above direct returns a negative loss, not a verdict")

    # the sweep moves the verdict without moving the published rates
    rows = denominator_sweep(0.90, 0.32, [5, 250])
    kinds = [row["result"]["kind"] for row in rows]
    ck(kinds[0] != kinds[1],
       "the verdict moves across the denominator sweep at fixed published rates")
    ck(kinds[1] == "CHANNEL_LOSS", "the large assumed denominator fires")
    big = [r for r in rows if r["n"] == 250][0]
    ck(abs(big["result"]["loss_point"] - 0.58) < 1e-9,
       "at a representable denominator the point loss is the published one")
    ck(big["reconstruction_error"] < 1e-9, "no reconstruction error at n=250")
    tiny = [r for r in rows if r["n"] == 5][0]
    ck(tiny["reconstruction_error"] > 1e-9,
       "at n=5 the denominator cannot represent the percentages and the POINT "
       "moves too, not only the interval")
    ck(abs(tiny["reconstruction_error"] - 0.02) < 1e-9,
       "the n=5 point loss is 0.60 against a published 0.58")
    ck(abs(tiny["realized_direct"] - 1.0) < 1e-9,
       "round-half-up sends a published 90% at n=5 to 5/5, not 4/5")
    ck(_reconstruct_count(0.9, 5) == 5 and round(0.9 * 5) == 4,
       "the declared tie rule differs from the built-in round() at a tie")

    # UNSEARCHED is not a rate of zero
    u = channel("x", 0, 0, reader="r", counts="UNSEARCHED")
    ck(detection_rate(u)["kind"] == "UNSEARCHED", "an unsearched channel has no rate")
    ck(compare(a, u)["kind"] == "UNSEARCHED",
       "a comparison against an unsearched channel is an absence")
    ck("not a rate of zero" in compare(a, u)["reason"],
       "the absence says what it is not")

    # a zero-attempt channel declared MEASURED is a refusal, not a zero rate
    z = compare(a, channel("m", 0, 0, reader="r"))
    ck(z["kind"] == "NOT_EVALUABLE", "a zero denominator refuses")

    # readers must be held fixed
    mixed = compare(a, channel("m", 100, 32, reader="other"))
    ck(mixed["kind"] == "NOT_EVALUABLE", "differing readers refuse")
    ck("not a property of the channel" in mixed["reason"],
       "the refusal names why")

    # the counts vocabulary is closed
    try:
        channel("x", 1, 1, counts="ESTIMATED")
        ck(False, "channel() accepted an undeclared counts value")
    except ValueError:
        ck(True, "channel() refuses an undeclared counts value")

    # the fixture is marked reconstructed on both channels
    fa, fb = fixture_channels(50)
    ck(fa["counts"] == "RECONSTRUCTED_FROM_PERCENT"
       and fb["counts"] == "RECONSTRUCTED_FROM_PERCENT",
       "both fixture channels are marked reconstructed")
    ck(fa["reader"] == fb["reader"], "the fixture holds the reader fixed")
    ck("SECONDARY" in FIXTURE_PROVENANCE, "the fixture is marked SECONDARY")
    ck("UNREAD" in FIXTURE_PROVENANCE, "the fixture records that the source is unread")
    ck("BOUND" in FIXTURE_PROVENANCE,
       "the fixture records that both published figures are bounds")

    # render never prints the word this tool refuses to return
    text = "\n".join(render(compare(a, b)))
    ck("noise" not in text.lower(), "the render does not return 'noise'")

    print("channel_loss.py: %d checks, 0 failed" % checks)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(run_fixture())
