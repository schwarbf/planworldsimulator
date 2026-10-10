You are building the simulator and agent interface of a PlanWorld world. Another agent builds the web view at the same time from the same design; stay exactly consistent with `design.md`.

World: $title
Request: $description

Everything you need is in this message; do NOT read or run anything. In ONE turn, make parallel `write` calls that replace these files completely: $files

## design.md (the plan, follow it)

$design

## Rules

- Follow the contract (below) and keep the structure of the placeholder files; replace the placeholder world with this one.
- `DIFFICULTIES = ("easy", "medium", "hard")` exactly. Difficulty fixes the structure (sites, actions, spaces); the seed only draws values. Same seed and actions give the same trace. Level n = `DIFFICULTIES[n-1]`. Use the level table in design.md; `Dict` spaces must be fixed per difficulty. At most 4 sites and 5 actions; episodes of 12 to 16 steps (one step = one week).
- Difficulty knobs: put every per-level parameter in ONE table in `rules.py`, e.g. `LEVEL = ({"demand_scale": 1.0, "cost_scale": 1.0, "shock_prob": 0.0, "shock_size": 0.0, "lead_weeks": 0}, {... 0.9, 1.2, 0.08, 0.25, 1}, {... 0.8, 1.45, 0.2, 0.4, 2})`, indexed by `level - 1`, and use every entry in the dynamics (demand times `demand_scale`, all costs times `cost_scale`, random shocks that cut demand or stock, delayed deliveries). This is what makes Medium and Hard harder for a naive player; the playability test fails if the baseline does not get clearly worse from Easy to Hard (by at least 0.05).
- Demand: write `sim/demand_config.py` as `build(base, level) -> DemandModel` from the blocks in `sim/demand.py` (API below), with the factors, parameters and first levels from design.md. In `rules.py` call `model.detail(ctx, rng)` every step with a `ctx` dict of what you know that week; call `model.newly_found(mults, found)` to report discovered factors. Never expose the formula or the multipliers to the agent: only sales and unmet demand. Show discoveries with `model.discoveries(found)` in `ui_state` (add your own hidden-rule discoveries to the same lists).
- `ui_state(ctx)` must return exactly the keys and types of the JSON in the `## UI state` section of design.md (same names, plain numbers, no numpy types). `ctx` provides `seed`, `story`, `discoveries`, `active`, `queued`, `agent`.
- Hidden rules live only in `rules.py` and `secret.md`. `secret.md` has `## Hidden rules` (each rule with its mechanism; put the rule's internal names in backticks) and `## Scoring`. `brief.md` (public: story, goal, actions with arguments and limits, 12 to 25 lines) must not mention hidden rules, factors or formulas, and must not contain any backticked name from `secret.md`'s hidden rules. A test fails the world if hidden names leak into `brief`, `observe` or `/api/state`.
- Discovery hints: the strings in `discoveries.hidden` (the "?" the player sees) must be vague plain words ("Something about the gate queue seems off"), never a rule's internal name from `secret.md`. Internal names never appear in `observe`, state or score.
- Economy: first make sure a sensible naive policy earns a clear positive result on Easy (revenue above costs, start cash enough for the first weeks); only then add the hidden penalties for Medium and Hard.
- Scoring: implement `result()` (the raw outcome so far, e.g. profit) and `score()` exactly like the placeholder: `score = clip(result() / self.target(), 0, 1)` with `target()` returning `calibrated_target(type(self))` from `sim/helpers.py`. NEVER hand-tune a score target: it is calibrated so the baseline scores about 0.5 on Easy. `score()` also returns `week`, `done`, `target`. `baseline_action()` is a naive but sensible policy (the same reasonable action every week); it must beat doing nothing, and score clearly lower on Hard than on Easy because of the LEVEL table. `brief.md` does not state a numeric target: it says the score is the result relative to a target that `score()` reports.
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
