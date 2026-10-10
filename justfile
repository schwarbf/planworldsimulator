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
up:
    docker compose up --build

[group('development')]
dev:
    docker compose -f compose.yaml -f compose.dev.yaml up --build
