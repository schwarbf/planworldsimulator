"""[base] World server: REST + WebSocket for the UI, MCP for the agent, one shared Game.

Same in every world; do not edit per world. World-specific parts come from
``sim/env.py`` (env class + world contract) and ``server/mcp.py`` (tools).
"""

from __future__ import annotations

import asyncio
import os

import httpx
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server import narration
from server.mcp import build_mcp
from sim.helpers import difficulty_for_level, to_jsonable, world

ROOT = Path(__file__).resolve().parents[1]
MAX_EVENTS = 500
CODE_LINES = 4


class Game:
    """One running world: env, this step's queued actions, event log, discoveries."""

    # UI controls handled here, not by the env: id → steps to advance.
    ADVANCE_CONTROLS = {"play": 1, "fast": 4}
    NOOP_CONTROLS = {"pause", "stats"}

    def __init__(self, seed: int | None = None, difficulty: str | None = None):
        self.env_cls: Any = world()
        self.events: list[dict[str, Any]] = []
        self.scores: list[float] = []  # final scores of earlier episodes
        self.mode = "you"  # "agent" while the harness plays: UI routes are rejected
        self.agent: str | None = None  # name of the agent that plays
        self._seq = 0
        self._lock = threading.RLock()
        self._subs: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()
        self.reset(seed, difficulty, source="system")

    # ---------- actions ----------

    def reset(self, seed: int | None = None, difficulty: str | None = None, source: str = "ui") -> dict[str, Any]:
        with self._lock:
            difficulty = difficulty or getattr(self, "difficulty", None) or "medium"
            if difficulty not in self.env_cls.DIFFICULTIES:
                raise ValueError(f"difficulty must be one of {self.env_cls.DIFFICULTIES}")
            if getattr(self, "env", None) is not None and self.env.score()["week"] > 1:
                self.scores.append(self.env.score()["score"])
            self.seed = int(seed) if seed is not None else 1000 + secrets.randbelow(9000)
            self.difficulty = difficulty
            self.env = self.env_cls(difficulty)
            self.env.reset(seed=self.seed)
            self.queued: list[tuple[str, dict[str, Any]]] = []
            self.discoveries: list[str] = []
            self.notes: list[str] = []
            self.story: dict[str, Any] | None = None
            self.active: str | None = None
            self.baseline = self._baseline_score()
            result = {"seed": self.seed, "difficulty": difficulty}
            self._log(source, "reset", "reset", {"seed": seed, "difficulty": difficulty}, result)
            return result

    def act(self, verb: str, args: dict[str, Any] | None = None, source: str = "ui") -> dict[str, Any]:
        """Queue a world action for this step, or run a UI control (play, fast, new_world, mode…)."""
        args = dict(args or {})
        with self._lock:
            if verb in self.ADVANCE_CONTROLS:
                return self.advance(self.ADVANCE_CONTROLS[verb], source)
            if verb in self.NOOP_CONTROLS:
                return {"ok": True}
            if verb == "new_world":
                return self.reset(None, self.difficulty, source)
            if verb == "mode":
                if args.get("mode") not in ("you", "agent"):
                    raise ValueError("mode must be 'you' or 'agent'")
                self.mode = args["mode"]
                self.agent = str(args.get("agent") or "agent") if self.mode == "agent" else None
                return {"mode": self.mode, "agent": self.agent}
            if self.env.score()["done"]:
                raise ValueError("the episode is over; reset to play again")
            clean = self.env.check_action(verb, args)
            self.queued.append((verb, clean))
            self.active = verb
            result = {"status": "queued", "action": verb, **clean, "queued": len(self.queued)}
            self._log(source, "action", verb, clean, result)
            return result

    def advance(self, steps: int = 1, source: str = "ui") -> dict[str, Any]:
        """Apply the queued actions and step the env ``steps`` times (empty actions after the first)."""
        steps = max(1, int(steps))
        with self._lock:
            total, story, found, done = 0.0, None, [], self.env.score()["done"]
            for _ in range(steps):
                if done:
                    break
                action = self.env.encode_actions(self.queued)
                self.queued = []
                _, reward, terminated, truncated, info = self.env.step(action)
                total += reward
                found += info.get("discovered", [])
                story = info.get("story") or story
                done = terminated or truncated
            self.discoveries += found
            self.story = story
            sc = self.env.score()
            result = {**sc, "reward": round(total), "discovered": found,
                      "story": story["text"] if story else None}
            self._log(source, "advance", "advance", {"steps": steps}, result)
            return result

    def unqueue(self, index: int, source: str = "ui") -> dict[str, Any]:
        """Remove one queued action of this step (0-based, in queue order)."""
        with self._lock:
            if not 0 <= index < len(self.queued):
                raise ValueError(f"no queued action {index}; {len(self.queued)} queued")
            verb, args = self.queued.pop(index)
            self.active = self.queued[-1][0] if self.queued else None
            result = {"status": "removed", "action": verb, **args, "queued": len(self.queued)}
            self._log(source, "action", "cancel", {"index": index}, result)
            return result

    def note(self, text: str, source: str = "agent") -> dict[str, Any]:
        with self._lock:
            self.notes.append(text)
            self._log(source, "note", "note", {"text": text}, "noted")
            return {"status": "noted", "notes": len(self.notes)}

    # ---------- reads ----------

    def brief(self, source: str = "agent") -> str:
        text = (ROOT / "brief.md").read_text()
        self._log(source, "read", "brief", {}, f"{len(text)} chars")
        return text

    def observe(self, site: str | None = None, source: str = "agent") -> dict[str, Any]:
        with self._lock:
            obs = to_jsonable(self.env.observe(site))
            obs["queued"] = [{"action": v, **a} for v, a in self.queued]
            self._log(source, "read", "observe", {"site": site} if site else {}, f"week {obs.get('week')}")
            return obs

    def score(self, source: str = "agent") -> dict[str, Any]:
        with self._lock:
            sc = {**self.env.score(), "baseline": self.baseline}
            self._log(source, "read", "score", {}, sc)
            return sc

    def narration_context(self) -> dict[str, Any]:
        """What the narrator's progress update is based on (not logged as a read)."""
        with self._lock:
            obs = to_jsonable(self.env.observe(None))
            recent = [{"by": e["source"], "did": e["name"], **e["args"]}
                      for e in self.events[-40:] if e["kind"] in ("action", "advance", "note")][-12:]
            return {
                "brief": (ROOT / "brief.md").read_text()[:3000],
                "seed": self.seed,
                "difficulty": self.difficulty,
                "weeks": obs.get("weeks"),
                "score": to_jsonable({**self.env.score(), "baseline": self.baseline}),
                "state": obs,
                "discoveries": list(self.discoveries),
                "notes": self.notes[-3:],
                "player": self.agent or "you",
                "recent_actions": to_jsonable(recent),
            }

    def state(self) -> dict[str, Any]:
        """Visible state for the UI (shape defined by the world's ui_state / World.tsx mockState)."""
        with self._lock:
            sc = self.env.score()
            agent_calls = [e for e in self.events if e["source"] == "agent"][-CODE_LINES:]
            ctx = {
                "seed": self.seed,
                "story": self.story,
                "discoveries": list(self.discoveries),
                "active": self.active,
                "queued": [{"action": v, **a} for v, a in self.queued],
                "agent": {
                    "experiment": len(self.scores) + 1,
                    "experiments": max(20, len(self.scores) + 1),
                    "mode": self.mode,
                    "scores": [*self.scores, sc["score"]],
                    "baseline": self.baseline,
                    "now": self.notes[-1] if self.notes else "Waiting for a hypothesis…",
                    "code": "\n".join(_call_line(e) for e in agent_calls) or "# no agent calls yet",
                },
            }
            ui = self.env.ui_state(ctx)
            ui["queued"] = ctx["queued"]  # base contract: the UI queue panel reads this
            ui["score"] = {**sc, "baseline": self.baseline}  # base contract: the Goal card reads this
            ui["play"] = {"mode": self.mode, "agent": self.agent}  # base contract: who plays (agent view)
            return to_jsonable(ui)

    # ---------- events ----------

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.add((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs = {s for s in self._subs if s[1] is not q}

    def _log(self, source: str, kind: str, name: str, args: dict[str, Any], result: Any) -> None:
        self._seq += 1
        event = to_jsonable({"seq": self._seq, "time": time.time(), "source": source, "kind": kind,
                             "name": name, "args": args, "result": result})
        self.events = [*self.events[-MAX_EVENTS + 1:], event]
        for loop, q in list(self._subs):
            try:
                loop.call_soon_threadsafe(q.put_nowait, event)
            except RuntimeError:  # loop closed
                self._subs.discard((loop, q))

    def _baseline_score(self) -> float:
        env = self.env_cls(self.difficulty)
        env.reset(seed=self.seed)
        done = False
        while not done:
            _, _, terminated, truncated, _ = env.step(env.baseline_action())
            done = terminated or truncated
        return env.score()["score"]


def _call_line(e: dict[str, Any]) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in e["args"].items())
    return f"{e['name']}({args})"


# ---------- app ----------

game = Game()
mcp_server = build_mcp(game)
mcp_app = mcp_server.streamable_http_app()  # serves /mcp


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="PlanWorld server", lifespan=lifespan)


def _player_only() -> None:
    """While an agent plays (mode "agent"), the UI may watch but not act."""
    if game.mode == "agent":
        raise HTTPException(status_code=409, detail=f"{game.agent} is playing; stop it to take over")


def _bad_request(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/state")
async def get_state() -> dict[str, Any]:
    return game.state()


@app.get("/api/score")
async def get_score() -> dict[str, Any]:
    """Score for the harness; not logged, so it does not show up as an agent call."""
    with game._lock:
        return to_jsonable({**game.env.score(), "baseline": game.baseline})


@app.post("/api/action")
async def post_action(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(body.get("id"), str):
        raise HTTPException(status_code=400, detail="body needs {id, args}")
    if body["id"] != "mode":  # the harness hands control over with mode
        _player_only()
    return _bad_request(game.act, body["id"], body.get("args") or {}, "ui")


@app.post("/api/unqueue")
async def post_unqueue(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(body.get("index"), int):
        raise HTTPException(status_code=400, detail="body needs {index}")
    _player_only()
    return _bad_request(game.unqueue, body["index"], "ui")


@app.post("/api/advance")
async def post_advance(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    _player_only()
    return _bad_request(game.advance, int((body or {}).get("steps", 1)), "ui")


@app.post("/api/reset")
async def post_reset(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    _player_only()
    body = body or {}
    difficulty = body.get("difficulty")
    if difficulty is None and body.get("level") is not None:
        difficulty = _bad_request(difficulty_for_level, body["level"])
    return _bad_request(game.reset, body.get("seed"), difficulty, "ui")


@app.get("/api/events")
async def get_events(after: int = 0) -> list[dict[str, Any]]:
    return [e for e in game.events if e["seq"] > after]


@app.websocket("/api/events")
async def ws_events(ws: WebSocket) -> None:
    await ws.accept()
    q = game.subscribe()
    try:
        for e in game.events[-50:]:
            await ws.send_json(e)
        while True:
            await ws.send_json(await q.get())
    except WebSocketDisconnect:
        pass
    finally:
        game.unsubscribe(q)


# ---------- narrator (decision 0006) ----------

@app.post("/api/narration")
async def post_narration(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    """Narrator text, sentences and audio URL; first call per world runs Gemini + Gradium."""
    kind = (body or {}).get("kind", "intro")
    context = game.narration_context() if kind == "commentary" else None
    return await asyncio.to_thread(_bad_request, narration.narrate, kind, context)


@app.get("/api/narration/{kind}/audio")
async def get_narration_audio(kind: str) -> FileResponse:
    path = narration.audio_path(kind)
    if path is None:
        raise HTTPException(status_code=404, detail="no narration audio")
    return FileResponse(path, media_type=narration.AUDIO_TYPE)


# The world server supplies its own address: generated worlds use dynamic ports.
# The browser never has to know a server-internal URL or the harness port.
@app.api_route("/harness/{operation}", methods=["GET", "POST"])
async def harness(operation: str, request: Request) -> Response:
    methods = {"agents": "GET", "status": "GET", "run": "POST", "stop": "POST", "pace": "POST"}
    if methods.get(operation) != request.method:
        raise HTTPException(404, "Unknown harness operation")
    world_url = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"
    harness_url = os.environ.get("HARNESS_URL", f"http://127.0.0.1:{os.environ.get('HARNESS_PORT', '8090')}")
    kwargs = {}
    if request.method == "POST":
        body = await request.json()
        kwargs["json"] = {**body, "world_url": world_url}
    elif operation == "status":
        kwargs["params"] = {"world_url": world_url}
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            upstream = await http.request(request.method, f"{harness_url.rstrip('/')}/{operation}", **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "No connection to the agent harness") from exc
    return Response(upstream.content, status_code=upstream.status_code,
                    headers={"content-type": upstream.headers.get("content-type", "application/json")})


# MCP lives at /mcp. Its routes are added directly (not mounted at "/") so the built UI
# can be served from "/" after them.
app.router.routes.extend(mcp_app.routes)

# The built UI (`pixi run build-ui`); without it, `pixi run ui` serves the UI in dev.
if (ROOT / "ui" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "ui" / "dist", html=True), name="ui")
