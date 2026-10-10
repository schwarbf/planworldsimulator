"""The built UI reaches the harness through its own world on dynamic ports."""
import json

import httpx
from fastapi.testclient import TestClient

from server import api


def test_harness_uses_world_port_and_overrides_browser_address(monkeypatch):
    seen = []
    monkeypatch.setenv("PORT", "9234")
    monkeypatch.setenv("HARNESS_URL", "http://harness:8090")
    original = httpx.AsyncClient

    def receive(request):
        seen.append(request)
        return httpx.Response(200, json={"status": "running"})

    monkeypatch.setattr(api.httpx, "AsyncClient", lambda **kw: original(
        transport=httpx.MockTransport(receive), **kw))
    client = TestClient(api.app)
    assert client.post("/harness/run", json={"agent": "gemini-flash", "world_url": "http://wrong"}).status_code == 200
    assert json.loads(seen[-1].content) == {"agent": "gemini-flash", "world_url": "http://127.0.0.1:9234"}
    assert seen[-1].url.host == "harness"
    assert client.get("/harness/status?world_url=http://wrong").status_code == 200
    assert seen[-1].url.params["world_url"] == "http://127.0.0.1:9234"
    assert client.post("/harness/stop", json={}).status_code == 200
    assert client.get("/harness/agents").status_code == 200
    assert client.get("/harness/run").status_code == 404
    assert client.get("/harness/nope").status_code == 404


def test_harness_offline_is_a_service_error(monkeypatch):
    original = httpx.AsyncClient

    def offline(request):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(api.httpx, "AsyncClient", lambda **kw: original(
        transport=httpx.MockTransport(offline), **kw))
    assert TestClient(api.app).get("/harness/agents").status_code == 503
