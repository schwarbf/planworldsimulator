"""The quality gates a generated world must pass before it goes live."""

import asyncio
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from planworldsimulator_backend import worldproc
from planworldsimulator_backend.generator.processes import reap

TAIL = 2500  # characters of output kept per gate


@dataclass
class GateResult:
    name: str
    ok: bool
    output: str = ""
    seconds: float = 0.0
    track: str = "sim"  # which agent track fixes it: sim | ui


@dataclass
class GateReport:
    results: list[GateResult]

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def failed(self, track: str | None = None) -> list[GateResult]:
        return [
            r for r in self.results if not r.ok and (track is None or r.track == track)
        ]

    def as_json(self) -> dict:
        return {"ok": self.ok, "gates": [asdict(r) for r in self.results]}

    def summary(self) -> str:
        return ", ".join(
            f"{r.name}: {'ok' if r.ok else 'FAILED'}" for r in self.results
        )


async def _run(
    name: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    track: str,
) -> GateResult:
    started = time.monotonic()
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            start_new_session=True,
            cwd=cwd,
            env=env,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except OSError as exc:
        return GateResult(name, False, f"cannot run {command[0]}: {exc}", 0, track)
    try:
        out, _ = await asyncio.wait_for(process.communicate(), timeout)
        ok = process.returncode == 0
    except TimeoutError:
        out, ok = f"timed out after {timeout:.0f}s".encode(), False
    finally:
        await reap(process)
    text = out.decode(errors="replace")
    return GateResult(name, ok, text[-TAIL:], time.monotonic() - started, track)


def _env(world_dir: Path) -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(world_dir), "CI": "1"}


async def run_backend_gate(
    world_dir: Path, python: Path, timeout: float = 90
) -> GateResult:
    """pytest: contract, rules, MCP, API, demand, playability, no-leak, UI samples."""
    return await _run(
        "backend tests",
        [
            str(python),
            "-m",
            "pytest",
            "tests/backend",
            "-q",
            "--maxfail=8",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            "--no-header",
        ],
        world_dir,
        _env(world_dir),
        timeout,
        "sim",
    )


async def run_typecheck(world_dir: Path, timeout: float = 90) -> GateResult:
    return await _run(
        "ui typecheck",
        ["npx", "--no-install", "tsc", "-b"],
        world_dir / "ui",
        _env(world_dir),
        timeout,
        "ui",
    )


async def run_ui_tests(world_dir: Path, timeout: float = 90) -> GateResult:
    """Vitest; needs the state samples that the backend gate dumps."""
    return await _run(
        "ui tests",
        ["npx", "--no-install", "vitest", "run"],
        world_dir / "ui",
        _env(world_dir),
        timeout,
        "ui",
    )


async def run_gates(world_dir: Path, python: Path) -> GateReport:
    # The type check does not depend on the backend, so they run side by side; the UI
    # contract test reads the state samples written by the backend gate.
    backend, typecheck = await asyncio.gather(
        run_backend_gate(world_dir, python), run_typecheck(world_dir)
    )
    results = [backend, typecheck]
    if backend.ok:
        results.append(await run_ui_tests(world_dir))
    return GateReport(results)


async def build_ui(world_dir: Path, timeout: float = 90) -> GateResult:
    return await _run(
        "ui build",
        ["npx", "--no-install", "vite", "build"],
        world_dir / "ui",
        _env(world_dir),
        timeout,
        "ui",
    )


async def smoke(
    world_dir: Path, python: Path, levels: int = 3, timeout: float = 30
) -> GateResult:
    """Boot the world and talk to it like the website and the agent will."""
    started = time.monotonic()
    port = worldproc.free_port()
    process = await worldproc.start_world(world_dir, python, port)
    base = f"http://127.0.0.1:{port}"
    try:
        async with asyncio.timeout(timeout):
            return await _smoke_requests(base, port, process, levels, timeout, started)
    except Exception as exc:
        return GateResult(
            "smoke",
            False,
            str(exc) or "Smoke check timed out",
            time.monotonic() - started,
            "sim",
        )
    finally:
        await worldproc.stop_world(process)


async def _smoke_requests(base, port, process, levels, timeout, started):
    await worldproc.wait_healthy(port, process, timeout)
    async with httpx.AsyncClient(timeout=10) as http:
        page = await http.get(f"{base}/")
        if page.status_code != 200 or '<div id="root"' not in page.text:
            raise RuntimeError(
                f"GET / returned {page.status_code} without the app (UI built?)"
            )
        for level in range(1, levels + 1):
            reset = await http.post(
                f"{base}/api/reset", json={"level": level, "seed": 1}
            )
            reset.raise_for_status()
            state = await http.get(f"{base}/api/state")
            state.raise_for_status()
            if "week" not in state.json():
                raise RuntimeError("/api/state has no week")
            (await http.post(f"{base}/api/advance")).raise_for_status()
        initialize = await http.post(
            f"{base}/mcp",
            headers={"Accept": "application/json, text/event-stream"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke", "version": "0"},
                },
            },
        )
        if initialize.status_code != 200:
            raise RuntimeError(f"MCP initialize returned {initialize.status_code}")
    return GateResult(
        "smoke", True, f"booted on :{port}", time.monotonic() - started, "sim"
    )
