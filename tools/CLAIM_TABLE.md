# tools/ — claim table

Claims about the four instruments in this directory. Ids are `NC_*` and are
**distinct from the dispatch's tool names N1–N4** and from the repository's own
`C1..C12` in `docs/FALSIFICATION_LOG.md`. Nothing here restates, endorses or
extends an older claim.

Five of these ids -- NC_002, NC_006, NC_009, NC_013, NC_022 -- are also rows
in `experiments/check_claims.py`, so one claim carries one id in both files,
and those five carry a harness VERDICT (HOLDS / FALSIFIED). The rest carry a
TABLE STATUS only (SUPPORTED / UNVERIFIED / CORRECTED / CLOSED / DERIVED), which is
a different thing and is never summed with a verdict. The harness prints the
two series on two lines with both denominators, and reads the NC denominator
out of this file rather than storing it (NC_025).

Every claim below is a property of code in this directory, recomputable by
anyone with the clone:

```
python3 tools/test_tools.py          # the instruments' own selftests
python3 experiments/check_claims.py  # the repository harness, NC rows included
```

The check total is printed by that command and is deliberately not written
here. A count stored in a document is a second place for it to drift.

---

## What was found by building, not by reading

| id | claim | status |
|----|-------|--------|
| NC_002 | **N1: with the counts unread, the verdict is a property of the assumed denominator.** The two published percentages are fixed. Read at n=10 the intervals overlap and the tool returns VALUE; at n=25 and above they are disjoint and it returns CHANNEL_LOSS. Nothing about the report changed. | SUPPORTED |
| NC_003 | **N1: at a small assumed denominator the POINT moves too, not only the interval.** An integer count over a small denominator cannot represent an arbitrary percentage: at n=5 the reconstructed loss is 0.60 against a published 0.58. A second reconstruction artifact sits inside the first — the tie rule. Python's built-in `round()` is half-to-even and sends a published 90% at n=5 to 4/5; the declared rule here is half-up and sends it to 5/5. A tie rule that alternates direction with the parity of the denominator is invisible unless it is named. | SUPPORTED |
| NC_004 | **N1: both published figures are BOUNDS, and in opposite directions.** ">= 90%" and "as low as 32%". Read as points they overstate the direct channel and overstate the gap. The fixture reads them as points because a point estimate needs one, and states that doing so is the most favourable reading of the loss available from the report. | SUPPORTED |
| NC_006 | **N2: the sharper number is not the one the headline carries.** The single find came off a SIDE path, so the ASSIGNED path found nothing in eleven runs: 0/11, interval [0.0000, 0.2849], against the headline 1/11 at [0.0023, 0.4128]. The tighter bound is on the route the campaign was designed around. | SUPPORTED |
| NC_012 | **N4: a phase lead against a quiet channel is not a measurement, so fixture F1 as first specified could not be read by phase.** With body B flat, any lag a correlation returns is a property of B's residual variation rather than of the coupling. The phase diagnostic returns NOT_EVALUABLE there. Under onset timing the same record reads differently and honestly: A has an onset, B is `NO_EVENT` (nothing moved -- kept apart from an absent channel), so A is first by default and the lead has no value. `F1b` (B moving a little, A first by 8 samples) ships beside it. | SUPPORTED |
| NC_013 | **N4: the lead is determined only modulo the forcing period, and the branch was being chosen by accident.** A constructed LAG of 4 samples in a 40-sample period came back from the raw search as a LEAD of 36 — the same peak read on the other branch. The sign of the lead was what the agreement check read, so the branch choice was deciding a verdict. Leads are wrapped into the principal branch (−P/2, +P/2] and near half a period the sign is withheld. **Consequence, acted on 2026-09-27 under the operator's instruction:** the phase lead is out of the decision path altogether. `phase_lead()` is kept as a DIAGNOSTIC that decides nothing, `source()` does not call it (asserted from its source) and no return from `source()` carries a phase field. | SUPPORTED, repaired; phase now diagnostic-only |
| NC_022 | **N4: with A leading by EXACTLY one forcing period, onset timing classifies the source and the phase diagnostic reads zero.** Fixture F4: A bursts at sample 100, B at sample 140, period 40 samples. Onset — first exceedance of half the body's own peak envelope — reads A first by one period and the verdict is `SOURCE_A_MODE` with onset agreeing; `phase_lead()` on the same two traces reads a lead of zero, because one period and zero are one peak to a periodic correlation. The worked instance predicts a lead of about one period, so this is the case the instrument exists for and the case phase cannot read. The two readings are shown to disagree by more than half a period on one trace pair, and the verdict, the agreement and the onset lead are shown invariant when the carrier is shifted half a period while the raw-trace phase reading moves — so nothing phase-shaped is left in the decision path. | WRITTEN, NOT RUN — see NC_024 |
| NC_023 | **N4: the envelope window must cover at least one carrier period, or the onset index moves with the carrier phase at onset.** A moving RMS over a window shorter than the carrier period is not stationary — over a quarter period it swings between roughly 0.43 and 0.90 of the amplitude — so where two bodies start at different carrier phases the first-exceedance index jitters by up to a quarter period, and a sub-period lead (F1b's 8 samples) can read with the wrong sign. `n4.envelope_window_frac` is therefore 1.0 here, where the ESP-1 side carries 0.25 with a 100-sample carrier. ESP-1's fixtures never exercise a sub-period lead (every lead there is zero or exactly one reversal), so the defect is unreached there rather than absent, and its carrier is referenced to t=0 rather than to onset, which is the case that would expose it. **Derived, not measured**: this session could not execute, so the swing figures are arithmetic on a sine and the jitter claim has not been observed. Cross-repo pointer: `JinnZ2/Simulators stability-trigger-envelope/RUN_NOTE.md` CHOICE 4 and `thresholds.txt envelope_window_frac`. | DERIVED, UNTESTED |
| NC_016 | **The closed `KINDS` vocabulary refused N4's verdicts on first build.** That is the tuple doing its job rather than a defect. It was widened deliberately, the three new members are commented at the site, and the widening is recorded in `threshold_provenance.txt` — a widening that leaves no trace is the guard being stepped around rather than used. | SUPPORTED |

## Refusals built in, each demonstrated in both directions

| id | claim | status |
|----|-------|--------|
| NC_005 | **N1 refuses to compare two channels read by different readers.** A rate difference across two readers is not a property of the channel. NOT_EVALUABLE with the two readers named. | SUPPORTED |
| NC_008 | **N2's side-path share is `None` with no finds, never 0.0.** An empty numerator over an empty denominator is not a zero, and a 0.0 there would read as "no find came off a side path" on a campaign that found nothing. | SUPPORTED |
| NC_009 | **N3 never scales and never subtracts a candidate.** Candidates carry a SIGN or a SHAPE and nothing else; `candidate()` refuses a magnitude, scale, amplitude, coefficient, weight, size or gain field outright. Asserted behaviourally: the residual series is identical with and without any candidate list. A fitted magnitude makes every candidate consistent, which is how an unexplained remainder becomes a confirmed mechanism with no measurement taken. | SUPPORTED |
| NC_010 | **N3 keeps `not_testable` apart from `inconsistent`.** A candidate whose prediction requires a variable the data does not carry has not failed; it was not asked. The two call for different next actions. | SUPPORTED |
| NC_011 | **N3's empty declaration is the loudest form of UNPARTITIONED, not the quietest.** With nothing declared the residual is the whole observation, and `sources_declared: []` says so rather than reading as a small remainder. | SUPPORTED |
| NC_014 | **N4 treats amplitude and onset pointing opposite ways as NOT_EVALUABLE, not as a verdict with a caveat.** Two readings disagreeing is not a finding. First built against phase; the same rule now reads onset, and an undetermined onset (`NO_RISE` on both bodies, a steady oscillation) is neither agreement nor disagreement — the verdict falls back to amplitude alone and `decided_by` says so. | SUPPORTED; re-read against onset, NOT RUN since |
| NC_015 | **N4's TRAILER_CHANNEL_ABSENT and an instrumented-but-flat body do not collapse.** A body that was not instrumented has not been shown to be quiet. The two return different kinds and the constructor keeps them apart at intake. | SUPPORTED |
| NC_007 | **N2's SINGLE_FIND bounds the process, not the result.** A rarely-reached real result and a once-reached artifact produce the same 1/11. The typed return exists so the interval is not read as a confidence in the finding. Misses are kept as rows carrying their run ids rather than collapsed into a denominator. | SUPPORTED |

## Scope, absences and what was not built

| id | claim | status |
|----|-------|--------|
| NC_001 | **Nothing in `tools/` duplicates an existing module.** The repository before this drop held four domain processors, an aggregator, a symbolic engine, an NLP detector and a claim harness. None computes an interval, a channel comparison, a rerun rate, a residual partition or a two-body source attribution. The nearest neighbour is `symbolic_intelligence.py`, which averages whatever scalars a domain returns — the operation `C6` in the falsification log records as unit-free — and these four tools do not touch it, call it or endorse it. | SUPPORTED |
| NC_017 | **The N4 cross-link is a cross-repo pointer, now LANDED.** First filed 2026-09-24 as `JinnZ2/Simulators, stability-trigger-envelope/ (ESP-1) -- PENDING, not yet landed`, checked against that repository as available to this session: 213 folders, none of them it, nearest by name `trigger-geometry/` and `envelope-asymmetry/`. Nothing was reconstructed in the interval. Closed 2026-09-27: the packet landed on branch `claude/noise-information-four-tools-5u0l4k` of that repository at commit `038a30f`, its `descent_record.classify()` reading onset rather than phase under the same instruction that changed this file. Its content is still unread from here in the sense that matters — neither side imports the other, and the two builds are one author's, so their agreement is a same-builder convergence and not two confirmations. | CLOSED by landing; the "pending" record kept |
| NC_018 | **Every published-value fixture is SECONDARY and its primary is UNREAD.** Probed 2026-09-24T11:25Z: `www.biorxiv.org`, `arxiv.org` and `www.nature.com` return no response through this environment's egress policy, with `github.com` answering as the control. No count in any fixture was transcribed from a paper. | UNVERIFIED |
| NC_019 | **The dispatch/contributing conflict was a misreading on my part, and is now closed.** First filing withheld the `NC_*` rows from `experiments/check_claims.py`, reading STEP 0's "do NOT edit, endorse or extend older claims" as covering the file rather than the claims in it. The operator clarified on 2026-09-24 that adding new rows is neither editing nor endorsing an older claim, and that the dispatch wording was **overbroad**. Four rows were then added under the repository's own contributing rule. The insertion is provably pure: `git diff` reports **162 insertions and 0 deletions**, and every `C1..C12` verdict is byte-identical before and after (`FALSIFIED=9 HOLDS=1 OPEN=1 REVISED=1` on the C rows both runs). The `NC_*` checks import from `tools/` only and touch no processor, so an NC row cannot move because a C row moved. | CLOSED by clarification |
| NC_020 | **CORRECTED. The harness runs.** First filing recorded that `experiments/check_claims.py` could not be run because numpy was absent from this environment, and that the processors were read and not executed. That was true of the environment as first found and false of the environment available: `pip install numpy` succeeded (2.4.6) when the clarification made running the harness necessary. The correction is recorded here rather than replacing the original line, because a first filing that reported an absence it had not tried to remove is the more useful half. **Baseline captured before any NC row was added**, so the no-movement result rests on a measurement and not on an assumption. What survives unchanged: nothing in `tools/` imports numpy, and the four instruments still run where numpy is absent. | CORRECTED |
| NC_021 | **Nothing here is a measurement of anything physical.** No sensor, no vehicle, no campaign, no survey. Three of the four tools run on CONSTRUCTED fixtures whose expected values are known in advance because they were authored; the fourth runs on percentages from a press report. Whether any of the four separates what it claims to separate on real data is untouched in both directions. | UNVERIFIED |
| NC_024 | **The N4 onset rewrite was WRITTEN WITHOUT A RUNNER and has not been executed.** On 2026-09-27 the session's command execution was refused for the rest of the session by a safety check reacting to earlier conversation content, not to any command. `two_body_source.py` was rewritten, `thresholds.txt` / `threshold_provenance.txt` gained three rows, and `check_claims.py` gained NC_022 and the two-series summary — none of it run. What is asserted: the file parses under Python 3.9 by inspection and every fixture's expected verdict is derived by hand in the module's own comments. What is not: that the selftest passes, that the render is clean, that NC_022 HOLDS. The first `python3 tools/test_tools.py` and `python3 experiments/check_claims.py` are the acceptance test, and a failure there is a finding about this build rather than about the instrument's design. Same shape as the ESP-1 side's `ESP_010`, which was written blind and later ran 217/0; this one has no "later" yet. | WRITTEN, NOT RUN |
| NC_025 | **The harness summary was stating one tally over two series, and the operator caught it.** The first filing reported `FALSIFIED=9 HOLDS=1 → HOLDS=5` as "the four added HOLDS": true, and it read as movement in a line where nothing moved, because twelve C rows and four NC rows were summed into one line while the NC series ran to NC_021 with only four ids carrying a verdict. The same shape as the 25/26/27 registry-denominator problem recorded in `Simulators/move-set/` (`MSV_024`). `main()` now prints the C tally and the NC tally on separate lines, each with its denominator stated, and reads the NC denominator from this file (every `NC_nnn` row id) rather than storing a count that could drift. Expected on the first run: `C rows FALSIFIED=9 HOLDS=1 OPEN=1 REVISED=1 (12 of 12)`; `NC rows HOLDS=5 (5 of 25 NC ids carry a harness verdict; 20 carry a table status)`. Those two numbers are predictions written before the run and are exactly what NC_024 says is unverified. | CORRECTED, NOT RUN |

---

## What would refute these

- **NC_002 / NC_003** die if the preprint's real per-channel counts are read and
  the verdict is stable across them. They are claims about what an unread
  denominator costs, not about the biology.
- **NC_012 / NC_013** die if a cross-correlation is shown to recover a lead
  against a channel at or below its own variance floor, or to determine a sign
  at half a period. Both are properties of the operation and neither depends on
  the fixtures.
- **NC_022** dies on its first run if F4 returns anything but `SOURCE_A_MODE`
  with onset agreeing, or if the phase diagnostic on F4 reads a non-zero lead.
  It also dies if the verdict moves when only the carrier phase moves — that
  would mean a phase reading is still in the decision path.
- **NC_023** dies if a sub-period-lead fixture run at `envelope_window_frac`
  0.25 recovers the lead's sign every time across carrier phases. Then the
  1.0 here is a cost with no benefit and should be brought back to the ESP-1
  value with a provenance row saying why.
- **NC_024 / NC_025** are the folder's own state and die by running: the
  first execution either confirms the predicted tallies or replaces them.
- **NC_009** dies the moment any function in `residual_partition.py` returns a
  quantity fitted to the residual. The behavioural check is in the selftest.
- **NC_001** dies if a reader finds an existing module computing any of the four
  quantities. The overlap scan behind it is a read of every `.py` in the
  repository, listed in `tools/README.md`.
- **NC_017** closed when the ESP-1 packet landed in `JinnZ2/Simulators`
  (2026-09-27, commit `038a30f`). It was a statement about where a pointer
  points and what is at the other end, not about the packet's content. It
  would reopen if that branch were deleted without merging.
