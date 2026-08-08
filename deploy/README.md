# Sauti, running locally

A four-container stack on this machine, for daily study. Not a public product:
plain HTTP, one origin, no cloud, no multi-tenant anything.

```
                     browser
                        │  http://sauti.localhost
                        ▼
              ┌───────────────────┐
              │ proxy  caddy:2    │  :80 on IPv4 and IPv6
              └─────┬───────┬─────┘
        /api/*      │       │      everything else
        /healthz    │       │
        /ws/*       ▼       ▼
            ┌──────────┐  ┌──────────┐
            │   api    │  │   web    │  Next.js standalone
            │ FastAPI  │  └──────────┘
            └────┬─────┘
                 │              ┌──────────────────────────────┐
      ┌──────────┴──────────┐   │ HOST (not containerised)     │
      ▼                     └──►│  :8093 YourTTS / Kokoro TTS  │
┌────────────┐  host.docker.    │  :8092 Kinyarwanda ASR       │
│     db     │  internal        └──────────────────────────────┘
│ postgres16 │
└────────────┘
```

## Why voice is on the host

`services/voice` runs on rent-rwanda's coqui virtualenv: Python 3.11, an old
pinned torch, the two Kinyarwanda YourTTS checkpoints and the Kokoro ONNX
model. That is roughly **8 GB already sitting on this disk**, and the disk has
~26 GB free. Containerising it would copy all of it a second time, for no
benefit on a single-machine deployment.

So the api container reaches the host services through the Docker bridge:

```yaml
extra_hosts: ["host.docker.internal:host-gateway"]
VOICE_SERVICE_URL: http://host.docker.internal:8093
SAUTI_ASR_URL:     http://host.docker.internal:8092
```

**The one thing this requires of you:** the host services must listen on
`0.0.0.0`, not `127.0.0.1`. A loopback-only bind is invisible to containers —
the api will get `Connection refused` on `172.17.0.1:8093`. Start them as:

```sh
cd services/voice
/home/delta-x/rent-rwanda/services/voice/.venv-yourtts/bin/uvicorn tts_app:app \
    --host 0.0.0.0 --port 8093
```

(and likewise `--host 0.0.0.0` for the ASR service on 8092).

Nothing breaks if they are down: the study buddy and conversation practice send
their text reply first and the audio frame separately, so a missing voice
service costs you audio, not the lesson. Cached phrases still play, because they
come from Cloudinary rather than from a live synthesis.

## Running it

```sh
cd deploy
docker compose up -d          # or: sauti up
open http://sauti.localhost
```

First boot on an empty volume needs no manual steps. The api entrypoint
(`api-entrypoint.sh`) waits for Postgres, runs `alembic upgrade head`, runs the
idempotent seed (26 lessons, 168 items, 24 can-dos, 2 voices, 3 scenarios) and
only then starts uvicorn. Both steps are safe to repeat, so this is also the
upgrade path: rebuild the image, `up -d`, and the existing volume is migrated
and re-seeded in place.

| service | image             | published                   |
|---------|-------------------|-----------------------------|
| `proxy` | `caddy:2-alpine`  | `:80` on IPv4 **and** IPv6  |
| `web`   | built here        | internal only               |
| `api`   | built here        | internal only               |
| `db`    | `postgres:16-alpine` | `127.0.0.1:55433` (debug) |

Nothing uses ports 8000 or 3000, so the host dev servers keep working
side by side. `55433` avoids `55432`, which is the e2e Postgres from
`services/api/scripts/e2e-db.sh`.

### Why the proxy is published on both IP stacks

`sauti.localhost` resolves to `::1` on this machine while plain `localhost`
resolves to `127.0.0.1`, so a v4-only bind gives a baffling "connection refused"
in the browser and a working `curl localhost`. Hence:

```yaml
ports: ["0.0.0.0:80:80", "[::]:80:80"]
```

Verify after any change:

```sh
curl -4 -s -o /dev/null -w '%{http_code}\n' http://sauti.localhost/healthz
curl -6 -s -o /dev/null -w '%{http_code}\n' http://sauti.localhost/healthz
```

WebSockets (the study buddy and conversation practice, at
`/api/v1/ws/buddy` and `/api/v1/ws/conversation/{id}`) go through the same
`/api/*` route; Caddy proxies the `Upgrade` handshake transparently.

## Configuration

Two layers, on purpose:

* **`docker-compose.yml`** holds every value that is a *deployment fact* —
  `POSTGRES_URL`, `APP_BASE_URL`, `VOICE_SERVICE_URL`, `SAUTI_FAKE_AI=0`.
* **`.env.docker`** (gitignored) holds only *secrets* — `JWT_SECRET`,
  `OPENAI_API_KEY`, the Cloudinary triple, SMTP. Copy the template and fill it
  in from the repo-root `.env`:

  ```sh
  cp deploy/.env.docker.example deploy/.env.docker
  ```

Compose `environment:` beats `env_file:`, so putting a deployment fact in
`.env.docker` would be silently ignored — keep them separate.

`NEXT_PUBLIC_API_BASE_URL` is **not** runtime config: Next inlines
`NEXT_PUBLIC_*` into the client bundle at build time. It is a build arg, fixed
at `http://sauti.localhost/api/v1` so the browser talks to the API through the
proxy, on the page's own origin. Changing it means rebuilding `web`.

## Rebuilding

```sh
cd deploy
docker compose build api          # after a change under services/api
docker compose build web          # after a change under apps/web
docker compose up -d
```

The build context is the repo root, trimmed by the root `.dockerignore`
(`node_modules` 728 MB, `.next` 659 MB, `.venv`, `services/api/var`,
`services/voice`, `.git`, `skills/`, `*.zip`). Without it the context would be
~1.5 GB; with it, ~60 MB.

## Importing your data from the cloud database

The remote Supabase database holds the learner history. The curriculum does
**not** need importing — the seed already created it locally — but it created it
with *fresh UUIDs*, so every learner row pointing at curriculum has to be
rewritten.

```sh
python3 deploy/import-from-cloud.py            # dry run, prints a summary
python3 deploy/import-from-cloud.py --apply    # write
python3 deploy/import-from-cloud.py --apply --email you@example.com   # just you
```

If the host has no psycopg: `uv run --with 'psycopg[binary]' python deploy/import-from-cloud.py`.

What it does:

* Copies `users` (**keeping their UUIDs**, so `attempts.user_id`, `srs_state`,
  `notebook_entries` … all stay valid without remapping), then `profiles`,
  `attempts`, `srs_state`, `cando_status`, `notebook_entries`,
  `placement_sessions`, `conversations`, `messages`.
* Remaps every curriculum foreign key by **natural key** — item `sentence`
  within its lesson, cando `text` within its level, course `code`, scenario
  `title`. Unmatched references are counted and the row is skipped; nothing
  crashes.
* Skips `refresh_tokens` deliberately: they are hashed credentials, and logging
  in again mints new ones.
* Re-keys `tts_cache` instead of copying it. The key is
  `sha256("<voice_id>|<sentence>")` and voice ids differ per database, so a
  verbatim copy would never be hit. Each local item is matched to its cloud twin
  and the Cloudinary URL already paid for is stored under the *local* key —
  which is what makes `audio_url` non-null on lesson items. Pass `--no-tts` to
  skip.
* Is **idempotent** (re-running inserts 0 rows) and **cannot write to the
  cloud**: the remote connection is opened read-only at session level.

Note that the cloud `users` table contains every account ever created against it,
e2e test accounts included. Use `--email` if you only want your own.

## Disk footprint

`postgres:16-alpine`, `node:22-alpine`, `python:3.12-slim` and `caddy:2-alpine`
were all already on this daemon, and the images here are built on exactly those
tags, so they cost nothing extra.

| | total | new bytes on this disk |
|---|---|---|
| `sauti-api` | 226 MB | **107 MB** (on `python:3.12-slim`, 119 MB, already present) |
| `sauti-web` | 199 MB | **36 MB** (on `node:22-alpine`, 163 MB, already present) |
| `sauti_sauti-pgdata` volume | 50 MB | 50 MB |
| **total added** | | **≈ 195 MB** |

Both images are multi-stage. The api runtime layer holds only the uv-resolved
virtualenv (`--no-dev`, so no pytest/testcontainers) plus `src/` and `alembic/`
— no uv, no compilers, no caches. The web runtime layer holds only
`.next/standalone` + `.next/static`, i.e. the traced 33 MB of node_modules
rather than the 728 MB dev tree. Neither contains torch, and neither should ever
grow one.

`/app/var` in the api container (learner audio uploads and the local WAV
fallback the Cloudinary cache writes when Cloudinary is unreachable) is a named
volume, not an image layer — runtime state stays out of the image and survives
rebuilds.
