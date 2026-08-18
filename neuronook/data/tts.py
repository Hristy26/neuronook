"""
Turns a Resource's text into spoken audio so "Read Aloud" can play it
back. Two backends, chosen automatically:

  - Offline (default, no setup needed): your OS's own built-in voice,
    via the pyttsx3 library. On Windows this is a SAPI5 voice that's
    already installed with Windows — no API key, no account, no
    network call, no cost. Sounds more "computerized" than a premium
    cloud voice, but it just works out of the box.
  - OpenAI cloud TTS (optional upgrade): used automatically instead,
    only if the user has set an OpenAI API key in Settings. More
    natural-sounding, but costs money per use and needs an account.

Like fetch.py, generating audio is manual/on-demand only — nothing
happens until the user clicks "Read Aloud." The OpenAI path is the
other place (besides fetch.py) where NeuroNook makes an outbound
network call, and only when that key is present; the offline path
never touches the network at all.

NeuroNook doesn't embed an audio player control for playback. Flet's
Audio control (like FilePicker) needs a native plugin that's only
bundled once the app is compiled with `flet build`/`flet pack` — it
won't render in the plain `python main.py` dev client. Rather than
risk repeating that exact bug, the generated audio file is handed off
to the operating system's own default player instead (see
NeuroNookApp._open_file_externally in neuronook/ui/app.py).
"""
from __future__ import annotations

from pathlib import Path

# OpenAI's current per-request character limit for /v1/audio/speech.
# The offline voice has no such hard limit, but the same cap keeps
# "Read Aloud" from trying to speak an entire book in one go either way.
MAX_INPUT_CHARS = 4096


class TTSError(Exception):
    """Raised for any failure that should be shown to the user as a
    plain-language message rather than a crash/traceback."""


def _validate_and_trim(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Pure validation/prep step, kept separate from the actual
    synthesis calls below so it can be unit-tested without needing a
    real connection or a working audio driver."""
    text = (text or "").strip()
    if not text:
        raise TTSError("There's no text to read yet.")
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def synthesize_speech_offline(text: str, out_path: Path) -> Path:
    """Generates speech using the OS's own built-in voice via pyttsx3.
    No API key, no network call, no cost. Saves a .wav file to out_path
    (creating its parent folder if needed) and returns out_path."""
    text = _validate_and_trim(text)

    try:
        import pyttsx3
    except ImportError as ex:
        raise TTSError(
            "The 'pyttsx3' package isn't installed. Run: pip install -r requirements.txt"
        ) from ex

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
    except Exception as ex:  # pyttsx3's failure modes vary by platform/driver — surface all of them the same way
        raise TTSError(f"Couldn't generate audio with your system's voice: {ex}") from ex

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise TTSError(
            "Audio generation finished but no audio file came out of it. This can happen if your "
            "system doesn't have a text-to-speech voice installed — try again, or add an OpenAI API "
            "key in Settings to use a cloud voice instead."
        )
    return out_path


def synthesize_speech_openai(
    text: str,
    api_key: str,
    out_path: Path,
    voice: str = "alloy",
    model: str = "tts-1",
    timeout: float = 60.0,
) -> Path:
    """Sends text to OpenAI's TTS API and saves the returned audio (mp3)
    to out_path, creating its parent folder if needed. Returns out_path
    on success; raises TTSError with a plain-language message on any
    failure (bad key, network error, bad response, etc.)."""
    text = _validate_and_trim(text)
    if not api_key or not api_key.strip():
        raise TTSError("No OpenAI API key set.")

    try:
        import requests
    except ImportError as ex:
        raise TTSError(
            "The 'requests' package isn't installed. Run: pip install -r requirements.txt"
        ) from ex

    try:
        response = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            },
            json={"model": model, "voice": voice, "input": text},
            timeout=timeout,
        )
    except requests.RequestException as ex:
        raise TTSError(f"Couldn't reach OpenAI: {ex}") from ex

    if response.status_code == 401:
        raise TTSError("OpenAI rejected that API key (401 Unauthorized) — double-check it in Settings.")
    if response.status_code == 429:
        raise TTSError("OpenAI rate-limited this request (429 Too Many Requests). Wait a moment and try again.")
    if response.status_code >= 400:
        raise TTSError(f"OpenAI returned an error ({response.status_code}): {response.text[:300]}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path


def synthesize_speech(text: str, base_path: Path, api_key: str | None = None, **openai_kwargs) -> Path:
    """The single entry point the UI calls. Uses the OpenAI cloud voice
    if an API key is supplied; otherwise falls back automatically to
    the free offline voice — no API key is ever required.

    base_path should have NO extension (e.g. ".../resource_12", not
    "resource_12.mp3") since the two backends produce different audio
    formats; the actual path written to (with the right extension) is
    returned.
    """
    if api_key and api_key.strip():
        return synthesize_speech_openai(text, api_key, base_path.with_suffix(".mp3"), **openai_kwargs)
    return synthesize_speech_offline(text, base_path.with_suffix(".wav"))
