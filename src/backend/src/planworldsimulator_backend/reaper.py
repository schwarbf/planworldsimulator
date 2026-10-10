import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from planworldsimulator_backend.db.models import World
from planworldsimulator_backend.launcher import Launcher

log = logging.getLogger(__name__)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


async def reap_idle(
    sessions: async_sessionmaker,
    launcher: Launcher,
    idle_seconds: int,
    now: datetime | None = None,
) -> list[str]:
    """Stop running worlds nobody has played for `idle_seconds`."""
    cutoff = _aware(now or datetime.now(UTC)) - timedelta(seconds=idle_seconds)
    stopped: list[str] = []
    async with sessions() as session:
        running = await session.scalars(select(World).where(World.running.is_(True)))
        for world in running:
            last = _aware(world.last_played_at or world.updated_at)
            if last < cutoff:
                await launcher.stop(world.id)
                world.running = False
                world.port = None
                stopped.append(world.id)
        await session.commit()
    return stopped


async def reap_loop(
    sessions: async_sessionmaker,
    launcher: Launcher,
    idle_seconds: int,
    interval: float,
) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            stopped = await reap_idle(sessions, launcher, idle_seconds)
            if stopped:
                log.info("stopped idle worlds: %s", ", ".join(stopped))
        except Exception:
            log.exception("idle reaper failed")
