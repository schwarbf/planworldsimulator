# Agent harness

Plays a world through its MCP server with a Pydantic AI agent. See
[decision 0005](../../docs/design-decisions/0005-define-the-agent-harness-and-benchmark.md).

```sh
cd src/worlds/bike-factory && pixi run serve        # start a world on :8000
GEMINI_API_KEY=... pixi run harness play http://127.0.0.1:8000 --agent gemini-flash
pixi run pytest src/harness                          # tests: real world, scripted model, no key
```

**Add an agent:** add an entry to `agents.toml` (model, base_url, api_key_env, settings).
**Budget:** `--tokens`, `--seconds`, one cap for the whole episode. Tool calls count through their tokens.
