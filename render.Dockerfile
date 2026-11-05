FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

ARG VITE_OTEL_EXPORTER_OTLP_ENDPOINT=
ARG VITE_SAVORLOOP_ENVIRONMENT=render
ARG RENDER_GIT_COMMIT=local
ENV VITE_OTEL_EXPORTER_OTLP_ENDPOINT=$VITE_OTEL_EXPORTER_OTLP_ENDPOINT \
    VITE_SAVORLOOP_ENVIRONMENT=$VITE_SAVORLOOP_ENVIRONMENT \
    VITE_SAVORLOOP_VERSION=$RENDER_GIT_COMMIT

COPY frontend/ ./
ARG VITE_EPHEMERAL_DEMO=true
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.8.15 AS uv
FROM python:3.11-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DATABASE_URL=sqlite:////tmp/savorloop.db \
    SAVORLOOP_ENVIRONMENT=render

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend ./backend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 10000

CMD ["sh", "-c", "uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
