set dotenv-load

web_port := env_var_or_default("PLANWORLDSIMULATOR_WEB_PORT", "8480")
api_port := env_var_or_default("PLANWORLDSIMULATOR_API_PORT", "8400")

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
    pnpm --filter @planworldsimulator/web run typecheck

[group('checks')]
test:
    pixi run pytest src/backend
    pnpm --filter @planworldsimulator/web run test

[group('development')]
build:                      # build the web and api images
    {{compose}} build

[group('development')]
up: build check-ports       # start the stack in the background and wait until it is healthy
    {{compose}} up --detach --wait
    @echo "PlanWorldSimulator: http://localhost:{{web_port}}  (API: http://localhost:{{api_port}}/docs)"

[group('development')]
down:                       # stop the stack (data and generated worlds are kept)
    {{compose}} down --remove-orphans

[group('development')]
dev:                        # run with live reload in the foreground (web on :5173)
    {{compose_dev}} up --build

[group('generator')]
world-setup:                # once: the shared world environment the generator and launcher use
    pixi install --manifest-path src/worlds-template/pixi.toml
    cd src/worlds-template/ui && npm ci
    pixi run playwright install chromium
    @command -v opencode >/dev/null || echo "Install OpenCode too: npm i -g opencode-ai (or brew install sst/tap/opencode)"

[group('generator')]
generate name prompt:       # generate one world with the real agent (needs GEMINI_API_KEY), no website
    PLANWORLDSIMULATOR_WORLDS_DIR=src/worlds pixi run python -m planworldsimulator_backend.generate "{{name}}" "{{prompt}}"

[group('generator')]
api-local:                  # run the API on this machine with the real generator and launcher
    mkdir -p data
    PLANWORLDSIMULATOR_GENERATOR=opencode PLANWORLDSIMULATOR_DATABASE_URL=sqlite+aiosqlite:///./data/local.db PLANWORLDSIMULATOR_PORT={{api_port}} pixi run planworldsimulator-backend

[group('generator')]
web-local:                  # the website with live reload, talking to `just api-local`
    API_PROXY_TARGET=http://localhost:{{api_port}} pnpm --filter @planworldsimulator/web run dev

[group('development')]
logs *services:             # follow logs, optionally for named services (e.g. `just logs api`)
    {{compose}} logs --follow --tail 100 {{services}}

[group('development')]
ps:                         # show the running services
    {{compose}} ps

[group('development')]
reset:                      # stop the stack and delete the database volume
    {{compose}} down --remove-orphans --volumes

# Fail early when another program holds a port we publish. Without this, the
# browser can silently reach that program instead of the site.
[private]
check-ports:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v lsof >/dev/null || exit 0
    status=0
    for port in {{web_port}} {{api_port}}; do
        owners="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null \
            | awk 'NR>1 && $1 !~ /docker|com\.docke|vpnkit|wslrelay/ {print $1 " (pid " $2 ")"}' | sort -u || true)"
        if [ -n "$owners" ]; then
            echo "Port $port is already in use by: $owners" >&2
            echo "Set PLANWORLDSIMULATOR_WEB_PORT / PLANWORLDSIMULATOR_API_PORT in .env to other ports." >&2
            status=1
        fi
    done
    exit $status
