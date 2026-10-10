"""`harness serve`: real bike-factory server + scripted models; no API key."""

import asyncio

import httpx
from planworldsimulator_harness.agents import AgentConfig
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.client import WorldClient
from planworldsimulator_harness.episode import run_episode
from planworldsimulator_harness.serve import Runner, create_app
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.models.function import AgentInfo, FunctionModel

SCRIPT = [
    ("brief", {}),
    ("observe", {}),
    ("order", {"site": "warehouse", "qty": 60}),
    ("advance", {"weeks": 4}),
]
FAKE = AgentConfig(name="scripted", model="test:scripted")

AGENTS = """\
[scripted]
label = "Scripted"
color = "#14a3a3"
model = "test:scripted"
"""


def scripted() -> FunctionModel:
    """Plays SCRIPT, then stops."""

    def play(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        step = sum(isinstance(m, ModelResponse) for m in messages)
        if step < len(SCRIPT):
            name, args = SCRIPT[step]
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart("played 4 weeks")])

    return FunctionModel(play)


def endless() -> FunctionModel:
    """Observes forever, so the run only ends when it is stopped."""

    def play(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[ToolCallPart("observe", {})])

    return FunctionModel(play)


def runner(tmp_path, model: Model, pace: float = 0.0) -> Runner:
    (tmp_path / "agents.toml").write_text(AGENTS)
    return Runner(
        Budget(), pace=pace, agents_file=tmp_path / "agents.toml", build=lambda _: model
    )


async def wait_until_done(http: httpx.AsyncClient, url: str) -> dict:
    for _ in range(200):
        status = (await http.get("/status", params={"world_url": url})).json()
        if not status["running"]:
            return status
        await asyncio.sleep(0.05)
    raise AssertionError("run did not finish")


async def test_run_continues_from_current_week_without_finishing(world_url, tmp_path):
    async with WorldClient(world_url) as world:
        await world.reset(7, "medium")
        await world.advance(3)  # the player played weeks 1–3 by hand
    app = create_app(runner(tmp_path, scripted()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://h") as http:
        agents = (await http.get("/agents")).json()
        assert agents == [
            {
                "name": "scripted",
                "label": "Scripted",
                "color": "#14a3a3",
                "model": "test:scripted",
            }
        ]
        r = await http.post("/run", json={"world_url": world_url, "agent": "scripted"})
        assert r.json()["status"] == "running"
        again = await http.post(
            "/run", json={"world_url": world_url, "agent": "scripted"}
        )
        assert again.status_code == 409
        status = await wait_until_done(http, world_url)

    last = status["last"]
    assert last["stopped_by"] == "agent", last
    assert last["seed"] == 7
    assert last["agent_steps"] == 4  # weeks 4–7; earlier weeks were the player's
    assert last["final"]["done"] is False  # no fair finish for UI runs
    async with WorldClient(world_url) as world:
        state = await world.state()
    assert state["week"] == 8
    assert state["play"] == {"mode": "you", "agent": None}  # handed back


async def test_stop_hands_the_world_back(world_url, tmp_path):
    async with WorldClient(world_url) as world:
        await world.reset(7, "medium")
    app = create_app(runner(tmp_path, endless(), pace=0.02))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://h") as http:
        await http.post("/run", json={"world_url": world_url, "agent": "scripted"})
        async with httpx.AsyncClient(base_url=world_url) as ui:
            await asyncio.sleep(0.3)
            assert (await ui.get("/api/state")).json()["play"]["agent"] == "scripted"
            locked = await ui.post("/api/advance", json={"steps": 1})
            assert locked.status_code == 409
            assert (await http.post("/stop", json={"world_url": world_url})).is_success
            status = (await http.get("/status", params={"world_url": world_url})).json()
            assert status["running"] is False
            assert status["last"]["stopped_by"] == "stopped"
            assert (await ui.get("/api/state")).json()["play"]["mode"] == "you"
            assert (await ui.post("/api/advance", json={"steps": 1})).is_success


async def test_unknown_agent_is_rejected(world_url, tmp_path):
    app = create_app(runner(tmp_path, endless()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://h") as http:
        r = await http.post("/run", json={"world_url": world_url, "agent": "nope"})
        assert r.status_code == 400
        assert (await http.post("/run", json={"agent": "scripted"})).status_code == 400


async def test_pace_spaces_tool_calls(world_url):
    result = await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(),
        model=scripted(),
        pace=0.1,
    )
    assert result.tool_calls == len(SCRIPT)
    assert result.seconds >= 0.1 * len(SCRIPT)
