You are building the simulator and agent interface of a PlanWorld world. Another agent builds the web view at the same time from the same design; stay exactly consistent with `design.md`.

World: $title
Request: $description

Everything you need is in this message; do NOT read or run anything. In ONE turn, make parallel `write` calls that replace these files completely: $files

## design.md (the plan, follow it)

$design

## Rules

- Follow the contract (below) and keep the structure of the placeholder files; replace the placeholder world with this one.
- `DIFFICULTIES = ("easy", "medium", "hard")` exactly. Difficulty fixes the structure (sites, actions, spaces); the seed only draws values. Same seed and actions give the same trace. Level n = `DIFFICULTIES[n-1]`. Use the level table in design.md; `Dict` spaces must be fixed per difficulty. At most 4 sites and 5 actions; episodes of 12 to 16 steps (one step = one week).
- Demand: write `sim/demand_config.py` as `build(base, level) -> DemandModel` from the blocks in `sim/demand.py` (API below), with the factors, parameters and first levels from design.md. In `rules.py` call `model.detail(ctx, rng)` every step with a `ctx` dict of what you know that week; call `model.newly_found(mults, found)` to report discovered factors. Never expose the formula or the multipliers to the agent: only sales and unmet demand. Show discoveries with `model.discoveries(found)` in `ui_state` (add your own hidden-rule discoveries to the same lists).
- `ui_state(ctx)` must return exactly the keys and types of the JSON in the `## UI state` section of design.md (same names, plain numbers, no numpy types). `ctx` provides `seed`, `story`, `discoveries`, `active`, `queued`, `agent`.
- Hidden rules live only in `rules.py` and `secret.md`. `secret.md` has `## Hidden rules` (each rule with its mechanism; put the rule's internal names in backticks) and `## Scoring`. `brief.md` (public: story, goal, actions with arguments and limits, 12 to 25 lines) must not mention hidden rules, factors or formulas, and must not contain any backticked name from `secret.md`'s hidden rules. A test fails the world if hidden names leak into `brief`, `observe` or `/api/state`.
- Scoring: `score()` returns `score` in [0, 1], `week`, `done` (and what else the UI needs). Tune constants so that `baseline_action()` (a naive policy, e.g. the same sensible action every week) scores strictly between 0 and 1, about 0.4 to 0.6 on easy, beats doing nothing, and never scores better on a harder level.
- `server/mcp.py`: keep the five core tools (brief, observe, note, advance, score) and add one tool per verb in `env.actions`, each calling `game.act(verb, args, source="agent")`, with a docstring describing arguments and limits.
- `tests/backend/test_rules.py`: 4 to 6 short invariant tests of this world (parametrised over all difficulties) plus one that `check_action` rejects bad arguments.
- The generic tests already in `tests/backend` (Gymnasium `check_env`, determinism, MCP covers every action, API, demand, playability, no-leak, contract) must pass without being edited.
- Python 3.13, numpy, gymnasium; type-correct and simple. No other files.

## Contract

$readme

## sim/demand.py (read-only, the API you build on)

$demand_api

## Current placeholder files to replace

$placeholders
