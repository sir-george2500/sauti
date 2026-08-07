"""Email verification + password reset — full flows against real Postgres.

The app fixture runs with SAUTI_FAKE_AI=1, so app.state.mailer is the
capturing ConsoleMailer: tests read the emailed link straight out of it.
"""
from __future__ import annotations

import re
from datetime import timedelta, timezone
from datetime import datetime as dt

from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from sauti.config import Settings
from sauti.main import create_app
from sauti.models import EmailVerificationToken, PasswordResetToken
from tests.conftest import TEST_JWT_SECRET, register_and_login

REGISTER = {
    "email": "ange@example.com",
    "password": "umutekano-2026",
    "course_code": "KIN",
    "pace_hours_week": 5,
}

TOKEN_RE = re.compile(r"token=([A-Za-z0-9_-]+)")


def _last_mail(app, to: str):
    return app.state.mailer.last_for(to)


def _token_from(mail) -> str:
    m = TOKEN_RE.search(mail.text)
    assert m, f"no token link in mail: {mail.text!r}"
    return m.group(1)


async def _expire_all(app, model) -> None:
    async with app.state.sessionmaker() as db:
        await db.execute(
            update(model).values(expires_at=dt.now(timezone.utc) - timedelta(minutes=1))
        )
        await db.commit()


class TestEmailVerification:
    async def test_register_sends_mail_and_verify_flips_me(self, app, client):
        auth = await register_and_login(client)

        r = await client.get("/api/v1/me", headers=auth["headers"])
        assert r.json()["email_verified"] is False

        mail = _last_mail(app, REGISTER["email"])
        assert mail is not None and "Verify" in mail.subject
        assert "/verify-email?token=" in mail.text
        token = _token_from(mail)

        r = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 200, r.text

        r = await client.get("/api/v1/me", headers=auth["headers"])
        assert r.json()["email_verified"] is True

    async def test_verify_token_is_single_use(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        token = _token_from(_last_mail(app, REGISTER["email"]))

        assert (await client.post("/api/v1/auth/verify-email", json={"token": token})).status_code == 200
        r = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 410
        assert r.json()["code"] == "TOKEN_USED"

    async def test_expired_verify_token_rejected(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        token = _token_from(_last_mail(app, REGISTER["email"]))
        await _expire_all(app, EmailVerificationToken)

        r = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert r.status_code == 410
        assert r.json()["code"] == "TOKEN_EXPIRED"

    async def test_unknown_verify_token_400(self, client):
        r = await client.post("/api/v1/auth/verify-email", json={"token": "A" * 43})
        assert r.status_code == 400
        assert r.json()["code"] == "INVALID_TOKEN"

    async def test_resend_mints_new_link_and_noops_once_verified(self, app, client):
        auth = await register_and_login(client)
        first = _token_from(_last_mail(app, REGISTER["email"]))

        r = await client.post("/api/v1/auth/resend-verification", headers=auth["headers"])
        assert r.status_code == 200
        second = _token_from(_last_mail(app, REGISTER["email"]))
        assert second != first

        assert (await client.post("/api/v1/auth/verify-email", json={"token": second})).status_code == 200

        sent_before = len(app.state.mailer.sent)
        r = await client.post("/api/v1/auth/resend-verification", headers=auth["headers"])
        # Already verified: same generic 200, but no new mail.
        assert r.status_code == 200
        assert len(app.state.mailer.sent) == sent_before

    async def test_resend_requires_auth(self, client):
        r = await client.post("/api/v1/auth/resend-verification")
        assert r.status_code == 401


class TestPasswordReset:
    NEW_PASSWORD = "gitondo-akabando-77"

    async def test_full_reset_flow(self, app, client):
        await register_and_login(client)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": REGISTER["password"]},
        )
        old_cookie = r.cookies["sauti_refresh"]
        client.cookies.clear()

        r = await client.post(
            "/api/v1/auth/forgot-password", json={"email": REGISTER["email"]}
        )
        assert r.status_code == 200

        mail = _last_mail(app, REGISTER["email"])
        assert "Reset" in mail.subject and "/reset-password?token=" in mail.text
        token = _token_from(mail)

        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": self.NEW_PASSWORD},
        )
        assert r.status_code == 200, r.text

        # Old password is dead …
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": REGISTER["password"]},
        )
        assert r.status_code == 401
        # … the new one works …
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": self.NEW_PASSWORD},
        )
        assert r.status_code == 200
        client.cookies.clear()
        # … and the pre-reset refresh cookie was revoked (every device out).
        r = await client.post(
            "/api/v1/auth/refresh", cookies={"sauti_refresh": old_cookie}
        )
        assert r.status_code == 401

    async def test_reset_token_is_single_use(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        await client.post("/api/v1/auth/forgot-password", json={"email": REGISTER["email"]})
        token = _token_from(_last_mail(app, REGISTER["email"]))

        body = {"token": token, "new_password": self.NEW_PASSWORD}
        assert (await client.post("/api/v1/auth/reset-password", json=body)).status_code == 200
        r = await client.post("/api/v1/auth/reset-password", json=body)
        assert r.status_code == 410
        assert r.json()["code"] == "TOKEN_USED"

    async def test_expired_reset_token_rejected(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        await client.post("/api/v1/auth/forgot-password", json={"email": REGISTER["email"]})
        token = _token_from(_last_mail(app, REGISTER["email"]))
        await _expire_all(app, PasswordResetToken)

        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": self.NEW_PASSWORD},
        )
        assert r.status_code == 410
        assert r.json()["code"] == "TOKEN_EXPIRED"

    async def test_reset_rejects_weak_password(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        await client.post("/api/v1/auth/forgot-password", json={"email": REGISTER["email"]})
        token = _token_from(_last_mail(app, REGISTER["email"]))

        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "password123"},
        )
        assert r.status_code == 422
        assert r.json()["code"] == "WEAK_PASSWORD"
        # Token survives the rejected attempt.
        r = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": self.NEW_PASSWORD},
        )
        assert r.status_code == 200

    async def test_forgot_password_never_enumerates(self, app, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        sent_before = len(app.state.mailer.sent)

        known = await client.post(
            "/api/v1/auth/forgot-password", json={"email": REGISTER["email"]}
        )
        unknown = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}
        )
        # Identical 200s — no existence oracle in status or body …
        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        # … and only the real account got mail.
        assert len(app.state.mailer.sent) == sent_before + 1
        assert _last_mail(app, "ghost@example.com") is None


class TestEmailRateLimits:
    async def test_forgot_password_is_ip_capped(self, pg_url, clean_db, tmp_path):
        settings = Settings(
            postgres_url=pg_url,
            jwt_secret=TEST_JWT_SECRET,
            sauti_fake_ai=True,
            db_null_pool=True,
            rate_limit_auth_max=1000,
            rate_limit_email_max=2,
            audio_dir=str(tmp_path / "a"),
            tts_dir=str(tmp_path / "t"),
        )
        app = create_app(settings)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            statuses = [
                (
                    await client.post(
                        "/api/v1/auth/forgot-password", json={"email": "x@example.com"}
                    )
                ).status_code
                for _ in range(3)
            ]
            assert statuses == [200, 200, 429]
        await app.state.engine.dispose()

    async def test_resend_verification_is_user_capped(self, pg_url, clean_db, tmp_path):
        settings = Settings(
            postgres_url=pg_url,
            jwt_secret=TEST_JWT_SECRET,
            sauti_fake_ai=True,
            db_null_pool=True,
            rate_limit_auth_max=1000,
            rate_limit_email_max=2,
            audio_dir=str(tmp_path / "a"),
            tts_dir=str(tmp_path / "t"),
        )
        app = create_app(settings)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            auth = await register_and_login(client)
            statuses = [
                (
                    await client.post(
                        "/api/v1/auth/resend-verification", headers=auth["headers"]
                    )
                ).status_code
                for _ in range(3)
            ]
            assert statuses == [200, 200, 429]
        await app.state.engine.dispose()
