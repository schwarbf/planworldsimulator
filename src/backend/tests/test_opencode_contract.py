"""The real `opencode` binary with a scripted local model: no API key, no LLM.

Guards what the pipeline relies on: the agent may write the files of its track,
and nothing else. OpenCode matches edit permissions relative to the enclosing git
repository, so every layout a world can be generated in is covered (this broke
generation inside the repository before).
"""

import shutil
import subprocess
from pathlib import Path

import pytest
from fake_model import CONTENT, FakeModel
from planworldsimulator_backend.generator import workspace
from planworldsimulator_backend.generator.opencode_runner import AgentConfig, run_agent

pytestmark = pytest.mark.skipif(
    shutil.which("opencode") is None, reason="needs the opencode command"
)


def config(world: Path, model: FakeModel, writable: tuple[str, ...]) -> AgentConfig:
    permissions = workspace.agent_config(world, writable)
    provider = {
        "fake": {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Fake",
            "options": {"baseURL": model.base_url, "apiKey": "unused"},
            "models": {"scripted": {"name": "scripted"}},
        }
    }
    return AgentConfig(
        "opencode", "fake/scripted", "", "unused", permissions | {"provider": provider}
    )


async def write(world: Path, rel: str, writable: tuple[str, ...]):
    with FakeModel() as model:
        return await run_agent(
            f"WRITE {world.resolve() / rel}",
            cwd=world,
            config=config(world, model, writable),
            timeout=90,
        )


LAYOUTS = ("no git", "inside a git repo", "own git repo")


def make_world(tmp_path: Path, layout: str) -> Path:
    world = (
        tmp_path / "src" / "worlds" / "w" if layout == "inside a git repo" else tmp_path
    )
    (world / "server").mkdir(parents=True)
    if layout != "no git":
        repo = tmp_path if layout == "inside a git repo" else world
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return world


@pytest.mark.parametrize("layout", LAYOUTS)
async def test_agent_writes_the_file_of_its_track(tmp_path: Path, layout: str) -> None:
    world = make_world(tmp_path, layout)
    result = await write(world, "design.json", ("design.json",))
    assert result.ok, result.summary
    assert (world / "design.json").read_text() == CONTENT


@pytest.mark.parametrize("layout", LAYOUTS)
async def test_agent_cannot_write_other_files(tmp_path: Path, layout: str) -> None:
    world = make_world(tmp_path, layout)
    await write(world, "server/api.py", ("design.json",))
    assert not (world / "server" / "api.py").exists()
