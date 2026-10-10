"""Orchestration checks without paid model calls or generated-world dependencies."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.generator import gates, workspace
from planworldsimulator_backend.generator.base import GenerationRequest
from planworldsimulator_backend.generator.checkpoint import Checkpoint
from planworldsimulator_backend.generator.opencode_generator import (
    SAMPLES,
    GenerationFailed,
    OpenCodeGenerator,
)
from planworldsimulator_backend.generator.opencode_runner import AgentResult
from planworldsimulator_backend.generator.spec import BASE_STATE, StateField, WorldSpec


def example(field):
    if field.nullable:
        return None
    if field.type == "object":
        return {k: example(v) for k, v in field.properties.items()}
    if field.type == "array":
        return []
    return {
        "string": field.enum[0] if field.enum else "Example",
        "number": 1,
        "boolean": False,
    }[field.type]


@pytest.fixture
def spec_data():
    sample = {k: example(v) for k, v in BASE_STATE.items()}
    sample["weeks"] = 12
    return {
        "storyline": "Run a small factory.",
        "weeks": 12,
        "sites": [
            {"id": name, "description": name, "tile": [i, i]}
            for i, name in enumerate(("shop", "factory"))
        ],
        "actions": [
            {
                "name": "invest",
                "arguments": {"amount": {"type": "integer", "limits": "1 to 3"}},
                "description": "Invest",
            }
        ],
        "levels": {
            name: {"sites": ["shop", "factory"], "actions": ["invest"], "rules": name}
            for name in ("easy", "medium", "hard")
        },
        "hidden_rules": ["rule one", "rule two", "rule three"],
        "demand": "Price and weather",
        "scoring": "Profit",
        "state_fields": {},
        "state_sample": sample,
        "visual": {
            "palette": {
                "sky": "#FFFFFF",
                "tree": "#00FF00",
                "shop": "#333333",
                "ground": "#CCCCCC",
            },
            "grid_size": 6,
            "objects": ["Tree"] * 8,
            "animation": "Cloud",
        },
    }


@pytest.fixture
def harness(tmp_path, monkeypatch, spec_data):
    import planworldsimulator_backend.generator.opencode_generator as pipeline

    template = tmp_path / "template"
    template.mkdir()
    files = (
        workspace.SIM_FILES
        + workspace.UI_FILES
        + (
            "README.md",
            "ui/src/shared/kit/README.md",
            "ui/src/shared/types.ts",
            "sim/demand.py",
        )
    )
    for rel in files:
        target = template / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# placeholder\n" if rel.endswith(".py") else "placeholder\n")
    settings = Settings(
        worlds_dir=tmp_path / "worlds",
        template_dir=template,
        reference_dir=None,
        world_python=Path(sys.executable),
        fix_rounds=2,
    )
    calls = []
    backend_started = asyncio.Event()
    ui_started = asyncio.Event()
    release_sim = asyncio.Event()
    release_ui = asyncio.Event()
    release_sim.set()
    release_ui.set()
    control = {
        "build_failures": 0,
        "smoke_failures": 0,
        "hold": False,
        "backend_runs": 0,
    }

    async def agent(prompt, *, cwd, config, **kwargs):
        writable = config.config["permission"]["edit"]
        track = (
            "design"
            if any(p.endswith("design.json") for p in writable)
            else "ui"
            if any(p.endswith("World.tsx") for p in writable)
            else "sim"
        )
        calls.append(track)
        if track == "design":
            (cwd / "design.json").write_text(json.dumps(spec_data))
        else:
            await (release_sim if track == "sim" else release_ui).wait()
            for rel in workspace.SIM_FILES if track == "sim" else workspace.UI_FILES:
                (cwd / rel).write_text(f"generated {track} {calls.count(track)}")
        return AgentResult(
            ok=True, session_id=track, seconds=0.01, tokens=10, tool_calls=1
        )

    async def backend(world_dir, python, timeout):
        control["backend_runs"] += 1
        backend_started.set()
        if control["hold"]:
            await asyncio.Event().wait()
        for rel in SAMPLES:
            target = world_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(spec_data["state_sample"]))
        return gates.GateResult("backend tests", True)

    async def typecheck(world_dir, timeout):
        ui_started.set()
        return gates.GateResult("ui typecheck", True, track="ui")

    async def build(world_dir, timeout):
        if control["build_failures"]:
            control["build_failures"] -= 1
            return gates.GateResult("ui build", False, "Cannot build", track="ui")
        dist = world_dir / "ui/dist"
        dist.mkdir(exist_ok=True)
        (dist / "index.html").write_text("built")
        return gates.GateResult("ui build", True, track="ui")

    async def ui_tests(world_dir, timeout):
        assert all((world_dir / rel).is_file() for rel in SAMPLES)
        return gates.GateResult("ui tests", True, track="ui")

    async def smoke(*args, **kwargs):
        if control["smoke_failures"]:
            control["smoke_failures"] -= 1
            return gates.GateResult("smoke", False, "Cannot boot")
        return gates.GateResult("smoke", True)

    for name, value in (
        ("run_backend_gate", backend),
        ("run_typecheck", typecheck),
        ("build_ui", build),
        ("run_ui_tests", ui_tests),
        ("smoke", smoke),
    ):
        monkeypatch.setattr(gates, name, value)
    monkeypatch.setattr(pipeline, "run_agent", agent)

    async def lookup(*args):
        return None

    generator = OpenCodeGenerator(settings, lookup)
    request = GenerationRequest("factory-test", "Factory", "A factory", 42)
    events = []

    async def run(attempt=1):
        from dataclasses import replace

        async for event in generator.run(replace(request, attempt=attempt)):
            events.append(event)

    return (
        settings,
        generator,
        calls,
        control,
        backend_started,
        ui_started,
        release_sim,
        release_ui,
        run,
        events,
    )


@pytest.mark.parametrize("slow", ["sim", "ui"])
async def test_validation_starts_before_other_agent_finishes(harness, slow):
    _, _, _, _, backend, ui, release_sim, release_ui, run, _ = harness
    release = release_sim if slow == "sim" else release_ui
    release.clear()
    task = asyncio.create_task(run())
    try:
        await asyncio.wait_for((ui if slow == "sim" else backend).wait(), 1)
        assert not task.done()
        release.set()
        await task
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_build_failure_repairs_ui_only(harness):
    settings, _, calls, control, *_, run, events = harness
    control["build_failures"] = 1
    await run()
    assert calls.count("ui") == 2
    assert calls.count("sim") == 1
    metrics = json.loads(
        (settings.worlds_dir / ".generation/factory-test-attempt-1.json").read_text()
    )
    assert metrics["repairs"] == {"sim": 0, "ui": 1}
    assert metrics["first_pass"] is False
    assert events[-1].step == "publish"


async def test_retry_preserves_successful_simulator(harness):
    settings, _, calls, control, *_, run, _ = harness
    settings.fix_rounds = 0
    control["build_failures"] = 1
    with pytest.raises(GenerationFailed):
        await run()
    before = control["backend_runs"]
    await run(attempt=2)
    assert calls == ["design", "sim", "ui"]
    assert control["backend_runs"] == before
    assert (settings.worlds_dir / "factory-test/world.json").is_file()


async def test_smoke_failure_revalidates_simulator_and_contract(harness):
    _, _, calls, control, *_, run, _ = harness
    control["smoke_failures"] = 1
    await run()
    assert calls.count("sim") == 2
    assert calls.count("ui") == 1
    assert control["backend_runs"] == 2


async def test_global_timeout_cancels_pending_validation(harness):
    settings, _, _, control, *_, run, _ = harness
    settings.generation_deadline_seconds = 0.1
    control["hold"] = True
    # Tiny deadline exercises the outer cap, not the normal final-stage reserve.
    from unittest.mock import patch

    import planworldsimulator_backend.generator.opencode_generator as pipeline

    with patch.object(pipeline, "FINAL_RESERVE_SECONDS", 0):
        with pytest.raises(GenerationFailed, match="time limit"):
            await run()
    metrics = json.loads(
        (settings.worlds_dir / ".generation/factory-test-attempt-1.json").read_text()
    )
    assert metrics["ok"] is False


async def test_template_change_invalidates_saved_work(harness):
    settings, _, calls, *_rest, run, _ = harness
    await run()
    (settings.template_dir / "README.md").write_text("Changed template")
    await run(attempt=2)
    assert calls.count("design") == 2
    assert calls.count("sim") == 2


def test_contract_validates_empty_arrays_nullability_and_enums(spec_data, tmp_path):
    spec = WorldSpec.model_validate(spec_data)
    spec.state.check(spec_data["state_sample"])
    changed = json.loads(json.dumps(spec_data["state_sample"]))
    changed["agent"]["scores"] = ["bad"]
    with pytest.raises(ValueError, match="scores"):
        spec.state.check(changed)
    changed["agent"]["scores"] = []
    changed["agent"]["mode"] = "invalid"
    with pytest.raises(ValueError, match="mode"):
        spec.state.check(changed)
    changed["agent"]["mode"] = "you"
    changed["week"] = None
    with pytest.raises(ValueError, match="week"):
        spec.state.check(changed)
    with pytest.raises(ValueError, match="items"):
        StateField(type="array")


def test_malformed_design_rejected_before_fill(spec_data):
    spec_data["levels"]["easy"]["actions"] = ["unknown"]
    with pytest.raises(ValueError, match="unknown"):
        WorldSpec.model_validate(spec_data)


def test_checkpoint_requires_complete_unchanged_artifacts(tmp_path):
    checkpoint = Checkpoint(tmp_path / "world", "identity")
    checkpoint.root.mkdir()
    (checkpoint.root / "one").write_text("first")
    checkpoint.save("sim", ("one", "two"))
    assert not checkpoint.valid("sim", ("one", "two"))
    (checkpoint.root / "two").write_text("second")
    checkpoint.save("sim", ("one", "two"))
    assert checkpoint.valid("sim", ("one", "two"))
    (checkpoint.root / "one").write_text("changed")
    assert not checkpoint.valid("sim", ("one", "two"))
    assert not Checkpoint(checkpoint.root, "new identity").valid("sim", ("one", "two"))


@pytest.mark.parametrize("cancel", [False, True])
async def test_gate_timeout_and_cancellation_reap_process(
    tmp_path, monkeypatch, cancel
):
    processes = []
    original = asyncio.create_subprocess_exec

    async def capture(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", capture)
    task = asyncio.create_task(
        gates._run(
            "sleep",
            [sys.executable, "-c", "import time; time.sleep(30)"],
            tmp_path,
            {},
            0.1 if not cancel else 30,
            "sim",
        )
    )
    while not processes:
        await asyncio.sleep(0.01)
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        assert not (await task).ok
    assert processes[0].returncode is not None


async def test_agent_timeout_reaps_reader_process_and_child(tmp_path):
    from planworldsimulator_backend.generator.opencode_runner import (
        AgentConfig,
        run_agent,
    )

    marker = tmp_path / "child-survived"
    executable = tmp_path / "agent"
    child = (
        "import time; from pathlib import Path; time.sleep(0.5); "
        f"Path({str(marker)!r}).touch()"
    )
    executable.write_text(
        f"#!{sys.executable}\n"
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
        "time.sleep(30)\n"
    )
    executable.chmod(0o755)
    result = await run_agent(
        "hello",
        cwd=tmp_path,
        config=AgentConfig(str(executable), "test", "", ""),
        timeout=0.15,
    )
    assert result.timed_out
    await asyncio.sleep(0.6)
    assert not marker.exists()


async def test_failed_spec_prevents_fill_calls(harness, monkeypatch):
    import planworldsimulator_backend.generator.opencode_generator as pipeline
    from planworldsimulator_backend.generator.opencode_runner import AgentResult

    _, _, calls, *_rest, run, _ = harness

    async def invalid_design(prompt, *, cwd, **kwargs):
        calls.append("design")
        (cwd / "design.json").write_text('{"storyline": "incomplete"}')
        return AgentResult(ok=True)

    monkeypatch.setattr(pipeline, "run_agent", invalid_design)
    with pytest.raises(GenerationFailed, match="design is incomplete"):
        await run()
    # The design and two correction rounds; no simulator or UI work follows.
    assert calls == ["design"] * 3
