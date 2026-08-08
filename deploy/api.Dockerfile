# Sauti API image — FastAPI + uvicorn, no ML.
#
# Build context is the repo root (see deploy/docker-compose.yml + .dockerignore).
# The ML voice services stay on the host: pulling torch + Hugging Face
# checkpoints into an image would add ~8 GB to a disk with ~27 GB free. The API
# reaches them over host.docker.internal instead.
#
# Multi-stage so the final layer carries no uv, no compilers and no build
# caches — just python:3.12-slim, the resolved virtualenv and the source tree.

# ---------- stage 1: resolve dependencies with uv ----------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Dependency layer first: it only re-resolves when pyproject/uv.lock change.
# --no-dev keeps pytest/testcontainers/websockets out of the image.
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then the project itself.
COPY services/api/src ./src
RUN uv sync --frozen --no-dev

# ---------- stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src

RUN useradd --create-home --uid 10001 sauti

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY services/api/src ./src
COPY services/api/alembic ./alembic
COPY services/api/alembic.ini ./alembic.ini
COPY deploy/api-entrypoint.sh /usr/local/bin/sauti-entrypoint

# Stub/local speech artefacts and the local TTS fallback dir (config.py derives
# both from services/api/var, i.e. /app/var here). Must exist and be writable.
RUN chmod 0755 /usr/local/bin/sauti-entrypoint \
    && mkdir -p /app/var/audio /app/var/tts \
    && chown -R sauti:sauti /app/var

USER sauti

EXPOSE 8000

# /healthz is the unversioned alias main.py registers outside /api/v1.
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=10 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"

ENTRYPOINT ["sauti-entrypoint"]
CMD ["uvicorn", "sauti.main:app", "--host", "0.0.0.0", "--port", "8000"]
