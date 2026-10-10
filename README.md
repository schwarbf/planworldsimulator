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

## Generate real worlds

Put `GEMINI_API_KEY` in `.env`, then `just build` and `just up` as above. The API image
contains the coding agent (OpenCode), the shared world environment and Chromium, so the site
generates real worlds that you can play (about 2–5 minutes each; the first build takes a
while and the image is around 3 GB). Without a key the stack still starts and generates
fake worlds: the API log says which one it uses ("world generation: ...").

Worlds are written to `src/worlds/` on your machine. The model defaults to
`google/gemini-3.5-flash` (`PLANWORLDSIMULATOR_GENERATOR_MODEL` changes it).

Without Docker, on your machine:

```sh
just world-setup                       # once: world environment, Chromium, OpenCode check
just generate "Lemonade" "A lemonade stand ..."   # one world from the command line
just api-local                         # or: the API with the real generator and launcher
just web-local                         # the website on http://localhost:5173
```

A world has three difficulty levels, must pass its tests, and is playable from the website.
See [decision 0006](docs/design-decisions/0006-create-worlds-with-a-sandboxed-coding-agent.md).

## Develop

Needs [pixi](https://pixi.sh), [pnpm](https://pnpm.io) and [just](https://just.systems).

```sh
just install
just format
just lint
just typecheck
just test
```
