"""Screenshots of a running world, for its thumbnail and the look check."""

import os
from pathlib import Path

from planworldsimulator_backend import worldproc

WIDTH, HEIGHT = 1440, 900
SETTLE_MS = 1800  # the world polls its state and animates; wait for a stable picture


def _browser_args() -> list[str]:
    # Chromium refuses to start as root without this; the Docker image sets it.
    return ["--no-sandbox"] if os.environ.get("PLANWORLDSIMULATOR_NO_SANDBOX") else []


class ScreenshotUnavailable(Exception):
    """Playwright or its browser is missing."""


async def capture_levels(
    world_dir: Path,
    python: Path,
    out_dir: Path,
    levels: tuple[int, ...] = (1, 2, 3),
    timeout: float = 30,
) -> list[Path]:
    """Boot the world, open it at each level and save `level-N.png` into `out_dir`."""
    try:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise ScreenshotUnavailable("playwright is not installed") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    port = worldproc.free_port()
    process = await worldproc.start_world(world_dir, python, port)
    paths: list[Path] = []
    try:
        await worldproc.wait_healthy(port, process, timeout)
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch(args=_browser_args())
            except PlaywrightError as exc:
                raise ScreenshotUnavailable(
                    "run `pixi run playwright install chromium`"
                ) from exc
            try:
                page = await browser.new_page(
                    viewport={"width": WIDTH, "height": HEIGHT}
                )
                for level in levels:
                    await page.goto(f"http://127.0.0.1:{port}/?level={level}")
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(SETTLE_MS)
                    path = out_dir / f"level-{level}.png"
                    await page.screenshot(path=path)
                    paths.append(path)
            finally:
                await browser.close()
    finally:
        await worldproc.stop_world(process)
    return paths
