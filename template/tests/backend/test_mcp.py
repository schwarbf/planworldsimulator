"""[base] MCP tools match the world's actions; reads and advance work."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from server.api import Game
from server.mcp import build_mcp

EXPECTED = {"brief", "observe", "observe_site", "order", "expand", "probe", "note", "advance", "score"}


@pytest.fixture
def game() -> Game:
    return Game(seed=42, difficulty="medium")


async def _call(server, name: str, args: dict | None = None):
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        result = await client.call_tool(name, args or {})
        assert not result.isError, result.content
        text = result.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


class TestTools:
    @pytest.mark.anyio
    async def test_tools_listed(self, game):
        server = build_mcp(game)
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
        assert EXPECTED <= names
        world_actions = {"order", "expand", "probe"}
        assert set(game.env.actions) <= world_actions & names

    @pytest.mark.anyio
    async def test_order_then_advance_changes_state(self, game):
        server = build_mcp(game)
        before = await _call(server, "observe")
        queued = await _call(server, "order", {"site": "warehouse", "qty": 60})
        assert queued["status"] == "queued"
        after_advance = await _call(server, "advance")
        after = await _call(server, "observe")
        assert after_advance["week"] == before["week"] + 1
        assert after["sites"]["warehouse"]["incoming"] != before["sites"]["warehouse"]["incoming"] or after["cash"] != before["cash"]

    @pytest.mark.anyio
    async def test_reads_and_notes(self, game):
        server = build_mcp(game)
        assert "Bike Factory" in await _call(server, "brief")
        assert 0 <= (await _call(server, "score"))["score"] <= 1
        await _call(server, "note", {"text": "Store B looks seasonal"})
        assert game.state()["agent"]["now"] == "Store B looks seasonal"

    @pytest.mark.anyio
    async def test_every_call_is_logged(self, game):
        server = build_mcp(game)
        start = len(game.events)
        await _call(server, "observe")
        await _call(server, "advance")
        assert [e["name"] for e in game.events[start:]] == ["observe", "advance"]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
