FROM python:3.13-slim

WORKDIR /app
COPY src/backend /app/src/backend
RUN pip install --no-cache-dir /app/src/backend

ENV PLANBENCH_DATABASE_URL=sqlite+aiosqlite:////data/planbench.db \
    PLANBENCH_WORLDS_DIR=/worlds \
    PLANBENCH_TEMPLATE_DIR=/worlds-template

EXPOSE 8000
CMD ["planbench-backend"]
