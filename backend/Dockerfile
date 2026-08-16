# ==================================================
# OncoVision AI Backend — Production Dockerfile
# ==================================================
# Multi-stage build: Python packages (including TensorFlow 2.10) are
# compiled/installed in a disposable "builder" stage that has the system
# build toolchain, then only the resulting packages and application source
# are copied into the slim "runtime" stage. This keeps the final image free
# of compilers and apt package lists without changing what actually runs.

# --------------------------------------------------
# Stage 1: builder
# --------------------------------------------------
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Build tools are only needed while resolving/installing dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (into the user site-packages dir) to
# leverage Docker layer caching -- this layer only rebuilds when
# requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --------------------------------------------------
# Stage 2: runtime
# --------------------------------------------------
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/home/appuser/.local/bin:$PATH

WORKDIR /app

# `curl` is retained in the runtime image only because it powers the
# container HEALTHCHECK below. No compiler/build toolchain ships here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create the non-root user before copying files so ownership can be set in
# the same layer as each COPY, avoiding an extra recursive chown pass.
RUN useradd --create-home --shell /bin/bash appuser

# Bring in the dependencies built in the previous stage.
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application source and the Alembic migration environment. Alembic is
# required inside the image so `python -m alembic upgrade head` can be run
# as a release/pre-deploy step against the container's own dependency set.
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini .

# Create storage/log directories expected by the application at runtime.
RUN mkdir -p storage/uploads storage/reports storage/models logs \
    && chown -R appuser:appuser storage logs

# Run as a non-root user for improved container security.
USER appuser

EXPOSE 8000

# Container-level healthcheck against the existing, unauthenticated health
# endpoint. `start-period` gives the AI Runtime Manager time to complete its
# startup model-loading sequence before failed checks count against it.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Production entrypoint: no `--reload`, bound to all interfaces on 8000.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
