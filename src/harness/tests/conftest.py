import subprocess
import time
from pathlib import Path

import httpx
import pytest
from planworldsimulator_harness.benchmarks.servers import free_port

WORLD = Path(__file__).resolve().parents[2] / "worlds" / "bike-factory"


@pytest.fixture(scope="session")
def world_url():
    """A real bike-factory server, run from its own pixi env."""
    port = free_port()
    cmd = [
        "pixi",
        "run",
        "--manifest-path",
        str(WORLD / "pixi.toml"),
        "uvicorn",
        "server.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd, cwd=WORLD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(300):
            try:
                httpx.get(f"{url}/api/state", timeout=1).raise_for_status()
                break
            except httpx.HTTPError:
                time.sleep(0.2)
        else:
            raise RuntimeError("bike-factory server did not start")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=10)
