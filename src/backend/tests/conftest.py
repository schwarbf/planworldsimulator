from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

import httpx
import pytest
from asgi_lifespan import LifespanManager
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.main import create_app


@asynccontextmanager
async def running_app(tmp_path: Path, **overrides) -> AsyncIterator[httpx.AsyncClient]:
    options = {
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        "worlds_dir": tmp_path / "worlds",
        "template_dir": tmp_path / "template",
        "step_delay_seconds": 0,
        # Tests create many worlds; the limits get their own dedicated tests.
        "create_limit_per_hour": 1000,
        "max_generating": 50,
        "seed_featured": False,
    }
    options.update(overrides)
    app = create_app(Settings(**options))
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as http:
            http.app = app  # type: ignore[attr-defined]
            yield http


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[httpx.AsyncClient]:
    async with running_app(tmp_path) as http:
        yield http


@pytest.fixture
def make_client(
    tmp_path: Path,
) -> Callable[..., AbstractAsyncContextManager[httpx.AsyncClient]]:
    """Start the app with settings overrides, e.g. make_client(max_running=1)."""
    return lambda **overrides: running_app(tmp_path, **overrides)
