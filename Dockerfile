# Multi-arch Dockerfile for kasa-exporter
# Uses catalyst-images:python as base (includes Python 3.12, Poetry, dev tools)
# Supports: linux/amd64, linux/arm64

FROM ghcr.io/thebranchdriftcatalyst/catalyst-images:python AS base

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml poetry.lock README.md /app/

# Configure Poetry to not create venv (use system python from catalyst-images)
RUN poetry config virtualenvs.create false

# Install dependencies only (no dev deps)
RUN poetry install --only main --no-interaction --no-ansi

# Copy source code
COPY ./kasa_exporter /app/kasa_exporter

# Install the project itself
RUN poetry install --only main --no-interaction --no-ansi

# Default port for metrics
EXPOSE 9200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9200/health || exit 1

ENTRYPOINT ["python", "-m", "kasa_exporter"]
