from typing import Protocol


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
