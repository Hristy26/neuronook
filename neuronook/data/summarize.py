"""
Turns a Resource's full extracted text into something shorter to skim.

Two summarization paths exist in NeuroNook, and only one of them lives
in this file:

  - local_extractive_summary() below: a small, fully local, no-AI
    algorithm. It runs automatically and instantly, entirely on your
    machine, with no network call — matching the "no AI baked into the
    core app" principle in docs/DESIGN.md.
  - The "AI Summary" field on a Resource: a manual copy/paste bridge —
    you copy the extracted text, paste it into your own external AI
    chat, and paste the summary it gives back into NeuroNook. That's
    just a text field in the UI layer (neuronook/ui/app.py); there's
    no function for it here, since NeuroNook never talks to an AI
    service on your behalf.
"""
from __future__ import annotations

import re

# A small, common-word list to ignore when scoring sentences — these
# appear everywhere regardless of topic, so they're not useful signals
# for "what is this text actually about."
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "so", "of", "to", "in", "on", "at",
    "by", "for", "with", "about", "as", "is", "are", "was", "were", "be", "been", "being",
    "it", "its", "this", "that", "these", "those", "from", "into", "than", "too", "very",
    "can", "will", "just", "not", "no", "do", "does", "did", "has", "have", "had", "he",
    "she", "they", "we", "you", "i", "your", "their", "our", "his", "her", "them", "which",
    "who", "whom", "what", "when", "where", "why", "how", "there", "here", "all", "any",
    "also", "more", "most", "other", "some", "such", "only", "over", "under", "again",
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z']+")


def local_extractive_summary(text: str, max_sentences: int = 3) -> str:
    """A small, fully local, no-AI/no-network extractive summarizer.

    Scores each sentence by how often its "meaningful" (non-stopword)
    words show up across the whole text — words that repeat a lot are
    assumed to matter more to what the text is about — then keeps the
    top-scoring sentences in their ORIGINAL order, so the result still
    reads top-to-bottom instead of as a jumbled list of highlights.

    This is intentionally simple: no ML model, no embeddings, nothing
    to download or run over a network. It's a quick skim aid, not a
    substitute for a real AI-written summary (see the AI Summary field
    for that, via your own external AI chat).
    """
    text = (text or "").strip()
    if not text:
        return ""

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text

    word_counts: dict[str, int] = {}
    for word in _WORD_RE.findall(text.lower()):
        if len(word) < 3 or word in _STOPWORDS:
            continue
        word_counts[word] = word_counts.get(word, 0) + 1

    def score(sentence: str) -> float:
        words = [w for w in _WORD_RE.findall(sentence.lower()) if len(w) >= 3 and w not in _STOPWORDS]
        if not words:
            return 0.0
        return sum(word_counts.get(w, 0) for w in words) / len(words)

    ranked_by_score = sorted(range(len(sentences)), key=lambda i: score(sentences[i]), reverse=True)
    top_indices = sorted(ranked_by_score[:max_sentences])  # restore original reading order
    return " ".join(sentences[i] for i in top_indices)
