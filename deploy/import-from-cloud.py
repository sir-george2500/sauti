#!/usr/bin/env python3
"""One-shot copy of the owner's learner data from the cloud (Supabase) database
into the local containerised Postgres.

The curriculum is NOT copied: the api entrypoint already seeds it locally, and
the seed mints fresh UUIDs. So every learner row that points at curriculum
(attempts -> items, cando_status -> cando, profiles -> courses, conversations ->
scenarios) has its foreign keys remapped by NATURAL key — item.sentence within
its lesson, cando.text within its level, course.code, scenario.title. Anything
that does not match locally is skipped and counted, never crashed on.

Users keep their original UUIDs, so every learner-to-learner foreign key
(attempts.user_id, srs_state.user_id, …) survives untouched.

Refresh tokens are deliberately not copied — they are hashed, machine-bound
credentials and logging in again mints new ones.

As a bonus the tts_cache is remapped too: for each local item we work out what
key the cloud database used for the same sentence, look up the Cloudinary URL it
already paid to synthesize, and store it under the LOCAL key. That is what makes
`audio_url` non-null on a fresh local database.

SAFETY: the remote connection is opened read-only at the session level, so a bug
here cannot write to the cloud database. Nothing is written locally without
--apply; the default is a dry run that prints exactly what would happen.

Usage (from the repo root, with the stack up):

    python3 deploy/import-from-cloud.py               # dry run
    python3 deploy/import-from-cloud.py --apply

Needs psycopg3 on the host; if it is missing, run it through the API image:

    docker compose -f deploy/docker-compose.yml run --rm --no-deps \\
        -v "$PWD/deploy:/import:ro" -v "$PWD/.env:/repo.env:ro" \\
        --entrypoint python api /import/import-from-cloud.py \\
        --remote-env /repo.env --local-url postgresql://sauti:sauti@db:5432/sauti
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - operator-facing
    sys.exit(
        "psycopg3 is required.  pip install 'psycopg[binary]'  — or run this "
        "inside the api image (see the docstring)."
    )

SCHEMA = "sauti"
DEFAULT_LOCAL_URL = "postgresql://sauti:sauti@127.0.0.1:55433/sauti"
REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# env
# --------------------------------------------------------------------------
def read_env_value(path: Path, key: str) -> str | None:
    """Minimal .env reader — we only ever want POSTGRES_URL out of it."""
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return None


# --------------------------------------------------------------------------
# key derivation (must match sauti.speech.cache.cache_key exactly)
# --------------------------------------------------------------------------
def cache_key(voice: str, text: str) -> str:
    return hashlib.sha256(f"{voice}|{text}".encode()).hexdigest()[:32]


# --------------------------------------------------------------------------
# natural-key maps
# --------------------------------------------------------------------------
class Curriculum:
    """Natural key -> id, for one database."""

    def __init__(self, conn: psycopg.Connection) -> None:
        q = lambda sql: conn.execute(sql).fetchall()  # noqa: E731

        self.course_by_code = {
            r["code"]: r["id"] for r in q(f"SELECT id, code FROM {SCHEMA}.courses")
        }
        self.code_by_course = {v: k for k, v in self.course_by_code.items()}

        levels = q(f"SELECT id, course_id, cefr FROM {SCHEMA}.levels")
        self.level_key = {
            r["id"]: (self.code_by_course.get(r["course_id"]), r["cefr"]) for r in levels
        }
        self.level_by_key = {k: i for i, k in self.level_key.items()}

        units = q(f"SELECT id, level_id, ord FROM {SCHEMA}.units")
        self.unit_key = {r["id"]: (*self.level_key.get(r["level_id"], (None, None)), r["ord"]) for r in units}

        lessons = q(f"SELECT id, unit_id, ord FROM {SCHEMA}.lessons")
        self.lesson_key = {
            r["id"]: (*self.unit_key.get(r["unit_id"], (None, None, None)), r["ord"])
            for r in lessons
        }

        items = q(f"SELECT id, lesson_id, sentence, voice_id FROM {SCHEMA}.items")
        self.item_key = {
            r["id"]: (*self.lesson_key.get(r["lesson_id"], (None, None, None, None)), r["sentence"])
            for r in items
        }
        self.item_by_key = {k: i for i, k in self.item_key.items()}
        self.item_voice = {r["id"]: r["voice_id"] for r in items}
        self.item_sentence = {r["id"]: r["sentence"] for r in items}

        cando = q(f"SELECT id, level_id, text FROM {SCHEMA}.cando")
        self.cando_key = {
            r["id"]: (*self.level_key.get(r["level_id"], (None, None)), r["text"]) for r in cando
        }
        self.cando_by_key = {k: i for i, k in self.cando_key.items()}

        scen = q(f"SELECT id, title FROM {SCHEMA}.scenarios")
        self.scenario_key = {r["id"]: r["title"] for r in scen}
        self.scenario_by_key = {r["title"]: r["id"] for r in scen}


class Remapper:
    """Remote id -> local id for each curriculum entity, by natural key."""

    def __init__(self, remote: Curriculum, local: Curriculum) -> None:
        self.remote, self.local = remote, local
        self.misses: dict[str, int] = {}

    def _map(self, kind: str, key_of, by_key, remote_id):
        if remote_id is None:
            return None
        key = key_of.get(remote_id)
        local_id = by_key.get(key) if key is not None else None
        if local_id is None:
            self.misses[kind] = self.misses.get(kind, 0) + 1
        return local_id

    def course(self, rid):
        code = self.remote.code_by_course.get(rid)
        local_id = self.local.course_by_code.get(code)
        if local_id is None:
            self.misses["course"] = self.misses.get("course", 0) + 1
        return local_id

    def item(self, rid):
        return self._map("item", self.remote.item_key, self.local.item_by_key, rid)

    def cando(self, rid):
        return self._map("cando", self.remote.cando_key, self.local.cando_by_key, rid)

    def scenario(self, rid):
        return self._map("scenario", self.remote.scenario_key, self.local.scenario_by_key, rid)


# --------------------------------------------------------------------------
# table copies
# --------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, int, int, int]] = []  # table, found, new, skipped

    def add(self, table: str, found: int, new: int, skipped: int) -> None:
        self.rows.append((table, found, new, skipped))

    def print(self, applied: bool) -> None:
        head = "inserted" if applied else "would insert"
        width = max(len(r[0]) for r in self.rows) if self.rows else 10
        print()
        print(f"{'table'.ljust(width)}  {'remote':>7}  {head:>13}  {'skipped':>7}")
        print("-" * (width + 34))
        for table, found, new, skipped in self.rows:
            print(f"{table.ljust(width)}  {found:>7}  {new:>13}  {skipped:>7}")
        totals = (sum(r[1] for r in self.rows), sum(r[2] for r in self.rows), sum(r[3] for r in self.rows))
        print("-" * (width + 34))
        print(f"{'TOTAL'.ljust(width)}  {totals[0]:>7}  {totals[1]:>13}  {totals[2]:>7}")


def existing_ids(local: psycopg.Connection, table: str) -> set:
    return {r["id"] for r in local.execute(f"SELECT id FROM {SCHEMA}.{table}").fetchall()}


def copy_table(
    *,
    remote: psycopg.Connection,
    local: psycopg.Connection,
    table: str,
    columns: list[str],
    transform,
    report: Report,
    apply: bool,
    order_by: str = "created_at",
    where: str = "",
) -> set:
    """Copy `table` remote -> local. `transform` returns a row dict or None to skip.

    Returns the set of ids that exist locally afterwards (for dependent tables).
    """
    cols = ", ".join(f'"{c}"' for c in columns)
    sql = f"SELECT {cols} FROM {SCHEMA}.{table}"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order_by}"
    rows = remote.execute(sql).fetchall()

    have = existing_ids(local, table)
    to_insert, skipped = [], 0
    for row in rows:
        out = transform(dict(row))
        if out is None:
            skipped += 1
            continue
        if out["id"] in have:
            continue
        to_insert.append(out)

    if apply and to_insert:
        placeholders = ", ".join(f"%({c})s" for c in columns)
        stmt = (
            f"INSERT INTO {SCHEMA}.{table} ({cols}) VALUES ({placeholders}) "
            "ON CONFLICT DO NOTHING"
        )
        with local.cursor() as cur:
            cur.executemany(stmt, to_insert)

    report.add(table, len(rows), len(to_insert), skipped)
    return have | {r["id"] for r in to_insert}


def copy_tts_cache(
    *,
    remote: psycopg.Connection,
    local: psycopg.Connection,
    remote_c: Curriculum,
    local_c: Curriculum,
    report: Report,
    apply: bool,
) -> None:
    """Re-key the cloud's Cloudinary URLs onto the local items.

    The cache key is sha256("<voice_id>|<sentence>") and voice ids differ between
    databases, so a verbatim copy would never be hit. Instead: for every local
    item, find the same item remotely by natural key, derive the REMOTE key, and
    store that row's URL under the LOCAL key.
    """
    remote_urls = {
        r["key"]: (r["voice"], r["url"])
        for r in remote.execute(f"SELECT key, voice, url FROM {SCHEMA}.tts_cache").fetchall()
    }
    have = {r["key"] for r in local.execute(f"SELECT key FROM {SCHEMA}.tts_cache").fetchall()}

    rows, skipped = [], 0
    for local_id, key in local_c.item_key.items():
        remote_id = remote_c.item_by_key.get(key)
        if remote_id is None:
            skipped += 1
            continue
        remote_key = cache_key(str(remote_c.item_voice.get(remote_id) or ""), key[-1])
        hit = remote_urls.get(remote_key)
        if hit is None:
            skipped += 1
            continue
        local_key = cache_key(str(local_c.item_voice.get(local_id) or ""), key[-1])
        if local_key in have:
            continue
        have.add(local_key)
        rows.append({"key": local_key, "voice": str(local_c.item_voice.get(local_id) or ""), "url": hit[1]})

    if apply and rows:
        with local.cursor() as cur:
            cur.executemany(
                f"INSERT INTO {SCHEMA}.tts_cache (id, key, voice, url, created_at, updated_at) "
                "VALUES (gen_random_uuid(), %(key)s, %(voice)s, %(url)s, now(), now()) "
                "ON CONFLICT DO NOTHING",
                rows,
            )

    report.add("tts_cache*", len(remote_urls), len(rows), skipped)


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--remote-url", default=None, help="cloud DSN (default: POSTGRES_URL from the repo .env)")
    ap.add_argument("--remote-env", default=str(REPO_ROOT / ".env"), help="file to read POSTGRES_URL from")
    ap.add_argument("--local-url", default=DEFAULT_LOCAL_URL, help=f"local DSN (default: {DEFAULT_LOCAL_URL})")
    ap.add_argument("--no-tts", action="store_true", help="skip the tts_cache re-key")
    ap.add_argument("--email", default=None, help="import only this learner (default: every user)")
    args = ap.parse_args()

    remote_url = args.remote_url or read_env_value(Path(args.remote_env), "POSTGRES_URL")
    if not remote_url:
        print(f"No remote DSN: pass --remote-url or put POSTGRES_URL in {args.remote_env}", file=sys.stderr)
        return 2

    print(f"remote : {_redact(remote_url)}  (READ ONLY)")
    print(f"local  : {_redact(args.local_url)}")
    print(f"mode   : {'APPLY — writing' if args.apply else 'dry run — nothing will be written'}")

    with psycopg.connect(remote_url, row_factory=dict_row) as remote, psycopg.connect(
        args.local_url, row_factory=dict_row
    ) as local:
        # Belt and braces: the session refuses writes even if a bug tried one.
        remote.read_only = True
        remote.execute("SET default_transaction_read_only = on")

        remote_c = Curriculum(remote)
        local_c = Curriculum(local)
        rm = Remapper(remote_c, local_c)
        report = Report()

        # 1. users — ids preserved, so every learner FK below stays valid.
        def user(r):
            return None if args.email and r["email"] != args.email else r

        user_ids = copy_table(
            remote=remote, local=local, table="users",
            columns=["id", "email", "password_hash", "email_verified_at", "created_at", "updated_at"],
            transform=user, report=report, apply=args.apply,
        )
        keep = lambda r: r["user_id"] in user_ids  # noqa: E731

        def profile(r):
            if not keep(r):
                return None
            r["course_id"] = rm.course(r["course_id"])
            return None if r["course_id"] is None else r

        copy_table(
            remote=remote, local=local, table="profiles",
            columns=["id", "user_id", "course_id", "pace_hours_week", "placed_level",
                     "gamification", "daily_goal_minutes", "created_at", "updated_at"],
            transform=profile, report=report, apply=args.apply,
        )

        def attempt(r):
            if not keep(r):
                return None
            r["item_id"] = rm.item(r["item_id"])
            # psycopg3 does not adapt a bare dict to jsonb; PronReport must be wrapped.
            r["pron"] = Jsonb(r["pron"]) if r["pron"] is not None else None
            return None if r["item_id"] is None else r

        attempt_ids = copy_table(
            remote=remote, local=local, table="attempts",
            columns=["id", "user_id", "item_id", "mode", "score", "audio_ref", "pron", "ts",
                     "created_at", "updated_at"],
            transform=attempt, report=report, apply=args.apply, order_by="ts",
        )

        def srs(r):
            if not keep(r):
                return None
            r["item_id"] = rm.item(r["item_id"])
            return None if r["item_id"] is None else r

        copy_table(
            remote=remote, local=local, table="srs_state",
            columns=["id", "user_id", "item_id", "due_at", "reps", "stability", "difficulty",
                     "last_reviewed_at", "created_at", "updated_at"],
            transform=srs, report=report, apply=args.apply, order_by="due_at",
        )

        def cando_status(r):
            if not keep(r):
                return None
            r["cando_id"] = rm.cando(r["cando_id"])
            if r["cando_id"] is None:
                return None
            # The proving attempt may itself have been skipped; the link is nullable.
            if r["confirmed_via_attempt"] not in attempt_ids:
                r["confirmed_via_attempt"] = None
            return r

        copy_table(
            remote=remote, local=local, table="cando_status",
            columns=["id", "user_id", "cando_id", "status", "confirmed_via_attempt",
                     "created_at", "updated_at"],
            transform=cando_status, report=report, apply=args.apply,
        )

        def notebook(r):
            if not keep(r):
                return None
            # Soft link: text/gloss are snapshots, so an unmatched item just
            # loses its play button rather than the whole entry.
            r["item_id"] = rm.item(r["item_id"]) if r["item_id"] else None
            return r

        copy_table(
            remote=remote, local=local, table="notebook_entries",
            columns=["id", "user_id", "item_id", "text", "gloss", "note", "created_at", "updated_at"],
            transform=notebook, report=report, apply=args.apply,
        )

        def placement(r):
            if not keep(r):
                return None
            served = [rm.item(i) for i in (r["served"] or [])]
            r["served"] = [i for i in served if i is not None]
            return r

        copy_table(
            remote=remote, local=local, table="placement_sessions",
            columns=["id", "user_id", "theta", "served", "n_correct", "result",
                     "created_at", "updated_at"],
            transform=placement, report=report, apply=args.apply,
        )

        def conversation(r):
            if not keep(r):
                return None
            r["scenario_id"] = rm.scenario(r["scenario_id"])
            return None if r["scenario_id"] is None else r

        conv_ids = copy_table(
            remote=remote, local=local, table="conversations",
            columns=["id", "user_id", "scenario_id", "goals_met", "started_at",
                     "created_at", "updated_at"],
            transform=conversation, report=report, apply=args.apply, order_by="started_at",
        )

        def message(r):
            if r["conversation_id"] not in conv_ids:
                return None
            r["coach"] = Jsonb(r["coach"]) if r["coach"] is not None else None
            return r

        copy_table(
            remote=remote, local=local, table="messages",
            columns=["id", "conversation_id", "role", "text", "gloss", "coach", "audio_ref",
                     "created_at", "updated_at"],
            transform=message, report=report, apply=args.apply,
        )

        if not args.no_tts:
            copy_tts_cache(
                remote=remote, local=local, remote_c=remote_c, local_c=local_c,
                report=report, apply=args.apply,
            )

        if args.apply:
            local.commit()
        remote.rollback()  # read-only anyway; leave no open transaction behind

        report.print(args.apply)
        if rm.misses:
            print("\nunmatched curriculum references (rows skipped, not fatal):")
            for kind, n in sorted(rm.misses.items()):
                print(f"  {kind}: {n}")
        print(
            "\n* tts_cache is re-keyed onto local item/voice ids so cached Cloudinary "
            "audio keeps working; it is not a verbatim copy."
        )
        if not args.apply:
            print("\nDry run. Re-run with --apply to write.")
    return 0


def _redact(dsn: str) -> str:
    """host/db only — never print credentials."""
    try:
        from urllib.parse import urlsplit

        u = urlsplit(dsn)
        return f"{u.scheme}://{u.hostname}:{u.port or 5432}{u.path}"
    except Exception:  # noqa: BLE001
        return "<dsn>"


if __name__ == "__main__":
    raise SystemExit(main())
