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

# UI runs only (harness serve): the notes are shown on the cursor and read aloud.
# Benchmarks do not get this, so their prompt and results stay comparable.
EXPLAIN_PROMPT = """\
Someone is watching you play and hears your notes read aloud. Think aloud for them:
before every advance(), call note() at least once and at most 3 times. Each note is
one or two short sentences (under 25 words) about a major idea: what you noticed,
what you are testing, or why you take your next actions."""

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
    explain: bool = False  # think aloud in notes (UI runs)

    def elapsed(self) -> float:
        return time.monotonic() - self.started


def _instructions(ctx: RunContext[Deps]) -> str:
    deps = ctx.deps
    deps.usage = ctx.usage
    return "\n\n".join(
        [
            SYSTEM_PROMPT.format(budget=deps.budget.describe()),
            *([EXPLAIN_PROMPT] if deps.explain else []),
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


Pace = float | Callable[[], float]


def paced(seconds: Pace) -> Callable[..., Awaitable[Any]]:
    """MCP tool-call hook that waits before each call (UI runs only).

    ``seconds`` may be a function, read before every call, so the pace can change
    while the agent plays (the UI speed slider).
    """

    async def call(
        ctx: RunContext[Any],
        call_tool: Callable[[str, dict[str, Any]], Awaitable[Any]],
        name: str,
        args: dict[str, Any],
    ) -> Any:
        wait = seconds() if callable(seconds) else seconds
        if wait > 0:
            await asyncio.sleep(wait)
        return await call_tool(name, args)

    return call


def build_agent(
    model: Model,
    mcp_url: str,
    settings: dict[str, Any] | None = None,
    pace: Pace = 0.0,
) -> Agent[Deps, str]:
    """``pace``: seconds to wait before each tool call, so a person can follow."""
    hook = paced(pace) if callable(pace) or pace > 0 else None
    return Agent(
        model,
        deps_type=Deps,
        instructions=_instructions,
        toolsets=[MCPToolset(mcp_url, process_tool_call=hook)],
        model_settings=settings or None,  # type: ignore[arg-type]
        capabilities=[ProcessHistory(trim_history)],
    )
