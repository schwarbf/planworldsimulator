# The API with everything real world generation needs: OpenCode, the shared world
# environment, the shared UI packages and Chromium (screenshots). Without a Gemini key
# the API still starts and generates fake worlds.

# Shared Python environment for all worlds (their dependencies are the template's).
FROM python:3.13-slim AS world-env
COPY src/backend/world-requirements.txt /tmp/world-requirements.txt
RUN python -m venv /opt/world-env \
    && /opt/world-env/bin/pip install --no-cache-dir -r /tmp/world-requirements.txt

# Shared node_modules for all worlds' UIs (type check, tests, vite build).
FROM node:24-slim AS world-ui
WORKDIR /ui
COPY src/worlds-template/ui/package.json src/worlds-template/ui/package-lock.json ./
RUN npm ci

FROM python:3.13-slim
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright \
    PIP_NO_CACHE_DIR=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g opencode-ai@1.18.35 \
    && pip install playwright \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY --from=world-env /opt/world-env /opt/world-env
COPY --from=world-ui /ui/node_modules /opt/world-ui/node_modules

WORKDIR /app
COPY src/backend /app/src/backend
RUN pip install /app/src/backend

# The API runs as a normal user: it starts agent-written code (see entrypoint.sh).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /worlds \
    && chown app:app /data /worlds
ENV HOME=/home/app

ENV PLANWORLDSIMULATOR_DATABASE_URL=sqlite+aiosqlite:////data/planworldsimulator.db \
    PLANWORLDSIMULATOR_WORLDS_DIR=/worlds \
    PLANWORLDSIMULATOR_TEMPLATE_DIR=/worlds-template \
    PLANWORLDSIMULATOR_REFERENCE_DIR=/worlds/bike-factory \
    PLANWORLDSIMULATOR_WORLD_PYTHON=/opt/world-env/bin/python \
    PLANWORLDSIMULATOR_NODE_MODULES_DIR=/opt/world-ui/node_modules \
    PLANWORLDSIMULATOR_NO_SANDBOX=1 \
    PLANWORLDSIMULATOR_GENERATOR=auto

EXPOSE 8000
ENTRYPOINT ["/app/src/backend/entrypoint.sh"]
CMD ["planworldsimulator-backend"]
