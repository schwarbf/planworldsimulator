"""[base] Narrator route: Gemini + Gradium are mocked; no network in tests."""

import httpx
import pytest
from fastapi.testclient import TestClient

from server import narration
from server.api import app

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt fake-audio"
INTRO = "Welcome to the world. You run it for a year. Good luck."


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
        assert client.post("/api/narration", json={"kind": "commentary"}).status_code == 400

    def test_missing_audio_is_404(self, client, fake_apis):
        assert client.get("/api/narration/intro/audio").status_code == 404

    def test_response_never_contains_keys(self, client, fake_apis, monkeypatch):
        with_keys(monkeypatch)
        text = client.post("/api/narration", json={"kind": "intro"}).text
        assert "gemini-test" not in text and "gradium-test" not in text
