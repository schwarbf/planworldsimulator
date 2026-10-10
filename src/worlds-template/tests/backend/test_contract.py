"""[base] The server's UI state per level is dumped for the frontend contract test.

`ui/src/World.contract.test.tsx` reads these samples and checks that they have the same
shape as `mockState` in `World.tsx` and that the world view renders them. Run this
before `pixi run test-ui`.
"""

import json
from pathlib import Path

import pytest

from server.api import Game
from sim.helpers import world

SAMPLES = Path(__file__).resolve().parents[2] / "ui" / "src" / "__samples__"
DIFFICULTIES = world().DIFFICULTIES


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_dump_state_samples(difficulty):
    game = Game(seed=5, difficulty=difficulty)
    samples = {"start": game.state()}
    game.advance(3)
    samples["week3"] = game.state()
    while not game.score()["done"]:
        game.advance(1)
    samples["end"] = game.state()
    SAMPLES.mkdir(exist_ok=True)
    for name, state in samples.items():
        (SAMPLES / f"{difficulty}-{name}.json").write_text(json.dumps(state, indent=1))
    assert samples["end"]["done"] is True


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_design_sites_actions_and_episode(difficulty):
    """Generated worlds must implement the validated design on every level."""
    design_path = SAMPLES.parents[2] / "design.json"
    if not design_path.is_file():
        pytest.skip("The standalone template has no generated design")
    design = json.loads(design_path.read_text())
    level = design["levels"][difficulty]
    game = Game(seed=5, difficulty=difficulty)
    assert set(game.env.site_ids) == set(level["sites"])
    assert set(game.env.actions) == set(level["actions"])
    assert game.state()["weeks"] == design["weeks"]
    steps = 0
    while not game.score()["done"] and steps <= design["weeks"]:
        game.advance(1)
        steps += 1
    assert steps == design["weeks"]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_design_action_argument_types():
    from server.mcp import build_mcp
    from mcp.shared.memory import create_connected_server_and_client_session

    design_path = SAMPLES.parents[2] / "design.json"
    if not design_path.is_file():
        pytest.skip("The standalone template has no generated design")
    design = json.loads(design_path.read_text())
    game = Game(seed=5, difficulty="hard")
    server = build_mcp(game)
    async with create_connected_server_and_client_session(server._mcp_server) as client:
        tools = {t.name: t.inputSchema for t in (await client.list_tools()).tools}
    for action in design["actions"]:
        properties = tools[action["name"]].get("properties", {})
        assert set(properties) == set(action["arguments"])
        for name, argument in action["arguments"].items():
            assert properties[name]["type"] == argument["type"]
