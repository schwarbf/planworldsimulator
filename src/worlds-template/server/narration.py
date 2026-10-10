"""[base] Voice narrator (decision 0006): spoken intro from ``brief.md``.

Gemini rewrites the brief into a short spoken intro; Gradium text-to-speech turns
it into audio. Both are cached in ``.narration/`` in the world folder, so each world
calls each API once. Keys (``GEMINI_API_KEY``, ``GRADIUM_API_KEY``) stay on the
server; they come from the environment (``GEMINI_API_KEY`` or ``GEMINI_API_KEY_FILE``,
a path to a file holding the key; same for Gradium) or the world's gitignored ``.env``.
Without Gemini the intro is the start of ``brief.md``; without Gradium there is no
audio and ``audio_error`` says why, so the UI can show the voice as disabled.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / ".narration"
KINDS = ("intro",)
INTRO_WORDS = 60
TIMEOUT_S = 60.0

GEMINI_MODEL = "gemini-3.8-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GRADIUM_URL = "https://api.gradium.ai/api/post/speech/tts"
GRADIUM_VOICE = "4SZHfMpw-p46Ywgs"  # "Harper": friendly US English flagship voice
AUDIO_FORMAT = "wav"  # plays in every browser
AUDIO_TYPE = "audio/wav"

PROMPT = (
    "You are the narrator of a strategy game. Rewrite the game brief below as a spoken "
    f"intro of about {INTRO_WORDS} words for a new player. Start with 'Welcome to <world name>.' "
    "Explain the setting, the goal and how a turn works. Use short plain sentences, "
    "address the player as 'you', no markdown, lists, code, symbols or arrows. "
    "Reply with the intro text only.\n\nBRIEF:\n"
)

log = logging.getLogger("uvicorn.error")


def load_env(path: Path = ROOT / ".env") -> None:
    """Read ``KEY=VALUE`` lines from the world's ``.env``; real env vars win."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def api_key(name: str) -> str:
    """``$NAME``, else the contents of the file at ``$NAME_FILE`` (``~`` allowed), else ""."""
    key = os.environ.get(name, "").strip()
    if key:
        return key
    path = os.environ.get(f"{name}_FILE", "").strip()
    if path and Path(path).expanduser().is_file():
        return Path(path).expanduser().read_text().strip()
    return ""


load_env()

_lock = threading.Lock()  # one generation at a time, so concurrent requests reuse the cache


def narrate(kind: str = "intro") -> dict[str, Any]:
    """Intro text, its sentences, the audio URL and why there is no audio (if so)."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    with _lock:
        text = _text(kind)
        audio_error = _audio(kind, text)
    if audio_error:
        log.warning("narrator: captions only (%s)", audio_error)
    return {"text": text, "sentences": split_sentences(text),
            "audio_url": None if audio_error else f"/api/narration/{kind}/audio",
            "audio_error": audio_error}


def audio_path(kind: str) -> Path | None:
    """Cached audio file for ``kind``, if it exists."""
    path = CACHE_DIR / f"{kind}.{AUDIO_FORMAT}"
    return path if kind in KINDS and path.is_file() else None


def split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def brief_intro(brief: str, words: int = INTRO_WORDS) -> str:
    """Fallback intro: 'Welcome to <title>.' plus the first sentences of the brief, as plain text."""
    title, body = "", []
    for line in re.sub(r"<!--.*?-->", "", brief, flags=re.S).splitlines():
        line = line.strip()
        if line.startswith("#"):
            title = title or line.lstrip("# ").strip()
        elif line and not line.startswith(("|", "- ", "* ")):  # skip tables and lists
            body.append(line)
    plain = re.sub(r"[`*_]|\s*\([^)]*\)", "", " ".join(body))
    plain = re.sub(r"\s*→\s*", ", ", plain)
    out, count = [f"Welcome to {title}."] if title else [], 0
    for s in split_sentences(plain):
        if out and count + len(s.split()) > words:
            break
        out.append(s)
        count += len(s.split())
    return " ".join(out)


# ---------- pipeline ----------

def _text(kind: str) -> str:
    cached = CACHE_DIR / f"{kind}.txt"
    if cached.is_file():
        return cached.read_text().strip()
    brief = (ROOT / "brief.md").read_text()
    key = api_key("GEMINI_API_KEY")
    if not key:
        log.warning("narrator: no GEMINI_API_KEY, intro taken from brief.md")
        return brief_intro(brief)
    try:
        text = _gemini(key, PROMPT + brief)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        log.warning("narrator: Gemini failed (%s), intro taken from brief.md", type(e).__name__)
        return brief_intro(brief)  # not cached: retry on the next open
    CACHE_DIR.mkdir(exist_ok=True)
    cached.write_text(text + "\n")
    return text


def _audio(kind: str, text: str) -> str | None:
    """Make sure the audio is cached; return why not, or None when it is there."""
    if audio_path(kind):
        return None
    key = api_key("GRADIUM_API_KEY")
    if not key:
        return "no GRADIUM_API_KEY on the world server"
    try:
        audio = _gradium(key, text)
    except httpx.HTTPStatusError as e:
        return f"Gradium error (HTTP {e.response.status_code})"
    except httpx.HTTPError:
        return "Gradium unreachable"
    if not audio:
        return "Gradium returned no audio"
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{kind}.{AUDIO_FORMAT}").write_bytes(audio)
    return None


def _gemini(key: str, prompt: str) -> str:
    res = httpx.post(GEMINI_URL, headers={"x-goog-api-key": key}, timeout=TIMEOUT_S,
                     json={"contents": [{"parts": [{"text": prompt}]}]})
    res.raise_for_status()
    parts = res.json()["candidates"][0]["content"]["parts"]
    text = " ".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise ValueError("empty Gemini reply")
    return re.sub(r"\s+", " ", text)


def _gradium(key: str, text: str) -> bytes:
    res = httpx.post(GRADIUM_URL, headers={"x-api-key": key}, timeout=TIMEOUT_S,
                     json={"text": text, "voice_id": os.environ.get("GRADIUM_VOICE_ID") or GRADIUM_VOICE,
                           "output_format": AUDIO_FORMAT, "only_audio": True})
    res.raise_for_status()
    return res.content
