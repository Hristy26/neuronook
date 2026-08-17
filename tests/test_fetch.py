"""
Unit tests for the pure (no-network) parts of neuronook/data/fetch.py.

The network-calling functions (fetch_page_text, fetch_youtube_transcript,
fetch_url_text) are intentionally NOT exercised here with a real network
call — that would make tests flaky/slow and dependent on the internet
being reachable. They're covered instead in tests/smoke_test_ui.py by
monkeypatching fetch.fetch_url_text, the same pattern already used for
config in that file.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from neuronook.data import fetch


# ---- is_youtube_url / extract_youtube_video_id -----------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://example.com/some-article", False),
        ("not a url at all", False),
        ("", False),
    ],
)
def test_is_youtube_url(url, expected):
    assert fetch.is_youtube_url(url) is expected


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/", None),
        ("https://example.com/watch?v=dQw4w9WgXcQ", None),
    ],
)
def test_extract_youtube_video_id(url, expected_id):
    assert fetch.extract_youtube_video_id(url) == expected_id


# ---- extract_text_from_html -------------------------------------------------


def test_extract_text_from_html_basic():
    html = """
    <html><head><title>OSHA Guidance</title>
    <style>.x { color: red; }</style>
    <script>console.log('nope');</script>
    </head>
    <body>
      <h1>Asbestos Rules</h1>
      <p>Workers must wear   proper respirators.</p>
      <p>See 29 CFR 1926.1101 for details.</p>
    </body></html>
    """
    result = fetch.extract_text_from_html(html)
    assert result.title == "OSHA Guidance"
    assert "Asbestos Rules" in result.text
    assert "Workers must wear proper respirators." in result.text
    assert "29 CFR 1926.1101" in result.text
    # script/style content must not leak into the extracted text
    assert "console.log" not in result.text
    assert "color: red" not in result.text


def test_extract_text_from_html_no_title():
    result = fetch.extract_text_from_html("<html><body><p>Just some text.</p></body></html>")
    assert result.title is None
    assert result.text == "Just some text."


def test_extract_text_from_html_empty():
    result = fetch.extract_text_from_html("<html><head><title></title></head><body></body></html>")
    assert result.title is None
    assert result.text == ""


# ---- format_transcript -------------------------------------------------------


def test_format_transcript_joins_segments():
    segments = [
        {"text": "Welcome back", "start": 0.0, "duration": 2.0},
        {"text": "to the channel.", "start": 2.0, "duration": 1.5},
        {"text": "  Today we cover   OSHA rules.  ", "start": 3.5, "duration": 3.0},
    ]
    assert fetch.format_transcript(segments) == "Welcome back to the channel. Today we cover OSHA rules."


def test_format_transcript_skips_empty_segments():
    segments = [{"text": ""}, {"text": "  "}, {"text": "actual words"}]
    assert fetch.format_transcript(segments) == "actual words"


def test_format_transcript_empty_list():
    assert fetch.format_transcript([]) == ""


# ---- fetch_url_text routing / error handling (no real network) -------------


def test_fetch_url_text_empty_url_raises():
    with pytest.raises(fetch.FetchError):
        fetch.fetch_url_text("")


def test_fetch_url_text_routes_youtube_urls(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch, "fetch_youtube_transcript", lambda url: calls.append(("yt", url)) or fetch.FetchResult(None, "t"))
    monkeypatch.setattr(fetch, "fetch_page_text", lambda url: calls.append(("page", url)) or fetch.FetchResult(None, "t"))
    fetch.fetch_url_text("https://youtu.be/abc123")
    assert calls == [("yt", "https://youtu.be/abc123")]


def test_fetch_url_text_routes_other_urls(monkeypatch):
    calls = []
    monkeypatch.setattr(fetch, "fetch_youtube_transcript", lambda url: calls.append(("yt", url)) or fetch.FetchResult(None, "t"))
    monkeypatch.setattr(fetch, "fetch_page_text", lambda url: calls.append(("page", url)) or fetch.FetchResult(None, "t"))
    fetch.fetch_url_text("https://example.com/article")
    assert calls == [("page", "https://example.com/article")]
