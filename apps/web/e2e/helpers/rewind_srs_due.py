"""E2e fixture: rewind a user's SRS due dates so items are due *now*.

FSRS (correctly) never schedules a review in the past, so a freshly created
e2e user can't have due items without waiting ~10 minutes. This helper stands
in for a time machine: it shifts the user's srs_state.due_at back by one hour.

Run from services/api (the e2e suite does this via `uv run`):
    uv run python <this file> <email>

Prints the number of rewound rows.
"""
from __future__ import annotations

import sys

from sqlalchemy import create_engine, text

from sauti.config import get_settings


def main() -> None:
    email = sys.argv[1]
    settings = get_settings()
    engine = create_engine(settings.sync_dsn)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE sauti.srs_state
                   SET due_at = now() - interval '1 hour'
                 WHERE user_id = (SELECT id FROM sauti.users WHERE email = :email)
                """
            ),
            {"email": email},
        )
        print(result.rowcount)
    engine.dispose()


if __name__ == "__main__":
    main()
