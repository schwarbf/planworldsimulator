import json

import httpx
from planworldsimulator_backend.generator import STEPS

PROMPT = "A nuclear plant under heat waves"


def app_of(client: httpx.AsyncClient):
    return client.app  # type: ignore[attr-defined]


async def wait(client: httpx.AsyncClient) -> None:
    await app_of(client).state.runner.wait_idle()


def visitor(client: httpx.AsyncClient) -> httpx.AsyncClient:
    """Another browser: same app, its own cookie jar."""
    transport = httpx.ASGITransport(app=app_of(client))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def create(client: httpx.AsyncClient, name: str = "Test world") -> dict:
    response = await client.post("/worlds", json={"name": name, "prompt": PROMPT})
    assert response.status_code == 201, response.text
    return response.json()


async def set_status(client: httpx.AsyncClient, world_id: str, status: str) -> None:
    from planworldsimulator_backend.db.models import World

    async with app_of(client).state.sessions() as session:
        world = await session.get(World, world_id)
        assert world is not None
        world.status = status
        await session.commit()


async def test_healthz(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_world_generates_and_becomes_ready(
    client: httpx.AsyncClient,
) -> None:
    created = await create(client, "Heat waves")
    assert created["levels"] == [1, 2, 3]

    await wait(client)

    world = (await client.get(f"/worlds/{created['id']}")).json()
    assert world["status"] == "ready"
    assert "nuclear plant" in world["storyline"]

    events = (await client.get(f"/worlds/{created['id']}/events")).json()
    steps = [e["step"] for e in events if e["state"] == "done"]
    assert steps == list(STEPS)


async def test_generated_world_folder_is_created(client: httpx.AsyncClient) -> None:
    created = await create(client, "Bike factory")
    await wait(client)
    world = (await client.get(f"/worlds/{created['id']}")).json()
    assert world["path"] is not None
    meta = json.loads(
        (
            app_of(client).state.settings.worlds_dir / created["id"] / "world.json"
        ).read_text()
    )
    assert meta["id"] == created["id"]
    assert meta["levels"] == [1, 2, 3]
    assert "difficulty" not in meta


async def test_name_is_required_and_validated(client: httpx.AsyncClient) -> None:
    for body in (
        {"prompt": "A bakery"},
        {"name": "x", "prompt": "A bakery"},
        {"name": "   ", "prompt": "A bakery"},
        {"name": "n" * 61, "prompt": "A bakery"},
        {"name": "Bakery", "prompt": "x"},
    ):
        assert (await client.post("/worlds", json=body)).status_code == 422


async def test_name_becomes_title_and_slugged_id(client: httpx.AsyncClient) -> None:
    world = await create(client, "  Fission   Ops! ")
    assert world["title"] == "Fission Ops!"
    assert world["id"].startswith("fission-ops-")
    await wait(client)
    meta = json.loads(
        (
            app_of(client).state.settings.worlds_dir / world["id"] / "world.json"
        ).read_text()
    )
    assert meta["name"] == "Fission Ops!"


async def test_names_without_letters_still_get_an_id(client: httpx.AsyncClient) -> None:
    assert (await create(client, "!!"))["id"].startswith("world-")


async def test_a_name_can_only_be_used_once(client: httpx.AsyncClient) -> None:
    first = await create(client, "Twin")
    for again in ("Twin", "  twin ", "TWIN!"):
        response = await client.post("/worlds", json={"name": again, "prompt": PROMPT})
        assert response.status_code == 409
        assert response.headers["x-existing-world"] == first["id"]


async def test_a_failed_world_does_not_hold_its_name(client: httpx.AsyncClient) -> None:
    first = await create(client, "Retry me")
    await wait(client)
    await set_status(client, first["id"], "failed")
    assert (await create(client, "Retry me"))["id"] != first["id"]


async def test_unknown_world_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get("/worlds/nope")).status_code == 404


async def test_stream_ends_with_done(client: httpx.AsyncClient) -> None:
    world = await create(client)
    await wait(client)
    response = await client.get(f"/worlds/{world['id']}/stream")
    assert response.status_code == 200
    assert "event: step" in response.text
    assert 'event: done\ndata: {"status": "ready"}' in response.text


# --- the public catalogue -------------------------------------------------


async def test_catalogue_is_public_newest_first_and_paginated(
    client: httpx.AsyncClient,
) -> None:
    ids = [(await create(client, f"World {n}"))["id"] for n in range(5)]
    await wait(client)

    stranger = visitor(client)  # nobody needs to be the creator to see worlds
    page = (await stranger.get("/worlds", params={"limit": 2})).json()
    assert page["total"] == 5
    assert [w["id"] for w in page["items"]] == [ids[4], ids[3]]
    assert all(w["mine"] is False for w in page["items"])

    rest = (await stranger.get("/worlds", params={"limit": 2, "offset": 2})).json()
    assert [w["id"] for w in rest["items"]] == [ids[2], ids[1]]
    await stranger.aclose()


async def test_catalogue_search_by_name(client: httpx.AsyncClient) -> None:
    await create(client, "Fission Ops")
    await create(client, "Bike Factory")
    await wait(client)

    page = (await client.get("/worlds", params={"q": "bike"})).json()
    assert [w["title"] for w in page["items"]] == ["Bike Factory"]
    assert page["total"] == 1


async def test_featured_worlds_come_first_and_are_seeded_once(make_client) -> None:
    from planworldsimulator_backend.featured import seed_featured

    async with make_client(seed_featured=True) as client:
        await create(client, "Mine")
        await wait(client)
        await seed_featured(app_of(client).state.sessions)  # idempotent

        page = (await client.get("/worlds")).json()
        titles = [w["title"] for w in page["items"]]
        assert titles == [
            "Fission Ops",
            "Bike Factory",
            "Grid Juggler",
            "Seven Seas",
            "Mine",
        ]
        assert [w["featured"] for w in page["items"]] == [True] * 4 + [False]
        assert all(w["status"] == "ready" for w in page["items"][:4])


async def test_failed_worlds_are_only_listed_for_their_creator(
    client: httpx.AsyncClient,
) -> None:
    world = await create(client, "Broken")
    await wait(client)
    await set_status(client, world["id"], "failed")

    mine = (await client.get("/worlds")).json()
    assert [w["id"] for w in mine["items"]] == [world["id"]]
    assert mine["items"][0]["mine"] is True

    stranger = visitor(client)
    assert (await stranger.get("/worlds")).json() == {"items": [], "total": 0}
    await stranger.aclose()


async def test_creator_cookie_is_httponly_and_reused(client: httpx.AsyncClient) -> None:
    first = await client.post("/worlds", json={"name": "One", "prompt": PROMPT})
    cookie = first.headers["set-cookie"]
    assert "pws_creator=" in cookie and "HttpOnly" in cookie

    second = await client.post("/worlds", json={"name": "Two", "prompt": PROMPT})
    assert "set-cookie" not in second.headers
    assert first.json()["mine"] and second.json()["mine"]


async def test_only_the_creator_can_retry(client: httpx.AsyncClient) -> None:
    world = await create(client, "Retry me")
    await wait(client)

    assert (await client.post(f"/worlds/{world['id']}/retry")).status_code == 409

    await set_status(client, world["id"], "failed")
    stranger = visitor(client)
    assert (await stranger.post(f"/worlds/{world['id']}/retry")).status_code == 403
    await stranger.aclose()

    retried = await client.post(f"/worlds/{world['id']}/retry")
    assert retried.status_code == 200
    await wait(client)
    assert (await client.get(f"/worlds/{world['id']}")).json()["status"] == "ready"


# --- limits for public use -----------------------------------------------


async def test_creating_worlds_is_rate_limited(make_client) -> None:
    async with make_client(create_limit_per_hour=2) as client:
        await create(client, "One")
        await create(client, "Two")
        blocked = await client.post("/worlds", json={"name": "Three", "prompt": PROMPT})
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) > 0
        await wait(client)


async def test_generation_is_capped(make_client, monkeypatch) -> None:
    async with make_client(max_generating=1) as client:
        monkeypatch.setattr(app_of(client).state.runner, "submit", lambda _r: None)
        await create(client, "First")  # stays queued
        busy = await client.post("/worlds", json={"name": "Second", "prompt": PROMPT})
        assert busy.status_code == 503
        assert "retry-after" in busy.headers


async def test_forwarded_ip_is_only_trusted_when_configured(make_client) -> None:
    for trust, expected in ((False, 429), (True, 201)):
        async with make_client(
            create_limit_per_hour=1, trust_forwarded_for=trust
        ) as client:
            await client.post(
                "/worlds",
                json={"name": "First", "prompt": PROMPT},
                headers={"x-forwarded-for": "1.1.1.1"},
            )
            second = await client.post(
                "/worlds",
                json={"name": "Second", "prompt": PROMPT},
                headers={"x-forwarded-for": "2.2.2.2"},
            )
            assert second.status_code == expected
            await wait(client)


async def test_being_turned_away_for_capacity_costs_no_allowance(
    make_client, monkeypatch
) -> None:
    async with make_client(create_limit_per_hour=2, max_generating=1) as client:
        monkeypatch.setattr(app_of(client).state.runner, "submit", lambda _r: None)
        first = await create(client, "First")  # queued, uses allowance 1 of 2

        body = {"name": "Second", "prompt": PROMPT}
        assert (await client.post("/worlds", json=body)).status_code == 503
        assert (await client.post("/worlds", json=body)).status_code == 503

        await set_status(client, first["id"], "ready")  # capacity frees up
        second = await client.post("/worlds", json=body)
        assert second.status_code == 201  # allowance 2 of 2

        await set_status(client, second.json()["id"], "ready")
        third = await client.post("/worlds", json={"name": "Third", "prompt": PROMPT})
        assert third.status_code == 429
