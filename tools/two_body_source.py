# tools/two_body_source.py
#
# N4 -- which body the signal is on.
#
# QUESTION
#   Two coupled bodies, one sensor site. Is the signal a property of the body
#   AT RISK, or of the body the SENSOR SITS ON?
#
# The sensor is mounted on body A and the question is about body B. A mode of
# the mounting body reads as a finding about the coupled system unless
# something separates them, and the separator is the pair
# (amplitude ratio, ONSET TIMING) -- neither alone.
#
# ONSET, NOT PHASE. The first build separated the bodies on a phase lead from
# a cross-correlation of the raw traces. NC_013 showed that a periodic
# cross-correlation fixes the lead only MODULO THE FORCING PERIOD: a lead of
# one full period and a lead of zero produce the same peak. The worked
# instance predicts a lead of about one period -- exactly the value a phase
# reading cannot resolve. On the operator's instruction (2026-09-24) the
# decision path now reads onset timing instead:
#
#   per body   first exceedance of a fraction of that body's OWN amplitude
#              envelope (moving RMS)
#   between    the lag at maximum cross-correlation of the two ENVELOPES,
#              searched within one forcing period of the event
#
# An envelope is not periodic at the forcing frequency, so neither reading
# has the modulo ambiguity. `phase_lead()` is kept as a DIAGNOSTIC and is
# read by nothing in `source()`; the harness row NC_013 still exercises it
# because the property it records is a property of the operation.
#
# REFUSALS BUILT IN
#
#   1. TRAILER_CHANNEL_ABSENT is an absence and is never inferred. A body that
#      was not instrumented has not been shown to be quiet.
#   2. Amplitude and onset pointing opposite ways is NOT_EVALUABLE, not a
#      verdict with a caveat.
#   3. Three onset states are kept apart -- MEASURED, NO_EVENT (nothing
#      moved), NO_RISE (already moving at the first sample, so the onset is
#      outside the record). Only the first is a measurement. A steady
#      oscillation is NO_RISE on both bodies, the verdict falls back to
#      amplitude alone, and the return says so.
#   4. A phase lead against a quiet channel is not a measurement (NC_012);
#      the diagnostic returns NOT_EVALUABLE there.
#
# Standard library only. Parses under Python 3.9.

from __future__ import annotations

import math
import sys
from typing import Dict, List, Optional, Sequence

from typed import (load_threshold, mean, not_evaluable, rms,
                   threshold_report, typed)

ONSET_STATES = ("MEASURED", "NO_EVENT", "NO_RISE")


def body(name: str, series: Optional[Sequence[float]], sample_rate_hz: float,
         role: str) -> Dict[str, object]:
    """One instrumented body.

    series=None means NOT INSTRUMENTED, which is not the same as instrumented
    and flat. The constructor keeps them apart because the verdict does.
    """
    if role not in ("SENSOR_SITE", "AT_RISK"):
        raise ValueError("role %r is outside the declared vocabulary" % role)
    return {"name": name,
            "series": None if series is None else list(series),
            "sample_rate_hz": sample_rate_hz, "role": role}


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[float]:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _peak_lag(a: Sequence[float], b: Sequence[float], max_lag: int):
    """Lag in [-max_lag, +max_lag] maximising the Pearson correlation of a
    against b. Returns (lag, r) or (None, None). A positive lag means
    a[t+lag] aligns with b[t], i.e. B moves first."""
    n = min(len(a), len(b))
    best_lag, best_r = None, None
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            xs, ys = a[lag:n], b[:n - lag]
        else:
            xs, ys = a[:n + lag], b[-lag:n]
        m = min(len(xs), len(ys))
        if m < 3:
            continue
        r = _pearson(xs[:m], ys[:m])
        if r is None:
            continue
        if best_r is None or r > best_r:
            best_lag, best_r = lag, r
    return best_lag, best_r


# ---------------------------------------------------------------------------
# onset timing -- the decision path
# ---------------------------------------------------------------------------

def envelope(samples: Sequence[float], window: int) -> List[float]:
    """Moving RMS about the series mean. Centred; edges shortened rather than
    padded, because a padded edge invents the quiet the onset is measured
    against."""
    xs = list(samples)
    n = len(xs)
    if n == 0:
        return []
    if window < 1:
        window = 1
    m = sum(xs) / n
    half = window // 2
    out = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        total = 0.0
        for j in range(lo, hi):
            total += (xs[j] - m) * (xs[j] - m)
        out.append(math.sqrt(total / (hi - lo)))
    return out


def onset(env: Sequence[float], sample_rate_hz: float, frac: float,
          floor: float) -> Dict[str, object]:
    """First exceedance of `frac` of this body's OWN peak envelope.

    Relative to itself on purpose: onset says WHEN a body started, never how
    much it moved. Size is the amplitude ratio's job, and merging the two
    would let a large late body and a small early one report the same.

    Three states, kept apart:
      MEASURED  a rise was found and can be timed
      NO_EVENT  the envelope never clears the floor; nothing to time
      NO_RISE   already moving at the first sample, so the record started
                mid-event and the onset is outside it. Not t = 0.
    """
    env = list(env)
    if not env:
        return {"state": "NO_EVENT", "reason": "empty trace"}
    peak = max(env)
    if peak <= floor:
        return {"state": "NO_EVENT",
                "reason": "peak envelope %.3g is at or below the floor %.3g"
                          % (peak, floor)}
    thr = frac * peak
    # The record has to START QUIET or there is no rise inside it to time. A
    # steady oscillation is the case this catches: its envelope is flat, so
    # the first sample is already near the peak and any index the scan
    # returns is an artifact of the window shortening at the edge rather
    # than an arrival. Half the threshold, so a genuine burst (whose envelope
    # starts at zero) is unaffected.
    if env[0] >= thr:
        return {"state": "NO_RISE",
                "reason": "already above threshold at the first sample; the "
                          "record starts mid-event and the onset is outside it"}
    if env[0] > 0.5 * thr:
        return {"state": "NO_RISE",
                "reason": "the record does not start quiet (first envelope "
                          "sample %.3g against a threshold of %.3g), so the "
                          "rise is not contained in it" % (env[0], thr)}
    idx = None
    for i, v in enumerate(env):
        if v >= thr:
            idx = i
            break
    if idx is None:
        return {"state": "NO_EVENT", "reason": "threshold never reached"}
    return {"state": "MEASURED", "index": idx, "t_s": idx / sample_rate_hz,
            "threshold": thr, "peak": peak}


def envelope_lag(env_a: Sequence[float], env_b: Sequence[float],
                 sample_rate_hz: float, forcing_period_s: float,
                 search_periods: float) -> Dict[str, object]:
    """Lag at maximum cross-correlation of the two ENVELOPES, searched within
    `search_periods` forcing periods.

    Envelopes rather than raw traces, because an envelope is not periodic at
    the forcing frequency -- which is the whole reason this replaces a phase
    lead. Positive lead_s means body A's envelope rose first.
    """
    a, b = list(env_a), list(env_b)
    n = min(len(a), len(b))
    if n < 4:
        return {"state": "NOT_EVALUABLE", "reason": "trace too short"}
    max_lag = int(round(search_periods * forcing_period_s * sample_rate_hz))
    if max_lag < 1:
        return {"state": "NOT_EVALUABLE",
                "reason": "the search window is under one sample"}
    if max_lag >= n:
        max_lag = n - 2
    if max_lag < 1:
        return {"state": "NOT_EVALUABLE",
                "reason": "the record is shorter than the search window"}
    if rms(a) == 0 or rms(b) == 0:
        return {"state": "NOT_EVALUABLE",
                "reason": "an envelope is flat; there is nothing to align"}
    lag, r = _peak_lag(a[:n], b[:n], max_lag)
    if r is None:
        return {"state": "NOT_EVALUABLE",
                "reason": "no lag produced a computable correlation"}
    return {"state": "MEASURED", "lead_samples": -lag,
            "lead_s": -lag / sample_rate_hz, "peak_correlation": r,
            "search_samples": max_lag}


# ---------------------------------------------------------------------------
# phase lead -- DIAGNOSTIC ONLY. Read by nothing in source().
# ---------------------------------------------------------------------------

def phase_lead(a: Sequence[float], b: Sequence[float], sample_rate_hz: float,
               forcing_period_s: float,
               variance_floor: Optional[float] = None) -> Dict[str, object]:
    """Lead of A over B from a cross-correlation of the RAW traces, reported in
    the principal branch (-P/2, +P/2].

    Kept as a diagnostic so NC_013's property -- a periodic correlation fixes
    the lead only modulo the forcing period -- stays demonstrable. It decides
    nothing. Positive means A moves first.
    """
    if variance_floor is None:
        variance_floor = float(load_threshold("n4.phase_variance_floor")["value"])
    ra, rb = rms(a), rms(b)
    if ra is None or rb is None:
        return not_evaluable("a channel is empty")
    if ra <= variance_floor or rb <= variance_floor:
        quiet = "A" if ra <= variance_floor else "B"
        return not_evaluable(
            "channel %s has rms %.3g at or below the variance floor %.3g; a "
            "phase lead against a channel that does not move is a property of "
            "its residual variation, not of the coupling"
            % (quiet, ra if quiet == "A" else rb, variance_floor),
            rms_a=ra, rms_b=rb)

    period_samples = forcing_period_s * sample_rate_hz
    if period_samples < 2:
        return not_evaluable(
            "the forcing period is %.4g s at %.4g Hz, under two samples; the "
            "sampling cannot resolve the feature"
            % (forcing_period_s, sample_rate_hz))
    max_lag = int(round(period_samples))
    if max_lag >= len(a):
        return not_evaluable(
            "one forcing period is %d samples against a record of %d; the "
            "record is shorter than the feature" % (max_lag, len(a)))

    best_lag, best_r = _peak_lag(list(a), list(b), max_lag)
    if best_r is None:
        return not_evaluable("no lag produced a computable correlation")

    # A positive lag means A[t+lag] aligns with B[t], i.e. B moves first.
    raw_lead = -best_lag

    # Wrap into the principal branch (-P/2, +P/2]. Found while building the
    # first F1b: a LAG of 4 samples in a 40-sample period came back as a LEAD
    # of 36, the same peak read on the other branch. Without the wrap the
    # branch is chosen by where the search happened to land.
    P = period_samples
    wrapped = raw_lead
    while wrapped > P / 2.0:
        wrapped -= P
    while wrapped <= -P / 2.0:
        wrapped += P

    # Near half a period the two branches are equally close and the sign is
    # not determined at all. It is withheld rather than reported.
    sign_determined = abs(abs(wrapped) - P / 2.0) > max(1.0, 0.05 * P)

    return typed("VALUE", quantity="phase_lead_s",
                 lead_s=wrapped / sample_rate_hz,
                 lead_samples=wrapped,
                 raw_lead_samples=raw_lead,
                 sign_determined=sign_determined,
                 peak_correlation=best_r,
                 forcing_period_s=forcing_period_s,
                 role="DIAGNOSTIC -- read by no verdict",
                 ambiguity="reported in the principal branch (-P/2, +P/2] with "
                           "P = %.4g s; any integer number of forcing periods "
                           "may be added, and a periodic correlation cannot "
                           "tell them apart" % forcing_period_s,
                 sign_note="" if sign_determined else
                           "the lead sits near half a period, where the two "
                           "branches are equally close; the SIGN is not "
                           "determined and is not read",
                 rms_a=ra, rms_b=rb)


# ---------------------------------------------------------------------------
# the verdict
# ---------------------------------------------------------------------------

def source(a: Dict[str, object], b: Dict[str, object], forcing_period_s: float,
           ratio_hi: Optional[float] = None, ratio_lo: Optional[float] = None,
           clock_tolerance_frac: Optional[float] = None) -> Dict[str, object]:
    """Which body the signal is on.

    Returns SOURCE_A_MODE, SOURCE_B, TRAILER_CHANNEL_ABSENT or NOT_EVALUABLE.
    The amplitude ratio decides; onset timing is read beside it and, where
    both onsets are measurable, is reported as agreeing or not. An onset
    reading that disagrees with the amplitude verdict does not override it --
    it downgrades the return to NOT_EVALUABLE, because two readings pointing
    opposite ways is not a verdict with a caveat. No phase is read here.
    """
    if ratio_hi is None:
        ratio_hi = float(load_threshold("n4.amplitude_ratio_hi")["value"])
    if ratio_lo is None:
        ratio_lo = float(load_threshold("n4.amplitude_ratio_lo")["value"])
    if clock_tolerance_frac is None:
        clock_tolerance_frac = float(load_threshold("n4.clock_tolerance_frac")["value"])
    window_frac = float(load_threshold("n4.envelope_window_frac")["value"])
    onset_frac = float(load_threshold("n4.onset_frac")["value"])
    search_periods = float(load_threshold("n4.onset_search_periods")["value"])
    floor = float(load_threshold("n4.phase_variance_floor")["value"])

    if a["role"] != "SENSOR_SITE" or b["role"] != "AT_RISK":
        return not_evaluable("body A must be the SENSOR_SITE and body B the "
                             "AT_RISK body; the question is not symmetric")
    if b["series"] is None:
        return typed("TRAILER_CHANNEL_ABSENT", body=b["name"],
                     reason="the at-risk body carries no channel. It has not "
                            "been shown to be quiet, and no verdict about "
                            "where the signal sits is available from one body.",
                     rms_a=rms(a["series"]) if a["series"] else None)
    if a["series"] is None:
        return not_evaluable("the sensor-site body carries no channel")
    if not a["series"] or not b["series"]:
        return not_evaluable("a channel is empty")

    ra_hz, rb_hz = a["sample_rate_hz"], b["sample_rate_hz"]
    if ra_hz <= 0 or rb_hz <= 0:
        return not_evaluable("a declared sample rate is not positive")
    mismatch = abs(ra_hz - rb_hz) / max(ra_hz, rb_hz)
    if mismatch > clock_tolerance_frac:
        return not_evaluable(
            "declared sample rates differ by %.2f%% (%g Hz vs %g Hz), above "
            "the %.2f%% tolerance; the two records are not on one clock and a "
            "lag between them is not a lag in the system"
            % (100 * mismatch, ra_hz, rb_hz, 100 * clock_tolerance_frac),
            clock_mismatch_frac=mismatch)
    if len(a["series"]) != len(b["series"]):
        return not_evaluable(
            "records differ in length (%d vs %d); they do not cover one "
            "interval" % (len(a["series"]), len(b["series"])))
    if forcing_period_s <= 0:
        return not_evaluable("the forcing period must be positive")

    ra, rb = rms(a["series"]), rms(b["series"])
    if rb == 0 and ra == 0:
        return not_evaluable("neither body moved; there is no signal to source")
    ratio = float("inf") if rb == 0 else ra / rb

    win = int(round(window_frac * forcing_period_s * ra_hz))
    if win < 1:
        win = 1
    env_a = envelope(a["series"], win)
    env_b = envelope(b["series"], win)
    onset_a = onset(env_a, ra_hz, onset_frac, floor)
    onset_b = onset(env_b, ra_hz, onset_frac, floor)
    lag = envelope_lag(env_a, env_b, ra_hz, forcing_period_s, search_periods)

    # onset lead: positive means body A rose first
    if onset_a["state"] == "MEASURED" and onset_b["state"] == "MEASURED":
        onset_lead_s: Optional[float] = onset_b["t_s"] - onset_a["t_s"]
        onset_basis = "both bodies timed"
    elif onset_a["state"] == "MEASURED" and onset_b["state"] == "NO_EVENT":
        onset_lead_s = None
        onset_basis = ("A has an onset and B has none; A is first by default "
                       "and the lead has no value")
    elif onset_b["state"] == "MEASURED" and onset_a["state"] == "NO_EVENT":
        onset_lead_s = None
        onset_basis = "B has an onset and A has none"
    else:
        onset_lead_s = None
        onset_basis = "A %s, B %s" % (onset_a["state"], onset_b["state"])

    common = dict(amplitude_ratio=ratio, rms_a=ra, rms_b=rb,
                  onset_a=onset_a, onset_b=onset_b, onset_lead_s=onset_lead_s,
                  onset_basis=onset_basis, envelope_lag=lag,
                  envelope_window_samples=win,
                  forcing_period_s=forcing_period_s)

    if ratio >= ratio_hi:
        verdict, why = "SOURCE_A_MODE", (
            "amplitude at the sensor site is %.3gx the at-risk body, at or "
            "above the declared ratio %g" % (ratio, ratio_hi))
    elif ratio <= ratio_lo:
        verdict, why = "SOURCE_B", (
            "amplitude at the sensor site is %.3gx the at-risk body, at or "
            "below the declared ratio %g" % (ratio, ratio_lo))
    else:
        return not_evaluable(
            "amplitude ratio %.3g sits between the declared bounds %g and %g; "
            "the two bodies move comparably and this record does not separate "
            "them" % (ratio, ratio_lo, ratio_hi), **common)

    # onset agreement. Undetermined is not agreement and is not disagreement.
    onset_agrees: Optional[bool] = None
    if onset_lead_s is not None and abs(onset_lead_s) > 1e-12:
        onset_agrees = onset_lead_s > 0 if verdict == "SOURCE_A_MODE" else onset_lead_s < 0
    elif (verdict == "SOURCE_A_MODE" and onset_a["state"] == "MEASURED"
          and onset_b["state"] == "NO_EVENT"):
        onset_agrees = True
    elif (verdict == "SOURCE_B" and onset_b["state"] == "MEASURED"
          and onset_a["state"] == "NO_EVENT"):
        onset_agrees = True

    if onset_agrees is False:
        return not_evaluable(
            "amplitude reads %s while onset has the other body moving first "
            "(lead %+.4g s); two readings pointing opposite ways is not a "
            "verdict" % (verdict, onset_lead_s), onset_agrees=False, **common)

    if onset_agrees is None:
        decided_by = "amplitude_ratio alone"
        onset_note = ("onset not measurable on this record (%s); the verdict "
                      "rests on amplitude alone" % onset_basis)
    else:
        decided_by = "amplitude_ratio, checked against onset timing"
        onset_note = "onset reported beside the verdict, not summed with it"

    return typed(verdict, reason=why, decided_by=decided_by,
                 onset_agrees=onset_agrees, onset_note=onset_note, **common)


# ---------------------------------------------------------------------------
# fixtures -- CONSTRUCTED
# ---------------------------------------------------------------------------

def _sine(n: int, period_samples: float, amp: float, phase_samples: float = 0.0,
          offset: float = 0.0) -> List[float]:
    return [offset + amp * math.sin(2 * math.pi * (i - phase_samples) / period_samples)
            for i in range(n)]


def burst(n: int, period_samples: float, amp: float, onset_idx: int,
          rise_samples: int, carrier_phase_samples: float = 0.0) -> List[float]:
    """A carrier at the forcing period under a ramp-and-hold envelope: zero
    before onset_idx, ramping to amp over rise_samples, held after. The
    carrier is what an accelerometer sees on a serpentine; the envelope is
    what the classifier reads.

    The carrier is referenced to the ONSET, not to t=0: a body that starts
    later starts its carrier later too, which is what a delayed response to
    one forcing looks like. Two consequences, both used by the fixtures: the
    carrier phase at onset is the same on every body, so the envelope shape
    is the same and an onset lead is recovered exactly; and a sub-period
    lead moves the carrier by the same amount, so the phase diagnostic and
    the onset reading can be compared on one trace pair.
    """
    out = []
    for i in range(n):
        if i < onset_idx:
            level = 0.0
        else:
            k = min(1.0, (i - onset_idx) / float(rise_samples))
            level = amp * k
        out.append(level * math.sin(2.0 * math.pi
                                    * (i - onset_idx - carrier_phase_samples)
                                    / period_samples))
    return out


RATE_HZ = 100.0
PERIOD_SAMPLES = 40.0
N = 400
RISE = 20

FIXTURE_NOTE = """\
CONSTRUCTED. No cab, no trailer, no descent and no accelerometer. The series
below are generated bursts -- a carrier at the forcing period under a
ramp-and-hold envelope -- and every verdict is a statement about the
instrument rather than about any vehicle.

WORKED INSTANCE the fixtures are shaped after, NOT RUN
  A tractor cab and its trailer on a serpentine descent: the sensor sits in
  the cab, the body at risk is the trailer, and a cab suspension mode reads
  as a trailer finding unless the two are separated.
  Cross-link: JinnZ2/Simulators, stability-trigger-envelope/ (ESP-1)
  Status: LANDED 2026-09-27 on branch claude/noise-information-four-tools-5u0l4k
  of that repository, commit 038a30f. Its descent_record.classify() reads
  onset instead of phase for the same reason this file does; the two were
  changed under one instruction and neither imports the other. First checked
  2026-09-24 as PENDING (213 folders, none of them it); the pointer was not
  reconstructed in the interval and the packet's content is unread here.
"""


def fixture_f1():
    """A bursts, B quiet. Onset: A MEASURED, B NO_EVENT -> A first by default.
    The phase diagnostic against a quiet B is NOT_EVALUABLE (NC_012)."""
    a = burst(N, PERIOD_SAMPLES, 1.0, 100, RISE)
    b = [0.0] * N
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_f1b():
    """A dominant, B moving a little, A first by 8 samples -- inside one
    period, where phase and onset both read the lead."""
    a = burst(N, PERIOD_SAMPLES, 1.0, 100, RISE)
    b = burst(N, PERIOD_SAMPLES, 0.1, 108, RISE)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_f2():
    """B dominant and first by 8 samples -> SOURCE_B."""
    b = burst(N, PERIOD_SAMPLES, 1.0, 100, RISE)
    a = burst(N, PERIOD_SAMPLES, 0.1, 108, RISE)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_f3():
    """B missing. An absence, never inferred."""
    a = burst(N, PERIOD_SAMPLES, 1.0, 100, RISE)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", None, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_f4(carrier_phase_samples: float = 0.0):
    """A dominant and first by EXACTLY ONE FORCING PERIOD -- the worked
    instance's own prediction. Onset reads a lead of one period; the phase
    diagnostic on the same traces reads a lead of zero, because one period
    and zero are the same peak to a periodic correlation."""
    a = burst(N, PERIOD_SAMPLES, 1.0, 100, RISE, carrier_phase_samples)
    b = burst(N, PERIOD_SAMPLES, 0.15, 100 + int(PERIOD_SAMPLES), RISE,
              carrier_phase_samples)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_disagree():
    """A dominant in amplitude, B first by one period -> the two readings
    point opposite ways -> NOT_EVALUABLE."""
    a = burst(N, PERIOD_SAMPLES, 1.0, 100 + int(PERIOD_SAMPLES), RISE)
    b = burst(N, PERIOD_SAMPLES, 0.1, 100, RISE)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


def fixture_steady():
    """Both bodies already oscillating at the first sample: NO_RISE on both,
    the verdict rests on amplitude alone and says so."""
    a = _sine(N, PERIOD_SAMPLES, 1.0)
    b = _sine(N, PERIOD_SAMPLES, 0.1, phase_samples=4.0)
    return (body("cab", a, RATE_HZ, "SENSOR_SITE"),
            body("trailer", b, RATE_HZ, "AT_RISK"), PERIOD_SAMPLES / RATE_HZ)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------

def _onset_line(label: str, o: Dict[str, object]) -> str:
    if o["state"] == "MEASURED":
        return "    onset %s: MEASURED at %.3f s (sample %d)" % (label, o["t_s"], o["index"])
    return "    onset %s: %s -- %s" % (label, o["state"], o["reason"])


def render(result: Dict[str, object]) -> List[str]:
    k = result["kind"]
    if k == "TRAILER_CHANNEL_ABSENT":
        return ["  VERDICT: TRAILER_CHANNEL_ABSENT (%s)" % result["body"],
                "    %s" % result["reason"]]
    out = ["  VERDICT: %s" % k, "    %s" % result["reason"]]
    if result.get("amplitude_ratio") is not None:
        out.append("    amplitude ratio A/B: %.4g   (rms A %.4g, rms B %.4g)"
                   % (result["amplitude_ratio"], result["rms_a"], result["rms_b"]))
    if "onset_a" in result:
        out.append(_onset_line("A", result["onset_a"]))
        out.append(_onset_line("B", result["onset_b"]))
        if result["onset_lead_s"] is not None:
            out.append("    onset lead of A over B: %+.3f s   (%s)"
                       % (result["onset_lead_s"], result["onset_basis"]))
        else:
            out.append("    onset lead: none -- %s" % result["onset_basis"])
        lag = result["envelope_lag"]
        if lag["state"] == "MEASURED":
            out.append("    envelope lag of A over B: %+.3f s, peak r %.3f, "
                       "searched +/-%d samples"
                       % (lag["lead_s"], lag["peak_correlation"], lag["search_samples"]))
        else:
            out.append("    envelope lag: %s -- %s" % (lag["state"], lag["reason"]))
    if k == "NOT_EVALUABLE":
        return out
    out.append("    onset agrees with amplitude: %s" % result["onset_agrees"])
    out.append("    decided by: %s" % result["decided_by"])
    out.append("    %s" % result["onset_note"])
    return out


def run_fixture() -> int:
    print("N4 two_body_source.py -- which body the signal is on")
    print("=" * 72)
    print()
    print(FIXTURE_NOTE)
    print("F1 -- A bursts, B quiet")
    a, b, per = fixture_f1()
    for line in render(source(a, b, per)):
        print(line)
    print("    B has no onset because nothing on B moved. That is NO_EVENT,")
    print("    kept apart from an absent channel (F3) and from a body that")
    print("    was already moving when the record began (steady, below).")
    print()
    print("F1b -- A dominant, B moving a little, A first by 8 samples")
    a, b, per = fixture_f1b()
    for line in render(source(a, b, per)):
        print(line)
    print()
    print("F2 -- B dominant and first")
    a, b, per = fixture_f2()
    for line in render(source(a, b, per)):
        print(line)
    print()
    print("F3 -- B missing")
    a, b, per = fixture_f3()
    for line in render(source(a, b, per)):
        print(line)
    print()
    print("F4 -- A first by EXACTLY ONE FORCING PERIOD (the worked instance's")
    print("own prediction). Onset classifies; the phase diagnostic cannot.")
    a, b, per = fixture_f4()
    for line in render(source(a, b, per)):
        print(line)
    ph = phase_lead(a["series"], b["series"], RATE_HZ, per)
    if ph["kind"] == "VALUE":
        print("    phase DIAGNOSTIC on the same traces: lead %+.3f s in the "
              "principal branch" % ph["lead_s"])
        print("    -- a lead of one period and a lead of zero are one peak to a")
        print("       periodic correlation, so phase reads the cab as not")
        print("       leading. Onset reads the period. Neither is summed.")
    else:
        print("    phase DIAGNOSTIC: %s -- %s" % (ph["kind"], ph["reason"]))
    print()
    print("CONTRAST -- amplitude says A, onset says B first: NOT_EVALUABLE")
    a, b, per = fixture_disagree()
    for line in render(source(a, b, per)):
        print(line)
    print()
    print("CONTRAST -- both bodies already oscillating at the first sample")
    a, b, per = fixture_steady()
    for line in render(source(a, b, per)):
        print(line)
    print()
    print("CONTRAST -- clocks misaligned beyond the declared tolerance")
    a, b, per = fixture_f1b()
    b2 = body("trailer", b["series"], 97.0, "AT_RISK")
    for line in render(source(a, b2, per)):
        print(line)
    print()
    print("CONTRAST -- the two bodies move comparably; the record does not")
    print("separate them, and that is a result rather than a default verdict.")
    mid_a = body("cab", burst(N, PERIOD_SAMPLES, 1.0, 100, RISE), RATE_HZ, "SENSOR_SITE")
    mid_b = body("trailer", burst(N, PERIOD_SAMPLES, 0.9, 100, RISE), RATE_HZ, "AT_RISK")
    for line in render(source(mid_a, mid_b, PERIOD_SAMPLES / RATE_HZ)):
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

    P = PERIOD_SAMPLES

    # F1: A dominant, B quiet
    a, b, per = fixture_f1()
    r1 = source(a, b, per)
    ck(r1["kind"] == "SOURCE_A_MODE", "F1 returns SOURCE_A_MODE")
    ck(r1["onset_a"]["state"] == "MEASURED", "F1 times A's onset")
    ck(r1["onset_b"]["state"] == "NO_EVENT", "F1 reads B as NO_EVENT, not NO_RISE")
    ck(r1["onset_lead_s"] is None, "F1 onset lead has no value against a body with no onset")
    ck(r1["onset_agrees"] is True, "F1: A first by default agrees with amplitude")
    ck("phase" not in r1, "F1's return carries no phase field")
    ph1 = phase_lead(a["series"], b["series"], RATE_HZ, per)
    ck(ph1["kind"] == "NOT_EVALUABLE" and "does not move" in ph1["reason"],
       "the phase diagnostic still refuses a quiet channel (NC_012)")

    # F1b: both timed, A first by 8, verdict and onset agree
    a, b, per = fixture_f1b()
    r1b = source(a, b, per)
    ck(r1b["kind"] == "SOURCE_A_MODE", "F1b returns SOURCE_A_MODE")
    ck(r1b["onset_a"]["state"] == "MEASURED" and r1b["onset_b"]["state"] == "MEASURED",
       "F1b times both onsets")
    ck(r1b["onset_lead_s"] > 0, "F1b reads A as rising first")
    ck(abs(r1b["onset_lead_s"] * RATE_HZ - 8) <= 2,
       "F1b recovers the constructed 8-sample onset lead to within two samples")
    ck(r1b["onset_agrees"] is True, "F1b onset agrees with amplitude")
    ck(r1b["decided_by"] == "amplitude_ratio, checked against onset timing",
       "F1b names both readings in decided_by")
    ph1b = phase_lead(a["series"], b["series"], RATE_HZ, per)
    ck(ph1b["kind"] == "VALUE" and ph1b["lead_samples"] > 0,
       "inside one period the phase diagnostic agrees with onset on the sign")

    # F2: B dominant and first
    a, b, per = fixture_f2()
    r2 = source(a, b, per)
    ck(r2["kind"] == "SOURCE_B", "F2 returns SOURCE_B")
    ck(r2["amplitude_ratio"] < 0.34, "F2 amplitude ratio is below the low bound")
    ck(r2["onset_lead_s"] < 0, "F2 reads B as rising first")
    ck(r2["onset_agrees"] is True, "F2 onset agrees with amplitude")

    # F3: absence, never inferred
    a, b, per = fixture_f3()
    r3 = source(a, b, per)
    ck(r3["kind"] == "TRAILER_CHANNEL_ABSENT", "F3 returns the absence")
    ck("has not been shown to be quiet" in r3["reason"],
       "the absence refuses the inference it would most invite")
    ck("amplitude_ratio" not in r3, "no ratio is computed against a missing body")
    flat = body("trailer", [0.0] * N, RATE_HZ, "AT_RISK")
    rflat = source(a, flat, per)
    ck(rflat["kind"] == "SOURCE_A_MODE",
       "an instrumented flat body gives a verdict where an absent one does not")
    ck(rflat["kind"] != r3["kind"], "absent and flat do not collapse")

    # F4: A first by exactly one forcing period. Onset classifies; phase is blind.
    a, b, per = fixture_f4()
    r4 = source(a, b, per)
    ck(r4["kind"] == "SOURCE_A_MODE", "F4 returns SOURCE_A_MODE")
    ck(r4["onset_agrees"] is True, "F4: onset agrees with amplitude")
    ck(abs(r4["onset_lead_s"] * RATE_HZ - P) <= 2,
       "F4 onset lead is one forcing period to within two samples")
    lag4 = r4["envelope_lag"]
    ck(lag4["state"] == "MEASURED" and lag4["lead_samples"] > 0,
       "F4 envelope lag has A first")
    ph4 = phase_lead(a["series"], b["series"], RATE_HZ, per)
    ck(ph4["kind"] == "VALUE", "F4's phase diagnostic computes")
    ck(abs(ph4["lead_samples"]) <= 2,
       "F4's phase diagnostic reads a lead of one period as a lead of zero")
    ck(abs(r4["onset_lead_s"] * RATE_HZ - ph4["lead_samples"]) > P / 2,
       "on F4 onset and phase disagree by more than half a period: phase alone fails")

    # carrier inversion: verdict, agreement and onset lead are invariant to
    # the carrier phase; the raw-trace phase reading moves. If a phase reading
    # were still in the decision path the first three assertions fail.
    a2, b2, _ = fixture_f4(carrier_phase_samples=P / 2.0)
    r4i = source(a2, b2, per)
    ck(r4i["kind"] == r4["kind"], "F4 verdict is invariant to carrier phase")
    ck(r4i["onset_agrees"] == r4["onset_agrees"], "F4 agreement is invariant to carrier phase")
    ck(abs(r4i["onset_lead_s"] - r4["onset_lead_s"]) < 1e-9,
       "F4 onset lead is invariant to carrier phase")
    ph_i = phase_lead(a2["series"], b["series"], RATE_HZ, per)
    ck(ph_i["kind"] == "VALUE" and abs(ph_i["lead_samples"] - ph4["lead_samples"]) > 2,
       "the raw-trace phase reading moves with the carrier when only one body is shifted")

    # the period ambiguity on pure sines (NC_013), demonstrated not asserted
    zero = _sine(N, P, 1.0, phase_samples=0.0)
    onep = _sine(N, P, 1.0, phase_samples=P)
    ref = _sine(N, P, 1.0)
    pz = phase_lead(zero, ref, RATE_HZ, per)
    po = phase_lead(onep, ref, RATE_HZ, per)
    ck(pz["kind"] == "VALUE" and po["kind"] == "VALUE", "both leads compute")
    ck(abs(pz["lead_s"] - po["lead_s"]) < 1e-9,
       "a lead of one full period is indistinguishable from zero lead")
    lagd = phase_lead(_sine(N, P, 1.0, phase_samples=4.0), ref, RATE_HZ, per)
    ck(lagd["raw_lead_samples"] == 36, "the unwrapped search returns the far branch (36 of 40)")
    ck(lagd["lead_samples"] == -4, "the wrap puts it in the principal branch as a lag of 4")
    ck(lagd["sign_determined"] is True, "a lag of 4 in 40 has a determined sign")
    half = phase_lead(_sine(N, P, 1.0, phase_samples=P / 2.0), ref, RATE_HZ, per)
    ck(half["sign_determined"] is False, "a lead near half a period has no determined sign")
    ck("not determined" in half["sign_note"], "the withheld sign says why")
    ck("DIAGNOSTIC" in pz["role"], "the phase return declares itself diagnostic")

    # steady oscillation: NO_RISE on both, amplitude alone, stated
    a, b, per = fixture_steady()
    rs = source(a, b, per)
    ck(rs["kind"] == "SOURCE_A_MODE", "a steady record still gets an amplitude verdict")
    ck(rs["onset_a"]["state"] == "NO_RISE" and rs["onset_b"]["state"] == "NO_RISE",
       "a steady oscillation is NO_RISE on both bodies, not an onset at t=0")
    ck(rs["onset_agrees"] is None, "NO_RISE is neither agreement nor disagreement")
    ck(rs["decided_by"] == "amplitude_ratio alone", "steady record is decided on amplitude alone")
    ck("amplitude alone" in rs["onset_note"], "the steady record says what carried the verdict")

    # the three onset states are distinct and all reached above
    ck({r1["onset_b"]["state"], rs["onset_a"]["state"], r4["onset_a"]["state"]}
       == set(ONSET_STATES), "all three onset states are reached")

    # disagreement between the two readings is a refusal, not a caveat
    a, b, per = fixture_disagree()
    dis = source(a, b, per)
    ck(dis["kind"] == "NOT_EVALUABLE", "amplitude and onset pointing opposite ways is not a verdict")
    ck("opposite ways" in dis["reason"], "the disagreement is named")
    ck(dis["onset_agrees"] is False, "the disagreement is carried as False, not None")

    # clocks
    a, b, per = fixture_f1b()
    skew = source(a, body("trailer", b["series"], 97.0, "AT_RISK"), per)
    ck(skew["kind"] == "NOT_EVALUABLE", "misaligned clocks refuse")
    ck("not on one clock" in skew["reason"], "the clock refusal says why")
    near = source(a, body("trailer", b["series"], 100.5, "AT_RISK"), per)
    ck(near["kind"] == "SOURCE_A_MODE", "a mismatch inside tolerance is accepted")

    # unequal lengths do not cover one interval
    short = source(a, body("trailer", b["series"][:100], RATE_HZ, "AT_RISK"), per)
    ck(short["kind"] == "NOT_EVALUABLE", "unequal record lengths refuse")

    # the middle band is a result, not a default
    mid = source(body("cab", burst(N, P, 1.0, 100, RISE), RATE_HZ, "SENSOR_SITE"),
                 body("trailer", burst(N, P, 0.9, 100, RISE), RATE_HZ, "AT_RISK"), per)
    ck(mid["kind"] == "NOT_EVALUABLE", "comparable amplitudes refuse")
    ck("does not separate them" in mid["reason"], "the refusal names what is missing")
    ck("onset_a" in mid, "the middle-band refusal still reports the onsets it read")

    # onset primitives on their own
    ck(onset([], RATE_HZ, 0.5, 1e-6)["state"] == "NO_EVENT", "empty envelope is NO_EVENT")
    ck(onset([0.0] * 50, RATE_HZ, 0.5, 1e-6)["state"] == "NO_EVENT", "flat envelope is NO_EVENT")
    ck(onset([1.0] * 50, RATE_HZ, 0.5, 1e-6)["state"] == "NO_RISE", "already-high envelope is NO_RISE")
    ramp = onset([0.0] * 10 + [0.5, 1.0, 1.0, 1.0], RATE_HZ, 0.5, 1e-6)
    ck(ramp["state"] == "MEASURED" and ramp["index"] == 10, "first exceedance is timed at the crossing")
    ck(envelope([], 5) == [], "empty series gives an empty envelope")
    ck(len(envelope([1.0, -1.0] * 20, 4)) == 40, "envelope preserves length")
    ck(envelope_lag([0.0] * 50, [0.0] * 50, RATE_HZ, per, 1.0)["state"] == "NOT_EVALUABLE",
       "flat envelopes have nothing to align")

    # sampling that cannot resolve the feature (phase diagnostic)
    ck(phase_lead(_sine(N, P, 1.0), _sine(N, P, 1.0), 1.0, 0.5)["kind"]
       == "NOT_EVALUABLE", "a sub-two-sample period refuses")
    ck(phase_lead(_sine(20, P, 1.0), _sine(20, P, 1.0), RATE_HZ, 1.0)["kind"]
       == "NOT_EVALUABLE", "a record shorter than the feature refuses")

    # roles are not symmetric
    swapped = source(body("trailer", b["series"], RATE_HZ, "AT_RISK"),
                     body("cab", a["series"], RATE_HZ, "SENSOR_SITE"), per)
    ck(swapped["kind"] == "NOT_EVALUABLE", "swapped roles refuse")
    try:
        body("x", [1.0], 1.0, "EITHER")
        ck(False, "an undeclared role was accepted")
    except ValueError:
        ck(True, "an undeclared role is refused")

    # no phase reading reaches the decision path: source() carries no phase
    # field on any return, and its body does not call phase_lead.
    import inspect
    src = inspect.getsource(source)
    ck("phase_lead(" not in src, "source() does not call phase_lead")
    for r in (r1, r1b, r2, r4, rs, dis, mid):
        ck("phase" not in r, "no return from source() carries a phase field")

    # the cross-link is recorded as landed, with where and when
    ck("LANDED" in FIXTURE_NOTE and "038a30f" in FIXTURE_NOTE,
       "the ESP-1 cross-link is marked landed with the commit named")
    ck("JinnZ2/Simulators" in FIXTURE_NOTE, "the cross-link names the repository")
    ck("PENDING" in FIXTURE_NOTE, "the cross-link keeps the record of having been pending")
    ck("CONSTRUCTED" in FIXTURE_NOTE, "the fixtures are marked constructed")

    for r in (r1, r1b, r2, r3, r4, rs, dis, mid):
        text = "\n".join(render(r))
        ck("noise" not in text.lower(), "the render does not return the refused word")

    print("two_body_source.py: %d checks, 0 failed" % checks)
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(_selftest())
    raise SystemExit(run_fixture())
