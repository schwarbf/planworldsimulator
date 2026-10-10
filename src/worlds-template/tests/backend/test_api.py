"""[base] REST routes and the event WebSocket drive the shared Game."""

import pytest
from fastapi.testclient import TestClient

from server.api import app
from sim.helpers import world

DIFFICULTY = world().DIFFICULTIES[0]


@pytest.fixture(scope="module")
def client():
    # One client per module: the MCP session manager can only start once per app.
    with TestClient(app) as c:
        yield c


class TestRest:
    def test_state_has_world_and_week(self, client):
        client.post("/api/reset", json={"seed": 7, "difficulty": DIFFICULTY})
        state = client.get("/api/state").json()
        assert state["world"]["seed"] == "7"
        assert "week" in state

    def test_score_has_contract_fields(self, client):
        score = client.get("/api/score").json()
        assert {"score", "baseline", "week", "done"} <= score.keys()

    def test_advance_moves_time(self, client):
        before = client.get("/api/state").json()["week"]
        client.post("/api/advance")
        assert client.get("/api/state").json()["week"] == before + 1

    def test_unknown_action_is_rejected(self, client):
        r = client.post("/api/action", json={"id": "not_an_action", "args": {}})
        assert r.status_code == 400

    def test_ui_controls(self, client):
        client.post("/api/reset", json={"seed": 1, "difficulty": DIFFICULTY})
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
