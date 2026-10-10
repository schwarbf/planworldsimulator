# Define the agent harness and benchmark

**Date:** 2026-10-10
**Status:** proposed

## Context

The Agent Harness (decision 0001) plays any world through its MCP server
(decision 0004). We want to benchmark different models on fixed worlds, with a
fair budget, and swap models by config only.

## Decision

### File tree

```
src/harness/                        Python package, same layout as src/backend
├─ pyproject.toml                   pydantic-ai-slim[google,openai,mcp], httpx
├─ README.md                        How to play, benchmark and add an agent.
├─ agents.toml                      One entry per agent: model, base_url, api_key_env.
├─ src/planworldsimulator_harness/
│  ├─ config.py                     Settings: results dir, default agent.
│  ├─ agents.py                     Load agents.toml; build a Pydantic AI model from model + base_url + key.
│  ├─ client.py                     Connect to a running world by URL: reset(seed, difficulty), score, events.
│  ├─ agent.py                      Generic agent: system prompt, world MCP as tools, history trimming.
│  ├─ budget.py                     Budget (tokens, seconds) → UsageLimits + timeout.
│  ├─ episode.py                    Run one episode on a world URL, finish remaining weeks, return EpisodeResult.
│  ├─ benchmarks/
│  │  ├─ servers.py                 Start N world servers on free ports; stop them after.
│  │  ├─ benchmark.py               Run a suite: agents × worlds × difficulties × seeds → JSONL.
│  │  ├─ report.py                  JSONL → markdown table.
│  │  ├─ suites/
│  │  │  └─ smoke.toml              bike-factory, 1 seed, small budget: does MCP control work?
│  │  └─ results/                   Gitignored: <run-id>/episodes.jsonl + transcripts.
│  └─ cli.py                        `harness play <url>`, `harness bench <suite>`, `harness report <run>`.
└─ tests/
   ├─ test_episode.py               Real bike-factory server + TestModel; no API key.
   └─ test_budget.py                Limits stop the run; episode still gets a score.
```

### Swappable agents

An agent is config, not code:

```toml
[gemini-flash]
model = "google-gla:gemini-2.5-flash"
api_key_env = "GEMINI_API_KEY"

[local-llama]
model = "openai:llama-3.1-70b"
base_url = "http://localhost:8001/v1"
api_key_env = "LOCAL_KEY"
```

Suites reference agents by name.

### Episode

1. Connect to the world URL; reset to a fixed seed and difficulty.
2. Run the agent with the budget. It acts only through MCP tools.
3. Stop when the episode is done, the agent stops, or a limit is hit.
4. The harness advances remaining weeks with no actions, so every run ends at week 52.
5. Record score, score − baseline, profit, served, tokens, tool calls, time, limit hit.

### Budget

- Tokens are the main cap for the whole episode.
- Time (30 min) is only a loose safety cap: wall-clock depends on API latency, so it is not fair as a budget.
- Tool calls and thinking count through their tokens; no separate tool-call cap.
- A hidden safety limit (2,000 tool calls) only catches loops.
- Thinking level is pinned per agent (`thinking` setting).
- The system prompt states the full budget at the start.
- Before each model request, a history processor adds a status line:
  `Budget left: 0.8M/2.0M tokens, 6:10 min.`
- The line is neutral numbers only; no advice, so it does not steer the model.
- Cap hit: Pydantic AI stops the run; the harness plays out remaining weeks with no actions.

### Fairness

- Same seeds, difficulty, prompt and budget for every agent.
- Temperature and thinking level pinned per agent.
- Token counts differ slightly between providers (tokenizers); fine for Gemini vs Gemini.
- The agent cannot reset (no MCP tool) and never sees `secret.md`.
- One server per episode; parallel runs use separate ports.

### Who starts worlds

- Harness core only takes a URL; it never starts servers.
- The backend Launcher (decision 0001) starts worlds for the web UI.
- `benchmarks/servers.py` starts worlds for benchmarks, without the backend. The
  real Launcher may reuse it later.

## Consequences

- New model = new `agents.toml` entry.
- The backend can later call `run_episode(world, agent)` for an agent picker in
  the web UI; the world UI already shows agent calls via `/api/events`.
- The harness relies only on the core tools (`brief`, `observe`, `note`,
  `advance`, `score`).

## Alternatives considered

- **Harness calls the agent once per week:** smaller context, but puts game-loop
  knowledge in the harness. Deferred; history trimming first.

## Implementation plan

1. `client.py`, `agents.py`, `agent.py`, `episode.py`; `harness play` on a running bike-factory.
2. `budget.py`, fair finish, tests.
3. `benchmarks/` (servers, benchmark, report, suites).
4. Later: agent picker in the web UI.

Models: `gemini-3.8-flash`, `gemini-3.1-pro-preview` (Gemini 2.5 is retired for
new keys). Budget: 2M tokens, 30 min safety cap per episode (smoke run: 1.1M tokens for 44 weeks).

## Supersedes

None
