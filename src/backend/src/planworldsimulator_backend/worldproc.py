"""Start and stop a world's server (/api, /mcp and the built UI) as a subprocess."""

import asyncio
import contextlib
import os
import socket
import time
from pathlib import Path

import httpx


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def resolve_world_python(template_dir: Path, configured: Path | None) -> Path:
    """The shared interpreter that runs every world (its dependencies are [base])."""
    python = (
        configured or template_dir / ".pixi" / "envs" / "default" / "bin" / "python"
    )
    if not python.exists():
        raise RuntimeError(
            f"world interpreter not found at {python}; run "
            "`pixi install --manifest-path src/worlds-template/pixi.toml`"
        )
    return python


async def start_world(
    world_dir: Path, python: Path, port: int
) -> asyncio.subprocess.Process:
    env = {**os.environ, "PYTHONPATH": str(world_dir), "PORT": str(port)}
    return await asyncio.create_subprocess_exec(
        str(python),
        "-m",
        "uvicorn",
        "server.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
        cwd=world_dir,
        env=env,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )


async def wait_healthy(
    port: int, process: asyncio.subprocess.Process, timeout: float
) -> None:
    """Return when /healthz answers; raise if the process dies or the timeout passes."""
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(timeout=2) as http:
        while time.monotonic() < deadline:
            if process.returncode is not None:
                error = b""
                if process.stderr is not None:
                    error = await process.stderr.read()
                raise RuntimeError(
                    f"world server exited with {process.returncode}: "
                    f"{error.decode(errors='replace')[-600:]}"
                )
            try:
                if (
                    await http.get(f"http://127.0.0.1:{port}/healthz")
                ).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.15)
    raise RuntimeError(
        f"world server did not answer on port {port} within {timeout:.0f}s"
    )


async def stop_world(process: asyncio.subprocess.Process) -> None:
    if process.returncode is None:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), 5)
        except TimeoutError:
            process.kill()
            with contextlib.suppress(Exception):
                await process.wait()
