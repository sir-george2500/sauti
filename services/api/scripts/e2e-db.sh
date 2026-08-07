#!/usr/bin/env bash
# Boot (or reuse) a local Postgres for the e2e suite, migrate and seed it.
#
# The dev/prod database is a remote Supabase instance ~380 ms away; with the
# pgbouncer transaction pooler forcing both statement caches off, every query
# costs several round trips (~1.6 s). Fine for a deployed API next to the DB,
# hopeless for a 13-journey browser suite. E2e therefore runs against this
# disposable local Postgres — same image and migrations as the integration
# tests — while dev and prod keep Supabase.
set -euo pipefail

CONTAINER=sauti-e2e-pg
PORT="${SAUTI_E2E_PG_PORT:-55432}"
export SAUTI_E2E_POSTGRES_URL="postgresql://postgres:sauti-e2e@localhost:${PORT}/postgres"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  docker run -d --name "$CONTAINER" \
    -e POSTGRES_PASSWORD=sauti-e2e \
    -p "${PORT}:5432" \
    postgres:16-alpine >/dev/null
else
  docker start "$CONTAINER" >/dev/null
fi

for _ in $(seq 1 60); do
  if docker exec "$CONTAINER" pg_isready -U postgres -q 2>/dev/null; then
    break
  fi
  sleep 0.5
done
docker exec "$CONTAINER" pg_isready -U postgres -q

cd "$(dirname "$0")/.."
POSTGRES_URL="$SAUTI_E2E_POSTGRES_URL" uv run alembic upgrade head
POSTGRES_URL="$SAUTI_E2E_POSTGRES_URL" uv run python -m sauti.seed
echo "e2e db ready on :${PORT}"
