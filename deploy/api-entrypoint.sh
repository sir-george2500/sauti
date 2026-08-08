#!/bin/sh
# Container entrypoint: make a fresh database into a working app, then serve.
#
# Same sequence scripts/e2e-db.sh proves against a disposable local Postgres —
# wait for the server, `alembic upgrade head`, then the idempotent seed. Both
# steps are safe to re-run, so this is also the upgrade path: a rebuilt image
# migrates and re-seeds the existing volume on start with no manual commands.
set -eu

echo "[entrypoint] waiting for postgres…"
python - <<'PY'
import os, sys, time, urllib.parse
import psycopg

dsn = os.environ["POSTGRES_URL"]
deadline = time.time() + 120
last = None
while time.time() < deadline:
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 — any connect failure is "not ready yet"
        last = exc
        time.sleep(1)
print(f"[entrypoint] postgres never became ready: {last}", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] alembic upgrade head"
alembic upgrade head

echo "[entrypoint] seeding curriculum (idempotent)"
python -m sauti.seed

echo "[entrypoint] starting: $*"
exec "$@"
