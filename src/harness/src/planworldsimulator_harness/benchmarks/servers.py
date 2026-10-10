"""Start world servers on free ports for benchmarks; stop them after."""

import asyncio
import socket
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx

from planworldsimulator_harness.config import WORLDS_DIR


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@asynccontextmanager
async def world_server(world: str, startup_seconds: float = 120) -> AsyncIterator[str]:
    """Run ``src/worlds/<world>`` from its own pixi env; yield its URL."""
    folder = Path(WORLDS_DIR / world)
    if not (folder / "pixi.toml").exists():
        raise FileNotFoundError(f"no world at {folder}")
    port = free_port()
    cmd = [
        "pixi",
        "run",
        "--manifest-path",
        str(folder / "pixi.toml"),
        "uvicorn",
        "server.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd, cwd=folder, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    url = f"http://127.0.0.1:{port}"
    try:
        await _wait_ready(url, proc, startup_seconds)
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


async def _wait_ready(url: str, proc: subprocess.Popen, seconds: float) -> None:
    async with httpx.AsyncClient(timeout=1) as http:
        for _ in range(int(seconds / 0.2)):
            if proc.poll() is not None:
                raise RuntimeError(f"world server exited with code {proc.returncode}")
            try:
                (await http.get(f"{url}/api/state")).raise_for_status()
                return
            except httpx.HTTPError:
                await asyncio.sleep(0.2)
    raise TimeoutError(f"world server at {url} did not start")
