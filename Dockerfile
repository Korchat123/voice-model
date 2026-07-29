# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.7.13 AS uv

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

RUN useradd --create-home --uid 10001 voice-model \
    && chown -R voice-model:voice-model /app
USER voice-model

EXPOSE 8765
CMD ["/app/.venv/bin/python", "scripts/run_service.py"]
