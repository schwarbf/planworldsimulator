import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from planworldsimulator_backend.api.worlds import router as worlds_router
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.db.session import (
    make_engine,
    make_session_factory,
    run_migrations,
)
from planworldsimulator_backend.generator import FakeGenerator
from planworldsimulator_backend.launcher import FakeLauncher
from planworldsimulator_backend.runner import GenerationRunner


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Alembic's async env runs its own event loop, so keep it off ours.
        await asyncio.to_thread(run_migrations, settings.database_url)
        engine = make_engine(settings.database_url)
        sessions = make_session_factory(engine)
        settings.worlds_dir.mkdir(parents=True, exist_ok=True)
        generator = FakeGenerator(
            settings.worlds_dir, settings.template_dir, settings.step_delay_seconds
        )
        app.state.settings = settings
        app.state.sessions = sessions
        app.state.runner = GenerationRunner(sessions, generator)
        app.state.launcher = FakeLauncher()
        yield
        await app.state.runner.wait_idle()
        await engine.dispose()

    app = FastAPI(title="PlanWorldSimulator", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(worlds_router)
    return app


def cli() -> None:
    settings = Settings()
    uvicorn.run(
        "planworldsimulator_backend.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
