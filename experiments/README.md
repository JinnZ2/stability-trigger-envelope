# experiments/

Executable claims. Every assertion this repository makes in prose should exist
here as something that can be run and can fail.

```bash
python experiments/check_claims.py
```

## Why this exists

Before round 1 the repo had four processors, a symbolic engine, an NLP tool and
several thousand words of documentation — and no way to tell which of it was
true. Twelve prose claims were restated as executable checks. One survived.

The failures were not in the exotic parts. Documentation pointed at files that
were never committed; a data file had never once parsed; the phantom detector
could not reproduce the example output printed in its own README. None of that
needed a hypothesis to find, only a run.

## Verdicts

| verdict | meaning |
|---------|---------|
| `HOLDS` | true of the code as it stands |
| `FALSIFIED` | contradicted by a reproducible run |
| `REVISED` | the original claim was wrong; a narrower claim replaced it, and the narrower claim is what is tested |
| `OPEN` | not decidable without hardware, a corpus, or a decision |

A `FALSIFIED` verdict is a **result, not a build failure**. Several are recorded
deliberately as known-open defects, so the harness exits 0 regardless. If you
want it as a gate, gate on the count changing rather than on the count being
zero — a claim that quietly flips from `HOLDS` to `FALSIFIED` is exactly the
event worth catching.

## Adding a check

```python
def c13_my_claim():
    """Where the claim is written down, quoted."""
    ...                                  # run something real
    record("C13", "FALSIFIED",
           "the claim, stated so it could be false",
           "what was observed, with numbers")

CHECKS = [..., c13_my_claim]
```

Rules that keep this useful:

- **State the claim so it can fail.** "The EM layer works" is untestable.
  "`analyze_em_field_noise` returns a non-zero solar correlation for the demo
  payload" is a claim.
- **Quote the source.** Put the doc line being tested in the docstring, so a
  reader can see what was promised and by whom.
- **Show numbers, not adjectives.** The evidence string is the finding. C5 is
  only convincing because it prints the sweep.
- **Record wrong guesses.** C5's first hypothesis was backwards — entropy went
  negative, not positive. Keeping the correction is more informative than
  presenting the revised claim as if it had been obvious.
- **Degrade, don't crash.** C12 first took the whole harness down when a model
  download hit a proxy block. An unavailable dependency is an `OPEN` verdict or
  a documented substitute, not a traceback.
- **Substitute honestly.** C12 stands in orthogonal vectors for the real
  embedder because `huggingface.co` is unreachable here. That stub is the *best*
  case for the metric being tested, so a negative result is still a valid
  falsification — a positive one would not have been. Say which direction your
  substitute biases.

## After a run

Write it up in [`docs/FALSIFICATION_LOG.md`](../docs/FALSIFICATION_LOG.md):
the hypothesis, the run, the result, the edited claim, and what you now know you
don't know. Move superseded files to `legacy/` rather than deleting them.

This file is the apparatus. The log is the notebook.
