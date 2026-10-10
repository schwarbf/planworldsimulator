"""[base] REST routes and the event WebSocket drive the shared Game."""

import pytest
from fastapi.testclient import TestClient

from server.api import app


@pytest.fixture(scope="module")
def client():
    # One client per module: the MCP session manager can only start once per app.
    with TestClient(app) as c:
        yield c


class TestRest:
    def test_order_and_advance_change_state(self, client):
        client.post("/api/reset", json={"seed": 4821, "difficulty": "medium"})
        before = client.get("/api/state").json()
        r = client.post("/api/action", json={"id": "order", "args": {"target": "warehouse", "amount": 60}})
        assert r.status_code == 200
        assert client.get("/api/state").json()["queued"]
        client.post("/api/advance")
        after = client.get("/api/state").json()
        assert after["week"] == before["week"] + 1
        assert after["cash"] != before["cash"]

    def test_invalid_action_is_rejected(self, client):
        r = client.post("/api/action", json={"id": "order", "args": {"target": "nowhere", "amount": 5}})
        assert r.status_code == 400

    def test_ui_controls(self, client):
        client.post("/api/reset", json={"seed": 1, "difficulty": "easy"})
        assert client.post("/api/action", json={"id": "play", "args": {}}).json()["week"] == 2
        assert client.post("/api/action", json={"id": "mode", "args": {"mode": "agent"}}).json()["mode"] == "agent"
        seed = client.post("/api/action", json={"id": "new_world", "args": {}}).json()["seed"]
        assert client.get("/api/state").json()["world"]["seed"] == str(seed)


class TestEvents:
    def test_websocket_pushes_advance(self, client):
        last = max((e["seq"] for e in client.get("/api/events").json()), default=0)
        with client.websocket_connect("/api/events") as ws:
            client.post("/api/advance")
            event = ws.receive_json()
            while event["seq"] <= last:
                event = ws.receive_json()
            assert event["kind"] == "advance"
