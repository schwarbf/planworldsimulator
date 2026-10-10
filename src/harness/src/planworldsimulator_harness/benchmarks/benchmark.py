"""Run a suite: agents × seeds on one world → episodes.jsonl + event logs."""

import json
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from planworldsimulator_harness.agents import get_agent
from planworldsimulator_harness.benchmarks.servers import world_server
from planworldsimulator_harness.budget import Budget
from planworldsimulator_harness.client import WorldClient
from planworldsimulator_harness.config import RESULTS_DIR, SUITES_DIR
from planworldsimulator_harness.episode import EpisodeResult, run_episode


@dataclass(frozen=True)
class Suite:
    name: str
    world: str
    difficulty: str
    seeds: list[int]
    agents: list[str]
    budget: Budget


def load_suite(name_or_path: str) -> Suite:
    path = Path(name_or_path)
    if not path.exists():
        path = SUITES_DIR / f"{name_or_path}.toml"
    data = tomllib.loads(path.read_text())
    return Suite(
        name=path.stem,
        world=data["world"],
        difficulty=data.get("difficulty", "medium"),
        seeds=list(data["seeds"]),
        agents=list(data["agents"]),
        budget=Budget(**data.get("budget", {})),
    )


async def run_suite(suite: Suite, results_dir: Path = RESULTS_DIR) -> Path:
    """One fresh world server per episode, so every run starts from a clean state."""
    run_dir = results_dir / f"{datetime.now():%Y%m%d-%H%M%S}-{suite.name}"
    (run_dir / "events").mkdir(parents=True)
    for agent_name in suite.agents:
        agent = get_agent(agent_name)
        for seed in suite.seeds:
            async with world_server(suite.world) as url:
                result = await run_episode(
                    url, agent, seed, suite.difficulty, suite.budget
                )
                async with WorldClient(url) as world:
                    events = await world.events()
            _save(run_dir, suite, result, events)
            print(
                f"{agent_name} seed {seed}: score {result.score:.3f} "
                f"(baseline {result.baseline:.3f}), stopped by {result.stopped_by}"
            )
    return run_dir


def _save(run_dir: Path, suite: Suite, result: EpisodeResult, events: list) -> None:
    row = {"suite": suite.name, "world": suite.world, **result.to_dict()}
    with (run_dir / "episodes.jsonl").open("a") as f:
        f.write(json.dumps(row) + "\n")
    name = f"{result.agent}-seed{result.seed}.json"
    (run_dir / "events" / name).write_text(json.dumps(events, indent=1))
