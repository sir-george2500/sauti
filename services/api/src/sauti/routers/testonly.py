"""Test-only endpoints — mounted ONLY when SAUTI_FAKE_AI=1 (see create_app).

The e2e suite can't read a real inbox, so when the app runs with the
capturing ConsoleMailer this exposes the most recent captured mail (the
verify / reset link is extracted from its text). Never mounted in a real
deployment: create_app skips the router unless settings.sauti_fake_ai is
set, and the handler double-checks the mailer type besides.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from sauti.errors import ApiError
from sauti.services.mail import ConsoleMailer

router = APIRouter(prefix="/__test__", tags=["test-only"], include_in_schema=False)


@router.get("/last-mail")
async def last_mail(request: Request, to: str | None = None) -> dict:
    mailer = request.app.state.mailer
    if not isinstance(mailer, ConsoleMailer):  # belt and braces — see module doc
        raise ApiError(404, "NOT_FOUND", "Not found")
    mail = mailer.last_for(to) if to else (mailer.sent[-1] if mailer.sent else None)
    if mail is None:
        raise ApiError(404, "NO_MAIL", "No captured mail yet")
    return {"to": mail.to, "subject": mail.subject, "text": mail.text, "html": mail.html}
