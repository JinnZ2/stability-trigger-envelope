"""
Claim checker for Noise-as-Information-Sensor.

Every claim this repository makes in prose is restated here as an executable
test. Run it and the docs either survive or they don't.

    python experiments/check_claims.py

Verdicts
    HOLDS      the claim is true of the code as it stands
    FALSIFIED  the claim is contradicted by a reproducible run
    REVISED    the original claim was wrong, a narrower claim replaced it,
               and the narrower claim is what is tested here
    OPEN       not yet decidable without hardware, a corpus, or a decision

Findings are written up in docs/FALSIFICATION_LOG.md. This file is the
apparatus; that file is the notebook. When you change a processor, run this
first and record what moved.

Exit code is 0 when the run completes. A FALSIFIED verdict is a result, not a
build failure -- several are recorded here deliberately as known-open defects.
"""

import json
import os
import sys
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

import numpy as np

from dashboard.dashboard import NoiseDashboard
from software.electromagnetic.em_processor import EMFieldNoiseProcessor
from software.planetary.gaia_processor import GaiaSystemNoiseProcessor
from software.quantum.quantum_processor import QuantumNoiseProcessor
from symbolic.symbolic_intelligence import SymbolicIntelligenceEngine

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The demo payload from main.py. Several claims below hold only for this
# payload, which is itself one of the findings.
DEMO = {
    "molecular": [0.98, 0.95, 1.01, 0.97, 0.99],
    "chemical": [0.88, 0.85, 0.83, 0.87, 0.89],
    "motion": [0.67, 0.70, 0.72, 0.71, 0.69],
    "atmospheric": [0.61, 0.65, 0.63, 0.60, 0.62],
}

RESULTS = []


def record(claim_id, verdict, claim, evidence):
    """Record one claim outcome for the summary table."""
    RESULTS.append((claim_id, verdict, claim, evidence))
    print(f"\n[{claim_id}] {verdict}")
    print(f"  claim:    {claim}")
    for line in evidence.splitlines():
        print(f"  evidence: {line}" if line is evidence.splitlines()[0]
              else f"            {line}")


# --------------------------------------------------------------------------
# C1  Documentation paths
# --------------------------------------------------------------------------

def c1_documented_paths():
    """v0.1 READMEs sent readers to files that were never committed."""
    claimed = [
        ("dashboard/index.html", "README v0.1 setup step 3"),
        ("hardware/arduino_code", "README v0.1 setup step 1"),
        ("software/noise_engine.py", "software/README v0.1"),
        ("software/em_field_processor.py", "README v0.1 module table"),
        ("software/bio_processor.py", "software/README v0.1"),
        ("dashboard/noise_dashboard.py", "README v0.1 module table"),
    ]
    missing = [(p, src) for p, src in claimed if not os.path.exists(os.path.join(ROOT, p))]
    ev = "\n".join(f"{p} -- absent, cited by {src}" for p, src in missing) or "all paths resolve"
    record("C1", "FALSIFIED" if missing else "HOLDS",
           "Setup instructions and module tables point at real files.", ev)


# --------------------------------------------------------------------------
# C2  Quantum timescale analysis
# --------------------------------------------------------------------------

def c2_quantum_timescales():
    """README: 'Quantum fluctuation timing (picosecond analysis)'."""
    src = open(os.path.join(ROOT, "software/quantum/quantum_processor.py")).read()
    uses = src.count("quantum_timescales")
    ev = (f"self.quantum_timescales = {QuantumNoiseProcessor().quantum_timescales}\n"
          f"occurrences of the name in the module: {uses} (assignment only)\n"
          "no method reads it; the input carries no timestamps and no sample rate")
    record("C2", "FALSIFIED" if uses <= 1 else "HOLDS",
           "The quantum processor analyses fluctuations at fs/ps/ns timescales.", ev)


# --------------------------------------------------------------------------
# C3  Synthetic noise injection
# --------------------------------------------------------------------------

def c3_synthetic_injection():
    """Field Manual: 'Raw data is always preserved... non-filtering'."""
    q = QuantumNoiseProcessor()
    pure = np.diff(DEMO["molecular"])
    mixed = q.extract_fluctuations(DEMO["molecular"])
    injected = mixed - pure
    ratio = float(np.mean(np.abs(injected)) / np.mean(np.abs(pure)))
    again = q.extract_fluctuations(DEMO["molecular"])
    ev = (f"np.diff(molecular)        = {np.round(pure, 6).tolist()}\n"
          f"extract_fluctuations()    = {np.round(mixed, 6).tolist()}\n"
          f"synthetic component added = {np.round(injected, 6).tolist()}\n"
          f"injected magnitude is {ratio:.1%} of the real signal\n"
          f"rng is reseeded to 42 on every call, so the identical synthetic\n"
          f"vector is re-added each run (repeat call identical: {np.allclose(mixed, again)})")
    record("C3", "FALSIFIED",
           "The pipeline is non-filtering and preserves raw data unmodified.", ev)


# --------------------------------------------------------------------------
# C4  Electromagnetic layer on realistic input
# --------------------------------------------------------------------------

def c4_em_dead_on_normalised_data():
    """README: EM layer 'correlates solar and geomagnetic patterns'."""
    em = EMFieldNoiseProcessor()
    anomalies = em.detect_motion_anomalies(DEMO["motion"])
    out = em.analyze_em_field_noise(DEMO["motion"])
    ev = (f"anomalies detected on demo motion data: {anomalies} (n={len(anomalies)})\n"
          "correlate_solar/geomagnetic both return 0.0 unless n >= 3\n"
          "detect_cosmic_ray_signatures tests `a > 1.2` against readings the\n"
          "rest of the pipeline treats as normalised to roughly 0..1\n"
          f"result: {out}")
    dead = out == {"solar_field_effects": 0.0, "geomagnetic_influences": 0.0,
                   "cosmic_ray_impacts": 0}
    record("C4", "FALSIFIED" if dead else "HOLDS",
           "The EM layer produces solar/geomagnetic/cosmic-ray readings for the demo input.", ev)


# --------------------------------------------------------------------------
# C5  Symbolic resonance is a measure of signal quality
# --------------------------------------------------------------------------

def c5_resonance_tracks_sample_count():
    """CLAUDE.md: resonance_threshold 0.75 over a domain's outputs.

    Original hypothesis was that large-magnitude input would dominate the
    average. That was wrong -- entropy goes negative above 1.0. The surviving
    claim is narrower and worse: entropy is extensive, so the verdict tracks
    how long you recorded for.
    """
    q, s = QuantumNoiseProcessor(), SymbolicIntelligenceEngine()
    base = np.sin(np.linspace(0, 4 * np.pi, 1000)) * 0.1 + 0.6
    rows = []
    for stride in (200, 100, 50, 20, 10):
        d = list(base[::stride])
        r = q.analyze_quantum_noise(d)
        rows.append(f"n={len(d):4d}  entropy={r['non_local_correlations']:8.3f}  "
                    f"verdict={s._detect_resonance(r)}")
    demo_r = q.analyze_quantum_noise(DEMO["molecular"])
    rows.append(f"main.py demo (n=5, values near 1.0): entropy="
                f"{demo_r['non_local_correlations']:.3f} -> {s._detect_resonance(demo_r)}")
    ev = ("one identical sine phenomenon, resampled:\n" + "\n".join(rows) +
          "\nnon_local_correlations is -sum(x*log|x|), which grows with sample count.\n"
          "It is averaged against a bounded [0,1] coherence term and a fixed 0.75\n"
          "threshold, so beyond a handful of samples the quantum domain saturates.\n"
          "The demo escapes only because its values sit near 1.0, where x*log(x) ~ 0.")
    record("C5", "REVISED",
           "Resonance detection measures coherence, not recording length.", ev)


# --------------------------------------------------------------------------
# C6  Averaging across incommensurable units
# --------------------------------------------------------------------------

def c6_unit_mixing():
    """_detect_resonance averages whatever scalars a domain happens to return."""
    g = GaiaSystemNoiseProcessor()
    r = g.analyze_gaia_noise(DEMO["atmospheric"])
    scalars = [float(v) for v in r.values()]
    ev = (f"gaia output: {r}\n"
          f"coerced to scalars and averaged: {scalars} -> mean {np.mean(scalars):.4f}\n"
          "booleans become 1.0/0.0 and are averaged with a Pearson r in [-1, 1];\n"
          "the quantum domain adds an unbounded entropy term to the same mean.\n"
          "The 0.75 threshold is therefore applied to a quantity with no unit.")
    record("C6", "FALSIFIED",
           "The 0.75 resonance threshold compares like with like across domains.", ev)


# --------------------------------------------------------------------------
# C7  Robustness of the dashboard to input length
# --------------------------------------------------------------------------

def c7_input_length():
    """No documented minimum sample count."""
    d = NoiseDashboard()
    rows = []
    ok = True
    for n in (2, 3, 4, 5):
        payload = {k: [v] * n for k, v in
                   (("molecular", 0.9), ("chemical", 0.8), ("motion", 0.7), ("atmospheric", 0.6))}
        try:
            d.analyze_all(payload)
            rows.append(f"n={n}: completes")
        except Exception as e:
            ok = False
            rows.append(f"n={n}: raises {type(e).__name__}")
    neg = {"molecular": [-0.9, -0.5, -0.7, -0.6, -0.8], "chemical": [0.8] * 5,
           "motion": [0.7] * 5, "atmospheric": [0.6] * 5}
    res = d.analyze_all(neg)
    rows.append(f"negative molecular input: earth_system_feedback="
                f"{res['planetary']['earth_system_feedback']} (silent nan, no warning)")
    ev = ("\n".join(rows) +
          "\ngaia and biological index fixed-length baselines (4 and 3 samples)\n"
          "without checking the input is long enough.")
    record("C7", "FALSIFIED" if not ok else "HOLDS",
           "The dashboard accepts any sensor series the Arduino sketch can produce.", ev)


# --------------------------------------------------------------------------
# C8  Dict-based pipeline is serialisable
# --------------------------------------------------------------------------

def c8_serialisable():
    """CLAUDE.md: 'Dict-based data flow between components'."""
    d = NoiseDashboard()
    res = d.analyze_all(DEMO)
    try:
        json.dumps(res)
        record("C8", "HOLDS", "Processor output can be logged or transported as JSON.",
               "json.dumps succeeds")
        return
    except TypeError as e:
        offenders = [f"{k}.{kk}: {type(vv).__name__}"
                     for k, v in res.items() for kk, vv in v.items()
                     if type(vv).__module__ == "numpy"]
        ev = (f"json.dumps raises TypeError: {e}\n"
              "numpy scalars leak out of the processors instead of Python types:\n" +
              "\n".join("  " + o for o in offenders))
        record("C8", "FALSIFIED",
               "Processor output can be logged or transported as JSON.", ev)


# --------------------------------------------------------------------------
# C9  Phantom word map is loadable data
# --------------------------------------------------------------------------

def c9_phantom_map():
    """symbolic/README: 'Run the detector pipeline... create a phantom_words entry'."""
    path = os.path.join(ROOT, "symbolic/PHANTOM_WORD_MAP.json")
    try:
        data = json.load(open(path))
    except json.JSONDecodeError as e:
        record("C9", "FALSIFIED", "PHANTOM_WORD_MAP.json is machine-readable.",
               f"json.load raises JSONDecodeError: {e}")
        return
    entries = data["phantom_words"]
    keys = set().union(*(set(e) for e in entries))
    ragged = {e["code"]: sorted(keys - set(e)) for e in entries if keys - set(e)}
    ev = (f"parses; {len(entries)} entries: {[e['code'] for e in entries]}\n"
          f"schema consistent across entries: {not ragged}\n"
          f"gravitational_pull.strength values: "
          f"{sorted({e['gravitational_pull']['strength'] for e in entries})}")
    record("C9", "HOLDS", "PHANTOM_WORD_MAP.json is machine-readable.", ev)


# --------------------------------------------------------------------------
# C10  silence_signal detects definitions
# --------------------------------------------------------------------------

def c10_silence_signal():
    """symbolic/README: 'Silence: how often they appear without a nearby definition'."""
    definers = ["is", "means", "defined as", "refers to"]
    probes = ["This analysis is noisy.", "The noise was measured.",
              "Anisotropy appeared in the sample.", "A misread signal."]
    hits = [(t, [d for d in definers if d in t.lower()]) for t in probes]
    false_pos = [(t, h) for t, h in hits if h and " is " not in t]
    ev = "\n".join(f"{t!r} -> scored as DEFINED via {h}" for t, h in hits if h)
    ev += ("\nthe test is a substring match, so 'is' fires inside analysis, noise,\n"
           "Anisotropy and misread. Any corpus in this domain is scored as\n"
           "fully defined, driving silence_signal toward 0 and suppressing every candidate.")
    record("C10", "FALSIFIED" if false_pos else "HOLDS",
           "silence_signal measures whether a phrase appears near a definition.", ev)


# --------------------------------------------------------------------------
# C11  jargon_mismatch is per-phrase
# --------------------------------------------------------------------------

def c11_jargon_mismatch():
    """symbolic/README: 'how differently the phrase clusters across domains'."""
    import ast
    src = open(os.path.join(ROOT, "symbolic/phantom_detector.py")).read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "jargon_mismatch")
    dumped = ast.dump(fn)
    phrase_used = "id='phrase'" in dumped

    rows = []
    for n in (2, 3, 4):
        sim = np.full((n, n), 0.0)
        np.fill_diagonal(sim, 1.0)
        rows.append(f"{n} domains, embeddings maximally unrelated (off-diagonal 0.0): "
                    f"reported mismatch {1 - sim.mean():.3f}, ceiling {1 - 1 / n:.3f}")
    ev = (f"the `phrase` parameter is never read in the function body: {not phrase_used}\n"
          "it embeds each domain's whole concatenated text, so every phrase sharing\n"
          "a domain set receives an identical score\n"
          "sim.mean() spans the full matrix including the self-similarity diagonal:\n" +
          "\n".join("  " + r for r in rows) +
          "\nfor realistic non-negative sentence similarities the score is capped at\n"
          "1 - 1/n, so with the documented 2-domain case it cannot exceed 0.500 and\n"
          "contributes at most 0.200 toward the 0.4 flagging threshold.")
    record("C11", "FALSIFIED",
           "jargon_mismatch scores how a given phrase diverges across domains.", ev)


# --------------------------------------------------------------------------
# C12  Detector runs end to end
# --------------------------------------------------------------------------

SAMPLE_CORPUS = [
    ("The anisotropy of the sample was measured but called bias in engineering docs.", "engineering"),
    ("In geology, anisotropy is a directional dependence of properties.", "geology"),
    ("The bias of the material seems unexplained in performance reports.", "policy"),
    ("Reciprocity is invoked in treaties but actual flows are asymmetric.", "policy"),
    ("Partnerships are described but often mask extraction of resources.", "economics"),
]


class _OrthogonalEmbedder:
    """Stand-in for all-MiniLM-L6-v2 when the real weights cannot be fetched.

    Returns mutually orthogonal unit vectors, i.e. the most divergent embedding
    result physically possible. Any candidate that fails to surface under this
    embedder would also fail under the real one, so a negative result here is
    a valid falsification; a positive result would not be.
    """

    def encode(self, sentences, convert_to_tensor=True):
        import torch
        return torch.eye(len(sentences))


def c12_detector_runs():
    """symbolic/README lists anisotropy 0.62 and reciprocity 0.45 as example output."""
    try:
        import spacy  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError as e:
        record("C12", "OPEN",
               "phantom_detector.py reproduces the example output in symbolic/README.md.",
               f"optional NLP stack not installed ({e.name}).\n"
               "install with: pip install -r requirements-nlp.txt\n"
               "             python -m spacy download en_core_web_sm")
        return

    import symbolic.phantom_detector as det
    try:
        det._get_embedder()
        mode = "real all-MiniLM-L6-v2 embedder"
    except Exception as e:
        det._embedder = _OrthogonalEmbedder()
        mode = (f"orthogonal stub embedder -- real weights unreachable "
                f"({type(e).__name__}); this is the best case for jargon_mismatch")

    try:
        out = det.detect_phantoms(SAMPLE_CORPUS)
    except Exception as e:
        record("C12", "FALSIFIED",
               "phantom_detector.py reproduces the example output in symbolic/README.md.",
               f"detect_phantoms raised {type(e).__name__}: {e}\nembedder mode: {mode}")
        return

    texts = [t for t, _ in SAMPLE_CORPUS]
    documented = {"anisotropy": 0.62, "reciprocity": 0.45}
    surfaced = {k: k in out for k in documented}
    ev = (f"embedder mode: {mode}\n"
          f"candidates returned: {len(out)}\n" +
          "\n".join(f"  {k!r} score={v['score']} silence={v['silence']} "
                    f"jargon={v['jargon_mismatch']} domains={v['domains']}"
                    for k, v in list(out.items())[:8]) +
          f"\ndocumented example terms surfaced: {surfaced}\n" +
          "\n".join(f"  silence_signal({t!r}) = {det.silence_signal(texts, t)}"
                    for t in documented) +
          "\nboth documented terms occur in only 2 documents and are dropped by the\n"
          "`cnt < 3` minimum-frequency gate; both also score silence 0.0 because\n"
          "'is' matches as a substring inside 'anisotropy' itself.\n"
          "there is no stopword filter, so what survives the gate are function words.\n"
          f"extract_phrases('noise noise noise') -> {det.extract_phrases('noise noise noise')}\n"
          "  (n-grams are emitted per occurrence, so one repetitive document alone\n"
          "   can push a phrase past the 3-occurrence gate)")
    ok = all(surfaced.values())
    record("C12", "HOLDS" if ok else "FALSIFIED",
           "phantom_detector.py reproduces the example output in symbolic/README.md.", ev)


CHECKS = [c1_documented_paths, c2_quantum_timescales, c3_synthetic_injection,
          c4_em_dead_on_normalised_data, c5_resonance_tracks_sample_count,
          c6_unit_mixing, c7_input_length, c8_serialisable, c9_phantom_map,
          c10_silence_signal, c11_jargon_mismatch, c12_detector_runs]


# ==========================================================================
# NC_*  tools/ -- the four instruments added under DISPATCH NOISE-1
# ==========================================================================
#
# Added as new rows under the repository's own contributing rule: a claim that
# has not been run is not a finding. Every C-row above is untouched.
#
# Ids are shared with tools/CLAIM_TABLE.md so one claim carries one id in both
# files. The five below are the ones executable here; the table holds the
# rest under a TABLE STATUS and says why each is not a harness row. The
# table's id count is READ at summary time, not stored here (NC_025).
#
# These checks import from tools/ only. They do not read, call or depend on
# any processor, the dashboard or the symbolic engine, so an NC row cannot
# move because a C row moved.

sys.path.insert(0, os.path.join(ROOT, "tools"))


def nc002_denominator_sets_the_verdict():
    """tools/channel_loss.py: with the counts unread, the verdict is a
    property of the assumed denominator rather than of the report."""
    import channel_loss as cl

    rows = cl.denominator_sweep(0.90, 0.32, [10, 25, 50, 100, 250])
    lines = []
    for row in rows:
        r = row["result"]
        lines.append(f"  n={row['n']:4d}  realized {row['realized_direct']:.2f}/"
                     f"{row['realized_mediated']:.2f}  point loss "
                     f"{r['loss_point']:.4f}  -> {r['kind']}")
    kinds = {row["result"]["kind"] for row in rows}
    small = [r for r in rows if r["n"] == 10][0]
    big = [r for r in rows if r["n"] == 250][0]
    ev = ("the same two published percentages (>= 90% direct, as low as 32%\n"
          "mediated), read at five assumed denominators:\n" + "\n".join(lines) +
          f"\nverdict at n=10:  {small['result']['kind']} "
          f"(intervals overlap: {small['result']['intervals_overlap']})\n"
          f"verdict at n=250: {big['result']['kind']} "
          f"(intervals overlap: {big['result']['intervals_overlap']})\n"
          "nothing about the report changed across those rows. The real counts\n"
          "are UNREAD -- the publisher hosts are unreachable from this\n"
          "environment -- so the denominator is assumed, and the verdict is a\n"
          "property of that assumption.\n"
          f"at the small end the POINT moves too: reconstruction error "
          f"{small['reconstruction_error']:.4f} at n=10 against "
          f"{big['reconstruction_error']:.4f} at n=250, because an integer\n"
          "count over a small denominator cannot represent an arbitrary\n"
          "percentage.")
    record("NC_002", "HOLDS" if len(kinds) > 1 else "FALSIFIED",
           "With the counts unread, the CHANNEL_LOSS verdict is set by the "
           "assumed denominator.", ev)


def nc006_assigned_path_is_the_sharper_bound():
    """tools/rerun_find_rate.py: the headline 1-of-11 is not the tightest
    number the same eleven runs support."""
    import rerun_find_rate as rf
    from typed import clopper_pearson, fmt_interval

    res = rf.score(rf.fixture_runs())
    headline = res["interval"]
    assigned = clopper_pearson(res["assigned_path_finds"], res["runs"])
    ev = (f"reported campaign: {res['runs']} runs, {res['finds']} find, "
          f"{res['misses']} misses\n"
          f"headline (any path):   {fmt_interval(headline)}\n"
          f"assigned path only:    {fmt_interval(assigned)}\n"
          f"verdict kind: {res['kind']}\n"
          f"side-path share of finds: {res['side_path_share']}\n"
          "the one find came off a SIDE path, so the route the campaign was\n"
          "designed around found nothing in eleven runs. Its upper bound is\n"
          f"{assigned['hi']:.4f} against the headline's {headline['hi']:.4f}.\n"
          "this bounds the PROCESS, not the result: a rarely-reached real\n"
          "result and a once-reached artifact produce the same 1/11.")
    record("NC_006", "HOLDS" if assigned["hi"] < headline["hi"] else "FALSIFIED",
           "The assigned-path bound is tighter than the headline bound on the "
           "same eleven runs.", ev)


def nc009_residual_is_never_fitted():
    """tools/residual_partition.py: no candidate is scaled or subtracted."""
    import residual_partition as rp

    observed, declared, _ = rp.fixture_f1()
    bare = rp.partition(observed, declared, [])
    loaded = rp.partition(observed, declared, [
        rp.candidate("a", "SIGN_POSITIVE", basis="CONSTRUCTED"),
        rp.candidate("b", "SIGN_NEGATIVE", basis="CONSTRUCTED"),
        rp.candidate("c", "MONOTONE_UP", basis="CONSTRUCTED")])
    identical = bare["residual_series"] == loaded["residual_series"]

    refused = []
    for field in rp.FORBIDDEN_CANDIDATE_FIELDS:
        try:
            rp._reject_magnitude(**{field: 1.0})
            refused.append(f"{field}=ACCEPTED")
        except ValueError:
            refused.append(f"{field}=refused")

    ev = (f"residual with no candidates:    {bare['residual_series']}\n"
          f"residual with three candidates: {loaded['residual_series']}\n"
          f"identical: {identical}\n"
          f"consistent candidates: {loaded['consistent']} of three offered, "
          "ranked by nothing\n"
          "magnitude fields at the constructor: " + ", ".join(refused) + "\n"
          "a candidate carries a SIGN or a SHAPE and nothing else. A fitted\n"
          "magnitude makes every candidate consistent, which is how an\n"
          "unexplained remainder becomes a confirmed mechanism with no\n"
          "measurement taken.")
    ok = identical and all(r.endswith("refused") for r in refused)
    record("NC_009", "HOLDS" if ok else "FALSIFIED",
           "No candidate is scaled or subtracted; the residual does not move "
           "with the candidate list.", ev)


def nc013_lead_is_modulo_the_forcing_period():
    """tools/two_body_source.py: a periodic correlation fixes the lead only
    within a period. Since 2026-09-27 phase_lead() is DIAGNOSTIC and decides
    nothing; the property is still a property of the operation."""
    import two_body_source as tb

    n, p, rate = 240, 40.0, 100.0
    ref = tb._sine(n, p, 1.0)
    zero = tb.phase_lead(tb._sine(n, p, 1.0, phase_samples=0.0), ref, rate, p / rate)
    onep = tb.phase_lead(tb._sine(n, p, 1.0, phase_samples=p), ref, rate, p / rate)
    lag4 = tb.phase_lead(tb._sine(n, p, 1.0, phase_samples=4.0), ref, rate, p / rate)
    half = tb.phase_lead(tb._sine(n, p, 1.0, phase_samples=p / 2.0), ref, rate, p / rate)

    a, b, per = tb.fixture_f1()
    f1 = tb.source(a, b, per)
    f1_phase = tb.phase_lead(a["series"], b["series"], a["sample_rate_hz"], per)

    ev = (f"forcing period {p:.0f} samples at {rate:.0f} Hz\n"
          f"lead of zero periods: {zero['lead_s']:+.4f} s\n"
          f"lead of one period:   {onep['lead_s']:+.4f} s   <- indistinguishable\n"
          f"constructed LAG of 4 samples: raw search returns "
          f"{lag4['raw_lead_samples']:+.0f}, wrapped to "
          f"{lag4['lead_samples']:+.0f}\n"
          "  the raw branch is chosen by where the search lands. When this row\n"
          "  was first run the SIGN of that lead was what the agreement check\n"
          "  read, so the branch was deciding a verdict. Leads are reported in\n"
          "  the principal branch (-P/2, +P/2] and, from 2026-09-27, the phase\n"
          "  is read by NO verdict: source() decides on amplitude checked\n"
          "  against ONSET timing (NC_022) and its return carries no phase.\n"
          f"near half a period: sign_determined={half['sign_determined']} "
          "-- the sign is withheld, not reported\n"
          f"fixture F1 (A bursts, B quiet): {f1['kind']}, decided by "
          f"{f1['decided_by']}; phase diagnostic on the same traces: "
          f"{f1_phase['kind']}\n"
          "  a phase lead against a channel that does not move is a property\n"
          "  of its residual variation (NC_012).")
    ok = (abs(zero["lead_s"] - onep["lead_s"]) < 1e-9
          and round(lag4["raw_lead_samples"]) == 36
          and round(lag4["lead_samples"]) == -4
          and half["sign_determined"] is False
          and f1_phase["kind"] == "NOT_EVALUABLE"
          and "phase" not in f1)
    record("NC_013", "HOLDS" if ok else "FALSIFIED",
           "A phase lead is fixed only modulo the forcing period, and is not "
           "measurable at all against a channel that does not move.", ev)


def nc022_onset_reads_the_lead_phase_cannot():
    """tools/two_body_source.py F4: A leads by exactly one forcing period.
    Onset timing classifies; the phase diagnostic on the same traces reads a
    lead of zero."""
    import two_body_source as tb

    a, b, per = tb.fixture_f4()
    r4 = tb.source(a, b, per)
    ph = tb.phase_lead(a["series"], b["series"], a["sample_rate_hz"], per)
    rate = a["sample_rate_hz"]
    lead_s = r4.get("onset_lead_s")
    onset_samples = (lead_s or 0.0) * rate
    lead_txt = "none" if lead_s is None else f"{onset_samples:+.1f} samples ({lead_s:+.3f} s)"
    ph_txt = (f"{ph['lead_samples']:+.1f} samples in the principal branch"
              if ph["kind"] == "VALUE" else f"{ph['kind']}: {ph.get('reason', '')}")
    ev = (f"F4: body A bursts at sample 100, body B at sample 140, one forcing\n"
          f"period ({per * rate:.0f} samples) later. Amplitude ratio "
          f"{r4.get('amplitude_ratio')}.\n"
          f"verdict: {r4['kind']}   decided by: {r4.get('decided_by')}\n"
          f"onset lead of A over B: {lead_txt}, onset agrees: {r4.get('onset_agrees')}\n"
          f"phase DIAGNOSTIC on the same traces: {ph_txt}\n"
          "  one period and zero are the same peak to a periodic correlation,\n"
          "  so phase reads A as not leading. Onset reads the period. The\n"
          "  worked instance predicts a lead of about one period, which is\n"
          "  exactly the value a phase reading cannot resolve.")
    ok = (r4["kind"] == "SOURCE_A_MODE"
          and r4.get("onset_agrees") is True
          and lead_s is not None
          and abs(onset_samples - per * rate) <= 2
          and ph["kind"] == "VALUE"
          and abs(ph["lead_samples"]) <= 2)
    record("NC_022", "HOLDS" if ok else "FALSIFIED",
           "With A leading by exactly one forcing period, onset timing "
           "classifies the source and the phase diagnostic reads zero.", ev)


CHECKS = CHECKS + [nc002_denominator_sets_the_verdict,
                   nc006_assigned_path_is_the_sharper_bound,
                   nc009_residual_is_never_fitted,
                   nc013_lead_is_modulo_the_forcing_period,
                   nc022_onset_reads_the_lead_phase_cannot]


def _nc_ids_in_table():
    """Every NC_* id declared in tools/CLAIM_TABLE.md, or None if unreadable.
    The denominator for the NC tally below is read from the table, not typed
    here, so the two cannot drift apart silently."""
    import re
    path = os.path.join(ROOT, "tools", "CLAIM_TABLE.md")
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError:
        return None
    return sorted(set(re.findall(r"^\| (NC_\d{3}) \|", text, re.M)))


def _tally(rows):
    out = {}
    for _, verdict, _, _ in rows:
        out[verdict] = out.get(verdict, 0) + 1
    return "  ".join(f"{k}={v}" for k, v in sorted(out.items()))


def main():
    print("=" * 74)
    print("CLAIM CHECK -- Noise-as-Information-Sensor")
    print("=" * 74)
    for check in CHECKS:
        check()

    print("\n" + "=" * 74)
    print("SUMMARY")
    print("=" * 74)
    for cid, verdict, claim, _ in RESULTS:
        print(f"  {cid:6s} {verdict:10s} {claim[:52]}")

    # Two series, two tallies, two denominators. A single line would read as
    # movement when a row is added to one series and none moved in the other.
    c_rows = [r for r in RESULTS if r[0].startswith("C")]
    nc_rows = [r for r in RESULTS if r[0].startswith("NC_")]
    table_ids = _nc_ids_in_table()
    print(f"\n  C  rows  {_tally(c_rows)}"
          f"   ({len(c_rows)} of {len(c_rows)} C ids carry a harness verdict)")
    if table_ids is None:
        nc_denominator = "tools/CLAIM_TABLE.md unreadable; denominator unstated"
    else:
        harness_ids = {r[0] for r in nc_rows}
        table_only = [i for i in table_ids if i not in harness_ids]
        not_in_table = sorted(harness_ids - set(table_ids))
        nc_denominator = (f"{len(nc_rows)} of {len(table_ids)} NC ids in "
                          f"tools/CLAIM_TABLE.md carry a harness verdict; the "
                          f"other {len(table_only)} carry a TABLE status "
                          f"(SUPPORTED / UNVERIFIED / CORRECTED / CLOSED), "
                          f"which is not a verdict here")
        if not_in_table:
            nc_denominator += f"; harness ids missing from the table: {not_in_table}"
    print(f"  NC rows  {_tally(nc_rows)}   ({nc_denominator})")
    print(f"  all      {_tally(RESULTS)}   (both series; read the two lines "
          f"above, not this one)")
    print("\n  Write-up: docs/FALSIFICATION_LOG.md (C rows); tools/CLAIM_TABLE.md (NC rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
