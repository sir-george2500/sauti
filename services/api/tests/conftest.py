"""Test fixtures: real Postgres via testcontainers (postgres:16-alpine), real
Alembic migrations, seeded curriculum, FakeLlmClient — never a paid API.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

from sauti.config import Settings
from sauti.main import create_app

API_DIR = Path(__file__).resolve().parents[1]

TEST_JWT_SECRET = "test-secret-0123456789abcdef0123456789abcdef"

DYNAMIC_TABLES = [
    "tts_cache",
    "llm_usage",
    "llm_reply_cache",
    "cando_status",
    "messages",
    "conversations",
    "placement_sessions",
    "srs_state",
    "attempts",
    "notebook_entries",
    "refresh_tokens",
    "email_verification_tokens",
    "password_reset_tokens",
    "profiles",
    "users",
]


@pytest.fixture(scope="session")
def pg_url() -> str:
    """One shared container per session; migrations + seed run once."""
    with PostgresContainer("postgres:16-alpine", driver=None) as pg:
        url = pg.get_connection_url()  # postgresql://user:pass@host:port/db

        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        os.environ["SAUTI_ALEMBIC_DSN"] = url.replace("postgresql://", "postgresql+psycopg://")
        command.upgrade(cfg, "head")

        from sauti.db import build_engine, build_sessionmaker
        from sauti.seed.runner import seed

        async def _seed() -> None:
            settings = Settings(
                postgres_url=url, jwt_secret=TEST_JWT_SECRET, db_null_pool=True
            )
            engine = build_engine(settings)
            maker = build_sessionmaker(engine)
            async with maker() as db:
                await seed(db)
            await engine.dispose()

        asyncio.run(_seed())
        yield url


@pytest.fixture()
def clean_db(pg_url: str) -> None:
    """Truncate learner-side tables before each test; curriculum stays seeded."""
    dsn = pg_url.replace("postgresql://", "postgresql://")
    with psycopg.connect(dsn) as conn:
        tables = ", ".join(f"sauti.{t}" for t in DYNAMIC_TABLES)
        conn.execute(f"TRUNCATE {tables} CASCADE")
        conn.commit()


@pytest.fixture()
def test_settings(pg_url: str, clean_db: None, tmp_path: Path) -> Settings:
    return Settings(
        postgres_url=pg_url,
        jwt_secret=TEST_JWT_SECRET,
        sauti_fake_ai=True,
        cookie_secure=False,
        db_null_pool=True,
        app_base_url="http://testserver",
        # High caps by default; the rate-limit test builds its own app.
        rate_limit_auth_max=1000,
        rate_limit_conversation_max=1000,
        rate_limit_buddy_max=1000,
        audio_dir=str(tmp_path / "audio"),
        tts_dir=str(tmp_path / "tts"),
    )


@pytest.fixture()
def app(test_settings: Settings):
    return create_app(test_settings)


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    await app.state.engine.dispose()


async def register_and_login(
    client: AsyncClient,
    email: str = "ange@example.com",
    password: str = "umutekano-2026",
    course_code: str = "KIN",
) -> dict:
    """Returns {'headers': ..., 'user': ..., 'access_token': ...}."""
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "course_code": course_code,
            "pace_hours_week": 5,
        },
    )
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user": data["user"],
        "access_token": data["access_token"],
    }
