"""
Turns a Resource's saved link into searchable text.

This is deliberately **manual, on-demand only** — the user clicks
"Fetch Text" on a Resource, and only then does anything leave the
machine. Nothing here runs automatically in the background; that
matches the "app never calls out to the internet silently" principle
in docs/DESIGN.md, the same way the AI Summarize step is a manual
bridge rather than something the app does on its own.

Two kinds of link are handled:
  - A YouTube video URL -> pull its existing captions/transcript
    (whatever YouTube already provides — no local transcription).
  - Anything else -> download the page and pull out its visible text.

The network-calling functions (fetch_page_text, fetch_youtube_transcript,
fetch_url_text) are kept separate from the pure parsing functions
(extract_text_from_html, format_transcript) so the parsing logic can be
unit-tested without needing a real network connection.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse


class FetchError(Exception):
    """Raised for any failure that should be shown to the user as a
    plain-language message rather than a crash/traceback."""


@dataclass
class FetchResult:
    title: str | None
    text: str


# ---- YouTube URL parsing (pure, no network) -----------------------------

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def is_youtube_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in _YOUTUBE_HOSTS


def extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        video_id = parsed.path.lstrip("/")
        return video_id or None
    if "youtube.com" in host:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v")
            return values[0] if values else None
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in ("embed", "shorts", "live"):
            return parts[1]
    return None


# ---- HTML text extraction (pure, no network) ----------------------------


class _TextExtractor(HTMLParser):
    """A small, dependency-free HTML -> plain text extractor.

    Not a full "readability" algorithm (no attempt to strip nav/ads) —
    good enough to make a page's visible words searchable, without
    pulling in a heavier parsing library for a project that's meant to
    stay simple to read and learn from.
    """

    # "head" is deliberately NOT in here: <title> lives inside <head>, and
    # if we skip all of <head>'s contents that skips <title> too. The other
    # tags <head> normally contains (<meta>, <link>, <base>) don't emit any
    # handle_data text anyway, so there's nothing to accidentally capture.
    _SKIP_TAGS = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if data.strip():
            self._text_parts.append(data.strip())

    @property
    def title(self) -> str | None:
        title = " ".join("".join(self._title_parts).split())
        return title or None

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self._text_parts)).strip()


def extract_text_from_html(html: str) -> FetchResult:
    """Pure function: HTML string in, title+text out. No network I/O."""
    parser = _TextExtractor()
    parser.feed(html)
    return FetchResult(title=parser.title, text=parser.text)


def format_transcript(segments: list[dict]) -> str:
    """Pure function: youtube-transcript-api's raw segment list
    (dicts with a "text" key) in, one searchable block of text out."""
    pieces = [seg.get("text", "").strip() for seg in segments if seg.get("text", "").strip()]
    return re.sub(r"\s+", " ", " ".join(pieces)).strip()


# ---- Network-calling functions -------------------------------------------


def fetch_page_text(url: str, timeout: float = 10.0) -> FetchResult:
    """Downloads a URL and extracts its visible text and title."""
    try:
        import requests
    except ImportError as ex:
        raise FetchError(
            "The 'requests' package isn't installed. Run: pip install -r requirements.txt"
        ) from ex

    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (NeuroNook)"})
        response.raise_for_status()
    except requests.RequestException as ex:
        raise FetchError(f"Couldn't reach that URL: {ex}") from ex

    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        raise FetchError(f"That URL didn't return a web page (Content-Type: {content_type or 'unknown'}).")

    result = extract_text_from_html(response.text)
    if not result.text:
        raise FetchError("Fetched the page, but couldn't find any readable text on it.")
    return result


def fetch_youtube_transcript(url: str) -> FetchResult:
    """Fetches a YouTube video's existing captions/transcript, if one is
    available. This reads captions YouTube already generated/hosts — it
    does not do any local transcription itself."""
    video_id = extract_youtube_video_id(url)
    if not video_id:
        raise FetchError("Couldn't find a video ID in that YouTube URL.")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, YouTubeTranscriptApiException
    except ImportError as ex:
        raise FetchError(
            "The 'youtube-transcript-api' package isn't installed. Run: pip install -r requirements.txt"
        ) from ex

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
    except YouTubeTranscriptApiException as ex:
        raise FetchError(f"Couldn't fetch a transcript for that video: {ex}") from ex

    text = format_transcript(fetched.to_raw_data())
    if not text:
        raise FetchError("Found a transcript for this video, but it was empty.")
    return FetchResult(title=None, text=text)


def fetch_url_text(url: str) -> FetchResult:
    """The one function UI code calls. Routes YouTube links to the
    transcript fetcher, everything else to plain page-text extraction."""
    url = (url or "").strip()
    if not url:
        raise FetchError("No URL to fetch.")
    if is_youtube_url(url):
        return fetch_youtube_transcript(url)
    return fetch_page_text(url)
