"""Auth integration: register/login/refresh rotation + reuse detection/logout,
rate limiting — against real Postgres with real migrations."""
from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from sauti.config import Settings
from sauti.main import create_app
from tests.conftest import TEST_JWT_SECRET, register_and_login

REGISTER = {
    "email": "ange@example.com",
    "password": "umutekano-2026",
    "course_code": "KIN",
    "pace_hours_week": 5,
}


class TestRegister:
    async def test_register_creates_user_and_profile(self, client):
        r = await client.post("/api/v1/auth/register", json=REGISTER)
        assert r.status_code == 201
        assert r.json()["user"]["email"] == "ange@example.com"

        auth = await register_and_login(client, email="two@example.com")
        r = await client.get("/api/v1/me", headers=auth["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["email"] == "two@example.com"
        assert body["profile"]["course_code"] == "KIN"
        assert body["profile"]["pace_hours_week"] == 5
        assert body["profile"]["placed_level"] is None

    async def test_duplicate_email_409(self, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        r = await client.post("/api/v1/auth/register", json=REGISTER)
        assert r.status_code == 409
        assert r.json()["code"] == "EMAIL_TAKEN"

    async def test_common_password_rejected(self, client):
        r = await client.post(
            "/api/v1/auth/register", json={**REGISTER, "password": "password123"}
        )
        assert r.status_code == 422
        assert r.json()["code"] == "WEAK_PASSWORD"

    async def test_unknown_course_rejected(self, client):
        r = await client.post(
            "/api/v1/auth/register", json={**REGISTER, "course_code": "ENG"}
        )
        assert r.status_code == 422


class TestLogin:
    async def test_generic_error_for_unknown_email_and_wrong_password(self, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        wrong_pw = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": "not-the-password"},
        )
        no_user = await client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "whatever-123"},
        )
        assert wrong_pw.status_code == no_user.status_code == 401
        # Identical bodies: no email-existence oracle.
        assert wrong_pw.json() == no_user.json()

    async def test_login_sets_scoped_refresh_cookie(self, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": REGISTER["password"]},
        )
        assert r.status_code == 200
        assert r.json()["access_token"]
        set_cookie = r.headers["set-cookie"]
        assert "sauti_refresh=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/api/v1/auth" in set_cookie
        assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()


class TestRefreshRotation:
    async def _login_cookie(self, client) -> str:
        await client.post("/api/v1/auth/register", json=REGISTER)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": REGISTER["password"]},
        )
        client.cookies.clear()
        return r.cookies["sauti_refresh"]

    async def test_refresh_rotates_token(self, client):
        cookie_a = await self._login_cookie(client)
        r = await client.post("/api/v1/auth/refresh", cookies={"sauti_refresh": cookie_a})
        assert r.status_code == 200
        assert r.json()["access_token"]
        cookie_b = r.cookies["sauti_refresh"]
        assert cookie_b and cookie_b != cookie_a

    async def test_reuse_detection_revokes_whole_family(self, client):
        cookie_a = await self._login_cookie(client)
        r = await client.post("/api/v1/auth/refresh", cookies={"sauti_refresh": cookie_a})
        cookie_b = r.cookies["sauti_refresh"]
        client.cookies.clear()

        # Replay the rotated-away token: 401 …
        r = await client.post("/api/v1/auth/refresh", cookies={"sauti_refresh": cookie_a})
        assert r.status_code == 401
        client.cookies.clear()
        # … and the WHOLE family is dead — the still-fresh cookie B fails too
        # (the revocation was committed before the 401 above).
        r = await client.post("/api/v1/auth/refresh", cookies={"sauti_refresh": cookie_b})
        assert r.status_code == 401

    async def test_refresh_without_cookie_401(self, client):
        r = await client.post("/api/v1/auth/refresh")
        assert r.status_code == 401

    async def test_garbage_cookie_401(self, client):
        r = await client.post(
            "/api/v1/auth/refresh", cookies={"sauti_refresh": "not-a-real-token"}
        )
        assert r.status_code == 401


class TestLogout:
    async def test_logout_revokes_family_and_is_idempotent(self, client):
        await client.post("/api/v1/auth/register", json=REGISTER)
        r = await client.post(
            "/api/v1/auth/login",
            json={"email": REGISTER["email"], "password": REGISTER["password"]},
        )
        cookie = r.cookies["sauti_refresh"]
        client.cookies.clear()

        r = await client.post("/api/v1/auth/logout", cookies={"sauti_refresh": cookie})
        assert r.status_code == 204
        client.cookies.clear()
        r = await client.post("/api/v1/auth/refresh", cookies={"sauti_refresh": cookie})
        assert r.status_code == 401
        client.cookies.clear()
        # Idempotent: logging out again (even with a dead cookie) succeeds.
        r = await client.post("/api/v1/auth/logout", cookies={"sauti_refresh": cookie})
        assert r.status_code == 204


class TestProtectedRoutes:
    async def test_no_token_401(self, client):
        for path in ("/api/v1/me", "/api/v1/session/today", "/api/v1/progress"):
            r = await client.get(path)
            assert r.status_code == 401, path

    async def test_tampered_token_401(self, client):
        auth = await register_and_login(client)
        bad = auth["access_token"][:-4] + "AAAA"
        r = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {bad}"})
        assert r.status_code == 401


class TestRateLimit:
    async def test_auth_surface_returns_429_after_cap(self, pg_url, clean_db, tmp_path):
        settings = Settings(
            postgres_url=pg_url,
            jwt_secret=TEST_JWT_SECRET,
            sauti_fake_ai=True,
            db_null_pool=True,
            rate_limit_auth_max=3,
            audio_dir=str(tmp_path / "a"),
            tts_dir=str(tmp_path / "t"),
        )
        app = create_app(settings)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            statuses = []
            for _ in range(4):
                r = await client.post(
                    "/api/v1/auth/login",
                    json={"email": "x@example.com", "password": "irrelevant-1"},
                )
                statuses.append(r.status_code)
            assert statuses[:3] == [401, 401, 401]
            assert statuses[3] == 429
            assert r.json()["code"] == "RATE_LIMITED"
        await app.state.engine.dispose()
