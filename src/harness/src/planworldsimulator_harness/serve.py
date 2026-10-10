"""`harness serve`: start and stop agents from the world UI (decision 0007).

A UI run continues from the current week (no reset) with a fresh budget, waits
``pace`` seconds before each tool call so a person can follow, and does not
play out the remaining weeks: whoever stops it can take over by hand. While it
runs the world is in ``mode = "agent"`` and rejects UI actions.
"""

import asyncio
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import Body, FastAPI, HTTPException
from pydantic_ai.models import Model

from planworldsimulator_harness.agents import AgentConfig, build_model, load_agents
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.client import WorldClient
from planworldsimulator_harness.config import AGENTS_FILE
from planworldsimulator_harness.episode import run_episode

DEFAULT_PORT = 8090
DEFAULT_PACE = 1.0
MAX_PACE = 5.0


@dataclass
class Run:
    agent: AgentConfig
    task: asyncio.Task[None]
    started: float = field(default_factory=time.monotonic)


class Runner:
    """At most one agent run per world URL."""

    def __init__(
        self,
        budget: Budget | None = None,
        pace: float = DEFAULT_PACE,
        agents_file: Path = AGENTS_FILE,
        build: Callable[[AgentConfig], Model] = build_model,
    ) -> None:
        self.budget = budget or Budget()
        self.pace = pace
        self.agents_file = agents_file
        self.build = build
        self.runs: dict[str, Run] = {}
        self.paces: dict[str, float] = {}  # world URL → pace set from the UI slider
        self.last: dict[str, dict[str, Any]] = {}  # world URL → last run outcome

    def agents(self) -> dict[str, AgentConfig]:
        return load_agents(self.agents_file)

    def pace_of(self, url: str) -> float:
        return self.paces.get(url, self.pace)

    def set_pace(self, url: str, seconds: float) -> dict[str, Any]:
        """Change the pace, also while an agent plays (read before each tool call)."""
        self.paces[url] = max(0.0, min(MAX_PACE, float(seconds)))
        return {"world_url": url, "pace": self.paces[url]}

    def running(self, url: str) -> Run | None:
        run = self.runs.get(url)
        return run if run and not run.task.done() else None

    async def start(self, url: str, name: str) -> dict[str, Any]:
        if self.running(url):
            raise ValueError(f"an agent is already playing {url}")
        agents = self.agents()
        if name not in agents:
            raise KeyError(f"unknown agent {name!r}; known: {', '.join(agents)}")
        agent = agents[name]
        model = self.build(agent)  # fails fast, e.g. on a missing API key
        async with WorldClient(url) as world:
            await world.set_mode("agent", agent.name)
        task = asyncio.create_task(self._play(url, agent, model))
        self.runs[url] = Run(agent, task)
        return {"status": "running", "agent": agent.name, "world_url": url}

    async def stop(self, url: str) -> dict[str, Any]:
        """Stop the run (if any) and hand the world back to the player."""
        run = self.running(url)
        if run:
            run.task.cancel()
            await asyncio.gather(run.task, return_exceptions=True)
        else:
            await _hand_back(url)  # e.g. a run of an earlier harness process
        return {"status": "stopped", "world_url": url}

    async def stop_all(self) -> None:
        for url in list(self.runs):
            await self.stop(url)

    def status(self, url: str) -> dict[str, Any]:
        run = self.running(url)
        return {
            "world_url": url,
            "running": run is not None,
            "agent": run.agent.name if run else None,
            "seconds": round(time.monotonic() - run.started, 1) if run else 0.0,
            "pace": self.pace_of(url),
            "last": self.last.get(url),
        }

    async def _play(self, url: str, agent: AgentConfig, model: Model) -> None:
        try:
            result = await run_episode(
                url,
                agent,
                None,
                None,
                self.budget,
                model,
                reset=False,
                finish=False,
                pace=lambda: self.pace_of(url),
            )
            self.last[url] = result.to_dict()
        except asyncio.CancelledError:
            self.last[url] = {"agent": agent.name, "stopped_by": "stopped"}
            raise
        except Exception as e:  # world gone, model error, ...: report, hand back
            error = f"{type(e).__name__}: {e}"
            self.last[url] = {
                "agent": agent.name,
                "stopped_by": "error",
                "error": error,
            }
        finally:
            await _hand_back(url)


async def _hand_back(url: str) -> None:
    try:
        async with WorldClient(url) as world:
            await world.set_mode("you")
    except httpx.HTTPError:
        pass  # world is gone; nothing to hand back


def _url(body: dict[str, Any]) -> str:
    url = body.get("world_url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise HTTPException(400, "body needs {world_url}")
    return url.rstrip("/")


def create_app(runner: Runner) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await runner.stop_all()

    app = FastAPI(title="PlanWorld harness", lifespan=lifespan)

    @app.get("/agents")
    async def get_agents() -> list[dict[str, Any]]:
        return [
            {"name": a.name, "label": a.display, "color": a.color, "model": a.model}
            for a in runner.agents().values()
        ]

    @app.post("/run")
    async def post_run(body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        url = _url(body)
        try:
            return await runner.start(url, str(body.get("agent") or ""))
        except KeyError as e:
            raise HTTPException(400, str(e.args[0])) from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
        except RuntimeError as e:  # missing API key
            raise HTTPException(400, str(e)) from e
        except httpx.HTTPError as e:
            raise HTTPException(502, f"world not reachable at {url}: {e}") from e

    @app.post("/stop")
    async def post_stop(body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        return await runner.stop(_url(body))

    @app.post("/pace")
    async def post_pace(body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        seconds = body.get("seconds")
        if not isinstance(seconds, int | float):
            raise HTTPException(400, "body needs {world_url, seconds}")
        return runner.set_pace(_url(body), seconds)

    @app.get("/status")
    async def get_status(world_url: str) -> dict[str, Any]:
        return runner.status(world_url.rstrip("/"))

    return app
