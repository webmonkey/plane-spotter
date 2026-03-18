FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY plane_spotter/ plane_spotter/

ENTRYPOINT [".venv/bin/python", "-m", "plane_spotter"]
