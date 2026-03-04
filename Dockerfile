# ---- Builder stage ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.12-slim

# Paquets systeme pour WeasyPrint (PDF generation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    fontconfig \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

ARG UID=1000
ARG GID=1000
RUN groupadd --gid $GID kandidat && useradd --uid $UID --gid kandidat kandidat

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

RUN mkdir -p /app/data && chown -R kandidat:kandidat /app/data

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    FT_DATA_DIR=/app/data \
    KANDIDAT_ENV=prod

EXPOSE 8000

USER kandidat

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:create_app()"]
