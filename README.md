# PlanBench world generator

Describe a planning benchmark in plain language and generate a playable world from it.
See [docs/design-decisions](docs/design-decisions) for the architecture.

The generator is a fake for now: it walks through the real steps (storyline, copy
template, fill template, tests) and writes a world folder, but does no LLM work.

## Layout

| Path                  | What it is                                                  |
| --------------------- | ----------------------------------------------------------- |
| `src/web`             | Website (Vite, React, TypeScript, Tailwind)                 |
| `src/backend`         | API (FastAPI, SQLite via SQLAlchemy and Alembic)            |
| `src/worlds-template` | Base template every world is copied from                    |
| `src/worlds`          | Generated worlds, one folder each (contents are gitignored) |

## Run it

```sh
docker compose up --build   # or: just up
```

Open http://localhost:8080. For live reload, run `just dev` (site on
http://localhost:5173). Copy `.env.example` to `.env` to change defaults.

## Develop

Needs [pixi](https://pixi.sh), [pnpm](https://pnpm.io) and [just](https://just.systems).

```sh
just install
just format
just lint
just typecheck
just test
```
