from datetime import UTC, datetime, timedelta

import httpx
from planworldsimulator_backend.limits import SlidingWindowLimiter
from planworldsimulator_backend.reaper import reap_idle

PROMPT = "A nuclear plant under heat waves"


def app_of(client: httpx.AsyncClient):
    return client.app  # type: ignore[attr-defined]


async def ready_world(client: httpx.AsyncClient, name: str = "Playable") -> str:
    created = await client.post("/worlds", json={"name": name, "prompt": PROMPT})
    await app_of(client).state.runner.wait_idle()
    return created.json()["id"]


async def test_playing_starts_the_world_and_shows_a_placeholder(
    client: httpx.AsyncClient,
) -> None:
    world_id = await ready_world(client)

    page = await client.get(f"/play/{world_id}/", params={"level": 3})
    assert page.status_code == 200
    assert "Playable" in page.text and "Level 3" in page.text

    world = (await client.get(f"/worlds/{world_id}")).json()
    assert world["running"] is True
    assert world["port"] is not None
    assert world["play_count"] == 1


async def test_only_page_opens_count_as_plays(client: httpx.AsyncClient) -> None:
    world_id = await ready_world(client)
    await client.get(f"/play/{world_id}/")
    await client.get(f"/play/{world_id}/assets/app.js")
    await client.get(f"/play/{world_id}/")

    assert (await client.get(f"/worlds/{world_id}")).json()["play_count"] == 2


async def test_anyone_can_play_without_being_the_creator(
    client: httpx.AsyncClient,
) -> None:
    world_id = await ready_world(client)
    stranger = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app_of(client)), base_url="http://test"
    )
    assert (await stranger.get(f"/play/{world_id}/")).status_code == 200
    await stranger.aclose()


async def test_play_rejects_unknown_unready_and_bad_levels(
    client: httpx.AsyncClient, monkeypatch
) -> None:
    assert (await client.get("/play/nope/")).status_code == 404

    world_id = await ready_world(client)
    assert (
        await client.get(f"/play/{world_id}/", params={"level": 9})
    ).status_code == 422

    monkeypatch.setattr(app_of(client).state.runner, "submit", lambda _r: None)
    queued = (
        await client.post("/worlds", json={"name": "Queued", "prompt": PROMPT})
    ).json()["id"]
    assert (await client.get(f"/play/{queued}/")).status_code == 409


async def test_requests_are_proxied_to_the_world_server(
    client: httpx.AsyncClient,
) -> None:
    world_id = await ready_world(client)
    seen: list[httpx.Request] = []

    def world_server(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200, text="hello from the world", headers={"content-type": "text/plain"}
        )

    await app_of(client).state.http.aclose()
    app_of(client).state.http = httpx.AsyncClient(
        transport=httpx.MockTransport(world_server)
    )

    response = await client.get(f"/play/{world_id}/state", params={"level": 2})
    assert response.status_code == 200
    assert response.text == "hello from the world"
    assert seen[0].url.path == "/state"
    assert seen[0].url.params["level"] == "2"


async def test_running_worlds_are_capped(make_client) -> None:
    async with make_client(max_running=1) as client:
        first = await ready_world(client, "First")
        second = await ready_world(client, "Second")
        assert (await client.get(f"/play/{first}/")).status_code == 200
        assert (await client.get(f"/play/{second}/")).status_code == 503
        # the running one can still be opened
        assert (await client.get(f"/play/{first}/")).status_code == 200


async def test_idle_worlds_are_stopped(client: httpx.AsyncClient) -> None:
    world_id = await ready_world(client)
    await client.get(f"/play/{world_id}/")
    state = app_of(client).state

    assert await reap_idle(state.sessions, state.launcher, 1800) == []
    later = datetime.now(UTC) + timedelta(hours=1)
    assert await reap_idle(state.sessions, state.launcher, 1800, now=later) == [
        world_id
    ]

    world = (await client.get(f"/worlds/{world_id}")).json()
    assert world["running"] is False and world["port"] is None


def test_sliding_window_limiter() -> None:
    limiter = SlidingWindowLimiter(max_events=2, window_seconds=10)
    assert limiter.hit("a", now=0) is None
    assert limiter.hit("a", now=1) is None
    assert limiter.hit("a", now=2) == 9
    assert limiter.hit("b", now=2) is None  # separate key
    assert limiter.hit("a", now=10.5) is None  # first event left the window
