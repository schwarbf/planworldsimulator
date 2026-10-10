"""[base] World server: REST + WebSocket for the UI, MCP for the agent, one shared Game.

Same in every world; do not edit per world. World-specific parts come from
``sim/env.py`` (env class + world contract) and ``server/mcp.py`` (tools).
"""

from __future__ import annotations

import asyncio
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from server.mcp import build_mcp
from sim.helpers import to_jsonable, world

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
        self.mode = "you"
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
                return {"mode": self.mode}
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
            return to_jsonable(self.env.ui_state(ctx))

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


def _bad_request(fn, *args):
    try:
        return fn(*args)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
    return _bad_request(game.act, body["id"], body.get("args") or {}, "ui")


@app.post("/api/advance")
async def post_advance(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    return _bad_request(game.advance, int((body or {}).get("steps", 1)), "ui")


@app.post("/api/reset")
async def post_reset(body: dict[str, Any] | None = Body(None)) -> dict[str, Any]:
    body = body or {}
    return _bad_request(game.reset, body.get("seed"), body.get("difficulty"), "ui")


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


app.mount("/", mcp_app)  # last, so /api routes win; MCP lives at /mcp
