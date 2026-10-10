# Define the generated world file tree

**Date:** 2026-10-10
**Status:** proposed

## Context

The Template Generator (decision 0001) creates one self-contained world per
run. It needs a fixed file tree: which files come from the base template and
which ones it writes.

## Decision

`[base]` = copied from the template, never edited · `[gen]` = written by the generator

```
worlds/<slug>/
├─ brief.md               [gen]  Public story, goal and actions; given to the agent.
├─ secret.md              [gen]  Hidden rules and scoring; never given to the agent.
├─ pixi.toml              [base] Dependencies (gymnasium, mcp, fastapi) and tasks (serve, test).
├─ process-compose.yaml   [base] Starts the server and the UI.
├─ sim/
│  ├─ env.py              [gen]  Gymnasium env: spaces per difficulty, new instance per seed, one step = one day.
│  ├─ rules.py            [gen]  World dynamics and hidden rules.
│  └─ helpers.py          [base] Padding and action masks, observation → JSON, env registration.
├─ server/
│  ├─ mcp.py              [gen]  One MCP tool per unlocked action, plus advance, observe and score.
│  └─ api.py              [base] REST/WebSocket for the UI and the agent event log; same process as MCP.
├─ ui/src/
│  ├─ shared/             [base] Branding and shared controls: inspector, discoveries, goal, agent panel, action dock.
│  ├─ App.tsx             [base] Page layout around the world view.
│  ├─ api.ts              [base] Connection to the server: state, actions, agent events.
│  └─ World.tsx           [gen]  How this world is drawn, plus its config (inspector fields, verbs, goal bars).
└─ tests/
   ├─ backend/
   │  ├─ test_env.py      [base] Gymnasium `check_env` and determinism for every difficulty.
   │  ├─ test_rules.py    [gen]  World-specific invariants.
   │  ├─ test_mcp.py      [base] MCP tools match the unlocked actions; advance, observe and score work.
   │  └─ test_run.py      [base] Optional: one agent run end to end.
   └─ frontend/
      └─ App.test.tsx     [base] Vitest: renders `World.tsx` with mock state without crashing.
```

- **Difficulty** is set in the env constructor and defines the available actions.
- **Seed** is set in `reset` and draws a new world instance.

## Consequences

- The generator writes only `[gen]` files; layout, server API and branding stay identical in every world.
- `check_env` tests every generated world for free.

## Alternatives considered

- **Custom env interface instead of Gymnasium:** rejected; coding agents know Gymnasium well, and its checker gives free tests.
- **Generator writes the whole UI:** rejected; worlds could break the layout or the server connection.

## Supersedes

None
