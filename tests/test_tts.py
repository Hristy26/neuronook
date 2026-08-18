"""
Unit tests for the pure (no-network, no-audio-driver) validation logic
and backend-routing in neuronook/data/tts.py. The actual synthesis
calls (synthesize_speech_offline's pyttsx3 call, synthesize_speech_openai's
requests.post) are intentionally NOT exercised here — that's covered in
tests/smoke_test_ui.py by monkeypatching tts.synthesize_speech as a
whole, the same pattern already used for fetch.fetch_url_text there.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from neuronook.data import tts


def test_validate_and_trim_empty_text_raises():
    with pytest.raises(tts.TTSError, match="no text"):
        tts._validate_and_trim("")


def test_validate_and_trim_whitespace_only_text_raises():
    with pytest.raises(tts.TTSError, match="no text"):
        tts._validate_and_trim("   \n  ")


def test_validate_and_trim_passes_through_short_text():
    assert tts._validate_and_trim("Hello world") == "Hello world"


def test_validate_and_trim_strips_whitespace():
    assert tts._validate_and_trim("  Hello world  \n") == "Hello world"


def test_validate_and_trim_truncates_long_text():
    long_text = "word " * 2000  # way over MAX_INPUT_CHARS
    result = tts._validate_and_trim(long_text, max_chars=100)
    assert len(result) == 100


def test_synthesize_speech_openai_raises_before_any_network_call_for_empty_text(tmp_path):
    with pytest.raises(tts.TTSError):
        tts.synthesize_speech_openai("", "sk-fake-key", tmp_path / "out.mp3")
    assert not (tmp_path / "out.mp3").exists()


def test_synthesize_speech_openai_raises_before_any_network_call_for_missing_key(tmp_path):
    with pytest.raises(tts.TTSError, match="API key"):
        tts.synthesize_speech_openai("Hello world", "", tmp_path / "out.mp3")
    assert not (tmp_path / "out.mp3").exists()


def test_synthesize_speech_offline_raises_before_touching_pyttsx3_for_empty_text(tmp_path):
    with pytest.raises(tts.TTSError, match="no text"):
        tts.synthesize_speech_offline("", tmp_path / "out.wav")
    assert not (tmp_path / "out.wav").exists()


# ---- synthesize_speech(): routes to the right backend, no key required -----


def test_synthesize_speech_uses_offline_backend_when_no_key(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        tts, "synthesize_speech_offline", lambda text, out_path: calls.append(("offline", text, out_path)) or out_path
    )
    monkeypatch.setattr(
        tts,
        "synthesize_speech_openai",
        lambda *a, **k: calls.append(("openai", a, k)) or (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    base = tmp_path / "resource_1"
    tts.synthesize_speech("Hello", base, api_key=None)
    assert len(calls) == 1
    assert calls[0][0] == "offline"
    assert calls[0][2] == base.with_suffix(".wav")


def test_synthesize_speech_uses_offline_backend_when_key_is_blank(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(tts, "synthesize_speech_offline", lambda text, out_path: calls.append("offline") or out_path)
    monkeypatch.setattr(
        tts,
        "synthesize_speech_openai",
        lambda *a, **k: calls.append("openai") or (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    tts.synthesize_speech("Hello", tmp_path / "resource_1", api_key="   ")
    assert calls == ["offline"]


def test_synthesize_speech_uses_openai_backend_when_key_present(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        tts,
        "synthesize_speech_offline",
        lambda *a, **k: calls.append("offline") or (_ for _ in ()).throw(AssertionError("should not be called")),
    )
    monkeypatch.setattr(
        tts,
        "synthesize_speech_openai",
        lambda text, api_key, out_path, **k: calls.append(("openai", text, api_key, out_path)) or out_path,
    )
    base = tmp_path / "resource_1"
    tts.synthesize_speech("Hello", base, api_key="sk-real-key")
    assert len(calls) == 1
    assert calls[0][0] == "openai"
    assert calls[0][2] == "sk-real-key"
    assert calls[0][3] == base.with_suffix(".mp3")
