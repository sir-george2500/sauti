"""E2e fixture: set a user's placed CEFR level directly in the DB.

GET /scenarios filters by the user's level, and reaching A2 through the real
adaptive placement flow is its own journey (placement.spec.ts). Specs that
just need an A2 user (e.g. to see A2 conversation scenarios) place the user
directly, the same time-machine style as rewind_srs_due.py.

Run from services/api (the e2e suite does this via `uv run`):
    uv run python <this file> <email> <cefr>

Prints the number of updated rows.
"""
from __future__ import annotations

import sys

from sqlalchemy import create_engine, text

from sauti.config import get_settings


def main() -> None:
    email, cefr = sys.argv[1], sys.argv[2]
    assert cefr in {"A1", "A2", "B1", "B2", "C1", "C2"}, cefr
    settings = get_settings()
    engine = create_engine(settings.sync_dsn)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE sauti.profiles
                   SET placed_level = :cefr
                 WHERE user_id = (SELECT id FROM sauti.users WHERE email = :email)
                """
            ),
            {"email": email, "cefr": cefr},
        )
        print(result.rowcount)
    engine.dispose()


if __name__ == "__main__":
    main()
