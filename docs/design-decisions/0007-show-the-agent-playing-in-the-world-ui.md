# Show the agent playing in the world UI

**Date:** 2026-10-10
**Status:** proposed

## Context

The harness (decision 0005) plays a world through MCP, but the player cannot
see it. We want to start an agent from the world UI, watch it act, and take
over at any time.

## Decision

### Start and stop

- Agent panel: picker (agents from `agents.toml`) and "Start agent" / "Stop".
- `harness serve`: small service with `GET /agents`, `POST /run {world_url, agent}`,
  `POST /stop {world_url}` and `GET /status?world_url=`; the world UI reaches it
  through the Vite proxy (`/harness` → `$HARNESS_PORT`, default 8090).
- A run continues from the current week (no reset) with a fresh budget; the
  agent re-reads the world with `brief()` and `observe()`.
- `--pace` (default 1 s per tool call, via the MCP `process_tool_call` hook) for
  UI runs only; benchmarks run at full speed.
- A UI run does not play out the remaining weeks (`run_episode(reset=False,
  finish=False)`); the fair finish is for benchmarks only.

### Agent cursor (fake, from MCP events)

- The UI already gets every agent call live (`WS /api/events`, `source: "agent"`).
- Each action becomes an animation: move to the site on the map, move to the
  dock verb, click pulse, action appears in the queue. `advance` goes to Play.
- Reads (`observe`, `brief`) show a short "reading…" bubble.
- Events play one after another, about 0.6 s per move.
- World-independent: map elements and dock buttons get `data-target`
  attributes in the base components (`map:<id>` via the `target` prop of `Hud`
  and `Building`, `verb:<id>`, `time:play`); the cursor moves to `map:<arg>` for
  any string argument of the call, and selects that object.
- Look: arrow + round robot-face badge + name pill, one colour per agent
  (violet Gemini Flash, teal Gemini Pro; `label` and `color` in `agents.toml`).

### Frozen controls and take over

- While the agent plays: dock, Inspector and time controls are dimmed with a
  lock; a banner shows "Gemini Flash is playing · week 12 / 52 · Stop & take over".
- The server rejects UI actions while the agent plays (`mode = "agent"`, set by
  the harness with `POST /api/action {id: "mode", args: {mode, agent}}`); 409.
  `state.play {mode, agent}` tells the UI who plays.
- "Stop & take over" ends the run; the world stays as it is and the player
  continues by hand. "Continue" starts the agent again from there.

### Design draft

Figma page "Agent cursor – draft": "Agent cursor – parts", "Agent playing",
"Agent panel – start", "Handoff".

## Consequences

- Every world gets the agent view, because it uses only base components and
  core MCP events.
- Mixed runs (agent + human) are not benchmark results; only full agent runs
  count.
- Built on its own branch with an Entire trail, so the work shows on the
  entire.io dashboard.

## Alternatives considered

- **Agent controls a real browser:** rejected; slow, and the agent must stay UI-agnostic.
- **Replay after the run:** rejected; we want to watch live and take over.

## Supersedes

None
