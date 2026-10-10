import html
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select

from planworldsimulator_backend.db.models import World

router = APIRouter(prefix="/play", tags=["play"])

FORWARDED_REQUEST_HEADERS = ("content-type", "accept", "accept-language")
FORWARDED_RESPONSE_HEADERS = ("content-type", "cache-control")


def _placeholder(world: World, level: int | None) -> HTMLResponse:
    level_text = f"Level {level}" if level else "Any level"
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(world.title)}</title>
<style>
  body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3eee4;
  color:#1b1f3b;font:16px/1.5 system-ui,sans-serif}}
  main{{max-width:34rem;padding:2rem}}
  h1{{font:400 2.5rem/1.1 Georgia,serif;margin:.25rem 0 1rem}}
  p{{color:#857d70}} code{{background:#fff;padding:.1rem .35rem;border-radius:4px}}
  .tag{{font:12px ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase}}
</style></head><body><main>
<p class="tag">{html.escape(level_text)} · seed {world.seed}</p>
<h1>{html.escape(world.title)}</h1>
<p>{html.escape(world.storyline or "")}</p>
<p>This world's own server is not running in this build, so there is nothing to
play yet. Once the real launcher is connected, this page shows the world itself.</p>
</main></body></html>"""
    return HTMLResponse(body)


async def _ensure_running(request: Request, world_id: str, first_hit: bool) -> World:
    state = request.app.state
    async with state.sessions() as session:
        world = await session.get(World, world_id)
        if world is None:
            raise HTTPException(status_code=404, detail="World not found")
        if world.status != "ready":
            raise HTTPException(status_code=409, detail="World is not ready")
        if not world.running:
            running = await session.scalar(
                select(func.count()).select_from(World).where(World.running.is_(True))
            )
            if (running or 0) >= state.settings.max_running:
                raise HTTPException(
                    status_code=503,
                    detail="Too many worlds are running. Try again in a few minutes.",
                    headers={"Retry-After": "120"},
                )
            world.port = await state.launcher.start(world.id, world.path)
            world.running = True
        if first_hit:
            world.play_count += 1
        world.last_played_at = datetime.now(UTC)
        await session.commit()
        return world


@router.api_route("/{world_id}/{path:path}", methods=["GET", "HEAD", "POST"])
async def play(
    world_id: str,
    path: str,
    request: Request,
    level: int | None = Query(default=None, ge=1, le=3),
) -> Response:
    """Open a world. Starts it on demand and proxies to its own server.

    Links must keep the trailing slash: /play/<id>/?level=2
    """
    world = await _ensure_running(request, world_id, first_hit=path == "")

    target = f"http://127.0.0.1:{world.port}/{path}"
    try:
        upstream = await request.app.state.http.request(
            request.method,
            target,
            params=request.query_params,
            content=await request.body(),
            headers={
                k: v
                for k, v in request.headers.items()
                if k.lower() in FORWARDED_REQUEST_HEADERS
            },
        )
    except httpx.HTTPError:
        return _placeholder(world, level)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers={
            k: v
            for k, v in upstream.headers.items()
            if k.lower() in FORWARDED_RESPONSE_HEADERS
        },
    )
