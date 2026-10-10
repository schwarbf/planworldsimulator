# Create worlds with a sandboxed coding agent

**Date:** 2026-10-10
**Status:** accepted; implemented except where "As built" below says otherwise

## Context

Decisions 0001, 0003 and 0004 define what a world is. Today the backend only
runs `FakeGenerator` (copies the template, writes `world.json`) and `FakeLauncher`
(hands out ports, runs nothing). We now build the real thing: a person enters a
name and a description, a coding agent powered by Gemini Flash writes the world
for **three difficulty levels**, tests prove it works, and it appears on the
website ready to play.

Gaps in the current code that this plan closes:

- The website, `generator.py`, `/play` and their tests say four levels; the
  template already has three (`easy`, `medium`, `hard`). **Three wins.**
- `/play` proxies plain HTTP to one port; a world is a server (8000) plus a Vite
  UI (5173) plus a WebSocket, and its UI uses absolute `/api/...` URLs.
- `pixi run` would install a full conda environment per world; far too slow on
  first play.
- `src/worlds/bike-factory` is the reference world for the agent, but
  `src/worlds/` is gitignored.
- Demand has no shared building block.

## Decision

### Pipeline

Python in the backend owns the order of steps; the LLM does only the creative
ones. Runs are repeatable and each step is a real progress event.

```
POST /worlds ─▶ 1 exists? ─▶ 2 design ─▶ 3 copy ─▶ 4 fill ─▶ 5 tests ─▶ 6 polish ─▶ 7 smoke ─▶ 8 publish
                  │ yes                   backend   agent    runs gates,  looks at     backend    backend
                  └─▶ status "exists"                        agent fixes  screenshots
```

| # | Step key | Who | Output |
|---|---|---|---|
| 1 | `check_exists` | backend only, no LLM: the world name's slug is already taken in the DB or in `src/worlds/` | continue, or status `exists` + `duplicate_of` |
| 2 | `design` | agent | `design.md`: storyline, entities, actions, hidden rules, demand factors, level table, the `ui_state` shape (so sim and UI can be written independently), a visual concept (palette, layout of the island) |
| 3 | `copy_template` | backend | `src/worlds/<id>/` from the template; `[base]` checksums stored |
| 4 | `fill` | agent | `brief.md`, `secret.md`, `sim/env.py`, `sim/rules.py`, `sim/demand_config.py`, `server/mcp.py`, `ui/src/World.tsx`, `tests/backend/test_rules.py` |
| 5 | `tests` | backend runs the gates; agent fixes failures, max 2 rounds | green gates or `failed` |
| 6 | `polish` | backend takes screenshots of the world at each level (Playwright); the agent (Gemini is multimodal) critiques them against a checklist and fixes `World.tsx`; 1 round | a world that looks good, not only one that runs |
| 7 | `smoke` | backend: build the UI, boot the world, hit `/api/state`, MCP `list_tools` and `/` | proof it runs |
| 8 | `publish` | backend | write `world.json` and `thumbnail.png`, set `path`, `status = ready` |

The agent may only write the `[gen]` files above (allow-list in OpenCode's
permission config). Before `tests` and `publish` the backend compares `[base]` file
checksums with the template, so the agent cannot weaken a test to turn it green.

### Agent loop: OpenCode is the loop; no PydanticAI wrapper

OpenCode already is a coding-agent loop (read, edit, bash, retries, context
management) and supports Gemini. Wrapping it in PydanticAI would give two loops
and no benefit. PydanticAI stays where decision 0001 put it: the **playing**
agent, which is a different job.

How the backend uses OpenCode (verified in the spike with opencode 1.18.35 and
`google/gemini-3.8-flash`):

1. Each prompt is one subprocess: `opencode run --format json --variant minimal --dir
   <world> [-s <session>] "<prompt>"`. Stdout is one JSON object per line and streams
   live (`step_start`, `tool_use` with `tool` and `state.status`, `text`, `step_finish`
   with `reason` and `tokens`). No `opencode serve`, HTTP client or SDK is needed;
   `-s` continues a session, and parallel tracks are parallel subprocesses.
2. A generated `opencode.json` in the world folder sets the model, `share: disabled`
   and permissions: `external_directory: deny`, `bash`, `webfetch`, `task` and
   `skill` denied, and `edit` denied except for the allow-listed files. **Patterns are
   matched against the absolute path without its leading slash**, so the config writes
   `private/tmp/.../<world>/brief.md`, not `brief.md`.
3. Environment: `GOOGLE_GENERATIVE_AI_API_KEY` (from `GEMINI_API_KEY`),
   `OPENCODE_DISABLE_EXTERNAL_SKILLS=1`, `OPENCODE_DISABLE_CLAUDE_CODE=1`,
   `OPENCODE_DISABLE_AUTOUPDATE=1`. Without these the agent loads the user's global
   skills and wanders outside the folder. Use the normal `HOME`: a fresh one costs
   about 50 s on the first run.
4. **One OpenCode session per track.** `design` runs in a main session. `fill` then
   runs two sessions in parallel, `sim` and `ui`, each seeded with `design.md`. Failed
   test rounds send one `fix` prompt (the failing output) to the session that owns the
   failing file. Each session keeps its context. The session ids are stored so a retry
   can resume.
5. Map OpenCode events (file written, tool call, bash result) to
   `GenerationEvent`s. That is the live detail in the website's progress list.
6. Kill the subprocess at the run's deadline.

**Spike result (step A):** works headless with Gemini 3.8 Flash. A one-line edit took
37 s: each model turn takes 3–14 s, so a world is affordable only with few turns. The
prompts therefore carry all context (design, contracts, reference files) so the agent
does not explore, and ask for each file in one `write` call. This is why the 5-minute
budget is tight and why `fill` runs in two parallel tracks.

### Three difficulty levels

Levels are cumulative and driven by one table in `sim/env.py`, so the rules are
written once. Level N maps to `DIFFICULTIES[N-1]`.

| Level | Name | Adds |
|---|---|---|
| 1 | Easy | Core loop, 1–2 sites, 3–4 actions, no hidden rules, noise off |
| 2 | Medium | More sites, 1–2 hidden rules, lead times or capacity limits, weather |
| 3 | Hard | The expert mode: competitors and events, all demand factors, 3+ interacting hidden rules, fog, action budget, noise on. The agent sees sales and demand signals, never the formula |

### Demand component

New `[base]` module `sim/demand.py`, used by every world, following the
multiplicative model in the FoodTruckBench screenshot:

```
demand = base × price × location × weather × time × day_of_week × events
              × variety × competition × reputation × popularity × noise
```

- A `DemandModel` is a list of `Factor`s `(site, state, rng) -> float`, neutral
  value 1.0. Shipped factors: `price_elasticity`, `affinity`, `weather`,
  `seasonality` (time, day of week), `events`, `variety`, `competition`,
  `reputation` (log of reviews), `popularity`, `noise`.
- The generator writes **no formulas**, only `sim/demand_config.py`: which
  factors exist, their parameters (drawn from the seed) and the first level that
  enables each.
- `env.py` calls `demand.compute(site)` and exposes only sales and unmet demand.
- `Discoveries` marks a factor as found once it has been probed. My reading of
  "somewhere in this world"; correct me if you meant a visible panel or chart.

### Template changes (`src/worlds-template/`)

| File | Change | Why |
|---|---|---|
| `sim/helpers.py` | add `LEVELS = {1: "easy", 2: "medium", 3: "hard"}` | one mapping from the URL level to the env difficulty |
| `sim/demand.py` **new** `[base]` | `DemandModel`, shipped factors | shared demand component |
| `sim/demand_config.py` **new** `[gen]` | factors, parameters, first level | the generator's only demand file |
| `server/api.py` | `reset` accepts `level`; `/healthz`; serve `ui/dist` at `/` | level link, play behind the proxy; the UI polls `/api/state`, so no SSE is needed |
| `ui/vite.config.ts`, `ui/src/api.ts` | `base: "./"`; relative URLs | works behind `/api/play/<id>/` |
| `ui/src/App.tsx` | read `?level=` and call reset | level link from the website |
| `ui/src/shared/controls/Brand.tsx`, `Discoveries.tsx` | level name; found demand factors | Easy / Medium / Hard; demand visible once probed |
| `ui/package.json`, `ui/src/test-setup.ts`, `ui/src/App.test.tsx` | add Vitest, jsdom and Testing Library, and the render test (next to the UI so React resolves) | decision 0003 lists the frontend gate; it does not exist yet |
| `pixi.toml`, `process-compose.yaml` | tasks `build-ui`, `test-ui`; prod mode runs only the server | no Vite dev server in a played world |
| `tests/backend/test_env.py`, `test_api.py`, `test_mcp.py` | parametrise over the three levels; reset by level | contract changes |
| `tests/backend/test_demand.py`, `test_playability.py`, `test_no_leak.py` **new** `[base]` | see Gates | quality gates |
| `brief.md`, `secret.md`, `README.md` | point at `src/worlds-reference/`; update the contract and file table | the agent reads them |
| `ui/src/shared/kit/README.md` | add the visual checklist | `polish` step |

The `Game` stays one global object per world server: everything runs locally with
one player at a time, so there is no per-player state.

Not changed: `sim/env.py`, `rules.py`, `server/mcp.py` and `World.tsx` keep their
contracts, so the placeholder world still runs.

### Gates (the sandbox)

`pixi run test` and `pixi run test-ui` inside the sandbox. Existing `[base]`
tests stay; new `[base]` tests are marked **new**.

| Gate | Checks |
|---|---|
| `test_env.py` | `check_env` and determinism per level |
| contract | `check_action`, `encode_actions`, `ui_state` shape equals `mockState` |
| `test_mcp.py`, `test_api.py` | every verb is a tool and a route; events work |
| `test_playability.py` **new** | baseline scores in (0, 1) on every level; do-nothing < baseline; baseline never improves with level |
| `test_no_leak.py` **new** | words from `secret.md` and factor parameters never appear in `brief`, `observe` or `/api/state` |
| `test_demand.py` **new** | disabled factors are 1.0; demand finite and ≥ 0 over a seeded rollout |
| frontend | `tsc`, `vite build`, Vitest render of `World.tsx` with `mockState` |
| smoke | boot, `/api/state`, MCP `list_tools`, `/` returns HTML |
| `test_run.py` | optional: one Gemini agent run at level 1 (later) |

The sandbox is a subprocess with its own temp directory, the Gemini key as the only
secret, and wall-clock and round limits. Dependencies come from a prebuilt shared
environment, so tests need no network. Everything runs on your machine, so
container-per-run is optional hardening for later.

### Time budget: hard cap 5 minutes per world

Tokens are free today, so wall-clock time is the only cost. The whole run (all
steps, the agent and the gates) has **one 5-minute deadline**. A phase that
overruns its slice is cut off; when the deadline passes, the run ends as
`failed` with the partial world kept on disk. Retry starts a new 5 minutes and
resumes the OpenCode session. Targets are estimates until step K measures them.

| Phase | Target | Cut-off |
|---|---|---|
| `check_exists`, `design` | 30 s | 45 s |
| `fill` (simulator and UI in parallel) | 2 min | 2 min 30 s |
| `tests` (gates and fix rounds) | 1 min | 2 rounds, 1 min 15 s |
| `polish` | 30 s | 1 round, 45 s |
| `smoke`, `publish` | 30 s | 30 s |
| **Total** | **about 4 min** | **5 min** |

This is tight for a nice world, so the plan makes five choices for speed:

- **Small worlds:** at most 4 sites and 5 actions; the level table and the demand
  config carry the difficulty. Fewer files means fewer bugs and fix rounds.
- **Parallel fill is the default, not a later optimisation:** `design.md` fixes the
  `ui_state` shape, then two OpenCode sessions run at once: simulator (`rules`,
  `env`, `demand_config`, `mcp`, `test_rules`) and UI (`World.tsx`).
- **Fast gates:** short seeded rollouts (20 steps), no browser in `tests`; Playwright
  runs only in `polish` and `smoke`.
- **Prewarmed environment:** shared Python and `node_modules`, so a copy needs no
  install, and `vite build` is the only slow command.
- **Fail soft on looks:** `polish` is the first thing skipped when time is short,
  never the tests.

Also a guard against runaway loops: 60 tool calls per prompt. Quality comes from
the design checklist in `kit/README.md` (island fills the stage, 8+ kit objects,
HUD pills do not overlap, palette from `design.md`, weather and flows animated) and
the single `polish` round.

If step K shows 5 minutes is not enough at the chosen model's speed, cut in this
order: `polish`, then the number of kit objects asked for, then the world size.

For the demo, pre-generate two or three worlds and keep live generation for one
prompt; four minutes of visible progress is watchable.

### Routing and going live: nothing is configured per world

Routing is data-driven. A world is one row in the database plus one folder on
disk:

```
Browser ─▶ nginx ─ /api/play/<id>/?level=2 ─▶ API  GET /play/<id>/
                                                │ 1. look up the row (id → status, path, port)
                                                │ 2. not running? launcher starts it, waits for /healthz
                                                │ 3. proxy to http://127.0.0.1:<port>/
                                                ▼
                                          world server (FastAPI: /api, /mcp, built UI at /)
```

- `/worlds/:id` in the website is one generic React route; the catalogue is
  `GET /worlds`. Publishing a world means setting `status = ready` and `path`.
  No route, nginx or frontend change is needed.
- **`ProcessLauncher`** runs `<shared-env>/bin/python -m uvicorn server.api:app --port N`
  with the world folder as working directory. Dependencies are `[base]` and fixed,
  so one environment baked into the API image serves every world; nothing is
  installed per world. It picks a free port, waits for `/healthz`, tracks the PID;
  the existing reaper stops idle worlds.
- **UI served by the world server:** the `smoke` step builds the UI (`vite build`, using a
  shared `node_modules` symlinked in). `server/api.py` serves `ui/dist` at `/`.
  Vite `base: "./"` and `api.ts` use relative URLs (`api/state`), so the UI works
  behind the `/api/play/<id>/` prefix.
- **Events:** the UI polls `/api/state` over plain HTTP, so the proxy needs no WebSocket
  or SSE support; the event WebSocket stays for direct use.
- **Level:** `?level=N` is forwarded; the world UI reads it on load and calls
  `POST /api/reset {level}`.
- **One game per world server:** the shared `Game` in `server/api.py` is kept. Only
  one player uses a world at a time on your machine, so there is no player id, no
  per-player registry and nothing to add to the proxy. The chain stays nginx → API
  (`/play`, an `httpx` reverse proxy) → world server; the API already knows each
  world's port from the database. There is no load balancer and none is needed.
- **Agent later:** it connects to the world's existing `/mcp` and plays the same
  `Game` as the UI, which is how the "You / Agent" toggle in decision 0004 works.
- If this is ever hosted for many visitors, the first change is a game per player
  in the world server; it is deliberately left out now.

### How a world is stored and shown

| Where | What |
|---|---|
| `worlds` table (SQLite) | Metadata only: `id`, `title`, `prompt`, `seed`, `status` (`queued`, `generating`, `ready`, `failed`, **`exists`**), `storyline`, `path`, `running`, `port`, `featured`, `play_count`, `creator_hash` |
| new columns (migration `0004`) | `duplicate_of`, `agent_sessions`, `model`, `gen_seconds`, `gate_report` (JSON of the last test run) |
| `world_events` table | One row per progress event, streamed to the website over SSE |
| `src/worlds/<id>/` (volume) | The world itself: code, `world.json`, `thumbnail.png`. Source of truth for the game |

The main website never renders a world. It shows the catalogue card (title,
premise, thumbnail, status, play count), the generation progress, and three
**Play at Easy / Medium / Hard** links. The link opens the world's own UI in a
new tab. This matches decision 0001: no shared frontend that must integrate every
generated world. `thumbnail.png` is a Playwright screenshot of level 1, served
by `GET /worlds/<id>/thumbnail`; featured worlds keep their static images.

## Implementation steps

Sizes are rough: S under an hour, M a few hours, L most of a day.

**A. Spike (S), done.** OpenCode runs headless with Gemini 3.8 Flash; see the spike
result above. Go; the PydanticAI fallback is not needed.

**B. Template: levels, one port, tests (M).** Everything in the table
"Template changes" except the demand files, in this order: `LEVELS` and `reset`
by level → `/healthz` and static UI → UI changes → tests. *Done when:*
`pixi run test` passes and the built UI works when opened through
`/api/play/<id>/?level=2`.

**C. Demand module, new gates and Vitest (M).** `sim/demand.py`, `sim/demand_config.py`
placeholder, `tests/backend/test_demand.py`, `test_playability.py`,
`test_no_leak.py`, and the frontend test setup; make the placeholder world use the demand model so the gates
run green on the template. Show found factors in `Discoveries`.

**D. Reference world (S).** Copy `src/worlds/bike-factory` to a committed
`src/worlds-reference/bike-factory` and bring it to the new contract (three
levels, demand config). The agent reads it as the example. Point
`worlds-template/README.md` at the new path.

**E. Website: three levels (S).** `src/web/src/`:
- `components/DifficultySection.tsx`: `LEVELS = ["Easy", "Medium", "Hard"]`,
  heading "Three levels in every world", copy "all three", and three cells per
  table row.
- `components/PromptWindow.tsx:72`, `components/ExistingWorlds.tsx:101`,
  `pages/WorldDetail.tsx`: "four" becomes "three".
- `components/PlayLevels.tsx`: show `Easy / Medium / Hard` labels with the level
  number in the `aria-label`.
- Tests: `DifficultySection.test.tsx`, `Home.test.tsx`, `ExistingWorlds.test.tsx`
  (`levels: [1, 2, 3]`, three links).
- Backend: `generator.py` `LEVELS = (1, 2, 3)`; `api/play.py` `le=3`;
  `tests/test_worlds_api.py` expects `[1, 2, 3]`. No migration, levels are not
  stored.

**F. Generator package (L).** Replace `generator.py` with a package:

```
generator/__init__.py          Generator protocol, GenerationRequest, GenerationEvent
generator/fake.py              FakeGenerator (kept for tests and key-less runs)
generator/opencode_generator.py  runs steps 1–8 in order
generator/opencode_runner.py   spawn `opencode run`, parse the JSON event lines
generator/exists.py            step 1 (slug check)
generator/gates.py             run pixi tests, parse the report, checksum guard
generator/prompts/             design.md, fill.md, fix.md, polish.md
generator/opencode_template/   opencode.json, world-builder agent prompt
```

Settings in `config.py`: `generator` (`fake` or `opencode`), `gemini_api_key`,
`generator_model`, `fix_rounds`, `generator_timeout_seconds`. `main.py` picks the
generator from settings. Tests: step ordering with a stubbed client, the checksum
guard catches an edited `[base]` file, failed gates end in `failed` with the
report in `gate_report`.

**G. Database and runner (S).** Migration `0004` with the new columns. `runner.py`
handles the `exists` outcome and stores `agent_sessions` and `gate_report`.
`retry` resumes the session. `POST /worlds` answers 409 with the world id for an
exact slug match.

**H. Launcher and play route (M).** `launcher.py`: `ProcessLauncher`
(free port, spawn, `/healthz` wait, stop); `play.py` returns a "starting" page
that retries instead of the placeholder when the world is slow to boot. Tests
with a tiny stub server.

**I. Website generation progress (S).** `WorldDetail.tsx` `STEPS` becomes
`check_exists`, `design`, `copy_template`, `fill`, `tests`, `polish`, `smoke`, `publish`,
with a per-file and per-test-round detail line; an "already exists" card with a
link to `duplicate_of`; `StatusChip` handles `exists`; catalogue card shows the
thumbnail. Update `PromptWindow` copy.

**J. Deployment (S).** API image gets Node, `opencode`, the shared Python and
`node_modules` environment, Chromium for thumbnails; `compose.yaml` passes
`GEMINI_API_KEY` and the generator settings; `.env.example` documents them;
README gets a section.

**K. End to end (M).** Add the `polish` step (Playwright screenshots, critique
prompt). Generate three different prompts, fix the template and
prompts where the agent gets stuck, record time and tokens per world and check the 5-minute budget. *Done
when:* a new world appears on the site, passes all gates and plays at all three
levels in a browser.

**L. Hardening (L, after the demo).** Container per generation with an egress
allow-list, `test_run.py` with the Gemini player, agent
vs. you in the same world.

Order: A first; B, C, D, E in parallel (different files); then F, G, H, I; then
J and K. Cut line for the demo: A–K.

## As built

What differs from the plan above, and what is still open.

- **Model:** `google/gemini-3.5-flash`. In the spike `gemini-3.8-flash` was about 6× slower on the
  same design prompt (about 90 s against 14 s), which cannot fit 5 minutes. Switch with
  `PLANWORLDSIMULATOR_GENERATOR_MODEL`.
- **Steps:** `check_exists`, `copy_template`, `design`, `sim` and `ui` (in parallel), `tests`,
  `polish`, `smoke`, `publish`. The copy comes before the design because the agent writes into the folder.
- **Design is data:** the agent writes `design.json`, validated by `WorldSpec`
  (`generator/spec.py`); an invalid file gets up to two correction rounds. From it the pipeline
  writes `design.md` and `ui/src/WorldState.ts` (the typed state contract), which the agent may
  not edit. The server state is checked against it at every level (except the shared `queued`).
- **Branches and resume:** the simulator and the web view are written, checked and repaired
  independently, then cross-checked. Hash-verified checkpoints let a retry resume; attempts and
  timings are stored (migration 0005).
- **Score target is calibrated,** not guessed: `calibrated_target()` makes the naive baseline
  score about 0.5 on easy. Generated worlds only have to make the baseline profitable and the
  higher levels harder. Hard may defeat the baseline.
- **Gates added during testing:** `test_contract.py` (the design's sites, actions and episode
  length per level, and MCP argument types), clear failure messages for the leak and playability
  gates, a seed test that explains itself.
- **Agent runs** are `opencode run` subprocesses, not `opencode serve`; the agent may only write
  its allow-listed files, and process groups are killed at the deadline.
- **Names:** a name can be used once (`409` with `X-Existing-World`); duplicates end as `exists`.
- **Local use:** `just world-setup`, `just generate`, `just api-local`, `just web-local`. The
  Docker image has no OpenCode or world environment, so the real generator runs on the host.
- **Look check (`polish`):** Playwright screenshots of all three levels go to the agent once; it
  may rewrite `World.tsx`, and the change is kept only if type check, build and UI tests still
  pass (otherwise the first view is restored). It is skipped when under 75 s remain or Chromium
  is missing (`pixi run playwright install chromium`). The model often answers "already looks
  good", so it has little effect so far.
- **Thumbnails:** a level 1 screenshot is saved as `thumbnail.png` at publish, served by
  `GET /worlds/<id>/thumbnail` and shown on the catalogue card (`has_thumbnail`).
- **Measured end to end:** a lemonade world went through the API and the process launcher in
  144 s: published, thumbnail served, played through `/play/<id>/?level=3` (the UI reset the
  world to hard). This found and fixed a bug: relative interpreter and world paths broke the
  launcher. Harder prompts (harbor, power grid, cold chain) failed in an earlier round; their
  causes (broken JSON, the shared `queued` field, an over-hard baseline gate) were fixed but not
  re-run, so there is no success rate yet.
- **Not built:** Docker support for the real generator, and a recorded success rate over several
  prompts.

## Consequences

- Quality comes from the template, `demand.py` and the gates more than from the
  prompt; a world is live only if the gates are green.
- Step order is code, so the agent cannot skip checks and single steps can be
  retried.
- The agent writes less per world, since levels are a table and demand is a
  config, which fits a Flash-class model.
- Template changes (levels in the URL, single port) do not
  reach worlds generated earlier.

## Alternatives considered

- **PydanticAI loop around Gemini instead of OpenCode:** more code to own
  (tools, edit format, retries); kept as the fallback.
- **OpenCode wrapped in PydanticAI:** two loops for one job.
- **Agent runs the whole workflow from one prompt:** it can skip the exists
  check, edit tests, or claim success without running anything.
- **One generation per level:** three rule sets drift apart and cost three times
  as much.
- **Free-form demand formulas:** break the playability gates and are hard to
  review.
- **`pixi install` per world:** minutes on first play.
- **Store worlds in the database:** code is a folder tree that tests and servers
  need on disk.

## Open questions

- Exact Gemini model ID and its speed: it decides whether 5 minutes is enough.
- Whether the budget table holds once measured (step K).
- Whether the Gemini critique in `polish` catches real layout problems; if not, replace it with fixed geometric checks (overlap, bounds).

## Supersedes

None
