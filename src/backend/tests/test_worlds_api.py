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
        "/worlds", json={"prompt": "A nuclear plant under heat waves"}
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
    world_id = (await client.post("/worlds", json={"prompt": "Bike factory"})).json()[
        "id"
    ]
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
    first = (await client.post("/worlds", json={"prompt": "First world"})).json()
    second = (await client.post("/worlds", json={"prompt": "Second world"})).json()
    await _wait(client)
    ids = [w["id"] for w in (await client.get("/worlds")).json()]
    assert ids == [second["id"], first["id"]]


async def test_prompt_is_validated(client: httpx.AsyncClient) -> None:
    response = await client.post("/worlds", json={"prompt": "x"})
    assert response.status_code == 422


async def test_unknown_world_is_404(client: httpx.AsyncClient) -> None:
    assert (await client.get("/worlds/w-nope")).status_code == 404


async def test_start_and_stop(client: httpx.AsyncClient) -> None:
    world_id = (await client.post("/worlds", json={"prompt": "Start me"})).json()["id"]
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
    world_id = (await client.post("/worlds", json={"prompt": "Stuck world"})).json()[
        "id"
    ]
    response = await client.post(f"/worlds/{world_id}/start")
    assert response.status_code == 409


async def test_stream_ends_with_done(client: httpx.AsyncClient) -> None:
    world_id = (await client.post("/worlds", json={"prompt": "Stream me"})).json()["id"]
    await _wait(client)
    response = await client.get(f"/worlds/{world_id}/stream")
    assert response.status_code == 200
    assert "event: step" in response.text
    assert 'event: done\ndata: {"status": "ready"}' in response.text
