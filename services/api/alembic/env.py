from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from sauti.config import Settings
from sauti.db import SCHEMA, metadata
import sauti.models  # noqa: F401  — register all tables on the metadata

config = context.config

# DSN: explicit env override (tests) else repo .env via Settings.
dsn = os.environ.get("SAUTI_ALEMBIC_DSN") or Settings().sync_dsn
config.set_main_option("sqlalchemy.url", dsn)

target_metadata = metadata


def include_name(name, type_, parent_names):
    """Never look at (or touch) anything outside the sauti schema.

    The Supabase database also hosts another project's tables in `public`.
    """
    if type_ == "schema":
        return name == SCHEMA
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Alembic creates its version table before any migration runs,
        # so the schema must exist first.
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
