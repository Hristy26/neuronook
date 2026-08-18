"""Unit tests for the local (no-AI, no-network) extractive summarizer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neuronook.data import summarize


def test_empty_text_returns_empty():
    assert summarize.local_extractive_summary("") == ""
    assert summarize.local_extractive_summary("   ") == ""


def test_short_text_returned_unchanged():
    text = "Cats are great. Dogs are great too."
    # only 2 sentences, under the default max_sentences=3 -> nothing to trim
    assert summarize.local_extractive_summary(text, max_sentences=3) == text


def test_picks_the_on_topic_sentences():
    text = (
        "Cats are wonderful pets. Cats need regular vet checkups. "
        "The weather today is sunny. Many people love cats because cats are affectionate. "
        "I went to the store yesterday."
    )
    result = summarize.local_extractive_summary(text, max_sentences=2)
    # off-topic, one-off sentences (sharing no repeated keywords) should be dropped
    assert "weather" not in result
    assert "store" not in result
    # the frequently-repeated topic ("cats") should survive into the summary
    assert "cat" in result.lower()


def test_result_preserves_original_sentence_order():
    text = (
        "Alpha topic mentioned once. Beta appears here, beta appears there, beta everywhere. "
        "Gamma is mentioned only here. Beta beta beta dominates this sentence too."
    )
    result = summarize.local_extractive_summary(text, max_sentences=2)
    sentences = [s.strip() for s in result.split(".") if s.strip()]
    # both surviving sentences should appear in the same relative order as the source text
    positions = [text.index(s) for s in sentences]
    assert positions == sorted(positions)


def test_deterministic_for_same_input():
    text = "One two three. Four five six. Seven eight nine. Ten eleven twelve."
    first = summarize.local_extractive_summary(text, max_sentences=2)
    second = summarize.local_extractive_summary(text, max_sentences=2)
    assert first == second


def test_max_sentences_respected():
    text = " ".join(f"Sentence number {i} talks about widgets." for i in range(10))
    result = summarize.local_extractive_summary(text, max_sentences=3)
    # roughly 3 sentences worth of text should come back, not all 10
    assert result.count("Sentence number") <= 3
