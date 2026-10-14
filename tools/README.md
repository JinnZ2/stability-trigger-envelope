> Before reading or editing anything here, read [READ_ME_THIS_WAY.md](../READ_ME_THIS_WAY.md).

# tools/

Four instruments, added as a set under DISPATCH NOISE-1. Standard library only,
no numpy, parses under Python 3.9, phone-buildable. CC0 as a dispatch
condition; the repository's own LICENSE is MIT and these files carry the more
permissive of the two, stated here rather than assumed.

They do not read, call, modify or endorse anything in `software/`,
`dashboard/` or `symbolic/`. Claims about them live in `tools/CLAIM_TABLE.md`
under `NC_*` ids, kept apart from the repository's own `C1..C12` in
`docs/FALSIFICATION_LOG.md`.

Five of those ids -- NC_002, NC_006, NC_009, NC_013, NC_022 -- are also rows
in `experiments/check_claims.py`, added under the repository's contributing
rule. They import from `tools/` only, so an NC row cannot move because a C row
moved. The harness tallies the C series and the NC series on separate lines
with both denominators stated (`NC_025`).

**STATE 2026-09-27: the N4 onset rewrite is WRITTEN, NOT RUN** (`NC_024`).
Command execution was refused for the rest of the session that wrote it. The
first `python3 tools/test_tools.py` and `python3 experiments/check_claims.py`
are the acceptance test.

```
python3 tools/test_tools.py          # every selftest, check total printed
python3 experiments/check_claims.py  # the repository harness, NC rows included
python3 tools/channel_loss.py        # N1 on its fixtures
python3 tools/rerun_find_rate.py     # N2
python3 tools/residual_partition.py  # N3
python3 tools/two_body_source.py     # N4
python3 tools/typed.py               # the thresholds in force
```

---

## The shared rule

**"Noise" is never a return value.**

What is left after the declared sources are removed comes back as a typed
residual carrying its provenance, or as a typed absence carrying its reason:

```
UNPARTITIONED(sources_declared=[...])   a residual, and what it is a residual against
CHANNEL_LOSS(channel=...)               detection lost between the data and the reader
SINGLE_FIND(k_runs=...)                 one positive over k runs; bounds, not a rate
NOT_EVALUABLE(reason=...)               the input cannot answer the question asked
UNSEARCHED                              not looked for. NOT a measured zero.
ABSENT_MEASURED                         looked for, not there. NOT the same as UNSEARCHED.
```

The vocabulary is closed. `typed()` refuses a kind outside it, which is how the
three N4 verdicts came to be added deliberately and recorded rather than
appearing by drift.

Every threshold lives in `thresholds.txt` with a status (`PLACEHOLDER` or
`DECLARED`) and a basis, and every value ever in force has a row in the
append-only `threshold_provenance.txt`. Every tool prints the whole threshold
table on every run: a PLACEHOLDER that never appears in an output is a
stipulation nobody can see they are relying on.

---

## N1 `channel_loss.py` — what the reading channel removed

How much detection is lost to the channel between the data and the reader,
versus the reader itself. Per channel: attempts, detections, and the reader.
Returns an exact Clopper-Pearson interval per channel, the loss, whether the
intervals overlap, and `CHANNEL_LOSS` when the mediated interval sits wholly
below the direct one.

The reader is held fixed across the comparison or the tool refuses — a rate
difference across two readers is not a property of the channel.

**Fixture: SECONDARY, RECONSTRUCTED_FROM_PERCENT.** A press report of the
preprint *"Autonomous AI agents discover reverse transcriptases with tandem
repeat arrays"*: models given the DNA directly described the array in >= 90% of
attempts, and with files and tools as low as 32%, the stated cause being that
the model often did not read enough raw DNA to see a full repeat. The real
counts are UNREAD — the host is not reachable from this session — so the
counts are rebuilt against an assumed denominator, and the denominator sweep
is printed because **the verdict moves across it while the published numbers
do not** (`NC_002`), and at the small end the point estimate moves too
(`NC_003`).

## N2 `rerun_find_rate.py` — one find, many misses

A result appeared in 1 run and not in k reruns; what does that bound? Returns
the per-run find probability with an exact interval, `SINGLE_FIND` when there
is exactly one, and the side-path share of finds. Misses are kept as rows
carrying their run ids, because which runs missed is the quantity a later
reader needs and a bare k/n throws it away.

It does not judge whether the find is real. A rarely-reached real result and a
once-reached artifact produce the same 1/11.

**Fixture: SECONDARY.** The finding reached by a side path in the original
campaign, ten reruns of the same campaign all missing it. The headline is
1 of 11 at [0.0023, 0.4128]; the sharper number is that the **assigned** path
found nothing in eleven runs (`NC_006`).

## N3 `residual_partition.py` — the residual is not error

After the declared sources are removed, what is left, and what could it be?
Returns `UNPARTITIONED` carrying `sources_declared` — a residual of 0.3 against
four declared sources and one against none are different findings — plus, per
candidate undeclared source, `consistent` / `inconsistent` / `not_testable`.

It never scales a candidate and never subtracts one. Candidates carry a sign or
a shape; a magnitude field is refused at the constructor. A consistent
candidate is therefore never an attribution, several can be consistent at once,
and the tool ranks none of them.

Fixtures F1 (matching sign), F2 (opposite sign), F3 (no candidate listed). The
worked example — a survey item whose "yes" mixes two meanings with opposite
risk signs, so the residual in a tenure curve is the candidate rather than the
error — is text only and marked NOT RUN.

## N4 `two_body_source.py` — which body the signal is on

Two coupled bodies, one sensor site. Is the signal a property of the body at
risk, or of the body the sensor sits on? Returns `SOURCE_A_MODE`, `SOURCE_B`,
`TRAILER_CHANNEL_ABSENT` or `NOT_EVALUABLE`, with the amplitude ratio, the
ONSET timing of each body, and whether the two agree.

**Onset, not phase.** The first build separated the bodies on a phase lead
from a cross-correlation of the raw traces. `NC_013` showed that fixes the lead
only modulo the forcing period, and the worked instance predicts a lead of
about one period — the value a phase reading cannot resolve. On the operator's
instruction (2026-09-24) the decision path reads onset timing instead:

```
per body    first exceedance of n4.onset_frac of the body's OWN peak
            amplitude envelope (moving RMS over n4.envelope_window_frac
            of a forcing period)
between     lag at max cross-correlation of the two ENVELOPES, searched
            within n4.onset_search_periods of the event
states      MEASURED / NO_EVENT (nothing moved) / NO_RISE (already moving
            at the first sample; the onset is outside the record)
```

`phase_lead()` is kept as a DIAGNOSTIC. `source()` does not call it and no
return carries a phase field, both asserted in the selftest. Fixtures:

```
F1   A bursts, B quiet          SOURCE_A_MODE; B is NO_EVENT, A first by default
F1b  A first by 8 samples       SOURCE_A_MODE; onset and phase agree inside a period
F2   B dominant and first       SOURCE_B
F3   B missing                  TRAILER_CHANNEL_ABSENT (an absence, never inferred)
F4   A first by EXACTLY ONE     SOURCE_A_MODE by onset; the phase diagnostic on
     forcing period             the same traces reads ZERO           (NC_022)
     + contrasts: opposite readings -> NOT_EVALUABLE; a steady oscillation ->
       NO_RISE on both, amplitude alone, stated; clock skew; comparable bodies
```

Two refusals found while building the first fixtures still stand: a phase lead
against a quiet channel is not a measurement (`NC_012`), and a lead is
determined only modulo the forcing period (`NC_013`). One finding from the
rewrite: the envelope window must cover a full carrier period or the onset
index moves with the carrier phase at onset (`NC_023`, derived and untested;
the ESP-1 side carries 0.25 and never exercises the case).

The worked instance — a tractor cab and its trailer on a serpentine descent,
sensor in the cab, body at risk the trailer — is text. Its cross-link
`JinnZ2/Simulators, stability-trigger-envelope/ (ESP-1)` was filed
**PENDING** on 2026-09-24 (213 folders there, none of them it) and **LANDED**
on 2026-09-27 at commit `038a30f` of that repository's
`claude/noise-information-four-tools-5u0l4k` branch (`NC_017`). Its
`classify()` reads onset for the same reason this file does; neither imports
the other, and both are one author's.

---

## STEP 0 — the inventory this drop was built against

Read before anything was written. Modules present, and what each claims:

| path | what it is | claims it makes |
|---|---|---|
| `main.py` | entry point, runs the pipeline on a 5-sample simulated payload | none of its own |
| `software/quantum/quantum_processor.py` | fluctuation statistics over an unlabelled sequence | coherence, entanglement strength, non-local correlations |
| `software/biological/biological_processor.py` | bio signals, inter-species coordination | ecosystem communication, collective intelligence |
| `software/electromagnetic/em_processor.py` | motion anomalies against two baselines | solar, geomagnetic, cosmic-ray readings |
| `software/planetary/gaia_processor.py` | atmospheric chaos, feedback | planetary coordination, climate intelligence |
| `dashboard/dashboard.py` | aggregator over the four | none of its own |
| `symbolic/symbolic_intelligence.py` | averages a domain's scalars against 0.75; weights 0.3/0.3/0.2/0.2 | alignment score, symbolic consensus |
| `symbolic/phantom_detector.py` | NLP detector (needs spacy + sentence-transformers) | silence signal, jargon mismatch |
| `experiments/check_claims.py` | executable checks for `C1..C12` | the repository's own claim record |
| `docs/FALSIFICATION_LOG.md` | round 1: 12 claims tested, 1 survived | `C1..C12`, `U1..U6` |

**Overlaps found: none** (`NC_001`). No existing module computes an interval, a
channel comparison, a rerun rate, a residual partition or a two-body source
attribution. The nearest neighbour is `symbolic_intelligence.py`, whose
`_detect_resonance` averages whatever scalars a domain returns — the operation
`C6` records as unit-free. These four tools do not call it, extend it or take a
position on it.

**Run:** the harness was first filed as unrunnable here for want of numpy;
numpy was then installed and it runs (`NC_020`, corrected in place rather than
replaced). A baseline was captured **before** any NC row was added, so the
no-movement result below is a measurement.

**Added under the contributing rule:** five `NC_*` rows in
`experiments/check_claims.py` -- one per tool, and a second for N4 (`NC_022`,
F4). The first filing withheld them on an overbroad reading of the dispatch's
STEP 0; the operator clarified that adding new rows is not editing or
endorsing an older claim (`NC_019`). The first insertion was pure -- 162
insertions, 0 deletions -- and every `C1..C12` verdict was byte-identical
before and after.

**The summary line was corrected on 2026-09-27** (`NC_025`). The first filing
reported it as one line, `FALSIFIED=9 HOLDS=1 -> HOLDS=5`, which reads as
movement in a tally where nothing moved: twelve C rows and four NC rows were
summed together, while the NC series ran to NC_021 with only four ids carrying
a harness verdict. The harness now prints two series, two denominators:

```
C  rows  FALSIFIED=9  HOLDS=1  OPEN=1  REVISED=1   (12 of 12 C ids carry a harness verdict)
NC rows  HOLDS=5                                   (5 of 25 NC ids in tools/CLAIM_TABLE.md carry
                                                    a harness verdict; the other 20 carry a
                                                    TABLE status, which is not a verdict here)
```

The NC denominator is read from `CLAIM_TABLE.md` at run time, not typed into
the harness. The two lines above are what the code is written to print and
have NOT been observed (`NC_024`); the C line is the measured 2026-09-24
baseline and is not expected to move.

Nothing in `tools/` imports numpy; the four instruments still run where it is
absent.
