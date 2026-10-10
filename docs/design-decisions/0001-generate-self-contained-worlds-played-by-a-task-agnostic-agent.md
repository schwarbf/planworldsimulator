# Generate self-contained worlds played by a task-agnostic agent

**Date:** 2026-10-10
**Status:** accepted

## Context

PlanWorldSimulator generates new planning worlds on demand and lets an agent
play them. Every world needs its own rules, actions and visuals, but the agent,
the branding and the controls must stay the same across worlds.

## Decision

The system has four parts:

```
Template Generator (coding agent)  ──generates──▶  World Template
                                                   ├─ Simulator
                                                   ├─ MCP server
                                                   └─ UI (website)
Agent Harness  ──plays via MCP──▶  World Template  ◀──starts/opens──  Launcher
```

### 1. Agent Harness (task-agnostic)

- PydanticAI + Gemini client.
- Input: the world description and the world's MCP server.
- Acts only through the MCP tools; knows nothing world-specific.

### 2. World Template (generated per world)

Each world is a self-contained, fully working website:

- **Simulator** — gym-style environment with evaluation (score).
- **MCP server** — the interface to the simulator: actions in, observations out.
- **UI** — the website for this world.

The base template ships the parts that stay the same in every world (from the
Figma design):

- **Branding** — background, colours, typography, layout.
- **Shared controls** — ready-made components: inspector, discoveries, goal,
  agent panel, action dock.

The generator only creates the world view (how the world is drawn) and the
game logic.

### 3. Template Generator (harness for creating worlds)

A coding agent (Claude Code, or OpenCode as an open-source option) with a
prompt:

1. Generate a storyline for the world.
2. Copy the base template.
3. Fill the template (simulator, MCP tools, world view using the shared
   components).
4. Run tests (optional: one agent run end to end).

### 4. Launcher

- Lists the generated worlds and opens each world's website.
- Starts and stops each world's servers in the background (`pixi run` /
  process-compose).

## Consequences

- The generator produces one self-contained thing that it can run and test in
  isolation; there is no integration contract with a main website.
- Every world can look different while branding and controls stay identical.
- Changes to the base template do not reach worlds generated earlier.

## Alternatives considered

- **One main website that renders every world** — rejected: every generated
  world would need to integrate into a shared frontend, which is harder for the
  generator to get right and to test.

## Implementation plan

| Time | Milestone | Owner |
|---|---|---|
| 14:00 | First template, runnable in a sandbox (frontend) | Bernhard |
| 14:00 | Technical design of the template-generation loop | Flo |
| 15:00 | First randomly generated world | Both |
| 15:00 | Take stock and decide next steps, including how we use all hackathon partners (Gemini, Gradium, Entire) | Both |
| 15:00–18:00 | Open, depending on progress | Both |
| 18:00 | Start recording the video | Both |
| 19:00 | Competition opt-in deadline | Both |

## Supersedes

None
