import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from planworldsimulator_backend.generator import workspace
from planworldsimulator_backend.generator.base import (
    LEVELS,
    GenerationEvent,
    GenerationRequest,
)


def _template_has_content(template_dir: Path) -> bool:
    if not template_dir.is_dir():
        return False
    return any(p.name != ".gitkeep" for p in template_dir.iterdir())


class FakeGenerator:
    """Stands in for the coding-agent loop: emits the real steps, does no LLM work."""

    def __init__(self, worlds_dir: Path, template_dir: Path, delay: float) -> None:
        self.worlds_dir = worlds_dir
        self.template_dir = template_dir
        self.delay = delay

    async def run(self, request: GenerationRequest) -> AsyncIterator[GenerationEvent]:
        world_dir = self.worlds_dir / request.world_id

        yield GenerationEvent("check_exists", "started", "Checking the name")
        await asyncio.sleep(self.delay)
        yield GenerationEvent("check_exists", "done", "The name is free")

        yield GenerationEvent("copy_template", "started", "Copying the base template")
        await asyncio.sleep(self.delay)
        if _template_has_content(self.template_dir):
            # Same copy as the real generator: no environments, caches or build output.
            workspace.copy_template(self.template_dir, world_dir, None)
            note = "Copied src/worlds-template"
        else:
            world_dir.mkdir(parents=True, exist_ok=True)
            (world_dir / "README.md").write_text(
                f"# {request.title}\n\nStub world: the template is not available yet.\n"
            )
            note = "Template is empty, wrote a stub"
        yield GenerationEvent("copy_template", "done", note, path=str(world_dir))

        yield GenerationEvent("design", "started", "Writing the storyline")
        await asyncio.sleep(self.delay)
        storyline = (
            f"{request.title}. A hidden-dynamics planning world generated from: "
            f"“{request.prompt.strip()}” (seed {request.seed}, "
            f"{len(LEVELS)} difficulty levels)."
        )
        yield GenerationEvent("design", "done", "Storyline ready", storyline)

        yield GenerationEvent("sim", "started", "Filling the template")
        await asyncio.sleep(self.delay)
        (world_dir / "world.json").write_text(
            json.dumps(
                {
                    "id": request.world_id,
                    "name": request.title,
                    "prompt": request.prompt,
                    "seed": request.seed,
                    "levels": list(LEVELS),
                    "storyline": storyline,
                },
                indent=2,
            )
        )
        yield GenerationEvent("sim", "done", "Wrote world.json")

        yield GenerationEvent("ui", "started", "Writing the world view")
        yield GenerationEvent("ui", "done", "World view ready")

        for step, started, done in (
            ("tests", "Running tests", "All checks passed"),
            ("polish", "Looking at the world", "The world looks good"),
            ("smoke", "Booting the world", "The world starts"),
            ("publish", "Publishing", "Published"),
        ):
            yield GenerationEvent(step, "started", started)
            await asyncio.sleep(self.delay)
            yield GenerationEvent(step, "done", done)
