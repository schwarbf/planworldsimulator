import asyncio
import json
import secrets
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from planbench_backend.db.models import World, WorldEvent
from planbench_backend.generator import GenerationRequest
from planbench_backend.schemas import EventOut, WorldCreate, WorldOut

router = APIRouter(prefix="/worlds", tags=["worlds"])

TERMINAL = {"ready", "failed"}


def _title(prompt: str) -> str:
    words = prompt.strip().split()
    title = " ".join(words[:6])
    return title if len(words) <= 6 else f"{title}…"


def _request(world: World) -> GenerationRequest:
    return GenerationRequest(
        world_id=world.id,
        title=world.title,
        prompt=world.prompt,
        seed=world.seed,
    )


async def _get_world(request: Request, world_id: str) -> World:
    async with request.app.state.sessions() as session:
        world = await session.get(World, world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


@router.post("", response_model=WorldOut, status_code=201)
async def create_world(body: WorldCreate, request: Request) -> World:
    world = World(
        id=f"w-{secrets.token_hex(4)}",
        title=_title(body.prompt),
        prompt=body.prompt.strip(),
        seed=body.seed if body.seed is not None else secrets.randbelow(10_000),
        status="queued",
    )
    async with request.app.state.sessions() as session:
        session.add(world)
        await session.commit()
    request.app.state.runner.submit(_request(world))
    return world


@router.get("", response_model=list[WorldOut])
async def list_worlds(request: Request) -> list[World]:
    async with request.app.state.sessions() as session:
        result = await session.scalars(select(World).order_by(World.created_at.desc()))
        return list(result)


@router.get("/{world_id}", response_model=WorldOut)
async def get_world(world_id: str, request: Request) -> World:
    return await _get_world(request, world_id)


@router.get("/{world_id}/events", response_model=list[EventOut])
async def list_events(world_id: str, request: Request) -> list[WorldEvent]:
    await _get_world(request, world_id)
    async with request.app.state.sessions() as session:
        result = await session.scalars(
            select(WorldEvent)
            .where(WorldEvent.world_id == world_id)
            .order_by(WorldEvent.id)
        )
        return list(result)


@router.get("/{world_id}/stream")
async def stream_events(world_id: str, request: Request) -> StreamingResponse:
    await _get_world(request, world_id)
    sessions = request.app.state.sessions

    async def gen() -> AsyncIterator[str]:
        last_id = 0
        while True:
            async with sessions() as session:
                events = list(
                    await session.scalars(
                        select(WorldEvent)
                        .where(WorldEvent.world_id == world_id, WorldEvent.id > last_id)
                        .order_by(WorldEvent.id)
                    )
                )
                world = await session.get(World, world_id)
            for event in events:
                last_id = event.id
                payload = EventOut.model_validate(event).model_dump(mode="json")
                yield f"event: step\ndata: {json.dumps(payload)}\n\n"
            if world is None or (world.status in TERMINAL and not events):
                status = world.status if world else "failed"
                yield f"event: done\ndata: {json.dumps({'status': status})}\n\n"
                return
            if await request.is_disconnected():
                return
            await asyncio.sleep(0.25)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{world_id}/retry", response_model=WorldOut)
async def retry_world(world_id: str, request: Request) -> World:
    world = await _get_world(request, world_id)
    if world.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed worlds can be retried")
    async with request.app.state.sessions() as session:
        world = await session.get(World, world_id)
        assert world is not None
        world.status = "queued"
        await session.commit()
    request.app.state.runner.submit(_request(world))
    return world


@router.post("/{world_id}/start", response_model=WorldOut)
async def start_world(world_id: str, request: Request) -> World:
    world = await _get_world(request, world_id)
    if world.status != "ready":
        raise HTTPException(status_code=409, detail="World is not ready")
    port = await request.app.state.launcher.start(world_id, world.path)
    async with request.app.state.sessions() as session:
        world = await session.get(World, world_id)
        assert world is not None
        world.running = True
        world.port = port
        await session.commit()
    return world


@router.post("/{world_id}/stop", response_model=WorldOut)
async def stop_world(world_id: str, request: Request) -> World:
    await _get_world(request, world_id)
    await request.app.state.launcher.stop(world_id)
    async with request.app.state.sessions() as session:
        world = await session.get(World, world_id)
        assert world is not None
        world.running = False
        await session.commit()
    return world
