# PlanWorldSimulator world generator

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
just up      # build, start in the background, wait until healthy
just down    # stop (database and generated worlds are kept)
```

Open http://localhost:8480 (API docs on http://localhost:8400/docs). If another program uses
those ports, `just up` says so; set `PLANWORLDSIMULATOR_WEB_PORT` and
`PLANWORLDSIMULATOR_API_PORT` in `.env` to change them. Other commands: `just build`, `just logs [service]`,
`just ps`, `just reset` (also deletes the database volume) and `just dev` (live
reload, site on http://localhost:5173). Copy `.env.example` to `.env` to change
defaults.

## Develop

Needs [pixi](https://pixi.sh), [pnpm](https://pnpm.io) and [just](https://just.systems).

```sh
just install
just format
just lint
just typecheck
just test
```
