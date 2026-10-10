FROM python:3.13-slim

WORKDIR /app
COPY src/backend /app/src/backend
RUN pip install --no-cache-dir /app/src/backend

ENV PLANWORLDSIMULATOR_DATABASE_URL=sqlite+aiosqlite:////data/planworldsimulator.db \
    PLANWORLDSIMULATOR_WORLDS_DIR=/worlds \
    PLANWORLDSIMULATOR_TEMPLATE_DIR=/worlds-template

EXPOSE 8000
CMD ["planworldsimulator-backend"]
