import asyncio
import logging

from sqlalchemy.ext.asyncio import async_sessionmaker

from planworldsimulator_backend.db.models import World, WorldEvent
from planworldsimulator_backend.generator import GenerationRequest, Generator

log = logging.getLogger(__name__)


class GenerationRunner:
    """Runs generations in the background and records progress in the database."""

    def __init__(self, sessions: async_sessionmaker, generator: Generator) -> None:
        self.sessions = sessions
        self.generator = generator
        self._tasks: set[asyncio.Task] = set()

    def submit(self, request: GenerationRequest) -> None:
        task = asyncio.create_task(self._run(request))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def wait_idle(self) -> None:
        while self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run(self, request: GenerationRequest) -> None:
        await self._update(request.world_id, status="generating")
        try:
            async for event in self.generator.run(request):
                async with self.sessions() as session:
                    session.add(
                        WorldEvent(
                            world_id=request.world_id,
                            step=event.step,
                            state=event.state,
                            message=event.message,
                        )
                    )
                    world = await session.get(World, request.world_id)
                    if world is not None:
                        if event.duplicate_of is not None:
                            world.duplicate_of = event.duplicate_of
                        if event.storyline is not None:
                            world.storyline = event.storyline
                        if event.path is not None:
                            world.path = event.path
                    await session.commit()
        except Exception as exc:
            log.exception("generation failed for %s", request.world_id)
            async with self.sessions() as session:
                session.add(
                    WorldEvent(
                        world_id=request.world_id,
                        step="error",
                        state="failed",
                        message=str(exc),
                    )
                )
                await session.commit()
            await self._update(request.world_id, status="failed")
            return
        await self._update(request.world_id, status=await self._final_status(request))

    async def _final_status(self, request: GenerationRequest) -> str:
        async with self.sessions() as session:
            world = await session.get(World, request.world_id)
            return "exists" if world is not None and world.duplicate_of else "ready"

    async def _update(self, world_id: str, **fields: object) -> None:
        async with self.sessions() as session:
            world = await session.get(World, world_id)
            if world is not None:
                for key, value in fields.items():
                    setattr(world, key, value)
                await session.commit()
