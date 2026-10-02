# Falsification Log

The working record of this repository: what was claimed, what happened when it
was run, which claims died, what replaced them, and what is still unknown.

The loop this project runs on:

```
hypothesise -> run -> result -> falsified? -> edit the claim -> search for unknowns -> rerun
```

A claim that has never been run is not a finding, it is a wish. A claim that
has been run and died is worth more than one that was never tested, and it
stays in this file after it dies. Nothing here is deleted; entries get
superseded, and the superseding entry says what changed.

**Reproduce every result in this file:**

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python experiments/check_claims.py
```

Each finding below carries the claim id printed by that harness.

---

## Round 1 — 2026-08-14

**Starting position.** Six months of committed documentation, four processor
modules, one symbolic engine, one NLP tool. No test had ever been run against
any of it. The question for this round was deliberately narrow: *of the claims
this repo makes in prose, which survive contact with the code?*

**Method.** Restate every prose claim as an executable assertion
(`experiments/check_claims.py`), run it, record the verdict. No code was
modified before testing — the point was to measure the repo as committed, not a
repaired version of it.

**Headline result: of 12 testable claims, 1 survived.**

| id | claim | verdict |
|----|-------|---------|
| C1 | Setup steps and module tables point at real files | **falsified** |
| C2 | The quantum processor analyses fs/ps/ns timescales | **falsified** |
| C3 | The pipeline is non-filtering and preserves raw data | **falsified** |
| C4 | The EM layer produces solar/geomagnetic/cosmic-ray readings | **falsified** |
| C5 | Resonance detection measures coherence, not recording length | **revised** |
| C6 | The 0.75 threshold compares like with like across domains | **falsified** |
| C7 | The dashboard accepts any sensor series the Arduino can produce | **falsified** |
| C8 | Processor output can be logged or transported as JSON | **falsified** |
| C9 | `PHANTOM_WORD_MAP.json` is machine-readable | **holds** (after repair) |
| C10 | `silence_signal` measures nearness to a definition | **falsified** |
| C11 | `jargon_mismatch` scores how a phrase diverges across domains | **falsified** |
| C12 | The detector reproduces its own documented example output | **falsified** |

---

### C1 — Documentation pointed at files that were never committed

**Claimed.** README v0.1: flash the Arduino code in `hardware/arduino_code/`,
then open `dashboard/index.html` for the real-time view. `software/README` v0.1
documented `bio_processor.py` and a central fusion engine, `noise_engine.py`.

**Run.** Existence check on every path named in prose.

**Result.** Six of six absent. `index.html` and `arduino_code/` were never
committed; `noise_engine.py` never existed in any commit. `em_field_processor.py`
and `noise_dashboard.py` are the real `em_processor.py` and `dashboard.py` under
old names.

**Claim edited to.** The dashboard is a text summary printed to stdout. Arduino
firmware lives in `software/arduino/`. There is no fusion engine module; that
role is split between `dashboard.py` and `symbolic_intelligence.py`. Both v0.1
READMEs are retired to `legacy/`.

---

### C2 — The picosecond analysis is an unused variable

**Claimed.** "Quantum fluctuation timing (picosecond analysis)"; the multi-scale
table assigns the quantum processor the fs–ns band.

**Run.** Counted references to `self.quantum_timescales` in the module.

**Result.** One — the assignment. No method reads it. More basically, the
processor receives a bare list of floats: no timestamps, no sample rate. There
is no information in the input from which any timescale could be recovered.

**Claim edited to.** `QuantumNoiseProcessor` computes order-independent
statistics over an unlabelled sequence. It has no notion of time. Nothing in the
repo currently justifies the fs/ps/ns framing.

**Left in place deliberately.** The attribute is not deleted. It records an
intended direction, and the honest fix is a timestamped input format, not a
tidier constructor. See U1.

---

### C3 — The non-filtering pipeline injects synthetic noise

This is the one that matters most, because it contradicts the project's founding
principle rather than its file layout.

**Claimed.** "Raw data is always preserved. All signal processing is
non-filtering." Stated in the Field Manual, the hardware README ("Log **all**
data — do not pre-filter") and `CLAUDE.md`.

**Run.** Compared `extract_fluctuations(x)` against `np.diff(x)`.

```
np.diff(molecular)        [-0.03,    0.06,    -0.04,    0.02   ]
extract_fluctuations()    [-0.029695, 0.05896, -0.03925, 0.020941]
synthetic component       [ 0.000305,-0.00104,  0.00075, 0.000941]
```

**Result.** The method adds `rng.normal(0, 0.001, ...)` to real measurements —
about 2% of signal magnitude on the demo data, and unboundedly more on quiet
data, since the injection is absolute while the signal is not. Every downstream
"quantum coherence" and "entanglement strength" number is computed partly from
noise the program invented.

Worse for reproducibility: the generator is reseeded to 42 *inside the method*,
so the identical synthetic vector is re-added on every call. This does not make
the result reproducible in a useful sense; it makes a constant artefact look
like a stable measurement.

**Claim edited to.** The pipeline is non-filtering in the sense that it discards
nothing. It is *not* non-modifying: the quantum path adds synthetic noise to
measurements before analysis. Any result from that path is currently
uninterpretable as a measurement of anything external.

**Not fixed here, and that is deliberate.** Removing the injection changes every
quantum number the project has ever printed. That is a change to the record, not
a bugfix, and it should be made as its own experiment with before/after captured
— see U3.

---

### C4 — The electromagnetic layer cannot fire on its own demo data

**Claimed.** The EM layer "correlates solar and geomagnetic patterns" and detects
cosmic ray impacts.

**Run.** `analyze_em_field_noise` on the `main.py` demo motion series.

**Result.** `{'solar_field_effects': 0.0, 'geomagnetic_influences': 0.0,
'cosmic_ray_impacts': 0}` — and not because the environment is quiet. Three
independent gates each guarantee zero:

- `detect_motion_anomalies` keeps readings more than 0.1 from the mean. On the
  demo series (spread 0.05) it returns an empty list.
- Both correlation methods return `0.0` unless at least 3 anomalies survive, so
  with 5 input samples they can essentially never run.
- `detect_cosmic_ray_signatures` tests `a > 1.2` against readings every other
  part of the pipeline treats as normalised to roughly 0–1.

A returned `0.0` is therefore ambiguous between "no solar correlation" and "not
enough data to look" — the two are indistinguishable to any caller.

**Claim edited to.** The EM layer is inert for inputs of the size and scale the
project currently produces. Its thresholds are written against a unit convention
that no documented sensor path supplies.

**Open.** Which is wrong, the thresholds or the normalisation? Undecidable until
a real unit convention exists. See U4.

---

### C5 — The first hypothesis of this round was itself wrong

Recorded in full because the correction is the useful part.

**Hypothesised.** `_detect_resonance` averages a domain's outputs against a fixed
0.75 threshold, and one of those outputs is an unbounded entropy term. So
large-magnitude input should dominate the mean and force a false
"Resonance Detected".

**Ran.** Fed the quantum processor the same series scaled ×50.

**Result — hypothesis falsified.** Entropy went to −1057, not +∞. The term is
`-sum(x * log|x|)`, which turns *negative* above 1.0. Scaling up suppresses
resonance rather than triggering it. The mechanism was real; the direction was
backwards.

**Searched the input space instead of guessing again.** Swept sample count with
values held in (0, 1), where `-x·log(x) > 0`:

```
one identical sine phenomenon, resampled:
n=   5  entropy=   1.512  verdict=Resonance Detected
n=  10  entropy=   3.023  verdict=Resonance Detected
n=  20  entropy=   6.047  verdict=Resonance Detected
n=  50  entropy=  15.116  verdict=Resonance Detected
n= 100  entropy=  30.232  verdict=Resonance Detected
```

**Revised claim, and it is worse than the original.** Entropy here is
*extensive* — it grows linearly with sample count. It is averaged against a
bounded coherence term and compared to a fixed threshold, so past a handful of
samples the quantum domain reports resonance permanently. The verdict tracks how
long you recorded for, not what you recorded.

**And the demo hides it.** `main.py` reports quantum as subthreshold only because
its values sit near 1.0, where `x·log(x) ≈ 0`. The single demo payload lands in
the one narrow regime where the defect is invisible. A working demo was
concealing a saturated detector.

---

### C6 — The threshold compares quantities with no common unit

**Claimed.** `resonance_threshold = 0.75` applied across domains.

**Run.** Inspected what `_detect_resonance` actually averages.

**Result.** For the planetary domain: `[1.0, 0.0, -0.941]` → mean 0.0197. Those
three numbers are a boolean, a boolean, and a Pearson correlation coefficient.
Booleans are coerced to 1.0/0.0 and averaged with an *r* that ranges to −1; the
quantum domain adds unbounded entropy to the same mean. The 0.75 threshold is
applied to a quantity with no unit, and a strongly *anti*-correlated planetary
signal pulls the mean toward zero exactly as a weak one would.

**Claim edited to.** The alignment score is currently an arbitrary function of
its inputs. `alignment_score` and `symbolic_consensus` should be read as
provisional, not as measurements.

**Note on the two thresholds.** `resonance_threshold` is 0.75 (per domain);
consensus requires `alignment_score > 0.7` (across domains). With weights
0.3/0.3/0.2/0.2 the second means at least three domains must agree — two can
reach at most 0.6. Easy to conflate; they are unrelated numbers.

---

### C7 — Short inputs crash; bad inputs return `nan` silently

**Run.** `analyze_all` across input lengths, plus a negative-valued series.

```
n=2: raises ValueError    n=4: completes
n=3: raises ValueError    n=5: completes
negative molecular input: earth_system_feedback=nan  (no warning)
```

**Result.** `gaia_processor` and `biological_processor` index fixed-length
baselines (4 and 3 samples) without checking the input is long enough. Below 4
samples the pipeline dies inside numpy with a message about concatenation axes
that says nothing about sample counts. Negative input propagates a silent `nan`
straight into the symbolic layer, which coerces it and carries on.

**Claim edited to.** Minimum input length is 4 samples per channel. This was
never documented and is now stated in the README.

---

### C8 — Output is not JSON-serialisable

**Claimed.** `CLAUDE.md`: dict-based data flow between components.

**Run.** `json.dumps(dashboard.analyze_all(demo))`.

**Result.** `TypeError: Object of type bool is not JSON serializable`. Four
fields leak numpy scalars (`np.float64`, `np.bool_`) instead of Python types.
The dicts pass between components in-process but cannot be logged, cached, or
sent anywhere — which is the main reason to have chosen dicts.

**Claim edited to.** Output is dict-shaped but not serialisable. Fixing it means
casting at each processor boundary; it changes no numbers and is safe to do
whenever. See U5.

---

### C9 — The phantom word map had never been loadable

**Claimed.** `symbolic/README.md` describes a workflow that reads and appends to
`PHANTOM_WORD_MAP.json`.

**Run.** `json.load`.

**Result.** `JSONDecodeError` at line 71 — a trailing comma after the final
entry plus a stray `}` before the closing `]`. The file had been unparseable for
its entire committed life. The documented workflow had never once been executed;
had it been, it would have failed at step one.

**Repaired.** Two-character syntax fix, no content touched. The map now parses:
6 entries, PW001–PW006, consistent schema, no missing keys.

This is the only claim in this round repaired directly, because a file that
cannot be parsed has no results to preserve — there was no record to protect.
The unparseable version is kept byte-for-byte at
`legacy/PHANTOM_WORD_MAP.v0.1.broken.json`.

---

### C10 — `silence_signal` scores almost every sentence as "defined"

**Claimed.** Silence measures how often a phrase appears *without* a nearby
definition.

**Run.** The definer list `["is", "means", "defined as", "refers to"]` against
sample sentences.

**Result.** The test is `d in t.lower()` — a raw substring match. `"is"` fires
inside **analysis**, **noise**, **Anisotropy**, **misread**:

```
'This analysis is noisy.'            -> scored DEFINED via ['is']
'The noise was measured.'            -> scored DEFINED via ['is']
'Anisotropy appeared in the sample.' -> scored DEFINED via ['is']
'A misread signal.'                  -> scored DEFINED via ['is']
```

Since `silence_signal` returns `(count - defined) / count`, and nearly every
English sentence contains the letters *i-s* somewhere, the signal is driven to
0 across any corpus. It carries weight 0.6 of the composite score — the largest
single term is structurally pinned near zero.

---

### C11 — `jargon_mismatch` never looks at the phrase

**Claimed.** "How differently the phrase clusters across domains."

**Run.** AST inspection plus a similarity-matrix sweep.

**Result.** Two independent defects.

1. The `phrase` parameter is never read in the function body. The function
   embeds each domain's entire concatenated text, so **every phrase sharing the
   same domain set receives an identical score**. It is a property of the corpus
   partition, not of the phrase.

2. `sim.mean()` averages the full similarity matrix *including the
   self-similarity diagonal*, which is fixed at 1.0. For realistic non-negative
   sentence similarities the score is capped at `1 − 1/n`:

   ```
   2 domains, maximally unrelated -> reported 0.500 (ceiling 0.500)
   3 domains, maximally unrelated -> reported 0.667 (ceiling 0.667)
   ```

   In the 2-domain case the README documents, the term cannot exceed 0.500, so
   at weight 0.4 it contributes at most 0.200 toward a 0.4 flagging threshold —
   it can never carry a candidate on its own.

---

### C12 — The detector does not reproduce its own documented example

**Claimed.** `symbolic/README.md` gives example output: `anisotropy` 0.62,
`reciprocity` 0.45.

**Run.** `detect_phantoms` on the sample corpus bundled in the module's own
`__main__` block.

Note on method: `huggingface.co` is blocked by this environment's network
policy, so `all-MiniLM-L6-v2` could not be fetched. The run substitutes
orthogonal unit vectors — the most divergent embedding result physically
possible, and therefore the *best* case for `jargon_mismatch`. A negative result
under this stub is a valid falsification; a positive one would not have been.

**Result.** Three candidates, all function words. Neither documented term
appears:

```
'of'  score=0.600  silence=0.500  jargon=0.750
'but' score=0.467  silence=0.333  jargon=0.667
'in'  score=0.400  silence=0.333  jargon=0.500

anisotropy surfaced: False        reciprocity surfaced: False
silence_signal('anisotropy') = 0.0
silence_signal('reciprocity') = 0.0
```

Three causes compounding:

- Both documented terms occur in only 2 documents and are cut by the `cnt < 3`
  minimum-frequency gate.
- Both score silence 0.0 — `"is"` matches as a substring *inside the word
  `anisotropy` itself* (C10).
- There is no stopword filter, so what survives the gate is exactly the set of
  words that appear everywhere and mean nothing.

A fourth issue inflates counts independently: `extract_phrases` emits n-grams
per occurrence, so `"noise noise noise"` yields `'noise'` three times. A single
repetitive document can push a phrase past a gate meant to require corroboration
across documents.

**Claim edited to.** The example output in `symbolic/README.md` is
aspirational — it was never produced by this code. It is labelled as such rather
than deleted, because it is a reasonable statement of what the detector was
*meant* to find, and makes a good acceptance test for U2.

---

## Open questions

Carried forward. These are the "search for unknowns" outputs of round 1 — none
are decidable from the current repo alone.

| id | question | what would settle it |
|----|----------|----------------------|
| U1 | Can any timescale claim be recovered? | An input format carrying timestamps or a sample rate. Until then C2 cannot be re-run, only restated. |
| U2 | Do the two dropped detector signals work? | `legacy/detector-pseudocode.v0.1.md` specified translation-gap and metaphor-overuse at weights 0.25/0.2; neither was implemented. Never refuted — just never built. Implement, then use the C12 example output as the acceptance test. |
| U3 | What do the quantum numbers look like without the synthetic injection? | Delete the `rng.normal` term, rerun, diff against the round-1 baseline. Must be run as its own experiment: it invalidates every previously printed quantum figure. |
| U4 | What are the units? | The EM thresholds (>1.2, >0.1) and the 0–1 normalisation the demo implies cannot both be right. Needs one documented convention from real sensor output, not simulated data. |
| U5 | Are the boolean outputs measurements or summaries? | `collective_intelligence`, `planetary_coordination` and `climate_intelligence` are thresholded booleans that the symbolic layer immediately re-casts to 1.0/0.0. If the underlying continuous value is what matters, returning the boolean discards it. Decide before fixing C8. |
| U6 | Is the demo payload representative? | C5 showed it sits in the one regime hiding a saturated detector. Every claim marked "holds" against demo data alone should be re-run on real capture before being trusted. |

---

## What this round did not do

Stated so a later reader does not mistake silence for absence.

- **No processor maths was changed.** C3, C5, C6 and C7 all describe live
  defects that are still live. They are documented, not repaired. Fixing them
  changes numbers this project has published, and each deserves its own round
  with a before/after captured — that is what U3 is for.
- **The only repairs made were:** the `PHANTOM_WORD_MAP.json` syntax error (C9 —
  no results existed to invalidate) and prose corrections to falsified claims.
- **`requirements.txt` was split.** The NLP stack is needed only by
  `phantom_detector.py` and pulls in torch; it now lives in
  `requirements-nlp.txt`. This affects no results.
- **Not tested at all:** anything requiring hardware. The Arduino sketch has
  never been run against a physical sensor in any record in this repo. Every
  number in this log comes from simulated input.

---

## How to add a round

1. Write the hypothesis down **before** running anything. If it is not falsifiable,
   it is not a hypothesis yet.
2. Add it to `experiments/check_claims.py` as an executable check with a claim id.
3. Run. Record the result whichever way it goes — C5 is in this log precisely
   because the first guess was wrong, and that correction was more informative
   than the original guess would have been.
4. If falsified, edit the claim in the docs. Do not delete the old claim: move
   the file to `legacy/` or record the old wording here.
5. Add what you now do not know to the open questions table.
6. Rerun the whole harness. Earlier claims can die from later changes.
