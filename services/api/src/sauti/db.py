from __future__ import annotations

import ssl
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import DateTime, MetaData, text
from sqlalchemy.pool import NullPool
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sauti.config import Settings

SCHEMA = "sauti"

metadata = MetaData(schema=SCHEMA)


class Base(DeclarativeBase):
    metadata = metadata
    type_annotation_map = {datetime: DateTime(timezone=True)}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampedBase(Base):
    """Every entity: id UUID pk, created_at, updated_at."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


def build_engine(settings: Settings) -> AsyncEngine:
    connect_args: dict = {
        # Supabase pooler (pgbouncer, transaction mode) breaks asyncpg's
        # prepared-statement cache — disable it and randomise statement names.
        "statement_cache_size": 0,
        # SQLAlchemy's asyncpg dialect keeps its OWN prepared-statement LRU
        # (default 100) on top of asyncpg's: it re-executes named statements
        # prepared in earlier transactions, which the transaction-mode pooler
        # may route to a different server connection →
        # InvalidSQLStatementNameError ("prepared statement ... does not
        # exist") under load. Disable that cache too.
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__sauti_{uuid.uuid4().hex}__",
    }
    if settings.ssl_required:
        # sslmode=require semantics: encrypt, but don't verify the chain
        # (Supabase's pooler presents a self-signed chain).
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx
    if settings.db_null_pool:
        return create_async_engine(
            settings.async_dsn, connect_args=connect_args, poolclass=NullPool
        )
    return create_async_engine(
        settings.async_dsn,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    maker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with maker() as session:
        yield session


async def ping(engine: AsyncEngine) -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
