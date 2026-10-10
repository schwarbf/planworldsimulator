"""Compare repeatable world-generation runs without the website or database.

Use a separate output directory for each revision; all artifacts stay there.
"""

import argparse
import asyncio
import json
import secrets
import statistics
import time
from pathlib import Path

from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.generator import GenerationRequest
from planworldsimulator_backend.generator.exists import slug
from planworldsimulator_backend.generator.opencode_generator import OpenCodeGenerator


async def benchmark(
    settings: Settings,
    cases: list[dict],
    output: Path,
    repeats: int = 2,
    concurrency: int = 1,
) -> dict:
    settings.worlds_dir = output / "worlds"
    output.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def lookup(_title, _own):
        return None

    async def run(case, repetition):
        async with semaphore:
            request = GenerationRequest(
                world_id=f"{slug(case['name'])[:20]}-{secrets.token_hex(3)}",
                title=case["name"],
                prompt=case["prompt"],
                seed=case["seed"],
            )
            started = time.monotonic()
            events = []
            row = {
                "name": case["name"],
                "seed": case["seed"],
                "repetition": repetition,
                "world_id": request.world_id,
            }
            try:
                async for event in OpenCodeGenerator(settings, lookup).run(request):
                    events.append(
                        {
                            "step": event.step,
                            "state": event.state,
                            "seconds": time.monotonic() - started,
                        }
                    )
                row["ok"] = True
            except Exception as exc:
                row.update(
                    ok=False,
                    error=str(exc),
                    failure_stage=events[-1]["step"] if events else "setup",
                )
            row["seconds"] = time.monotonic() - started
            row["events"] = events
            metrics = (
                settings.worlds_dir
                / ".generation"
                / f"{request.world_id}-attempt-1.json"
            )
            if metrics.is_file():
                row["metrics"] = json.loads(metrics.read_text())
            results.append(row)
            # Persist completed runs even if a later run is interrupted.
            (output / "runs.json").write_text(json.dumps(results, indent=2))
            print(
                f"{case['name']} #{repetition}: "
                f"{'ready' if row['ok'] else 'failed'} "
                f"in {row['seconds']:.1f}s",
                flush=True,
            )

    async with asyncio.TaskGroup() as group:
        for repetition in range(1, repeats + 1):
            for case in cases:
                group.create_task(run(case, repetition))
    durations = [r["seconds"] for r in results]
    successes = [r for r in results if r["ok"]]
    first_pass = [
        r for r in results if r.get("metrics", {}).get("first_pass") and r["ok"]
    ]
    summary = {
        "model": settings.generator_model,
        "variant": settings.generator_variant,
        "deadline_seconds": settings.generation_deadline_seconds,
        "fix_rounds": settings.fix_rounds,
        "concurrency": concurrency,
        "runs": len(results),
        "successes": len(successes),
        "median_seconds": statistics.median(durations),
        "slowest_seconds": max(durations),
        "successful_median_seconds": statistics.median(r["seconds"] for r in successes)
        if successes
        else None,
        "first_pass_successes": len(first_pass)
        if all("metrics" in r for r in results)
        else None,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases", type=Path, default=Path("benchmarks/world_generation.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--concurrency", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")
    settings = Settings(generator="opencode")
    print(
        json.dumps(
            asyncio.run(
                benchmark(
                    settings,
                    json.loads(args.cases.read_text()),
                    args.output,
                    args.repeats,
                    args.concurrency,
                )
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    cli()
