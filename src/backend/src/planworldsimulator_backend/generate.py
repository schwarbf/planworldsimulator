"""Generate one world from the command line, without the website or the database.

    pixi run python -m planworldsimulator_backend.generate "Lemonade" "A stand ..."

Uses the settings from the environment (PLANWORLDSIMULATOR_*, GEMINI_API_KEY).
"""

import argparse
import asyncio
import secrets
import time

from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.generator import GenerationRequest
from planworldsimulator_backend.generator.exists import slug
from planworldsimulator_backend.generator.opencode_generator import OpenCodeGenerator


async def _no_owner(_title: str, _own_id: str) -> str | None:
    return None


async def main(name: str, prompt: str, seed: int | None) -> int:
    settings = Settings(generator="opencode")
    request = GenerationRequest(
        world_id=f"{slug(name)[:24].strip('-') or 'world'}-{secrets.token_hex(3)}",
        title=name,
        prompt=prompt,
        seed=seed if seed is not None else secrets.randbelow(10_000),
    )
    started = time.monotonic()
    print(
        f"world {request.world_id} (budget {settings.generation_deadline_seconds:.0f}s)"
    )
    try:
        async for event in OpenCodeGenerator(settings, _no_owner).run(request):
            at = time.monotonic() - started
            line = f"{event.step:<14} {event.state:<8} {event.message}"
            print(f"{at:6.1f}s  {line}")
    except Exception as exc:
        print(f"{time.monotonic() - started:6.1f}s  FAILED: {exc}")
        return 1
    path = settings.worlds_dir / request.world_id
    print(f"done in {time.monotonic() - started:.0f}s: {path}")
    return 0


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one world from the command line."
    )
    parser.add_argument("name")
    parser.add_argument("prompt")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.name, args.prompt, args.seed)))


if __name__ == "__main__":
    cli()
