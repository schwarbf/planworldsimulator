import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from sqlalchemy import update

from planworldsimulator_backend.api.play import router as play_router
from planworldsimulator_backend.api.worlds import router as worlds_router
from planworldsimulator_backend.config import Settings
from planworldsimulator_backend.db.models import World
from planworldsimulator_backend.db.session import (
    make_engine,
    make_session_factory,
    run_migrations,
)
from planworldsimulator_backend.featured import seed_featured
from planworldsimulator_backend.generator import FakeGenerator, Generator
from planworldsimulator_backend.generator.exists import name_owner
from planworldsimulator_backend.generator.opencode_generator import OpenCodeGenerator
from planworldsimulator_backend.launcher import FakeLauncher, Launcher, ProcessLauncher
from planworldsimulator_backend.limits import SlidingWindowLimiter
from planworldsimulator_backend.reaper import reap_loop
from planworldsimulator_backend.runner import GenerationRunner
from planworldsimulator_backend.worldproc import resolve_world_python


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Alembic's async env runs its own event loop, so keep it off ours.
        await asyncio.to_thread(run_migrations, settings.database_url)
        engine = make_engine(settings.database_url)
        sessions = make_session_factory(engine)
        settings.worlds_dir.mkdir(parents=True, exist_ok=True)
        generator: Generator
        if settings.generator == "opencode":
            generator = OpenCodeGenerator(
                settings, lambda title, own: name_owner(sessions, title, own)
            )
        else:
            generator = FakeGenerator(
                settings.worlds_dir, settings.template_dir, settings.step_delay_seconds
            )
        app.state.settings = settings
        app.state.sessions = sessions
        app.state.runner = GenerationRunner(sessions, generator)
        launcher: Launcher
        use_processes = settings.launcher == "process" or (
            settings.launcher == "auto" and settings.generator == "opencode"
        )
        if use_processes:
            launcher = ProcessLauncher(
                settings.worlds_dir,
                resolve_world_python(settings.template_dir, settings.world_python),
            )
        else:
            launcher = FakeLauncher()
        app.state.launcher = launcher
        # Worlds that were running when the API last stopped are gone.
        async with sessions() as session:
            await session.execute(
                update(World)
                .where(World.running.is_(True))
                .values(running=False, port=None)
            )
            await session.commit()
        app.state.create_limiter = SlidingWindowLimiter(
            settings.create_limit_per_hour, 3600
        )
        app.state.http = httpx.AsyncClient(timeout=30)
        if settings.seed_featured:
            await seed_featured(sessions)
        reaper = asyncio.create_task(
            reap_loop(
                sessions,
                app.state.launcher,
                settings.idle_stop_seconds,
                settings.reap_interval_seconds,
            )
        )
        yield
        reaper.cancel()
        await app.state.runner.wait_idle()
        if isinstance(launcher, ProcessLauncher):
            await launcher.stop_all()
        await app.state.http.aclose()
        await engine.dispose()

    app = FastAPI(title="PlanWorldSimulator", lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(worlds_router)
    app.include_router(play_router)
    return app


def cli() -> None:
    settings = Settings()
    uvicorn.run(
        "planworldsimulator_backend.main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
