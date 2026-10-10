# Define the generated world file tree

**Date:** 2026-10-10
**Status:** proposed

## Context

The Template Generator (decision 0001) creates one self-contained world per
run. It needs a fixed file tree: which files come from the base template and
which ones it writes.

## Decision

`[base]` = copied from the template, never edited · `[gen]` = written by the generator

The template lives in `src/worlds-template/`; each world is a copy in
`src/worlds/<id>/`. `src/worlds/bike-factory/` is the reference world.

```
src/worlds/<id>/
├─ brief.md               [gen]  Public story, goal and actions; given to the agent.
├─ secret.md              [gen]  Hidden rules and scoring; never given to the agent.
├─ pixi.toml              [base] Dependencies (gymnasium, mcp, fastapi) and tasks (serve, ui, test, dev).
├─ process-compose.yaml   [base] Starts the server ($PORT) and the UI ($UI_PORT).
├─ sim/
│  ├─ env.py              [gen]  Gymnasium env: spaces per difficulty, new instance per seed, one step = one week.
│  ├─ rules.py            [gen]  World dynamics and hidden rules.
│  └─ helpers.py          [base] Observation → JSON, env registration.
├─ server/
│  ├─ mcp.py              [gen]  Core tools (brief, observe, note, advance, score) plus one tool per world action.
│  └─ api.py              [base] REST/WebSocket for the UI and the agent event log; same process as MCP.
├─ ui/src/
│  ├─ shared/             [base] Branding, shared controls and the SVG kit (see below).
│  ├─ App.tsx             [base] Page layout around the world view.
│  ├─ api.ts              [base] Connection to the server: state, actions, agent events.
│  └─ World.tsx           [gen]  How this world is drawn, plus its config (inspector fields, verbs, goal bars).
└─ tests/
   ├─ backend/
   │  ├─ test_env.py      [base] Gymnasium `check_env` and determinism for every difficulty.
   │  ├─ test_rules.py    [gen]  World-specific invariants.
   │  ├─ test_mcp.py      [base] MCP tools cover the world's actions; reads, notes and advance work.
   │  ├─ test_api.py      [base] REST routes, UI controls and the event WebSocket work.
   │  └─ test_run.py      [base] Optional: one agent run end to end.
   └─ frontend/
      └─ App.test.tsx     [base] Vitest: renders `World.tsx` with mock state without crashing.
```

- **Difficulty** (env constructor) fixes the structure: buildings, instance kinds and available actions.
- **Seed** (`reset`) only changes values, so no padding or action masks.

### `ui/src/shared/`

```
shared/
├─ theme.css           Paper background, colours, fonts, radii, shadows (Figma tokens).
├─ controls/           Same in every world; driven by the config in World.tsx.
│  ├─ Brand.tsx         Logo, world name, seed, difficulty.
│  ├─ TopBar.tsx        Main number (cash/bill), rate chip, time progress.
│  ├─ StoryToast.tsx    Story event banner.
│  ├─ Inspector.tsx     Selected object: title, level, stats grid, main action, extra actions.
│  ├─ Discoveries.tsx   Found and hidden rules.
│  ├─ Goal.tsx          Goal text and progress bars.
│  ├─ AgentPanel.tsx    You/agent toggle, score chart, now testing, policy code.
│  └─ ActionDock.tsx    Verbs, "N / 8 actions", stats, time controls, new world.
├─ primitives/         Small UI pieces.
│  ├─ Card.tsx          Rounded white card.
│  ├─ Chip.tsx          Small label pill.
│  ├─ Bar.tsx           Progress bar with optional target tick.
│  ├─ Hud.tsx           Map label pill: level, name, bar, tag.
│  └─ Icon.tsx          Icon set (probe, order, bolt, auto, …).
└─ kit/                SVG building blocks for isometric world views.
   ├─ README.md         What exists and how to use it; the generator reads this.
   ├─ iso.ts            Isometric projection and tile math.
   ├─ Stage.tsx         Frame that keeps the SVG and the Hud overlay aligned.
   ├─ IsoIsland.tsx     Floating tile slab with grid, path and water tiles.
   ├─ IsoBox.tsx        Shaded box; the base for buildings.
   ├─ Building.tsx      Box with windows, roof, chimney and gable variants.
   ├─ Tree.tsx          Tree.
   ├─ Person.tsx        Worker figure.
   ├─ Vehicle.tsx       Truck, car, ship.
   ├─ Fog.tsx           Fog tiles, clouds, "?".
   ├─ Flow.tsx          Animated dashed lines (routes, power, water).
   └─ Weather.tsx       Sun, cloud, storm.
```

- World views are **isometric only**. The generator uses the kit and adds its own components inside `World.tsx`.

## Consequences

- The generator writes only `[gen]` files; layout, server API and branding stay identical in every world.
- `check_env` tests every generated world for free.

## Alternatives considered

- **Custom env interface instead of Gymnasium:** rejected; coding agents know Gymnasium well, and its checker gives free tests.
- **Generator writes the whole UI:** rejected; worlds could break the layout or the server connection.

## Supersedes

None
