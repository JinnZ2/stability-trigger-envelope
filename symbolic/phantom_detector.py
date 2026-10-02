"""
Phantom Word Detector v0.1
Flags candidate phantom words by combining simple heuristics and embeddings.
Requires: spacy, sentence-transformers
"""

import spacy
from collections import Counter, defaultdict
from sentence_transformers import SentenceTransformer, util

_nlp = None
_embedder = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

# --- Core Functions ---

def extract_phrases(text, n=(1,3)):
    """Return n-grams (1-3 tokens) + named entities from text."""
    doc = _get_nlp()(text)
    phrases = []
    # n-grams
    tokens = [t.text for t in doc if not t.is_punct and not t.is_space]
    for size in range(n[0], n[1]+1):
        for i in range(len(tokens)-size+1):
            phrases.append(" ".join(tokens[i:i+size]))
    # entities
    phrases.extend([ent.text for ent in doc.ents])
    return phrases

def silence_signal(texts, phrase):
    """Heuristic: phrase appears often without definition markers."""
    definers = ["is", "means", "defined as", "refers to"]
    count, defined = 0, 0
    for t in texts:
        if phrase in t:
            count += 1
            if any(d in t.lower() for d in definers):
                defined += 1
    if count == 0:
        return 0.0
    return (count - defined) / count

def jargon_mismatch(phrase, domains):
    """High mismatch if phrase appears in many domains but embeddings diverge."""
    if len(domains) < 2:
        return 0.0
    domain_sents = []
    for d, texts in domains.items():
        joined = " ".join(texts)
        domain_sents.append(joined)
    embs = _get_embedder().encode(domain_sents, convert_to_tensor=True)
    sim = util.pytorch_cos_sim(embs, embs)
    avg_sim = sim.mean().item()
    return 1 - avg_sim  # higher = more mismatch

def detect_phantoms(corpus, min_score=0.4):
    """
    corpus: list of (text, domain_tag)
    Returns candidate phantom words with scores.
    """
    phrase_counter = Counter()
    examples = defaultdict(list)
    domain_map = defaultdict(lambda: defaultdict(list))

    # extract phrases
    for text, domain in corpus:
        phrases = extract_phrases(text)
        for p in phrases:
            phrase_counter[p] += 1
            if len(examples[p]) < 3:
                examples[p].append(text[:200])
            domain_map[p][domain].append(text)

    candidates = {}
    for phrase, cnt in phrase_counter.items():
        if cnt < 3:
            continue
        s_silence = silence_signal([t for t, _ in corpus], phrase)
        s_jargon = jargon_mismatch(phrase, domain_map[phrase])
        score = 0.6*s_silence + 0.4*s_jargon
        if score >= min_score:
            candidates[phrase] = {
                "score": round(score, 3),
                "silence": round(s_silence, 3),
                "jargon_mismatch": round(s_jargon, 3),
                "domains": list(domain_map[phrase].keys()),
                "examples": examples[phrase]
            }
    return dict(sorted(candidates.items(), key=lambda kv: kv[1]["score"], reverse=True))

# --- Example Run ---

if __name__ == "__main__":
    sample_corpus = [
        ("The anisotropy of the sample was measured but called bias in engineering docs.", "engineering"),
        ("In geology, anisotropy is a directional dependence of properties.", "geology"),
        ("The bias of the material seems unexplained in performance reports.", "policy"),
        ("Reciprocity is invoked in treaties but actual flows are asymmetric.", "policy"),
        ("Partnerships are described but often mask extraction of resources.", "economics"),
    ]

    results = detect_phantoms(sample_corpus)
    for k,v in results.items():
        print(k, v)
