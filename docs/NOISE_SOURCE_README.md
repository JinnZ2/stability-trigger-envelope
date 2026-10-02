# Noise-as-Information Sensor

A multi-scale sensor framework that treats environmental **noise as a source of
information** rather than as error. It decodes patterns across quantum,
biological, electromagnetic, and planetary domains using signal processing,
symbolic reasoning, and cross-domain resonance detection.

**Status: early research prototype.** All results to date come from simulated
input. Nothing here has been validated against a physical sensor.

> **Read [`docs/FALSIFICATION_LOG.md`](docs/FALSIFICATION_LOG.md) before trusting any
> number this code prints.** Of 12 documented claims tested in round 1, one
> survived. The failures are recorded there rather than quietly patched, and
> several are still live.

---

## Premise

Traditional instrumentation treats fluctuation as something to be filtered out.
This project asks what is in the part that gets discarded — whether structure
persists across scales that no single-domain instrument would notice, and
whether that structure carries information.

That premise is a hypothesis, not a finding. It has not been confirmed by
anything in this repository.

---

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

`main.py` runs the full pipeline on a small simulated payload and prints a
per-domain summary followed by a symbolic alignment score.

Check the documented claims against the code:

```bash
.venv/bin/python experiments/check_claims.py
```

The phantom word detector is a separate tool with a heavier dependency set:

```bash
.venv/bin/pip install -r requirements-nlp.txt
.venv/bin/python -m spacy download en_core_web_sm
.venv/bin/python symbolic/phantom_detector.py
```

---

## Architecture

```
raw sensor data (4 channels)
    ├── molecular   → QuantumNoiseProcessor      → coherence, entanglement estimate
    ├── chemical    → BiologicalNoiseProcessor   → ecosystem signatures, coordination
    ├── motion      → EMFieldNoiseProcessor      → solar, geomagnetic, cosmic ray
    └── atmospheric → GaiaSystemNoiseProcessor   → planetary coordination, feedback
                              │
                       NoiseDashboard  (aggregates, prints a text summary)
                              │
                   SymbolicIntelligenceEngine
                              │
                 alignment_score + symbolic_consensus
```

Each processor is domain-isolated and returns a dict. Cross-domain logic lives
in `symbolic/`. Nothing is discarded as noise on the way through.

### Modules

| Path | Role |
|------|------|
| `main.py` | Entry point; runs dashboard then symbolic engine on a demo payload |
| `software/quantum/quantum_processor.py` | Fluctuation statistics over an unlabelled sequence |
| `software/biological/biological_processor.py` | Correlation against known bio signatures |
| `software/electromagnetic/em_processor.py` | Anomaly detection, solar/geomagnetic correlation |
| `software/planetary/gaia_processor.py` | Atmospheric chaos and feedback detection |
| `dashboard/dashboard.py` | Aggregator over all four processors; prints to stdout |
| `symbolic/symbolic_intelligence.py` | Cross-domain resonance and weighted alignment |
| `symbolic/phantom_detector.py` | Standalone NLP tool for sensed-but-unnamed concepts |
| `software/arduino/noise_capture.ino` | Firmware; streams `timestamp,rawValue` CSV at 9600 baud |
| `experiments/check_claims.py` | Executable version of every claim in these docs |

### Cross-domain weights

```python
quantum 0.3   biological 0.3   electromagnetic 0.2   planetary 0.2
resonance_threshold = 0.75   # per domain
consensus requires alignment_score > 0.7   # across domains, so >= 3 must agree
```

---

## Known limitations

These are measured, not suspected. Each links to a claim id in the
[falsification log](docs/FALSIFICATION_LOG.md).

- **Minimum 4 samples per channel.** Fewer raises a `ValueError` from inside
  numpy with an unhelpful message. Negative input yields a silent `nan`. (C7)
- **The quantum path adds synthetic noise to your measurements.**
  `extract_fluctuations` adds `rng.normal(0, 0.001)` before analysis, reseeded to
  42 on every call. Quantum outputs are not currently interpretable as
  measurements. (C3)
- **The quantum resonance verdict saturates with sample count.** The entropy term
  is extensive, so past a handful of samples the domain reports resonance
  permanently. The demo payload happens to sit in the one regime where this is
  invisible. (C5)
- **The alignment score has no unit.** It averages booleans, correlation
  coefficients and unbounded entropy, then thresholds the result. Treat it as
  provisional. (C6)
- **The EM layer is inert at demo scale.** Its thresholds assume a unit
  convention no documented sensor path supplies; `0.0` means "no correlation"
  and "not enough data to look" indistinguishably. (C4)
- **Output is not JSON-serialisable.** numpy scalars leak through processor
  boundaries. (C8)
- **The phantom detector does not reproduce its own documented example.** Its
  `silence` signal substring-matches `"is"` inside words like *analysis* and
  *anisotropy*; its `jargon_mismatch` ignores the phrase argument entirely.
  (C10, C11, C12)
- **No hardware validation.** Every result in this repo is from simulated input.

---

## Repository layout

```
main.py                  entry point
software/                the four domain processors + Arduino firmware
dashboard/               aggregator
symbolic/                resonance engine, phantom detector, phantom word map
experiments/             executable claim checks
tools/                   four instruments added under DISPATCH NOISE-1
docs/Field_Manual.md     conceptual framing
docs/FALSIFICATION_LOG.md  what was claimed, what was run, what died
hardware/                component specs by sensor layer
legacy/                  superseded files, kept as record — see legacy/README.md
```

`legacy/` holds documentation whose claims have been falsified. It is kept
rather than deleted: precedent carries, and a project that erases its wrong
turns looks like it always knew what it knows now.

---

## Contributing

1. Follow the class-based processor pattern; return dicts from analysis methods.
2. Preserve the non-filtering philosophy — do not discard data as noise.
3. Keep processors domain-isolated; cross-domain logic belongs in `symbolic/`.
4. Use numpy for numerical work.
5. Docstrings on public methods.
6. **Add your claim to `experiments/check_claims.py` and run it.** A claim that
   has not been run is not a finding.
7. If you falsify something, record it in the log and move the superseded file
   to `legacy/`. Do not delete it.

---

## Disclaimer

Experimental research prototype. Not a medical device, not a certified
environmental instrument. Its purpose is to explore and reframe what noise means.

## License

CC0-1.0 — see [LICENSE](LICENSE).

---

> "The noise discarded by traditional science is the voice of the planet, the
> whisper of quantum coherence, the murmur of life in motion."

— JinnZ2
