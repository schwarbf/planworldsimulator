compose := "docker compose"
compose_dev := "docker compose -f compose.yaml -f compose.dev.yaml"

default:
    @just --list

[group('setup')]
install:
    pixi install
    pnpm install

[group('checks')]
format:
    pixi run ruff format .
    pnpm run format

[group('checks')]
lint:
    pixi run ruff check .
    pnpm run lint

[group('checks')]
typecheck:
    pixi run pyright
    pnpm --filter @planbench/web run typecheck

[group('checks')]
test:
    pixi run pytest src/backend
    pnpm --filter @planbench/web run test

[group('development')]
build:                      # build the web and api images
    {{compose}} build

[group('development')]
up: build                   # start the stack in the background and wait until it is healthy
    {{compose}} up --detach --wait
    @echo "PlanBench: http://localhost:8080  (API: http://localhost:8000/docs)"

[group('development')]
down:                       # stop the stack (data and generated worlds are kept)
    {{compose}} down --remove-orphans

[group('development')]
dev:                        # run with live reload in the foreground (web on :5173)
    {{compose_dev}} up --build

[group('development')]
logs *services:             # follow logs, optionally for named services (e.g. `just logs api`)
    {{compose}} logs --follow --tail 100 {{services}}

[group('development')]
ps:                         # show the running services
    {{compose}} ps

[group('development')]
reset:                      # stop the stack and delete the database volume
    {{compose}} down --remove-orphans --volumes
