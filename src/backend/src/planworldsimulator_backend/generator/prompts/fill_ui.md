You are building the isometric web view of a PlanWorld world. Another agent builds the simulator at the same time from the same design; stay exactly consistent with `design.md`.

World: $title
Request: $description

Everything you need is in this message; do NOT read or run anything. In ONE turn, make a single `write` call that replaces `ui/src/World.tsx` completely.

## design.md (the plan, follow it)

$design

## Rules

- Import `State` from `./WorldState` and re-export `State` and `mockState` from that file. Do not redefine or edit either. Keep the exports and their signatures: `toControls(state, selectedId)`, `WorldView({ state, selectedId, onSelect })`. `State` and `mockState` must have exactly the keys and types of the JSON in the `## UI state` section of design.md; the real server state will be checked against `mockState`.
- `toControls` maps the state to the shared controls (brand, top bar, story, inspector for the selected site, discoveries, goal with progress bars, agent panel, action dock). Use the world's verbs from design.md as inspector actions (`primary` and `actions`, ids = verb names, args as in the placeholder). Selecting a site changes the inspector. Be defensive: the state may be missing optional fields; never divide by zero.
- `WorldView` draws the world with `./shared/kit` only (see the kit docs below): follow the `## Visual concept` of design.md: its palette, island size and object placement. Painter's order: sort by `i + j`. At least 8 objects, a `Hud` pill per site, something animated (`Flow`, a moving `Vehicle`, weather, `pulse`), `Fog` on unexplored things at higher levels (state.world.difficulty), and visible differences between Easy, Medium and Hard (more sites and objects on higher levels). Sites that are not available on a level are not drawn.
- It must look good: fill the stage, balanced composition, readable HUD labels that do not overlap, consistent colours.
- TypeScript strict; no new dependencies; imports only from `./shared/...`. No other files.

## Shared types (the contract of `toControls`; use only these names, especially the icons in `IconName`)

$types

## Kit documentation

$kit_readme

## Current placeholder (replace completely; it shows the exact imports and shared types in use)

$placeholder

## Generated shared state contract (read-only)

$state_contract
