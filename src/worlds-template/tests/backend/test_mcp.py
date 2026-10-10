"""[base] MCP tools cover the world's actions; reads, notes and advance work."""

import json

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from server.api import Game
from server.mcp import build_mcp
from sim.helpers import world

CORE = {"brief", "observe", "note", "advance", "score"}


@pytest.fixture
def game() -> Game:
    return Game(seed=42, difficulty=world().DIFFICULTIES[0])


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
    async def test_core_and_action_tools_listed(self, game):
        server = build_mcp(game)
        async with create_connected_server_and_client_session(server._mcp_server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
        assert CORE <= names
        assert set(game.env.actions) <= names

    @pytest.mark.anyio
    async def test_advance_moves_time(self, game):
        server = build_mcp(game)
        week = game.state()["week"]
        assert (await _call(server, "advance"))["week"] == week + 1

    @pytest.mark.anyio
    async def test_reads_and_notes(self, game):
        server = build_mcp(game)
        assert await _call(server, "brief")
        assert isinstance(await _call(server, "observe"), dict)
        assert 0 <= (await _call(server, "score"))["score"] <= 1
        await _call(server, "note", {"text": "testing a hypothesis"})
        assert game.state()["agent"]["now"] == "testing a hypothesis"

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
