# First-run report — stability-trigger-envelope

Run: 2026-10-02 UTC, Python 3.12.3, NumPy 2.5.3. All commands below were executed from the root of this new repository. **No claim check, fixture expectation, threshold, or instrument was edited to match a predicted result.** The input files attached by the user were copied intact to their respective paths (with `README2.md` installed as `tools/README.md`).

## What did not hold first

| Command | First result | Finding |
|---|---|---|
| `python3 tools/test_tools.py` | Exit **1**; **218 checks** across five modules, **one wrapper-level failure** | All five module selftests report zero failed checks (33 + 31 + 28 + 37 + 89). The wrapper's whole-output text screen sees the word `noise` in the printed branch name `claude/noise-information-four-tools-5u0l4k` and calls it a forbidden return value. This is a false positive in the output-word screen, not a module selftest failure. See [`tools-first.log`](tools-first.log). |
| `python3 experiments/check_claims.py` | Exit **0**; C tally exactly as predicted; NC tally **4 HOLDS, 1 FALSIFIED** rather than 5 HOLDS | **NC_013 was FALSIFIED** by its exact assertion: a constructed lag of four samples produced `raw_lead_samples = -4`, not the expected `+36` (wrapped lead still `-4`). Zero and one-period leads both read zero; the half-period sign is withheld; NC_022 HOLDS. The broader modulo-period observation is still demonstrated, but the particular raw-search branch prediction did not hold. Exit 0 means the harness completed, **not** that every claim HOLDS. See [`claims-first.log`](claims-first.log). |
| `python3 descent_record.py` | Exit **1**; no render | The current `Simulators/main` copy of `descent_record.py` fails parsing at line 766: an unterminated triple-quoted string. Compared with the documented landing commit `038a30f`, the current file has 63 stray appended lines before `main()`. This first failure is preserved in [`esp-render-first.log`](esp-render-first.log). |
| `python3 test_envelope.py` | Exit **1**; no checks ran | Import of that same malformed `descent_record.py` failed. See [`esp-test-first.log`](esp-test-first.log). |

**Predicted vs. observed harness summary:**

```text
Predicted C: FALSIFIED=9 HOLDS=1 OPEN=1 REVISED=1 (12/12)
Observed  C: FALSIFIED=9 HOLDS=1 OPEN=1 REVISED=1 (12/12)
Predicted NC: HOLDS=5 (5 of 25)
Observed  NC: FALSIFIED=1 HOLDS=4 (5 of 25)
```

The five executable NC ids are `NC_002`, `NC_006`, `NC_009`, `NC_013`, and `NC_022`; only `NC_013` failed. The 20 other NC ids have table statuses, not harness verdicts. This mismatch is **the finding**, not something to tune away.

## ESP-1 render after recovering its landed file

To actually observe the previously unobserved render, I replaced **only** `descent_record.py` with its **byte-for-byte** version from the existing [`Simulators` landing commit `038a30f`](https://github.com/JinnZ2/Simulators/commit/038a30f13c99b4aaa0d26affd35eebfa99460b2b). Its SHA-256 is `89dfd145d37de2b9766f8076e6dd9bdb3b89ece3d06b252c92b661d3fc555b11`. This selects an intact upstream artifact, not a new algorithm or a changed assertion. The current main-branch syntax failure remains recorded above. I excluded the unrelated upstream `test_descent_record.py`, `thresholds.json`, and `samples/`, which target a different ESP API and are not part of the root packet's documented test path.

With the landed file, `python3 descent_record.py` exited **0**. The render shows these **constructed regression fixtures, not physical measurements**:

| Fixture | Rendered outcome | Noteworthy reading |
|---|---|---|
| F1 cab oscillation | `GEOMETRIC_CAB_MODE` | Cab/trailer RMS ratio **7.039**; cab onset 4.36 s, trailer onset 6.36 s; cab leads **+2 s**. |
| F2 trailer roll | `TRAILER_ROLL_RISK` | Ratio **0.1894**; cab onset 6.36 s, trailer onset 4.36 s; cab lead **−2 s**. |
| F3 trailer uninstrumented | `TRAILER_CHANNEL_ABSENT` | Refuses to infer that an unmeasured trailer was quiet. |
| F4 clock skew | `NOT_EVALUABLE` | Start times differ 0.5 s, exceeding the 0.05 s tolerance. |
| F5 two triggered runs | `INSUFFICIENT_RUNS` | Two triggered, one untriggered at 26 mph; minimum three triggered runs. |
| F6 ice | `OUT_OF_ENVELOPE` | Ice lies outside the reader's declared dry/wet set. |
| F7 axes disagree | `NOT_EVALUABLE` | Cab amplitude dominates while trailer onset is first. |
| F8 comparable amplitudes | `NOT_EVALUABLE` | Ratio 1.148 lies between the declared separation bounds. |

The render also tallies **nine constructed records** by event (none 2, pass 2, near-miss 2, incident 1, closure 2) and access bin, returns **`score: None`**, and prints all current thresholds, including `envelope_window_frac = 0.25`. Full output: [`esp-render-pinned.log`](esp-render-pinned.log). `python3 test_envelope.py` now exits **0**, **217 checks / 0 failed**; see [`esp-test-pinned.log`](esp-test-pinned.log).

## Additional attached-file checks

- `python3 probe_subperiod.py` exited **0** without changing the 0.25 window. Its absolute-carrier arm found **0 wrong signs in 80 cells** (at a five-sample lead, two cells read zero). Its onset-referenced control also found **0/80 wrong signs**. However, F10's planted **10-sample** lead read as **+37 samples**: sign survived while magnitude drifted. Thus this sweep **does not support a wrong-sign finding** for `NC_023`; it does expose timing error on the constructed case. The derivation's broader claim is not globally settled by this finite sweep. See [`probe-first.log`](probe-first.log).
- The uploaded [`test/singularfunnelpitchfork.py`](../test/singularfunnelpitchfork.py) passed its **four selftest assertions**; its full edge scan was not run. See [`singular-smoke.log`](singular-smoke.log).

## Status of NC_024 and the old state notes

`NC_024`'s **“WRITTEN, NOT RUN” absence is closed**: both acceptance commands were executed and recorded. But it **did not close as a successful acceptance**: the tool wrapper exits 1 and NC_013 is FALSIFIED despite the harness exiting 0. The historical `tools/CLAIM_TABLE.md`, `tools/README.md`, and the ESP README still contain their original dated unrun/unobserved statements; those are preserved as source records, and **this report supersedes them for current execution status**. The ESP render absence is likewise closed **only after using the pinned landing version**; the first attempt against current main failed to parse. No real descent or IMU measurement was performed.

## Source and layout

- ESP-1 packet: `JinnZ2/Simulators` `stability-trigger-envelope/` as available on `main` at `c03efc4`, with the single instrument pinned to `038a30f` for the reason above; uploaded `cases.py` and `RUN_NOTE.md` supersede upstream copies.
- Noise claim dependencies and four tools: `JinnZ2/Noise-as-Information-Sensor` at `6a5656d`, with uploaded `experiments/check_claims.py`, `tools/README.md`, and `tools/CLAIM_TABLE.md` superseding older upstream copies. The C-series harness requires NumPy; ESP-1 and the `tools/` modules are standard-library-only.
- Uploaded `probe_subperiod.py` is at repo root; the independent singular-funnel script is under `test/`. All seven attached files are represented. Root [`LICENSE`](../LICENSE) is CC0-1.0. The imported historical `tools/README.md` mentions an MIT license in its earlier-repository narrative; the actual source repository's `LICENSE`, like this repository's, is CC0.
