"""Real bike-factory server + a scripted model: no API key, no cost."""

from planworldsimulator_harness.agents import AgentConfig
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.client import WorldClient
from planworldsimulator_harness.episode import run_episode
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

SCRIPT = [
    ("brief", {}),
    ("observe", {}),
    ("order", {"site": "warehouse", "qty": 60}),
    ("advance", {"weeks": 4}),
]
FAKE = AgentConfig(name="scripted", model="test:scripted")


def scripted(seen: list[str]) -> FunctionModel:
    """Plays SCRIPT, then stops. Records the instructions it was given."""

    def play(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info.instructions or "")
        step = sum(isinstance(m, ModelResponse) for m in messages)
        if step < len(SCRIPT):
            name, args = SCRIPT[step]
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(parts=[TextPart("played 4 weeks")])

    return FunctionModel(play)


async def test_agent_plays_through_mcp(world_url):
    seen: list[str] = []
    result = await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(),
        model=scripted(seen),
    )
    assert result.stopped_by == "agent", result.error
    assert result.agent_steps == 4
    assert result.tool_calls == len(SCRIPT)
    assert result.final["done"] is True  # harness played out the rest
    assert 0.0 <= result.score <= 1.0
    assert result.summary == "played 4 weeks"

    async with WorldClient(world_url) as world:
        calls = [e["name"] for e in await world.events() if e["source"] == "agent"]
    assert calls[-4:] == ["brief", "observe", "order", "advance"]


async def test_budget_line_is_shown_every_request(world_url):
    seen: list[str] = []
    await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(),
        model=scripted(seen),
    )
    assert len(seen) == len(SCRIPT) + 1
    assert "Budget left: 2.0M/2.0M tokens" in seen[0]
    assert "tool calls" not in seen[-1]


async def test_limit_stops_run_and_episode_still_scores(world_url):
    result = await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(tokens=200),
        model=scripted([]),
    )
    assert result.stopped_by == "limit"
    assert result.agent_steps == 0
    assert result.final["done"] is True


async def test_think_aloud_prompt_only_when_asked(world_url):
    plain: list[str] = []
    await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(),
        model=scripted(plain),
    )
    loud: list[str] = []
    await run_episode(
        world_url,
        FAKE,
        seed=7,
        difficulty="medium",
        budget=Budget(),
        model=scripted(loud),
        explain=True,
    )
    assert "Think aloud" not in plain[0]
    assert "Think aloud" in loud[0] and "at most 3 times" in loud[0]
