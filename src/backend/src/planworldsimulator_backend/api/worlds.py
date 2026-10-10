import asyncio
import json
import re
import secrets
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select

from planworldsimulator_backend.api.deps import (
    CREATOR_COOKIE,
    client_ip,
    current_creator,
    hash_token,
)
from planworldsimulator_backend.db.models import World, WorldEvent
from planworldsimulator_backend.generator import GenerationRequest
from planworldsimulator_backend.generator.exists import name_owner
from planworldsimulator_backend.schemas import (
    EventOut,
    WorldCreate,
    WorldOut,
    WorldPage,
)

router = APIRouter(prefix="/worlds", tags=["worlds"])

TERMINAL = {"ready", "failed", "exists"}


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:24].strip("-")
    return slug or "world"


def _request(world: World) -> GenerationRequest:
    return GenerationRequest(
        world_id=world.id,
        title=world.title,
        prompt=world.prompt,
        seed=world.seed,
        attempt=world.generation_attempt,
    )


async def _get_world(request: Request, world_id: str) -> World:
    async with request.app.state.sessions() as session:
        world = await session.get(World, world_id)
    if world is None:
        raise HTTPException(status_code=404, detail="World not found")
    return world


def _out(world: World, me: str | None) -> WorldOut:
    out = WorldOut.model_validate(world)
    out.mine = me is not None and world.creator_hash == me
    return out


@router.post("", response_model=WorldOut, status_code=201)
async def create_world(
    body: WorldCreate, request: Request, response: Response
) -> WorldOut:
    state = request.app.state
    settings = state.settings

    token = request.cookies.get(CREATOR_COOKIE)
    new_token = token is None
    if token is None:
        token = secrets.token_urlsafe(24)

    async with state.generation_lock:
        owner = await name_owner(state.sessions, body.name)
        if owner is not None:
            raise HTTPException(
                status_code=409,
                detail=f"A world called “{body.name}” already exists.",
                headers={"X-Existing-World": owner},
            )

        world = World(
            id=f"{_slug(body.name)}-{secrets.token_hex(3)}",
            title=body.name,
            prompt=body.prompt.strip(),
            seed=body.seed if body.seed is not None else secrets.randbelow(10_000),
            status="queued",
            creator_hash=hash_token(token),
        )
        async with state.sessions() as session:
            busy = await session.scalar(
                select(func.count())
                .select_from(World)
                .where(World.status.in_(("queued", "generating")))
            )
            # Turned away for capacity? That must not use up the visitor's allowance.
            if (busy or 0) >= settings.max_generating:
                raise HTTPException(
                    status_code=503,
                    detail="Too many worlds are being generated right now. "
                    "Try again in a minute.",
                    headers={"Retry-After": "60"},
                )
            wait = state.create_limiter.hit(client_ip(request))
            if wait is not None:
                raise HTTPException(
                    status_code=429,
                    detail="You are generating worlds too fast. Try again later.",
                    headers={"Retry-After": str(wait)},
                )
            session.add(world)
            await session.commit()
        state.runner.submit(_request(world))

    if new_token:
        response.set_cookie(
            CREATOR_COOKIE,
            token,
            max_age=365 * 24 * 3600,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
        )
    return _out(world, hash_token(token))


@router.get("", response_model=WorldPage)
async def list_worlds(
    request: Request,
    q: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=12, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> WorldPage:
    """The public catalogue. Failed and duplicate worlds only show for their creator."""
    me = current_creator(request)
    visible = World.status.not_in(("failed", "exists"))
    if me is not None:
        visible = or_(visible, World.creator_hash == me)
    filters = [visible]
    if q and q.strip():
        filters.append(World.title.ilike(f"%{q.strip()}%"))

    async with request.app.state.sessions() as session:
        total = await session.scalar(
            select(func.count()).select_from(World).where(*filters)
        )
        rows = await session.scalars(
            select(World)
            .where(*filters)
            .order_by(World.featured.desc(), World.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = [_out(world, me) for world in rows]
    return WorldPage(items=items, total=total or 0)


@router.get("/{world_id}", response_model=WorldOut)
async def get_world(world_id: str, request: Request) -> WorldOut:
    return _out(await _get_world(request, world_id), current_creator(request))


@router.get("/{world_id}/events", response_model=list[EventOut])
async def list_events(
    world_id: str, request: Request, attempt: int | None = Query(default=None, ge=1)
) -> list[WorldEvent]:
    world = await _get_world(request, world_id)
    async with request.app.state.sessions() as session:
        result = await session.scalars(
            select(WorldEvent)
            .where(
                WorldEvent.world_id == world_id,
                WorldEvent.attempt == (attempt or world.generation_attempt),
            )
            .order_by(WorldEvent.id)
        )
        return list(result)


@router.get("/{world_id}/stream")
async def stream_events(
    world_id: str,
    request: Request,
    attempt: int | None = Query(default=None, ge=1),
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    initial = await _get_world(request, world_id)
    selected_attempt = attempt or initial.generation_attempt
    try:
        after = max(after, int(request.headers.get("last-event-id", "0")))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Last-Event-ID") from None
    sessions = request.app.state.sessions

    async def gen() -> AsyncIterator[str]:
        last_id = after
        while True:
            async with sessions() as session:
                events = list(
                    await session.scalars(
                        select(WorldEvent)
                        .where(
                            WorldEvent.world_id == world_id,
                            WorldEvent.attempt == selected_attempt,
                            WorldEvent.id > last_id,
                        )
                        .order_by(WorldEvent.id)
                    )
                )
                world = await session.get(World, world_id)
            for event in events:
                last_id = event.id
                payload = EventOut.model_validate(event).model_dump(mode="json")
                yield f"id: {event.id}\nevent: step\ndata: {json.dumps(payload)}\n\n"
            if (
                world is None
                or world.generation_attempt != selected_attempt
                or (world.status in TERMINAL and not events)
            ):
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
async def retry_world(world_id: str, request: Request) -> WorldOut:
    me = current_creator(request)
    world = await _get_world(request, world_id)
    if me is None or world.creator_hash != me:
        raise HTTPException(status_code=403, detail="Only the creator can retry")
    if world.status != "failed":
        raise HTTPException(status_code=409, detail="Only failed worlds can be retried")
    state = request.app.state
    async with state.generation_lock:
        async with state.sessions() as session:
            world = await session.get(World, world_id)
            assert world is not None
            if world.status != "failed":
                raise HTTPException(
                    status_code=409, detail="Only failed worlds can be retried"
                )
            busy = await session.scalar(
                select(func.count())
                .select_from(World)
                .where(World.status.in_(("queued", "generating")))
            )
            if (busy or 0) >= state.settings.max_generating:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Too many worlds are being generated right now. "
                        "Try again in a minute."
                    ),
                    headers={"Retry-After": "60"},
                )
            wait = state.create_limiter.hit(client_ip(request))
            if wait is not None:
                raise HTTPException(
                    status_code=429,
                    detail="You are generating worlds too fast. Try again later.",
                    headers={"Retry-After": str(wait)},
                )
            world.status = "queued"
            world.generation_attempt += 1
            await session.commit()
        state.runner.submit(_request(world))
    return _out(world, me)
