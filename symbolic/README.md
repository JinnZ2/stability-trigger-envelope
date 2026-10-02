# Phantom Word Map — usage & purpose

`PHANTOM_WORD_MAP.json` catalogs sensed-but-unnamed concepts that repeatedly
exert semantic pull across domains. Use it to:

- Record candidate phantom words (labels, detection signals, example contexts).
- Link detectors (silence, metaphor drift, cross-domain word mismatches) to
  items that show gravitational pull.
- Surface "dark matter" in conversation and corpora so humans can name and test
  the concepts.

Current contents: 6 entries, `PW001`–`PW006`.

> **Note.** This file did not parse as JSON for the whole of its committed life
> — a trailing comma and a stray brace at the end of the array. The workflow
> below was documented but had never been run end to end. Fixed 2026-08-14; the
> unparseable version is preserved at `legacy/PHANTOM_WORD_MAP.v0.1.broken.json`.
> See claim C9 in [`docs/FALSIFICATION_LOG.md`](../docs/FALSIFICATION_LOG.md).

## Quick workflow

1. Run the detector pipeline on a corpus → produces candidate phrases + signals.
2. Inspect candidates; if persistent, create a `phantom_words` entry (code,
   label, description, examples).
3. Track `gravitational_pull` strength over time (low/med/high) and link to repo
   issues for prototype experiments.

## Principles

- Treat these entries as **living hypotheses** — update, split, or deprecate as
  more evidence arrives.
- Prioritize examples that show cross-domain resonance (the same pattern in at
  least two distinct fields or genres).
- Respect context: flagged items are prompts for human sense-making, not
  automated renaming.

---

## `phantom_detector.py`

### What it is designed to do

- Extract candidate phrases (n-grams + named entities).
- Score them by:
  - **Silence** — how often they appear without a nearby definition.
  - **Jargon mismatch** — how differently the phrase clusters across domains,
    via embeddings.
- Flag phantoms with a composite score ≥ 0.4, weighted `0.6 * silence +
  0.4 * jargon_mismatch`.

### Aspirational example output

```
anisotropy  {'score': 0.62, 'silence': 0.5, 'jargon_mismatch': 0.74, 'domains': ['engineering','geology']}
reciprocity {'score': 0.45, 'silence': 0.6, 'jargon_mismatch': 0.22, 'domains': ['policy','economics']}
```

> **This output has never been produced by this code.** Run against the sample
> corpus in the module's own `__main__` block, the detector returns three
> function words — `'of'`, `'but'`, `'in'` — and neither documented term
> surfaces. Three causes compound: both terms appear in only 2 documents and are
> cut by the `cnt < 3` frequency gate; both score silence 0.0 because the
> definer `"is"` substring-matches *inside the word `anisotropy` itself*; and
> there is no stopword filter, so what survives the gate is exactly the set of
> words that appear everywhere and mean nothing.
>
> Kept here rather than deleted because it is a reasonable statement of what the
> detector was meant to find, and it makes a good acceptance test for the fix.
> See claims C10, C11, C12 and open question U2 in
> [`docs/FALSIFICATION_LOG.md`](../docs/FALSIFICATION_LOG.md).

### Known defects

| defect | effect | claim |
|--------|--------|-------|
| `silence_signal` matches definers as raw substrings | `"is"` fires inside *analysis*, *noise*, *anisotropy*, *misread*; the 0.6-weighted term is pinned near zero on any English corpus | C10 |
| `jargon_mismatch` never reads its `phrase` argument | every phrase sharing a domain set gets an identical score; it measures the corpus partition, not the phrase | C11 |
| `sim.mean()` includes the self-similarity diagonal | score capped at `1 − 1/n`; in the documented 2-domain case it cannot exceed 0.5, contributing at most 0.2 toward a 0.4 threshold | C11 |
| `extract_phrases` emits n-grams per occurrence | one repetitive document can push a phrase past a gate meant to require corroboration across documents | C12 |
| no stopword filter | function words dominate the candidate list | C12 |

### Not yet implemented

`legacy/detector-pseudocode.v0.1.md` specified **four** signals — silence
(0.35), translation gap (0.25), metaphor overuse (0.2), jargon mismatch (0.2).
Only two shipped, reweighted to 0.6/0.4. The two dropped signals were never
refuted, only never built. See open question U2.

### Requirements

```bash
pip install -r ../requirements-nlp.txt
python -m spacy download en_core_web_sm
```

`sentence-transformers` fetches `all-MiniLM-L6-v2` from huggingface.co on first
use — a **runtime** network dependency, not an install-time one. It will fail at
the point of scoring in a restricted environment.
