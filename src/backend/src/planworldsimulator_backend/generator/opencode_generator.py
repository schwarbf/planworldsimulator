"""Generate independent branches, validate early, and resume hash-verified work."""

import asyncio
import contextlib
import json
import logging
import shutil
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from planworldsimulator_backend import worldproc
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.generator import gates, prompts, workspace
from planworldsimulator_backend.generator.base import (
    LEVELS,
    GenerationEvent,
    GenerationRequest,
)
from planworldsimulator_backend.generator.checkpoint import (
    Checkpoint,
    fingerprint,
    hashes,
)
from planworldsimulator_backend.generator.opencode_runner import (
    AgentConfig,
    AgentEvent,
    run_agent,
)
from planworldsimulator_backend.generator.spec import BASE_STATE, WorldSpec

log = logging.getLogger(__name__)
NameLookup = Callable[[str, str], Awaitable[str | None]]
DESIGN_SECONDS = 60
FILL_SECONDS = 150
FIX_SECONDS = 60
MIN_FIX_SECONDS = 25
FINAL_RESERVE_SECONDS = 20
SAMPLES = tuple(
    f"ui/src/__samples__/{level}-{point}.json"
    for level in ("easy", "medium", "hard")
    for point in ("start", "week3", "end")
)


class GenerationFailed(Exception):
    pass


class Deadline:
    def __init__(self, seconds: float) -> None:
        self.end = time.monotonic() + seconds

    def left(self) -> float:
        return self.end - time.monotonic()

    def slice(self, cap: float, step: str, reserve: float = 0) -> float:
        left = self.left() - reserve
        if left <= 0:
            raise GenerationFailed(f"The time budget ran out before the {step} step.")
        return min(cap, left)


async def together(*coroutines):
    """Cancel and await sibling work when a branch fails or the run is cancelled."""
    tasks = [asyncio.create_task(c) for c in coroutines]
    try:
        return await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


class OpenCodeGenerator:
    def __init__(self, settings: Settings, name_lookup: NameLookup) -> None:
        self.settings = settings
        self.name_lookup = name_lookup

    async def run(self, request: GenerationRequest) -> AsyncIterator[GenerationEvent]:
        queue: asyncio.Queue[GenerationEvent | None] = asyncio.Queue()
        task = asyncio.create_task(self._pipeline(request, queue.put_nowait))
        task.add_done_callback(lambda _t: queue.put_nowait(None))
        try:
            while (event := await queue.get()) is not None:
                yield event
            await task
        finally:
            if not task.done():
                task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _pipeline(self, request, emit) -> None:
        started = time.monotonic()
        metrics = {
            "attempt": request.attempt,
            "stages": {},
            "agents": [],
            "repairs": {"sim": 0, "ui": 0},
            "first_pass": True,
        }
        active: dict[str, float] = {}

        def step(name, state, message="", **extra):
            now = time.monotonic()
            if state == "started":
                active.setdefault(name, now)
            elif state in ("done", "failed") and name in active:
                metrics["stages"][name] = (
                    metrics["stages"].get(name, 0) + now - active.pop(name)
                )
            if state in ("done", "failed"):
                extra.setdefault("metrics", {"seconds": metrics["stages"].get(name, 0)})
            emit(
                GenerationEvent(
                    name, state, message, elapsed_seconds=now - started, **extra
                )
            )

        try:
            async with asyncio.timeout(self.settings.generation_deadline_seconds):
                await self._generate(request, step, metrics)
            metrics["ok"] = True
        except TimeoutError as exc:
            metrics["ok"] = False
            raise GenerationFailed(
                "Generation reached its time limit. Retry to resume saved work."
            ) from exc
        except BaseException:
            metrics["ok"] = False
            raise
        finally:
            metrics["seconds"] = time.monotonic() - started
            metrics["stages"].update(
                {
                    k: metrics["stages"].get(k, 0) + time.monotonic() - v
                    for k, v in active.items()
                }
            )
            directory = self.settings.worlds_dir.resolve() / ".generation"
            directory.mkdir(parents=True, exist_ok=True)
            (
                directory / f"{request.world_id}-attempt-{request.attempt}.json"
            ).write_text(json.dumps(metrics, indent=2))
            log.info("generation metrics %s", json.dumps(metrics))

    async def _generate(self, request, step, metrics) -> None:
        s = self.settings
        deadline = Deadline(s.generation_deadline_seconds)
        world_dir = (s.worlds_dir / request.world_id).resolve()
        template = s.template_dir.resolve()
        python = worldproc.resolve_world_python(template, s.world_python)
        checkpoint = Checkpoint(world_dir, fingerprint(request, template, s))

        step("check_exists", "started", "Checking that the name is free")
        owner = await self.name_lookup(request.title, request.world_id)
        if owner is not None:
            step(
                "check_exists",
                "exists",
                f"A world called “{request.title}” already exists",
                duplicate_of=owner,
            )
            return
        step("check_exists", "done", "The name is free")

        step("copy_template", "started", "Preparing the world")
        design_files = tuple(workspace.DESIGN_FILES) + tuple(
            sorted(workspace.CONTRACT_FILES)
        )
        resume = checkpoint.valid(
            "design", design_files
        ) and not workspace.changed_base_files(template, world_dir)
        if not resume:
            checkpoint.data["stages"] = {}
            shutil.rmtree(world_dir, ignore_errors=True)
            # Avoid detached file writes after cancellation.
            workspace.copy_template(
                template,
                world_dir,
                s.reference_dir.resolve() if s.reference_dir else None,
            )
        else:
            workspace.link_node_modules(template, world_dir)
        step(
            "copy_template",
            "done",
            "Resuming saved work" if resume else "World prepared",
            path=str(world_dir),
        )

        def agent(writable):
            return AgentConfig(
                binary=s.opencode_bin,
                model=s.generator_model,
                variant=s.generator_variant,
                gemini_api_key=s.gemini_api_key,
                config=workspace.agent_config(world_dir, writable),
            )

        def progress(name):
            def on_event(event: AgentEvent):
                if (
                    event.kind == "tool"
                    and event.tool in ("write", "edit")
                    and event.status == "completed"
                ):
                    step(
                        name,
                        "started",
                        "Saving the world design"
                        if name == "design"
                        else "Writing world files",
                    )

            return on_event

        sessions: dict[str, str | None] = {}

        async def call(name, prompt, writable, cap, repair=False):
            result = await run_agent(
                prompt,
                cwd=world_dir,
                config=agent(writable),
                timeout=deadline.slice(cap, name, FINAL_RESERVE_SECONDS),
                max_tool_calls=s.max_tool_calls,
                session_id=sessions.get(name) if repair else None,
                on_event=progress(name),
            )
            sessions[name] = result.session_id
            metrics["agents"].append(
                {
                    "stage": name,
                    "repair": repair,
                    "seconds": result.seconds,
                    "tokens": result.tokens,
                    "tool_calls": result.tool_calls,
                    "ok": result.ok,
                }
            )
            return result

        step("design", "started", "Designing the world")
        if not resume:
            result = await call(
                "design",
                prompts.render(
                    "design",
                    title=request.title,
                    description=request.prompt,
                    seed=str(request.seed),
                    readme=prompts.read(world_dir, "README.md"),
                    design_path=str(world_dir / "design.json"),
                    spec_schema=json.dumps(
                        WorldSpec.model_json_schema(), separators=(",", ":")
                    ),
                    base_state=json.dumps(
                        {k: v.model_dump() for k, v in BASE_STATE.items()}, indent=2
                    ),
                ),
                workspace.DESIGN_FILES,
                DESIGN_SECONDS,
            )
            try:
                spec = WorldSpec.model_validate_json(
                    (world_dir / "design.json").read_text()
                )
            except (OSError, ValueError) as exc:
                raise GenerationFailed(
                    f"The design is incomplete ({result.summary}): {exc}"
                ) from exc
            spec.write_contract(world_dir)
            checkpoint.save("design", design_files)
        else:
            spec = WorldSpec.model_validate_json(
                (world_dir / "design.json").read_text()
            )
        step(
            "design",
            "done",
            "Saved design ready" if resume else "Design ready",
            storyline=spec.storyline,
        )
        contract_hashes = hashes(world_dir, design_files)

        def guard():
            changed = workspace.changed_base_files(template, world_dir)
            if changed or hashes(world_dir, design_files) != contract_hashes:
                raise GenerationFailed(
                    "The agent changed a read-only template or design contract."
                )

        design = spec.markdown()
        state_contract = prompts.fenced(world_dir, "ui/src/WorldState.ts")
        fill = {
            "sim": prompts.render(
                "fill_sim",
                title=request.title,
                description=request.prompt,
                design=design,
                files=", ".join(f"`{f}`" for f in workspace.SIM_FILES),
                readme=prompts.read(world_dir, "README.md"),
                demand_api=prompts.demand_api(world_dir),
                state_contract=state_contract,
                placeholders="\n\n".join(
                    prompts.fenced(world_dir, f) for f in workspace.SIM_FILES
                ),
            ),
            "ui": prompts.render(
                "fill_ui",
                title=request.title,
                description=request.prompt,
                design=design,
                kit_readme=prompts.read(world_dir, "ui/src/shared/kit/README.md"),
                types=prompts.fenced(world_dir, "ui/src/shared/types.ts"),
                placeholder=prompts.fenced(world_dir, "ui/src/World.tsx"),
                state_contract=state_contract,
            ),
        }
        files = {"sim": workspace.SIM_FILES, "ui": workspace.UI_FILES}
        repairs = metrics["repairs"]

        async def repair(track, failures):
            metrics["first_pass"] = False
            if (
                repairs[track] >= s.fix_rounds
                or deadline.left() < MIN_FIX_SECONDS + FINAL_RESERVE_SECONDS
            ):
                raise GenerationFailed(
                    f"The {track} checks did not pass: {failures[0].name}\n"
                    f"{failures[0].output[-800:]}"
                )
            repairs[track] += 1
            step(
                track,
                "started",
                f"Refining {'simulator' if track == 'sim' else 'world view'} "
                f"(round {repairs[track]})",
            )
            if track == "ui":
                shutil.rmtree(world_dir / "ui/dist", ignore_errors=True)
            await call(
                track,
                prompts.render(
                    "fix",
                    files=", ".join(f"`{f}`" for f in files[track]),
                    extra="Use the real state samples in ui/src/__samples__/*.json."
                    if track == "ui"
                    else "",
                    failures="\n\n".join(
                        f"### {r.name}\n```\n{r.output}\n```" for r in failures
                    ),
                    state_contract=state_contract,
                ),
                files[track],
                FIX_SECONDS,
                repair=True,
            )
            guard()
            checkpoint.save(track, files[track])

        async def validate_sim():
            guard()
            shutil.rmtree(world_dir / "ui/src/__samples__", ignore_errors=True)
            backend = await gates.run_backend_gate(
                world_dir,
                python,
                timeout=deadline.slice(90, "backend tests", FINAL_RESERVE_SECONDS),
            )
            results = [backend]
            if backend.ok:
                try:
                    for rel in SAMPLES:
                        value = json.loads((world_dir / rel).read_text())
                        spec.state.check(value)
                        if value["weeks"] != spec.weeks:
                            raise ValueError(
                                f"{rel}: episode length differs from design"
                            )
                    results.append(gates.GateResult("state contract", True))
                except (OSError, ValueError) as exc:
                    results.append(gates.GateResult("state contract", False, str(exc)))
            return results

        def build_files():
            return tuple(
                p.relative_to(world_dir).as_posix()
                for p in sorted((world_dir / "ui/dist").rglob("*"))
                if p.is_file()
            )

        async def validate_ui():
            guard()
            # These write different outputs: tsc build metadata and vite dist.
            return await together(
                gates.run_typecheck(
                    world_dir,
                    timeout=deadline.slice(90, "typecheck", FINAL_RESERVE_SECONDS),
                ),
                gates.build_ui(
                    world_dir,
                    timeout=deadline.slice(90, "UI build", FINAL_RESERVE_SECONDS),
                ),
            )

        async def branch(track):
            step(
                track,
                "started",
                "Writing the simulator"
                if track == "sim"
                else "Creating the world view",
            )
            if not checkpoint.valid(track, files[track]):
                await call(track, fill[track], files[track], FILL_SECONDS)
                guard()
                checkpoint.save(track, files[track])
            dependencies = files[track] + (SAMPLES if track == "sim" else build_files())
            cached = checkpoint.valid(f"{track}_checks", dependencies)
            # A build must have an index, not just a coincidentally empty directory.
            cached = cached and (
                track == "sim" or (world_dir / "ui/dist/index.html").is_file()
            )
            results = checkpoint.results(f"{track}_checks") if cached else []
            while True:
                if not results:
                    step(
                        track,
                        "started",
                        "Checking simulator behavior"
                        if track == "sim"
                        else "Checking and building the world view",
                    )
                    results = await (
                        validate_sim() if track == "sim" else validate_ui()
                    )
                failed = [r for r in results if not r.ok]
                if not failed:
                    dependencies = files[track] + (
                        SAMPLES if track == "sim" else build_files()
                    )
                    checkpoint.save(f"{track}_checks", dependencies, results)
                    step(
                        track,
                        "done",
                        "Simulator ready" if track == "sim" else "World view ready",
                    )
                    return results
                await repair(track, failed)
                results = []

        sim_results, ui_results = await together(branch("sim"), branch("ui"))
        # Cross-branch checks require both validated artifacts.
        while True:
            guard()
            step("tests", "started", "Checking the world view against the simulator")
            ui_tests = await gates.run_ui_tests(
                world_dir, timeout=deadline.slice(90, "UI tests", FINAL_RESERVE_SECONDS)
            )
            if not ui_tests.ok:
                await repair("ui", [ui_tests])
                ui_results = await branch("ui")
                continue
            step("tests", "done", "All behavior and rendering checks passed")
            step("smoke", "started", "Booting and checking the world")
            smoke = await gates.smoke(
                world_dir, python, len(LEVELS), timeout=deadline.slice(30, "smoke")
            )
            if not smoke.ok:
                await repair("sim", [smoke])
                sim_results = await branch("sim")
                continue
            step("smoke", "done", "The world starts and responds")
            break

        step("publish", "started", "Publishing")
        guard()
        if stray := workspace.stray_files(template, world_dir):
            raise GenerationFailed(
                f"Unexpected files in the world: {', '.join(stray[:5])}"
            )
        workspace.remove_reference(world_dir)
        report = gates.GateReport(sim_results + ui_results + [ui_tests, smoke])
        (world_dir / "world.json").write_text(
            json.dumps(
                {
                    "id": request.world_id,
                    "name": request.title,
                    "prompt": request.prompt,
                    "seed": request.seed,
                    "levels": list(LEVELS),
                    "storyline": spec.storyline,
                    "model": s.generator_model,
                    "gates": report.as_json(),
                },
                indent=2,
            )
        )
        step("publish", "done", "Published", path=str(world_dir), metrics=metrics)
