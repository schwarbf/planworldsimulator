# World template

The base every world is copied from. As shipped it runs a placeholder "Example world".
Full reference world: `src/worlds/bike-factory`.

```bash
pixi run dev    # server on $PORT (default 8000: REST /api, MCP /mcp) + UI on $UI_PORT (default 5173)
pixi run test   # backend tests
pixi run build-ui && pixi run serve   # one process: API, MCP and the built UI at http://127.0.0.1:8000
pixi run test-ui                       # UI tests (Vitest)
```

## Files

`[base]` = same in every world, never edited · `[gen]` = written per world

| File | |
|---|---|
| `pixi.toml`, `process-compose.yaml` | [base] dependencies, tasks, processes |
| `brief.md` | [gen] public story, goal, actions (given to the agent) |
| `secret.md` | [gen] hidden rules and scoring (never given to the agent) |
| `sim/env.py` | [gen] Gymnasium env + world contract (below) |
| `sim/rules.py` | [gen] dynamics and hidden rules |
| `sim/helpers.py` | [base] observation → JSON, `register_world`, `difficulty_for_level` |
| `sim/demand.py` | [base] multiplicative demand model and its factors |
| `sim/demand_config.py` | [gen] which demand factors this world has, their parameters and first level |
| `server/api.py` | [base] FastAPI app, generic `Game`, `/api` routes, `/mcp` mount |
| `server/narration.py` | [base] voice narrator: Gemini intro text + Gradium TTS, cached in `.narration/` |
| `server/mcp.py` | [gen] `build_mcp(game) -> FastMCP` with the world's tools |
| `ui/src/World.tsx` | [gen] world view and controls config; the rest of `ui/` is [base] |
| `tests/backend/test_rules.py` | [gen] world invariants; all other tests are [base] |

## Contracts

**`sim/env.py`** — one `gymnasium.Env` subclass, registered with `register_world(EnvClass)`.

- `NAME`, `DIFFICULTIES` (exactly three: easy, medium, hard; website level N = `DIFFICULTIES[N-1]`), `__init__(difficulty)`, `actions` (tuple of world verbs).
- Difficulty fixes the structure and the `Dict` spaces; `reset(seed)` only draws values. Same seed + actions → same trace.
- `step` = one week; reward = the week's profit; `info` may carry `discovered: list[str]` and `story: {tag, text, tone}`.
- `check_action(verb, args) -> dict` — validate and normalise; raise `ValueError` if invalid.
- `encode_actions([(verb, args), ...]) -> action` — merge a week's queued actions.
- `observe(site=None) -> dict` — visible state only.
- `result() -> float` — the raw outcome so far (e.g. profit since the start).
- `score() -> dict` — at least `score` (0–1), `week`, `done`, and `formula` (how the score is computed, shown in the Goal card). `score` = `result() / target`, clipped, with `target = calibrated_target(type(self))` from `sim/helpers.py`: the target is derived from the baseline policy on easy (the baseline scores about 0.5 there), never hand-tuned. Include `target` in the result and the UI state so the goal can show it.
- `baseline_action() -> action` — naive policy for the baseline score.
- `ui_state(ctx) -> dict` — at least `world {name, seed, difficulty}` and `week`; **same shape as `mockState` in `World.tsx`**. `ctx` has `seed`, `story`, `discoveries`, `active`, `queued`, `agent`.

**`server/mcp.py`** — `build_mcp(game)`. Core tools `brief`, `observe`, `note`, `advance`, `score`, `cancel`, plus one tool per verb in `env.actions`. Each tool calls `game.*(…, source="agent")`.

**`ui/src/World.tsx`** — exports `mockState`, `toControls(state, selectedId)`, `WorldView({ state, selectedId, onSelect })`. Draw with `shared/kit` (see `shared/kit/README.md`). Give each actionable object its id as `target` on `Hud` / `Building`, so the agent cursor can move to it.

**Agent playing (decision 0007)** — the Agent panel starts an agent from `agents.toml` through `harness serve` (the world server forwards relative `harness/` requests to `$HARNESS_URL`, or localhost `$HARNESS_PORT`, default 8090; it supplies its own runtime port). While it plays, `mode = "agent"`: the server rejects UI actions, the dock, inspector and time controls are locked, and `AgentCursor` replays the agent's MCP calls from `WS /api/events` on the `data-target` elements (`map:<id>`, `verb:<id>`, `time:play`). "Stop & take over" hands the world back; "Continue" restarts the agent from the current week.

## Server

| Route | |
|---|---|
| `GET /api/state` | `env.ui_state(...)` plus `queued` (this step's actions), `score` (`env.score()` + `baseline`) and `play {mode, agent}` (who plays) |
| `GET /api/score` | `env.score()` plus `baseline`; not logged (for the harness) |
| `POST /api/action {id, args}` | world verb (queued) or UI control: `play`, `fast`, `pause`, `stats`, `new_world`, `mode {mode, agent?}` |
| | while `mode = "agent"` (set by `harness serve`), `/api/action` (except `mode`), `/api/unqueue`, `/api/advance` and `/api/reset` answer 409; MCP calls still work |
| `POST /api/unqueue {index}` | remove one queued action |
| `POST /api/advance {steps?}` | apply queued actions and step |
| `POST /api/reset {seed?, difficulty? \| level?}` | new episode; `level` is 1–3 |
| `GET /healthz` | `{ok: true}` |
| `GET /api/events?after=` · `WS /api/events` | event log: MCP calls, UI actions, advances |
| `POST /api/narration {kind}` | narrator (`kind: "intro"` or `"commentary"`, a progress update from the current game): `{text, sentences, audio_url, audio_error}`; Gemini rewrites `brief.md`, Gradium speaks it; cached in `.narration/`. Keys: `GEMINI_API_KEY` / `GRADIUM_API_KEY`, or `*_FILE` paths, or the world `.env`. Without Gemini: brief captions; without Gradium: `audio_url` null and `audio_error` says why |
| `GET /api/narration/{kind}/audio` | cached narrator audio (`audio/wav`) |
| `/mcp` | MCP, streamable HTTP |

The cursor uses the relative event WebSocket when available and polls the event log when a reverse proxy does not support WebSockets. Narration and audio URLs resolve within the world’s path prefix.
