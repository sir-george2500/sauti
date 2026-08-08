# Running Sauti

Two commands. That is the whole thing.

```sh
sauti up      # sit down to study
sauti down    # done for the day
```

`sauti up` prints a URL when everything is actually answering. Open it and
start.

```
http://sauti.localhost
```

Everything else in this file is for the day something goes wrong.

---

## What `sauti` actually starts

Sauti is two halves that the CLI drives as one thing.

**Containers** — `deploy/docker-compose.yml`, compose project `sauti`:

| service | what it is | reachable at |
| --- | --- | --- |
| `db` | Postgres 16. **Your study data lives here.** | `127.0.0.1:55433` (debugging only) |
| `api` | the FastAPI backend | through the proxy, `/api/v1` |
| `web` | the Next.js app | through the proxy, `/` |
| `proxy` | Caddy, the one front door | `http://sauti.localhost` |

**Host ML voice services** — started by `sauti`, not by Docker:

| service | what it is | port |
| --- | --- | --- |
| `tts` | Kinyarwanda (YourTTS) + English (Kokoro) speech synthesis | `127.0.0.1:8093` |
| `asr` | Kinyarwanda speech recognition — scores your pronunciation | `127.0.0.1:8092` |

> **Why the voice services are not in Docker:** their virtualenvs and Hugging
> Face checkpoints come to roughly 8 GB, and this machine's disk is ~95% full.
> Containerising them would copy those 8 GB into an image for no benefit on a
> single-user laptop. They run on the host, bound to `127.0.0.1` only, and the
> `api` container reaches them via `host.docker.internal`.

---

## The commands

```
sauti up [--no-voice]   start everything and wait until it genuinely answers
sauti down              stop everything (your study data is kept)
sauti status            one screen: containers, voice services, URL, data volume
sauti logs [svc] [-f]   svc = api | web | db | proxy | tts | asr
sauti restart [svc]     restart everything, or one service
sauti rebuild [svc]     rebuild images after a code change, then bring it up
sauti open              open the app in your browser
sauti reset --yes-really   DESTROYS the database and everything you have learned
sauti help
```

`sauti up` is idempotent. If everything is already healthy it says so and exits
in about a second — no harm in running it twice.

`--no-voice` skips the ML services. Use it when you only want lessons and
reviews and do not care about speaking or listening: it boots in seconds
instead of waiting a minute or two for the models to warm up.

### Cold start is slow, and that is normal

The first `sauti up` after a reboot loads two neural models into memory:

- **TTS**: about 1–2 minutes
- **ASR**: about 1 minute

`sauti up` waits for both and prints dots while it does. It is not stuck. A
second `sauti up` later the same day is nearly instant, because the models are
already loaded and `up` just confirms they are healthy.

There is a second, subtler wait. The TTS server starts answering as soon as
uvicorn is serving, but its three voices (Kinyarwanda female, Kinyarwanda male,
English) load in a background thread and can take several more minutes. So
`sauti up` can honestly say "healthy" while speech is not yet ready.
`sauti status` shows the difference:

```
tts  ✓  healthy on :8093 (pid 12345) voices 3/3        <- speech works
tts  ✓  healthy on :8093 (pid 12345) voices 0/3 — still loading, speech not ready
```

If the first phrase you play is slow or silent, check that line and wait.

### What "normal" looks like

Measured on this machine, with the images already built:

| | |
| --- | --- |
| `sauti up` — everything already healthy | ~20 ms |
| `sauti up` — containers only (`--no-voice`, from stopped) | ~14 s |
| `sauti up` — full cold boot, containers + both voice models | ~25–32 s |
| `sauti up` — TTS voices fully loaded after that | a further 1–3 min, in the background |
| `sauti status` | ~0.2 s |
| `sauti down` | ~3–6 s |

The first `sauti up` after a `sauti rebuild` is much slower, because it builds
the `api` and `web` images before any of this.

### Where things live

| | |
| --- | --- |
| Voice service logs | `~/.local/state/sauti/logs/{tts,asr}.log` |
| Voice service pidfiles | `~/.local/state/sauti/run/{tts,asr}.pid` |
| Lockfile | `~/.local/state/sauti/run/sauti.lock` |
| Container logs | `sauti logs api` (they live in Docker) |
| The CLI itself | `scripts/sauti`, symlinked to `~/.local/bin/sauti` |

---

## Your data

`sauti down` stops containers but **never** removes the Postgres volume. Your
lessons, reviews, streaks and recordings survive reboots, rebuilds and
`sauti down`.

Exactly one command deletes them:

```sh
sauti reset --yes-really
```

Without the flag it prompts and makes you type `DELETE`. Without a terminal it
refuses outright. `sauti status` shows the volume under **data** so you can
confirm at a glance that it is still there.

---

## When something goes wrong

Start with `sauti status`. It tells you which of the six pieces is unhappy.

### "cannot talk to the Docker daemon"

```sh
sudo systemctl start docker
sauti up
```

### "port 80 is already in use"

Something else owns the web port, so the proxy cannot bind it. Find it:

```sh
sudo ss -ltnp '( sport = :80 )'
```

Usually another local web server. Stop it, then `sauti up` again. If you would
rather leave it alone, move Sauti:

```sh
SAUTI_URL=http://sauti.localhost:8080 sauti up
```

(The compose file publishes port 80, so this also needs the proxy's published
port changed in `deploy/docker-compose.yml`.)

### "port 8093 is in use by something that is not a Sauti voice service"

An old voice server from a previous session, probably one started by hand:

```sh
ss -ltnp '( sport = :8093 )'   # find the pid
kill <pid>
sauti up
```

`sauti` only ever adopts or kills a process whose command line is actually
running our app module, so it will never take down something unrelated of
yours.

### "the app did not become healthy in time"

The containers came up but nothing answers `/healthz`. Almost always the API:

```sh
sauti logs api -f
```

Common cause: `api` cannot reach `db`. Check `db` is `running` in
`sauti status`, then `sauti restart api`.

### The voice model is still warming up

If `sauti status` shows `running but not answering yet — still warming up`,
that is exactly what it says: uvicorn is alive but the model is still loading.
Give it another minute. To watch it happen:

```sh
sauti logs tts -f
```

If it never becomes healthy, the log will normally show a missing checkpoint or
an out-of-memory kill. The venvs it needs are:

```
/home/delta-x/rent-rwanda/services/voice/.venv-yourtts   (TTS)
/home/delta-x/rent-rwanda/services/voice/.venv-asr       (ASR)
```

### "env file not found: deploy/.env.docker"

```sh
cp deploy/.env.docker.example deploy/.env.docker
```

Then fill in the secrets it asks for. This file is never committed.

### "another sauti command is already running"

Two `sauti up`s cannot run at once — a lockfile prevents it. Wait for the first
to finish. If one was killed mid-flight and the lock is genuinely stale, no
cleanup is needed: the lock is held by the process, not the file, so it is
released the moment that process is gone.

### After changing application code

```sh
sauti rebuild        # everything
sauti rebuild api    # or just the one that changed
```

`sauti restart` alone will not pick up code changes — the images have to be
rebuilt.

### `http://sauti.localhost` will not load in the browser

`sauti.localhost` resolves to `::1` on this machine, so the proxy has to be
listening on IPv6 loopback too — the compose file publishes on both. If the
browser fails but `sauti status` says the app is healthy (it probes IPv4
directly), check that the `[::]:80` publish is still in
`deploy/docker-compose.yml`. As a fallback, `http://localhost` works too.

---

## Checking the CLI itself

```sh
./scripts/sauti-selftest.sh
```

Covers argument parsing, exit codes, every preflight message, lockfile and
pidfile handling, and the process-matching rules — without booting the stack.
Run it after editing `scripts/sauti`.
