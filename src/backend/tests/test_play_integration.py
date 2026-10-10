"""Generated world, launcher, play proxy and scripted harness; no paid APIs."""

import asyncio
import os
import re
import sys
from pathlib import Path

import httpx
import pytest
from planworldsimulator_backend import worldproc
from planworldsimulator_backend.generator import gates

ROOT = Path(__file__).resolve().parents[3]
TEMPLATE = ROOT / "src/worlds-template"
WORLD_PYTHON = TEMPLATE / ".pixi/envs/default/bin/python"


@pytest.mark.skipif(not WORLD_PYTHON.exists(), reason="World environment not installed")
async def test_generated_world_preserves_main_features_through_proxy(
    tmp_path, monkeypatch, make_client
):
    # Inherit no provider keys: narration exercises the caption fallback only.
    for name in (
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_FILE",
        "GRADIUM_API_KEY",
        "GRADIUM_API_KEY_FILE",
    ):
        monkeypatch.delenv(name, raising=False)
    port = worldproc.free_port()
    monkeypatch.setenv("HARNESS_URL", f"http://127.0.0.1:{port}")
    agents = tmp_path / "agents.toml"
    agents.write_text('[scripted]\nmodel = "test:scripted"\n')
    script = tmp_path / "harness.py"
    script.write_text("""
import sys
import uvicorn
from pathlib import Path
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.messages import ModelResponse, ToolCallPart
from planworldsimulator_harness.serve import Runner, create_app

def play(messages, info):
    return ModelResponse(parts=[ToolCallPart("advance", {"weeks": 1})])

runner = Runner(
    pace=0.2, agents_file=Path(sys.argv[2]), build=lambda _: FunctionModel(play)
)
uvicorn.run(
    create_app(runner), host="127.0.0.1", port=int(sys.argv[1]), log_level="warning"
)
""")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script),
        str(port),
        str(agents),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src/harness/src")},
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        async with httpx.AsyncClient() as http:
            for _ in range(100):
                try:
                    if (await http.get(f"http://127.0.0.1:{port}/agents")).is_success:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("scripted harness did not start")
        async with make_client(
            template_dir=TEMPLATE,
            launcher="process",
            world_python=WORLD_PYTHON,
        ) as client:
            created = await client.post(
                "/worlds", json={"name": "Combined world", "prompt": "A tiny shop"}
            )
            world_id = created.json()["id"]
            await client.app.state.runner.wait_idle()  # type: ignore[attr-defined]
            folder = tmp_path / "worlds" / world_id
            built = await gates.build_ui(folder)
            assert built.ok, built.output
            base = f"/play/{world_id}/"
            page = await client.get(base)
            assert page.status_code == 200 and '<div id="root"' in page.text
            asset = re.search(r'src="\./([^\"]+\.js)"', page.text)
            assert asset and (await client.get(base + asset[1])).status_code == 200
            for level, difficulty in enumerate(("Easy", "Medium", "Hard"), 1):
                reset = await client.post(
                    base + "api/reset", json={"level": level, "seed": 7}
                )
                assert reset.is_success
                state = (await client.get(base + "api/state")).json()
                assert state["world"]["difficulty"] == difficulty
                assert {"score", "baseline", "formula"} <= state["score"].keys()
                assert state["play"] == {"mode": "you", "agent": None}
                assert (await client.post(base + "api/advance")).is_success
            narration = await client.post(
                base + "api/narration", json={"kind": "intro"}
            )
            assert narration.is_success and narration.json()["sentences"]
            commentary = await client.post(
                base + "api/narration", json={"kind": "commentary"}
            )
            assert commentary.is_success and commentary.json()["text"]
            # A cached WAV proves audio is reachable beneath the same prefix.
            cache = folder / ".narration" / "v2"  # narration.CACHE_DIR in the world
            cache.mkdir(parents=True, exist_ok=True)
            (cache / "intro.wav").write_bytes(b"RIFFfake")
            narrated = (
                await client.post(base + "api/narration", json={"kind": "intro"})
            ).json()
            assert (
                await client.get(base + narrated["audio_url"].lstrip("/"))
            ).content == b"RIFFfake"
            assert (await client.get(base + "harness/agents")).json()[0][
                "name"
            ] == "scripted"
            started = await client.post(
                base + "harness/run", json={"agent": "scripted"}
            )
            assert started.is_success, started.text
            changed = await client.post(base + "harness/pace", json={"seconds": 0.1})
            assert changed.is_success, changed.text
            status = (await client.get(base + "harness/status")).json()
            assert status["pace"] == 0.1
            assert (await client.get(base + "api/state")).json()["play"][
                "agent"
            ] == "scripted"
            assert (await client.post(base + "api/advance")).status_code == 409
            for _ in range(100):
                events = (await client.get(base + "api/events")).json()
                if any(
                    e["source"] == "agent" and e["kind"] == "advance" for e in events
                ):
                    break
                await asyncio.sleep(0.1)
            else:
                status = (await client.get(base + "harness/status")).json()
                raise AssertionError(f"agent did not advance: {status}")
            assert (await client.post(base + "harness/stop", json={})).is_success
            assert (await client.get(base + "api/state")).json()["play"][
                "mode"
            ] == "you"
            assert (await client.post(base + "api/advance")).is_success
            # A live HTTP bridge exercises streaming and session headers too.
            import uvicorn
            from fastapi import FastAPI
            from mcp import ClientSession, types
            from mcp.client.streamable_http import streamable_http_client
            from planworldsimulator_backend.api.play import router

            bridge = FastAPI()
            bridge.state = client.app.state  # type: ignore[attr-defined]
            bridge.include_router(router)
            bridge_port = worldproc.free_port()
            server = uvicorn.Server(
                uvicorn.Config(
                    bridge, host="127.0.0.1", port=bridge_port, log_level="warning"
                )
            )
            task = asyncio.create_task(server.serve())
            try:
                for _ in range(100):
                    if server.started:
                        break
                    await asyncio.sleep(0.05)
                assert server.started
                url = f"http://127.0.0.1:{bridge_port}{base}mcp"
                async with streamable_http_client(url) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        assert "observe" in {tool.name for tool in tools.tools}
                        result = await session.call_tool("observe", {})
                        assert isinstance(result, types.CallToolResult)
                        assert not result.is_error
            finally:
                server.should_exit = True
                await asyncio.wait_for(task, 10)
    finally:
        await worldproc.stop_world(process)
