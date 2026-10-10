"""Run one episode on a world URL, finish remaining steps, return EpisodeResult.

Benchmarks reset the world and play out the remaining weeks (fair finish).
UI runs (``harness serve``) continue from the current week and stop where the
agent stops, so a person can take over.
"""

import asyncio
import time
from dataclasses import asdict, dataclass
from typing import Any

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.models import Model

from planworldsimulator_harness.agent import (
    CONTINUE_PROMPT,
    START_PROMPT,
    Deps,
    build_agent,
)
from planworldsimulator_harness.agents import AgentConfig, build_model
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.client import WorldClient


@dataclass
class EpisodeResult:
    agent: str
    url: str
    seed: int
    difficulty: str
    stopped_by: str  # done | agent | limit | timeout | error
    agent_steps: int  # steps the agent played before it stopped
    score: float
    baseline: float
    final: dict[str, Any]  # full final score from the world
    requests: int
    tool_calls: int
    input_tokens: int
    output_tokens: int
    seconds: float
    summary: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def run_episode(
    url: str,
    agent: AgentConfig,
    seed: int | None,
    difficulty: str | None,
    budget: Budget,
    model: Model | None = None,
    *,
    reset: bool = True,
    finish: bool = True,
    pace: float = 0.0,
) -> EpisodeResult:
    """Play one episode.

    ``reset=False`` continues from the current week (seed and difficulty are
    read from the world). ``finish=False`` leaves the remaining weeks unplayed.
    ``pace`` waits that many seconds before each tool call (UI runs only).
    """
    async with WorldClient(url) as world:
        if reset:
            if seed is None or difficulty is None:
                raise ValueError("reset needs a seed and a difficulty")
            await world.reset(seed, difficulty)
        else:
            info = (await world.state())["world"]
            seed, difficulty = int(info["seed"]), str(info["difficulty"]).lower()
        start = await world.score()
        prompt = (
            START_PROMPT
            if int(start["week"]) <= 1
            else CONTINUE_PROMPT.format(week=start["week"])
        )
        runner = build_agent(
            model or build_model(agent), world.mcp_url, agent.settings, pace
        )
        deps = Deps(budget)
        started = time.monotonic()
        stopped_by, summary, error = "agent", "", ""
        try:
            async with asyncio.timeout(budget.seconds):
                result = await runner.run(
                    prompt, deps=deps, usage_limits=budget.usage_limits()
                )
            summary = result.output
        except UsageLimitExceeded as e:
            stopped_by, error = "limit", str(e)
        except TimeoutError:
            stopped_by = "timeout"
        except Exception as e:  # keep the benchmark going; record what failed
            stopped_by, error = "error", f"{type(e).__name__}: {e}"
        seconds = time.monotonic() - started

        before = await world.score()
        if before["done"] and stopped_by == "agent":
            stopped_by = "done"
        final = await world.finish() if finish else before

    usage = deps.usage
    played_to = int(before["week"]) if before["done"] else int(before["week"]) - 1
    return EpisodeResult(
        agent=agent.name,
        url=url,
        seed=seed,
        difficulty=difficulty,
        stopped_by=stopped_by,
        agent_steps=played_to - (int(start["week"]) - 1),
        score=float(final["score"]),
        baseline=float(final.get("baseline", 0.0)),
        final=final,
        requests=usage.requests if usage else 0,
        tool_calls=usage.tool_calls if usage else 0,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        seconds=round(seconds, 1),
        summary=summary,
        error=error,
    )
