"""Generic agent: system prompt, world MCP as tools, budget line, history trimming."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import ProcessHistory
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models import Model
from pydantic_ai.usage import RunUsage

from planworldsimulator_harness.budget import Budget

KEEP_MESSAGES = 40

SYSTEM_PROMPT = """\
You play a simulated world. You act only through the world's tools.
Start with brief(). It explains the story, the goal and the actions.
Actions are queued; advance() applies them and moves time forward.
Use note() to record the hypothesis you are testing.
Play until the episode is done, then reply with a one-line summary.
Your budget for the whole episode: {budget}.
If the budget runs out, you stop and the remaining steps run with no actions."""

START_PROMPT = "Play this world. Start with brief()."
CONTINUE_PROMPT = (
    "Continue playing this world from week {week}; earlier weeks were played "
    "by someone else. Start with brief() and observe()."
)


@dataclass
class Deps:
    budget: Budget
    started: float = field(default_factory=time.monotonic)
    usage: RunUsage | None = None  # live usage of the run, captured on first request

    def elapsed(self) -> float:
        return time.monotonic() - self.started


def _instructions(ctx: RunContext[Deps]) -> str:
    deps = ctx.deps
    deps.usage = ctx.usage
    return "\n\n".join(
        [
            SYSTEM_PROMPT.format(budget=deps.budget.describe()),
            deps.budget.status(ctx.usage, deps.elapsed()),
        ]
    )


def trim_history(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep the first prompt and the last messages, cut before a model response."""
    if len(messages) <= KEEP_MESSAGES:
        return messages
    cut = len(messages) - KEEP_MESSAGES
    while cut < len(messages) and not isinstance(messages[cut], ModelResponse):
        cut += 1
    return [messages[0], *messages[cut:]]


def paced(seconds: float) -> Callable[..., Awaitable[Any]]:
    """MCP tool-call hook that waits ``seconds`` before each call (UI runs only)."""

    async def call(
        ctx: RunContext[Any],
        call_tool: Callable[[str, dict[str, Any]], Awaitable[Any]],
        name: str,
        args: dict[str, Any],
    ) -> Any:
        await asyncio.sleep(seconds)
        return await call_tool(name, args)

    return call


def build_agent(
    model: Model,
    mcp_url: str,
    settings: dict[str, Any] | None = None,
    pace: float = 0.0,
) -> Agent[Deps, str]:
    """``pace``: seconds to wait before each tool call, so a person can follow."""
    hook = paced(pace) if pace > 0 else None
    return Agent(
        model,
        deps_type=Deps,
        instructions=_instructions,
        toolsets=[MCPToolset(mcp_url, process_tool_call=hook)],
        model_settings=settings or None,  # type: ignore[arg-type]
        capabilities=[ProcessHistory(trim_history)],
    )
