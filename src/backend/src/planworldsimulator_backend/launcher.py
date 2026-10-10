import asyncio
from pathlib import Path
from typing import Protocol

from planworldsimulator_backend import worldproc


class Launcher(Protocol):
    async def start(self, world_id: str, path: str | None) -> int: ...

    async def stop(self, world_id: str) -> None: ...


class FakeLauncher:
    """Hands out ports without running anything. The real one runs `pixi run`."""

    BASE_PORT = 9000

    def __init__(self) -> None:
        self._ports: dict[str, int] = {}

    async def start(self, world_id: str, path: str | None) -> int:
        if world_id not in self._ports:
            self._ports[world_id] = self.BASE_PORT + len(self._ports)
        return self._ports[world_id]

    async def stop(self, world_id: str) -> None:
        return None


class WorldUnavailable(Exception):
    """The world cannot be started (no files, or its server does not come up)."""


class ProcessLauncher:
    """Runs each world's server (`uvicorn server.api:app`) as a subprocess.

    All worlds share one interpreter: their dependencies are the template's.
    """

    def __init__(
        self,
        worlds_dir: Path,
        python: Path,
        start_timeout: float = 30,
    ) -> None:
        self.worlds_dir = worlds_dir
        self.python = python
        self.start_timeout = start_timeout
        self._processes: dict[str, tuple[asyncio.subprocess.Process, int]] = {}
        self._lock = asyncio.Lock()

    def _folder(self, world_id: str, path: str | None) -> Path:
        folder = Path(path) if path else self.worlds_dir / world_id
        if not (folder / "server" / "api.py").is_file():
            raise WorldUnavailable("This world has no playable files yet.")
        return folder

    async def start(self, world_id: str, path: str | None) -> int:
        async with self._lock:
            known = self._processes.get(world_id)
            if known is not None and known[0].returncode is None:
                return known[1]
            folder = self._folder(world_id, path)
            port = worldproc.free_port()
            process = await worldproc.start_world(folder, self.python, port)
            try:
                await worldproc.wait_healthy(port, process, self.start_timeout)
            except RuntimeError as exc:
                await worldproc.stop_world(process)
                raise WorldUnavailable(str(exc)) from exc
            self._processes[world_id] = (process, port)
            return port

    async def stop(self, world_id: str) -> None:
        known = self._processes.pop(world_id, None)
        if known is not None:
            await worldproc.stop_world(known[0])

    async def stop_all(self) -> None:
        for world_id in list(self._processes):
            await self.stop(world_id)
