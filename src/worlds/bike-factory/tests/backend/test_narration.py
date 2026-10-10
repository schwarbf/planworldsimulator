"""[base] Narrator route: Gemini + Gradium are mocked; no network in tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from server import narration
from server.api import app

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt fake-audio"
INTRO = "Welcome to the world. You run it for a year. Good luck."


KEY_VARS = ("GEMINI_API_KEY", "GRADIUM_API_KEY")


@pytest.fixture(autouse=True)
def no_real_keys(monkeypatch):
    """Tests never see real keys, also not via *_API_KEY_FILE or a world .env."""
    for name in KEY_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(f"{name}_FILE", raising=False)


@pytest.fixture
def client():
    # No `with`: the narrator routes do not need the MCP lifespan (it can only start once per app).
    return TestClient(app)


@pytest.fixture
def fake_apis(monkeypatch, tmp_path):
    """Cache in tmp_path; record the URLs httpx.post is called with."""
    monkeypatch.setattr(narration, "CACHE_DIR", tmp_path / ".narration")
    calls: list[str] = []

    def post(url, **kwargs):
        calls.append(url)
        req = httpx.Request("POST", url)
        if url == narration.GEMINI_URL:
            assert kwargs["headers"]["x-goog-api-key"] == "gemini-test"
            body = {"candidates": [{"content": {"parts": [{"text": INTRO}]}}]}
            return httpx.Response(200, json=body, request=req)
        assert url == narration.GRADIUM_URL
        assert kwargs["headers"]["x-api-key"] == "gradium-test"
        assert kwargs["json"]["text"] == INTRO
        return httpx.Response(200, content=WAV, headers={"content-type": "audio/wav"}, request=req)

    monkeypatch.setattr(narration.httpx, "post", post)
    return calls


def with_keys(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("GRADIUM_API_KEY", "gradium-test")


class TestNarration:
    def test_without_keys_returns_brief_captions_only(self, client, fake_apis, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GRADIUM_API_KEY", raising=False)
        res = client.post("/api/narration", json={"kind": "intro"}).json()
        assert res["audio_url"] is None
        assert res["text"].startswith("Welcome to ")
        assert res["sentences"] and " ".join(res["sentences"]) == res["text"]
        assert fake_apis == []

    def test_with_keys_returns_intro_and_playable_audio(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        res = client.post("/api/narration", json={"kind": "intro"}).json()
        assert res["text"] == INTRO
        assert res["sentences"] == ["Welcome to the world.", "You run it for a year.", "Good luck."]
        audio = client.get(res["audio_url"])
        assert audio.status_code == 200
        assert audio.headers["content-type"] == "audio/wav"
        assert audio.content == WAV

    def test_each_api_is_called_once_per_world(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        client.post("/api/narration", json={"kind": "intro"})
        client.post("/api/narration", json={"kind": "intro"})
        assert fake_apis == [narration.GEMINI_URL, narration.GRADIUM_URL]

    def test_api_failure_falls_back_to_captions(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)

        def fail(url, **kwargs):
            raise httpx.ConnectError("offline")

        monkeypatch.setattr(narration.httpx, "post", fail)
        res = client.post("/api/narration", json={"kind": "intro"}).json()
        assert res["audio_url"] is None and res["text"].startswith("Welcome to ")

    def test_unknown_kind_is_rejected(self, client, fake_apis):
        assert client.post("/api/narration", json={"kind": "gossip"}).status_code == 400

    def test_commentary_is_based_on_the_current_game(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        prompts: list[str] = []
        real = narration._gemini
        monkeypatch.setattr(narration, "_gemini", lambda key, prompt: prompts.append(prompt) or real(key, prompt))
        client.post("/api/reset", json={"seed": 7})
        res = client.post("/api/narration", json={"kind": "commentary"}).json()
        assert res["text"] == INTRO
        assert res["audio_url"] == "/api/narration/commentary-7-1/audio"
        assert client.get(res["audio_url"]).content == WAV
        assert '"score"' in prompts[0] and '"discoveries"' in prompts[0]

    def test_commentary_once_per_week(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        client.post("/api/reset", json={"seed": 7})
        client.post("/api/narration", json={"kind": "commentary"})
        client.post("/api/narration", json={"kind": "commentary"})
        client.post("/api/advance", json={"steps": 1})
        client.post("/api/narration", json={"kind": "commentary"})
        assert fake_apis.count(narration.GEMINI_URL) == 2

    def test_commentary_without_keys_reads_the_numbers(self, client, fake_apis, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GRADIUM_API_KEY", raising=False)
        client.post("/api/reset", json={"seed": 7})
        res = client.post("/api/narration", json={"kind": "commentary"}).json()
        assert res["text"].startswith("Week 1")
        assert "score" in res["text"] and res["audio_url"] is None

    def test_missing_audio_is_404(self, client, fake_apis):
        assert client.get("/api/narration/intro/audio").status_code == 404

    def test_response_never_contains_keys(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        text = client.post("/api/narration", json={"kind": "intro"}).text
        assert "gemini-test" not in text and "gradium-test" not in text

    def test_no_gradium_key_says_why_and_keeps_gemini_text(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        monkeypatch.delenv("GRADIUM_API_KEY")
        res = client.post("/api/narration", json={"kind": "intro"}).json()
        assert res["text"] == INTRO
        assert res["audio_url"] is None
        assert "GRADIUM_API_KEY" in res["audio_error"]

    def test_gradium_down_says_unreachable(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        real = narration.httpx.post

        def gradium_down(url, **kwargs):
            if url == narration.GRADIUM_URL:
                raise httpx.ConnectError("offline")
            return real(url, **kwargs)

        monkeypatch.setattr(narration.httpx, "post", gradium_down)
        res = client.post("/api/narration", json={"kind": "intro"}).json()
        assert res["text"] == INTRO
        assert res["audio_error"] == "Gradium unreachable"

    def test_audio_ok_has_no_error(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        assert client.post("/api/narration", json={"kind": "intro"}).json()["audio_error"] is None


def test_load_env_reads_dotenv_without_overriding(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nNARRATOR_TEST_A=from-file\nNARRATOR_TEST_B='quoted'\n")
    monkeypatch.setenv("NARRATOR_TEST_A", "from-env")
    monkeypatch.delenv("NARRATOR_TEST_B", raising=False)
    narration.load_env(env)
    import os

    assert os.environ["NARRATOR_TEST_A"] == "from-env"
    assert os.environ["NARRATOR_TEST_B"] == "quoted"
    monkeypatch.delenv("NARRATOR_TEST_B")


def test_api_key_from_file(tmp_path, monkeypatch):
    keyfile = tmp_path / "key.txt"
    keyfile.write_text("file-key\n")
    monkeypatch.delenv("NARRATOR_TEST_KEY", raising=False)
    monkeypatch.setenv("NARRATOR_TEST_KEY_FILE", str(keyfile))
    assert narration.api_key("NARRATOR_TEST_KEY") == "file-key"
    monkeypatch.setenv("NARRATOR_TEST_KEY", "env-key")
    assert narration.api_key("NARRATOR_TEST_KEY") == "env-key"


def test_fallback_intro_explains_the_actions():
    brief = "# Demo\n\nYou run it.\n\n| Action | Effect |\n|---|---|\n| `order(site, qty)` | Ships qty units. Costs money. |\n| `note(text)` | Record a hypothesis. |\n"
    text = narration.brief_intro(brief)
    assert text.startswith("Welcome to Demo.")
    assert "Order: Ships qty units." in text
    assert "Note" not in text


class TestNoteVoice:
    def test_note_is_read_in_the_agent_voice_without_gemini(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        voices: list[str] = []
        real = narration.httpx.post

        def post(url, **kwargs):
            voices.append(kwargs["json"].get("voice_id", ""))
            return real(url, **kwargs)

        monkeypatch.setattr(narration.httpx, "post", post)
        res = client.post("/api/narration", json={"kind": "note", "text": INTRO}).json()
        assert res["text"] == INTRO
        assert res["audio_url"].startswith("/api/narration/note-")
        assert client.get(res["audio_url"]).content == WAV
        assert fake_apis == [narration.GRADIUM_URL]  # no Gemini call
        assert voices == [narration.GRADIUM_AGENT_VOICE]

    def test_long_notes_are_cut(self, client, fake_apis, monkeypatch):
        monkeypatch.delenv("GRADIUM_API_KEY", raising=False)
        long = " ".join(f"word{k}" for k in range(60))
        res = client.post("/api/narration", json={"kind": "note", "text": long}).json()
        assert len(res["text"].split()) == narration.NOTE_WORDS
        assert res["text"].endswith("…") and res["audio_url"] is None

    def test_empty_note_is_rejected(self, client, fake_apis):
        assert client.post("/api/narration", json={"kind": "note"}).status_code == 400
