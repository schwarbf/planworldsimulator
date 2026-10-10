# World template

The base every world is copied from. As shipped it runs a placeholder "Example world".
Full reference world: `src/worlds/bike-factory`.

```bash
pixi run dev    # server on $PORT (default 8000: REST /api, MCP /mcp) + UI on $UI_PORT (default 5173)
pixi run test   # backend tests
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
| `sim/helpers.py` | [base] observation → JSON, `register_world` |
| `server/api.py` | [base] FastAPI app, generic `Game`, `/api` routes, `/mcp` mount |
| `server/narration.py` | [base] voice narrator: Gemini intro text + Gradium TTS, cached in `.narration/` |
| `server/mcp.py` | [gen] `build_mcp(game) -> FastMCP` with the world's tools |
| `ui/src/World.tsx` | [gen] world view and controls config; the rest of `ui/` is [base] |
| `tests/backend/test_rules.py` | [gen] world invariants; all other tests are [base] |

## Contracts

**`sim/env.py`** — one `gymnasium.Env` subclass, registered with `register_world(EnvClass)`.

- `NAME`, `DIFFICULTIES`, `__init__(difficulty)`, `actions` (tuple of world verbs).
- Difficulty fixes the structure and the `Dict` spaces; `reset(seed)` only draws values. Same seed + actions → same trace.
- `step` = one week; reward = the week's profit; `info` may carry `discovered: list[str]` and `story: {tag, text, tone}`.
- `check_action(verb, args) -> dict` — validate and normalise; raise `ValueError` if invalid.
- `encode_actions([(verb, args), ...]) -> action` — merge a week's queued actions.
- `observe(site=None) -> dict` — visible state only.
- `score() -> dict` — at least `score` (0–1), `week`, `done`, and `formula` (one line: how the score is computed; shown in the Goal card).
- `baseline_action() -> action` — naive policy for the baseline score.
- `ui_state(ctx) -> dict` — at least `world {name, seed, difficulty}` and `week`; **same shape as `mockState` in `World.tsx`**. `ctx` has `seed`, `story`, `discoveries`, `active`, `queued`, `agent`.

**`server/mcp.py`** — `build_mcp(game)`. Core tools `brief`, `observe`, `note`, `advance`, `score`, `cancel`, plus one tool per verb in `env.actions`. Each tool calls `game.*(…, source="agent")`.

**`ui/src/World.tsx`** — exports `mockState`, `toControls(state, selectedId)`, `WorldView({ state, selectedId, onSelect })`. Draw with `shared/kit` (see `shared/kit/README.md`).

## Server

| Route | |
|---|---|
| `GET /api/state` | `env.ui_state(...)` plus `queued` (this step's actions) and `score` (`env.score()` + `baseline`) |
| `GET /api/score` | `env.score()` plus `baseline`; not logged (for the harness) |
| `POST /api/action {id, args}` | world verb (queued) or UI control: `play`, `fast`, `pause`, `stats`, `new_world`, `mode {mode}` |
| `POST /api/unqueue {index}` | remove one queued action |
| `POST /api/advance {steps?}` | apply queued actions and step |
| `POST /api/reset {seed?, difficulty?}` | new episode |
| `GET /api/events?after=` · `WS /api/events` | event log: MCP calls, UI actions, advances |
| `POST /api/narration {kind}` | narrator (`kind: "intro"`): `{text, sentences, audio_url}`; Gemini rewrites `brief.md`, Gradium speaks it; cached in `.narration/`. Without `GEMINI_API_KEY` / `GRADIUM_API_KEY`: brief captions, `audio_url` null |
| `GET /api/narration/{kind}/audio` | cached narrator audio (`audio/wav`) |
| `/mcp` | MCP, streamable HTTP |
