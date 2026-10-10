import json

import httpx


async def _wait(client: httpx.AsyncClient) -> None:
    await client.app.state.runner.wait_idle()  # type: ignore[attr-defined]


async def test_healthz(client: httpx.AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_create_world_generates_and_becomes_ready(
    client: httpx.AsyncClient,
) -> None:
    created = await client.post(
        "/worlds",
        json={"name": "Test world", "prompt": "A nuclear plant under heat waves"},
    )
    assert created.status_code == 201
    world_id = created.json()["id"]
    assert created.json()["levels"] == [1, 2, 3, 4]

    await _wait(client)

    world = (await client.get(f"/worlds/{world_id}")).json()
    assert world["status"] == "ready"
    assert "nuclear plant" in world["storyline"]

    events = (await client.get(f"/worlds/{world_id}/events")).json()
    steps = [e["step"] for e in events if e["state"] == "done"]
    assert steps == ["storyline", "copy_template", "fill_template", "tests"]


async def test_generated_world_folder_is_created(client: httpx.AsyncClient) -> None:
    world_id = (
        await client.post(
            "/worlds", json={"name": "Test world", "prompt": "Bike factory"}
        )
    ).json()["id"]
    await _wait(client)
    world = (await client.get(f"/worlds/{world_id}")).json()
    assert world["path"] is not None
    meta = json.loads(
        (client.app.state.settings.worlds_dir / world_id / "world.json").read_text()  # type: ignore[attr-defined]
    )
    assert meta["id"] == world_id
    assert meta["levels"] == [1, 2, 3, 4]
    assert "difficulty" not in meta


async def test_list_worlds_newest_first(client: httpx.AsyncClient) -> None:
    first = (
        await client.post(
            "/worlds", json={"name": "Test world", "prompt": "First world"}
        )
    ).json()
    second = (
        await client.post(
            "/worlds", json={"name": "Test world", "prompt": "Second world"}
        )
    ).json()
    await _wait(client)
    ids = [w["id"] for w in (await client.get("/worlds")).json()]
    assert ids == [second["id"], first["id"]]


async def test_prompt_is_validated(client: httpx.AsyncClient) -> None:
    response = await client.post("/worlds", json={"name": "Test world", "prompt": "x"})
    assert response.status_code == 422


async def test_unknown_world_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get("/worlds/w-nope")).status_code == 404


async def test_start_and_stop(client: httpx.AsyncClient) -> None:
    world_id = (
        await client.post("/worlds", json={"name": "Test world", "prompt": "Start me"})
    ).json()["id"]
    await _wait(client)

    started = (await client.post(f"/worlds/{world_id}/start")).json()
    assert started["running"] is True
    assert started["port"] is not None

    stopped = (await client.post(f"/worlds/{world_id}/stop")).json()
    assert stopped["running"] is False


async def test_cannot_start_world_that_is_not_ready(
    client: httpx.AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(client.app.state.runner, "submit", lambda _r: None)  # type: ignore[attr-defined]
    world_id = (
        await client.post(
            "/worlds", json={"name": "Test world", "prompt": "Stuck world"}
        )
    ).json()["id"]
    response = await client.post(f"/worlds/{world_id}/start")
    assert response.status_code == 409


async def test_stream_ends_with_done(client: httpx.AsyncClient) -> None:
    world_id = (
        await client.post("/worlds", json={"name": "Test world", "prompt": "Stream me"})
    ).json()["id"]
    await _wait(client)
    response = await client.get(f"/worlds/{world_id}/stream")
    assert response.status_code == 200
    assert "event: step" in response.text
    assert 'event: done\ndata: {"status": "ready"}' in response.text


async def test_name_is_required_and_validated(client: httpx.AsyncClient) -> None:
    missing = await client.post("/worlds", json={"prompt": "A bakery"})
    assert missing.status_code == 422

    too_short = await client.post("/worlds", json={"name": "x", "prompt": "A bakery"})
    assert too_short.status_code == 422

    blank = await client.post("/worlds", json={"name": "   ", "prompt": "A bakery"})
    assert blank.status_code == 422

    too_long = await client.post(
        "/worlds", json={"name": "n" * 61, "prompt": "A bakery"}
    )
    assert too_long.status_code == 422


async def test_name_becomes_title_and_slugged_id(client: httpx.AsyncClient) -> None:
    created = await client.post(
        "/worlds", json={"name": "  Fission   Ops! ", "prompt": "A nuclear plant"}
    )
    assert created.status_code == 201
    world = created.json()
    assert world["title"] == "Fission Ops!"
    assert world["id"].startswith("fission-ops-")
    await _wait(client)

    meta = json.loads(
        (client.app.state.settings.worlds_dir / world["id"] / "world.json").read_text()  # type: ignore[attr-defined]
    )
    assert meta["name"] == "Fission Ops!"


async def test_names_without_letters_still_get_an_id(client: httpx.AsyncClient) -> None:
    created = await client.post("/worlds", json={"name": "!!", "prompt": "A bakery"})
    assert created.status_code == 201
    assert created.json()["id"].startswith("world-")


async def test_same_name_gets_distinct_ids(client: httpx.AsyncClient) -> None:
    ids = {
        (
            await client.post("/worlds", json={"name": "Twin", "prompt": "A bakery"})
        ).json()["id"]
        for _ in range(3)
    }
    assert len(ids) == 3
