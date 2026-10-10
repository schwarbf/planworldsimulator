"""Connect to a running world by URL: reset, score, advance, events."""

from typing import Any

import httpx


class WorldClient:
    """REST access to one world server. The agent itself only uses ``mcp_url``."""

    def __init__(self, url: str, timeout: float = 30) -> None:
        self.url = url.rstrip("/")
        self.mcp_url = f"{self.url}/mcp"
        self._http = httpx.AsyncClient(base_url=self.url, timeout=timeout)

    async def __aenter__(self) -> "WorldClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._http.aclose()

    async def _call(self, method: str, path: str, **kw: Any) -> Any:
        resp = await self._http.request(method, path, **kw)
        resp.raise_for_status()
        return resp.json()

    async def reset(self, seed: int, difficulty: str) -> dict[str, Any]:
        body = {"seed": seed, "difficulty": difficulty}
        return await self._call("POST", "/api/reset", json=body)

    async def state(self) -> dict[str, Any]:
        return await self._call("GET", "/api/state")

    async def set_mode(self, mode: str, agent: str | None = None) -> dict[str, Any]:
        """``agent`` while an agent plays: the world then rejects UI actions."""
        args = {"mode": mode, **({"agent": agent} if agent else {})}
        return await self._call(
            "POST", "/api/action", json={"id": "mode", "args": args}
        )

    async def score(self) -> dict[str, Any]:
        return await self._call("GET", "/api/score")

    async def advance(self, steps: int) -> dict[str, Any]:
        return await self._call("POST", "/api/advance", json={"steps": steps})

    async def finish(self) -> dict[str, Any]:
        """Play out the remaining steps with no actions; return the final score."""
        while not (score := await self.score())["done"]:
            await self.advance(1000)
        return score

    async def events(self, after: int = 0) -> list[dict[str, Any]]:
        return await self._call("GET", "/api/events", params={"after": after})
