# Define the world simulator and server

**Date:** 2026-10-10
**Status:** proposed

## Context

Each generated world (decision 0003) needs a simulator, a server for the UI and
an MCP server for the agent. Humans and the agent must be able to do the same
things in the same world.

## Decision

### Simulator (`sim/env.py`)

- Gymnasium env; one `step` = one day.
- **Difficulty** (constructor) fixes the structure: number of buildings, kinds
  of instances (e.g. competitors, weather) and available actions.
- **Seed** (`reset`) only changes values: positions, lead times, demand,
  hidden-rule parameters.
- Every difficulty has fixed spaces, so no padding or action masks.

### Server (`server/`)

One process (port 8000) with one shared `Game` (env, today's queued actions,
event log). REST for the UI and MCP for the agent both call the same `Game`
methods.

```
Agent (Gemini) ──▶ /mcp  tools ─┐
                                ├──▶ Game: env, today's actions, event log
UI (browser)   ──▶ /api  REST ──┘
```

| | UI (REST) | Agent (MCP) |
|---|---|---|
| Read | `GET /api/state`: whole visible state at once | `brief()`, `observe()`, `observe(site)`, `score()` |
| Act | `POST /api/action`, `POST /api/advance`, `POST /api/reset` | `order()`, `expand()`, `probe()`, `advance()` |
| Extra | `WS /api/events`: every MCP call, for the agent panel | `note(text)`: records a hypothesis |

- Same actions for both, so "Agent vs You" is fair.
- `/api/state` contains only what is visible; fog and hidden rules stay out
  until probed.
- The UI keeps the selection locally and reads the selected site from the
  state.

### Example (Bike Factory, Medium)

MCP tools: `brief`, `observe`, `order(site, qty)`, `expand(site)`,
`probe(site)`, `note(text)`, `advance(days=1)`, `score`.

Agent:

```
brief()                          → "Bike Factory… goal: CHF 1M, ≥95% served"
observe()                        → {week: 12, sites: [{id: "warehouse", stock: 212, …}]}
note("Store B demand seems seasonal")
order(site="warehouse", qty=60)  → "queued"
advance()                        → {week: 13, reward: 4120, served: 0.94, …}
```

UI:

| UI | Endpoint |
|---|---|
| World view and controls | `GET /api/state` |
| Inspector "Order 60" | `POST /api/action {id: "order", args: {target: "warehouse", amount: 60}}` |
| Play / Fast-forward | `POST /api/advance` |
| New world | `POST /api/reset {seed, difficulty}` |
| Agent panel | `WS /api/events` |

### Base files

- `sim/helpers.py` — observation → JSON, env registration.
- `server/api.py` — FastAPI with `/api` routes and `/mcp` mounted; owns `Game`.
- `pixi.toml` — Python 3.13, gymnasium, fastapi, uvicorn, mcp, pytest, nodejs;
  tasks `serve`, `ui`, `test`, `dev`.
- `process-compose.yaml` — `server` (8000) and `ui` (Vite, 5173).

## Consequences

- The generator writes `env.py`, `rules.py` and `mcp.py`; `Game`, routes and
  wiring come from the base.
- The UI shows the agent playing live by reading the same state and event log.

## Alternatives considered

- **UI calls MCP tools directly:** rejected; one state snapshot is simpler and
  always consistent.
- **Padding and masks for variable sizes:** rejected; difficulty fixes the
  structure.

## Supersedes

None
