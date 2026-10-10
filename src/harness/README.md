# Agent harness

Plays a world through its MCP server with a Pydantic AI agent. See
[decision 0005](../../docs/design-decisions/0005-define-the-agent-harness-and-benchmark.md).

```sh
cd src/worlds/bike-factory && pixi run serve        # start a world on :8000
GEMINI_API_KEY=... pixi run harness play http://127.0.0.1:8000 --agent gemini-flash
pixi run pytest src/harness                          # tests: real world, scripted model, no key
```

**Watch it play in the world UI** ([decision 0007](../../docs/design-decisions/0007-show-the-agent-playing-in-the-world-ui.md)):

```sh
cd src/worlds/bike-factory && pixi run dev           # world on :8000, UI on :5173 (proxies /harness → :8090)
GEMINI_API_KEY=... pixi run harness serve            # :8090; --pace 1.0 s per tool call, --tokens, --seconds
```

Pick an agent in the Agent panel and press Start (or Continue). A UI run continues
from the current week with a fresh budget, waits `--pace` seconds before each tool
call, and does not play out the remaining weeks (not a benchmark result).
Benchmarks and `harness play` stay at full speed.

| Route | |
|---|---|
| `GET /agents` | agents from `agents.toml`: `name, label, color, model` |
| `POST /run {world_url, agent}` | start a background run on that world (409 if one is running) |
| `POST /stop {world_url}` | stop it; the world goes back to `mode = "you"` |
| `POST /pace {world_url, seconds}` | change the pace, also while an agent plays (0–5 s) |
| `GET /status?world_url=` | `running, agent, seconds, pace, last` (how the last run ended) |

**Add an agent:** add an entry to `agents.toml` (model, base_url, api_key_env, settings; `label` and `color` for the world UI).
**Budget:** `--tokens`, `--seconds`, one cap for the whole episode. Tool calls count through their tokens.
