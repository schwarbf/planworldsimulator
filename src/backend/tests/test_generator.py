import json
import shutil
import sys
from pathlib import Path

import pytest
from planworldsimulator_backend import worldproc
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.generator import GenerationRequest, prompts, workspace
from planworldsimulator_backend.generator.opencode_generator import (
    GenerationFailed,
    OpenCodeGenerator,
)
from planworldsimulator_backend.generator.opencode_runner import (
    AgentConfig,
    parse_event,
    run_agent,
)
from planworldsimulator_backend.launcher import ProcessLauncher, WorldUnavailable

REPO = Path(__file__).resolve().parents[3]
TEMPLATE = REPO / "src" / "worlds-template"
FAKE = Path(__file__).parent / "fake_opencode.py"
HAS_ENV = (TEMPLATE / ".pixi" / "envs" / "default" / "bin" / "python").exists()
HAS_UI = (TEMPLATE / "ui" / "node_modules").is_dir()
needs_template_env = pytest.mark.skipif(
    not (HAS_ENV and HAS_UI),
    reason="run `pixi install` and `npm ci` in src/worlds-template first",
)


def agent_config(world: Path) -> AgentConfig:
    return AgentConfig(str(FAKE), "m", "", "key", workspace.agent_config(world, ()))


# ---------- pieces ----------


def test_parse_event_reads_tool_calls_relative_to_the_world(tmp_path: Path) -> None:
    line = json.dumps(
        {
            "type": "tool_use",
            "sessionID": "ses_1",
            "part": {
                "tool": "write",
                "state": {
                    "status": "completed",
                    "input": {"filePath": str(tmp_path / "sim" / "env.py")},
                },
            },
        }
    )
    session, event = parse_event(line, tmp_path)
    assert session == "ses_1"
    assert event is not None
    assert (event.kind, event.tool, event.path, event.status) == (
        "tool",
        "write",
        "sim/env.py",
        "completed",
    )
    assert parse_event("not json", tmp_path) == (None, None)


def test_sections_of_a_design() -> None:
    design = "## Storyline\nA shop.\n\n## Sites\n- a\n"
    assert prompts.section(design, "Storyline") == "A shop."
    assert "Actions" in prompts.missing_sections(design)


def test_agent_may_only_edit_its_files(tmp_path: Path) -> None:
    config = workspace.agent_config(tmp_path, ("brief.md",))
    edit = config["permission"]["edit"]
    assert edit["*"] == "deny"
    root = str(tmp_path.resolve()).lstrip("/")
    assert edit[f"{root}/brief.md"] == "allow"
    assert config["permission"]["external_directory"] == "deny"
    assert config["permission"]["bash"] == "deny"


def test_base_files_are_guarded(tmp_path: Path) -> None:
    template = tmp_path / "template"
    (template / "server").mkdir(parents=True)
    (template / "server" / "api.py").write_text("base")
    (template / "brief.md").write_text("gen")
    world = tmp_path / "world"
    workspace.copy_template(template, world, None)
    assert workspace.changed_base_files(template, world) == []
    (world / "brief.md").write_text("the agent may edit this")
    (world / "extra.txt").write_text("stray")
    assert workspace.changed_base_files(template, world) == []
    assert workspace.stray_files(template, world) == ["extra.txt"]
    (world / "server" / "api.py").write_text("tampered")
    assert workspace.changed_base_files(template, world) == ["server/api.py"]


# ---------- the agent process ----------


async def test_run_agent_streams_events_and_reports_success(tmp_path: Path) -> None:
    events = []
    result = await run_agent(
        "hello",
        cwd=tmp_path,
        config=agent_config(tmp_path),
        timeout=10,
        on_event=events.append,
    )
    assert result.ok and result.session_id == "ses_fake" and result.tokens == 123
    assert [e.kind for e in events] == ["text", "step_finish"]


async def test_run_agent_times_out(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_OPENCODE", "hang")
    result = await run_agent(
        "hi", cwd=tmp_path, config=agent_config(tmp_path), timeout=0.5
    )
    assert result.timed_out and not result.ok and result.seconds < 8


async def test_run_agent_stops_runaway_tool_calls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FAKE_OPENCODE", "chatty")
    result = await run_agent(
        "hi", cwd=tmp_path, config=agent_config(tmp_path), timeout=10, max_tool_calls=2
    )
    assert result.too_many_calls and not result.ok


async def test_run_agent_without_the_binary(tmp_path: Path) -> None:
    config = AgentConfig("/nonexistent/opencode", "m", "", "k")
    result = await run_agent("hi", cwd=tmp_path, config=config, timeout=5)
    assert not result.ok and "cannot start" in result.error


# ---------- the whole pipeline, with a fake agent ----------


def two_site_template(tmp_path: Path) -> Path:
    """The template with a second site, as the design (at least two sites) says."""
    copy = tmp_path / "template"
    shutil.copytree(
        TEMPLATE,
        copy,
        ignore=shutil.ignore_patterns(
            ".pixi", "node_modules", "dist", "__pycache__", "__samples__"
        ),
    )
    (copy / "ui" / "node_modules").symlink_to(TEMPLATE / "ui" / "node_modules")
    env = copy / "sim" / "env.py"
    env.write_text(env.read_text().replace('["shop"]', '["shop", "outlet"]'))
    return copy


def settings_for(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        generator="opencode",
        opencode_bin=str(FAKE),
        gemini_api_key="key",
        worlds_dir=tmp_path / "worlds",
        template_dir=two_site_template(tmp_path),
        world_python=TEMPLATE / ".pixi" / "envs" / "default" / "bin" / "python",
        reference_dir=None,
        **overrides,
    )


async def no_owner(_title: str, _own: str) -> str | None:
    return None


REQUEST = GenerationRequest("shop-abc123", "Shop", "A tiny shop", 1)


@needs_template_env
async def test_pipeline_publishes_a_world_that_passes_every_gate(
    tmp_path: Path,
) -> None:
    generator = OpenCodeGenerator(settings_for(tmp_path), no_owner)
    events = [e async for e in generator.run(REQUEST)]

    done = [e.step for e in events if e.state == "done"]
    assert done[:3] == ["check_exists", "copy_template", "design"]
    assert set(done[3:5]) == {"sim", "ui"}
    assert done[5:] == ["tests", "smoke", "publish"]
    storylines = [e.storyline for e in events if e.step == "design" and e.storyline]
    assert storylines and storylines[0].startswith("A tiny shop")
    world = tmp_path / "worlds" / "shop-abc123"
    meta = json.loads((world / "world.json").read_text())
    assert meta["levels"] == [1, 2, 3] and meta["gates"]["ok"] is True
    assert not (world / "reference").exists()
    assert events[-1].path == str(world)


async def test_pipeline_stops_when_the_name_is_taken(tmp_path: Path) -> None:
    async def taken(_title: str, _own: str) -> str | None:
        return "shop-111111"

    generator = OpenCodeGenerator(settings_for(tmp_path), taken)
    events = [e async for e in generator.run(REQUEST)]
    assert [(e.step, e.state) for e in events][-1] == ("check_exists", "exists")
    assert events[-1].duplicate_of == "shop-111111"
    assert not (tmp_path / "worlds" / "shop-abc123").exists()


@needs_template_env
async def test_pipeline_rejects_an_agent_that_edits_base_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FAKE_OPENCODE", "tamper")
    generator = OpenCodeGenerator(settings_for(tmp_path), no_owner)
    with pytest.raises(GenerationFailed, match="read-only template"):
        _ = [e async for e in generator.run(REQUEST)]


async def test_pipeline_fails_when_the_design_is_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FAKE_OPENCODE", "silent")
    settings = settings_for(tmp_path)
    with pytest.raises(GenerationFailed, match="design is incomplete"):
        _ = [e async for e in OpenCodeGenerator(settings, no_owner).run(REQUEST)]


# ---------- running a world ----------


@needs_template_env
async def test_process_launcher_runs_and_stops_a_world(tmp_path: Path) -> None:
    python = worldproc.resolve_world_python(TEMPLATE, None)
    launcher = ProcessLauncher(TEMPLATE.parent, python)
    port = await launcher.start("worlds-template", str(TEMPLATE))
    try:
        assert await launcher.start("worlds-template", str(TEMPLATE)) == port
        import httpx

        async with httpx.AsyncClient() as http:
            assert (
                await http.get(f"http://127.0.0.1:{port}/api/state")
            ).status_code == 200
    finally:
        await launcher.stop("worlds-template")
    with pytest.raises(WorldUnavailable):
        await launcher.start("nothing-here", None)
    assert sys.version_info >= (3, 13)


@needs_template_env
async def test_pipeline_asks_the_agent_to_correct_a_broken_design(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FAKE_OPENCODE", "badjson")
    generator = OpenCodeGenerator(settings_for(tmp_path), no_owner)
    events = [e async for e in generator.run(REQUEST)]
    assert any(e.message == "Correcting the design" for e in events)
    assert events[-1].step == "publish" and events[-1].state == "done"
