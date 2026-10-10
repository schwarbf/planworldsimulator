"""The real generator: OpenCode + Gemini fill the template, the gates prove it."""

import asyncio
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
from planworldsimulator_backend.generator.opencode_runner import (
    AgentConfig,
    AgentEvent,
    run_agent,
)

log = logging.getLogger(__name__)

NameLookup = Callable[[str, str], Awaitable[str | None]]  # (title, own id) -> owner id

# Per-phase cut-offs in seconds (decision 0005); the whole run has one deadline on top.
DESIGN_SECONDS = 60
FILL_SECONDS = 150
FIX_SECONDS = 60
MIN_FIX_SECONDS = 25


class GenerationFailed(Exception):
    pass


class Deadline:
    def __init__(self, seconds: float) -> None:
        self.end = time.monotonic() + seconds

    def left(self) -> float:
        return self.end - time.monotonic()

    def slice(self, cap: float, step: str) -> float:
        left = self.left()
        if left < 5:
            raise GenerationFailed(f"The time budget ran out before the {step} step.")
        return min(cap, left)


class OpenCodeGenerator:
    def __init__(self, settings: Settings, name_lookup: NameLookup) -> None:
        self.settings = settings
        self.name_lookup = name_lookup

    # ----- Generator protocol -----

    async def run(self, request: GenerationRequest) -> AsyncIterator[GenerationEvent]:
        queue: asyncio.Queue[GenerationEvent | None] = asyncio.Queue()
        task = asyncio.create_task(self._pipeline(request, queue.put_nowait))
        task.add_done_callback(lambda _t: queue.put_nowait(None))
        try:
            while (event := await queue.get()) is not None:
                yield event
            await task  # re-raises GenerationFailed and unexpected errors
        finally:
            if not task.done():
                task.cancel()

    # ----- pipeline -----

    async def _pipeline(
        self, request: GenerationRequest, emit: Callable[[GenerationEvent], None]
    ) -> None:
        s = self.settings
        deadline = Deadline(s.generation_deadline_seconds)
        world_dir = (s.worlds_dir / request.world_id).resolve()
        template = s.template_dir.resolve()
        python = worldproc.resolve_world_python(template, s.world_python)

        def step(name: str, state: str, message: str = "", **extra: str | None) -> None:
            emit(GenerationEvent(name, state, message, **extra))  # type: ignore[arg-type]

        # 1. the name must be free
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

        # 2. copy the template (and a read-only example world)
        step("copy_template", "started", "Copying the base template")
        shutil.rmtree(world_dir, ignore_errors=True)
        await asyncio.to_thread(
            workspace.copy_template,
            template,
            world_dir,
            s.reference_dir.resolve() if s.reference_dir else None,
        )
        step("copy_template", "done", "Copied src/worlds-template", path=str(world_dir))

        def agent(writable: tuple[str, ...]) -> AgentConfig:
            return AgentConfig(
                binary=s.opencode_bin,
                model=s.generator_model,
                variant=s.generator_variant,
                gemini_api_key=s.gemini_api_key,
                config=workspace.agent_config(world_dir, writable),
            )

        def progress(name: str) -> Callable[[AgentEvent], None]:
            def on_event(event: AgentEvent) -> None:
                if (
                    event.kind == "tool"
                    and event.tool in ("write", "edit")
                    and event.status == "completed"
                ):
                    step(name, "started", f"Wrote {event.path}")

            return on_event

        # 3. design
        step("design", "started", "Designing the world")
        design = await run_agent(
            prompts.render(
                "design",
                title=request.title,
                description=request.prompt,
                seed=str(request.seed),
                readme=prompts.read(world_dir, "README.md"),
            ),
            cwd=world_dir,
            config=agent(workspace.DESIGN_FILES),
            timeout=deadline.slice(DESIGN_SECONDS, "design"),
            max_tool_calls=s.max_tool_calls,
            on_event=progress("design"),
        )
        design_md = world_dir / "design.md"
        text = design_md.read_text() if design_md.is_file() else ""
        if missing := prompts.missing_sections(text):
            raise GenerationFailed(
                f"The design is incomplete ({design.summary}); "
                f"missing sections: {', '.join(missing)}."
            )
        storyline = prompts.section(text, "Storyline")
        step("design", "done", "Design ready", storyline=storyline)

        # 4. fill: simulator and web view in parallel
        step("fill", "started", "Writing the simulator and the world view")
        design_text = prompts.read(world_dir, "design.md")
        sim_prompt = prompts.render(
            "fill_sim",
            title=request.title,
            description=request.prompt,
            design=design_text,
            files=", ".join(f"`{f}`" for f in workspace.SIM_FILES),
            readme=prompts.read(world_dir, "README.md"),
            demand_api=prompts.demand_api(world_dir),
            placeholders="\n\n".join(
                prompts.fenced(world_dir, f) for f in workspace.SIM_FILES
            ),
        )
        ui_prompt = prompts.render(
            "fill_ui",
            title=request.title,
            description=request.prompt,
            design=design_text,
            kit_readme=prompts.read(world_dir, "ui/src/shared/kit/README.md"),
            types=prompts.fenced(world_dir, "ui/src/shared/types.ts"),
            placeholder=prompts.fenced(world_dir, "ui/src/World.tsx"),
        )
        fill_timeout = deadline.slice(FILL_SECONDS, "fill")
        sim, ui = await asyncio.gather(
            run_agent(
                sim_prompt,
                cwd=world_dir,
                config=agent(workspace.SIM_FILES),
                timeout=fill_timeout,
                max_tool_calls=s.max_tool_calls,
                on_event=progress("fill"),
            ),
            run_agent(
                ui_prompt,
                cwd=world_dir,
                config=agent(workspace.UI_FILES),
                timeout=fill_timeout,
                max_tool_calls=s.max_tool_calls,
                on_event=progress("fill"),
            ),
        )
        sessions = {"sim": sim.session_id, "ui": ui.session_id}
        step("fill", "done", f"Simulator: {sim.summary}; world view: {ui.summary}")

        # 5. gates, with fix rounds
        report = await self._test_loop(
            world_dir, template, python, deadline, sessions, agent, step, progress
        )
        if not report.ok:
            names = ", ".join(r.name for r in report.failed())
            raise GenerationFailed(
                f"The tests did not pass ({names}).\n{report.failed()[0].output[-800:]}"
            )

        # 6. build and boot
        step("smoke", "started", "Building the UI and booting the world")
        build = await gates.build_ui(world_dir)
        smoke = (
            build if not build.ok else await gates.smoke(world_dir, python, len(LEVELS))
        )
        if not smoke.ok:
            raise GenerationFailed(f"{smoke.name} failed:\n{smoke.output[-800:]}")
        step("smoke", "done", smoke.output)

        # 7. publish
        step("publish", "started", "Publishing")
        stray = workspace.stray_files(template, world_dir)
        if stray:
            raise GenerationFailed(
                f"Unexpected files in the world: {', '.join(stray[:5])}"
            )
        workspace.remove_reference(world_dir)
        (world_dir / "world.json").write_text(
            json.dumps(
                {
                    "id": request.world_id,
                    "name": request.title,
                    "prompt": request.prompt,
                    "seed": request.seed,
                    "levels": list(LEVELS),
                    "storyline": storyline,
                    "model": s.generator_model,
                    "gates": report.as_json(),
                },
                indent=2,
            )
        )
        step("publish", "done", "Published", path=str(world_dir))

    async def _test_loop(
        self, world_dir, template, python, deadline, sessions, agent, step, progress
    ):
        s = self.settings
        report = gates.GateReport([])
        for attempt in range(s.fix_rounds + 1):
            step(
                "tests",
                "started",
                "Running the tests"
                if attempt == 0
                else f"Running the tests again (fix round {attempt})",
            )
            if changed := workspace.changed_base_files(template, world_dir):
                raise GenerationFailed(
                    f"The agent changed base files: {', '.join(changed[:5])}"
                )
            report = await gates.run_gates(world_dir, python)
            step("tests", "started", report.summary())
            if report.ok:
                step("tests", "done", "All checks passed")
                return report
            if attempt == s.fix_rounds or deadline.left() < MIN_FIX_SECONDS + 15:
                break
            timeout = deadline.slice(FIX_SECONDS, "fix")
            fixes = []
            for track, writable, extra in (
                ("sim", workspace.SIM_FILES, ""),
                (
                    "ui",
                    workspace.UI_FILES,
                    "`ui/src/__samples__/*.json` is the real server state; make "
                    "`mockState`, "
                    "`toControls` and the view agree with it.",
                ),
            ):
                failed = report.failed(track)
                if not failed:
                    continue
                prompt = prompts.render(
                    "fix",
                    files=", ".join(f"`{f}`" for f in writable),
                    extra=extra,
                    failures="\n\n".join(
                        f"### {r.name}\n```\n{r.output}\n```" for r in failed
                    ),
                )
                fixes.append(
                    run_agent(
                        prompt,
                        cwd=world_dir,
                        config=agent(writable),
                        timeout=timeout,
                        max_tool_calls=s.max_tool_calls,
                        session_id=sessions.get(track),
                        on_event=progress("tests"),
                    )
                )
            await asyncio.gather(*fixes)
        step("tests", "failed", report.summary())
        return report
