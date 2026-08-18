"""
NeuroNook's own tiny settings file.

Remembers two things: which folder your data (the neuronook.db file)
lives in, and (optionally) an OpenAI API key used for the "Read Aloud"
text-to-speech feature. Both are stored outside the project folder — in
your home directory — so they survive moving, reinstalling, or updating
the app itself, and stay put until changed again from the Settings
screen.

Note this file is plain, unencrypted JSON (matching the rest of the
app's current "no security tier yet" state — see docs/DESIGN.md). If
you set an API key here, it sits on disk in plain text until the
password/encryption tier gets built.
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".neuronook"
CONFIG_FILE = CONFIG_DIR / "config.json"

# First-run default: a plain "NeuroNook" folder in your home directory
# (e.g. C:\Users\you\NeuroNook). Chosen over a relative "data/" folder
# because a relative path depends on which directory you happen to
# launch the app from — inconsistent between a desktop shortcut, a
# terminal, or a USB drive. This default is used until you pick your
# own folder in Settings.
DEFAULT_DATA_DIR = Path.home() / "NeuroNook"


def _load() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))


def get_data_dir() -> Path:
    saved = _load().get("data_dir")
    return Path(saved) if saved else DEFAULT_DATA_DIR


def set_data_dir(path: Path) -> None:
    cfg = _load()
    cfg["data_dir"] = str(path)
    _save(cfg)


def get_db_path() -> Path:
    return get_data_dir() / "neuronook.db"


def get_openai_api_key() -> str | None:
    key = _load().get("openai_api_key")
    return key or None


def set_openai_api_key(key: str | None) -> None:
    cfg = _load()
    if key:
        cfg["openai_api_key"] = key
    else:
        cfg.pop("openai_api_key", None)
    _save(cfg)
