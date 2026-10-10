# World template

The base for every generated world. As shipped it is **Bike Factory**, a complete, runnable first world.

```bash
pixi install
pixi run dev    # server on :8000 (REST /api, MCP /mcp) + UI on :5173
pixi run test   # backend tests
```

Single parts: `pixi run serve`, `pixi run ui`. Copy `.env.example` to `.env` for agent runs.

## Files

`[base]` = same in every world, never edited · `[gen]` = written per world

| File | |
|---|---|
| `pixi.toml`, `process-compose.yaml` | [base] dependencies and tasks |
| `brief.md` | [gen] public story, goal, actions (given to the agent) |
| `secret.md` | [gen] hidden rules and scoring (never given to the agent) |
| `sim/env.py` | [gen] Gymnasium env + world contract (below) |
| `sim/rules.py` | [gen] dynamics and hidden rules |
| `sim/helpers.py` | [base] observation → JSON, `register_world` |
| `server/api.py` | [base] FastAPI app, generic `Game`, `/api` routes, `/mcp` mount |
| `server/mcp.py` | [gen] `build_mcp(game) -> FastMCP` with the world's tools |
| `ui/src/World.tsx` | [gen] world view and controls config; the rest of `ui/` is [base] |
| `tests/backend/test_rules.py` | [gen] world invariants; all other tests are [base] |

## Contracts for a generated world

**`sim/env.py`** defines one `gymnasium.Env` subclass and calls `register_world(EnvClass)`.

- `NAME`, `DIFFICULTIES` (e.g. `("easy", "medium", "hard")`), `__init__(difficulty)`.
- Difficulty fixes the structure and the (fixed) `Dict` spaces; `reset(seed)` only draws values. Same seed + actions → same trace.
- `step` = one time unit (Bike Factory: one week), reward = profit of the step. `info` may carry `discovered: list[str]` and `story: {tag, text, tone} | None`.
- `actions`: tuple of world verbs (e.g. `order`, `expand`, `probe`).
- `check_action(verb, args) -> dict` — validate and normalise one action; raise `ValueError` if invalid.
- `encode_actions([(verb, args), ...]) -> action` — merge one step's queued actions into a Gymnasium action.
- `observe(site=None) -> dict` — visible state only (no hidden rules).
- `score() -> dict` with `score` (0–1), `week`, `done`.
- `baseline_action() -> action` — naive policy; its final score is the baseline.
- `ui_state(ctx) -> dict` — the UI state, **same shape as `mockState` in `World.tsx`**. `ctx` has `seed`, `story`, `discoveries`, `active`, `queued`, `agent`.

**`server/mcp.py`** exports `build_mcp(game)`. Each tool is a thin call into `game`, always with `source="agent"` so it is logged:
`game.brief()`, `game.observe(site)`, `game.act(verb, args)`, `game.advance(n)`, `game.note(text)`, `game.score()`.

**`ui/src/World.tsx`** exports `mockState`, `toControls(state, selectedId)` and `WorldView({ state, selectedId, onSelect })`.

## Server

| Route | |
|---|---|
| `GET /api/state` | `env.ui_state(...)` |
| `POST /api/action {id, args}` | world verb (queued for the next step) or UI control: `play` (+1 step), `fast` (+4), `pause`, `stats`, `new_world`, `mode {mode}` |
| `POST /api/advance {steps?}` | apply queued actions and step |
| `POST /api/reset {seed?, difficulty?}` | new episode |
| `GET /api/events?after=` · `WS /api/events` | event log: every MCP call, UI action and advance |
| `/mcp` | MCP, streamable HTTP |
