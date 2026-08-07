"""feature tables — LLM usage metering + reply cache, email verification, password reset

One migration for the whole feature round so parallel workstreams share a
single linear revision history:
- llm_usage: per-call token accounting (the OpenAI usage payload, persisted)
- llm_reply_cache: synthesize-once for conversation replies — early-turn
  learner utterances repeat constantly; cache key is
  sha256(scenario|turn|normalized user text)
- email_verification_tokens / password_reset_tokens: single-use, hashed at
  rest, same discipline as refresh_tokens

Revision ID: f4a1c9d27e01
Revises: 9c41f2ab7d10
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f4a1c9d27e01"
down_revision = "9c41f2ab7d10"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "llm_usage",
        *_timestamps(),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("surface", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cached_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["sauti.users.id"], ondelete="SET NULL"),
        schema="sauti",
    )
    op.create_index(
        "ix_llm_usage_user_created", "llm_usage", ["user_id", "created_at"], schema="sauti"
    )

    op.create_table(
        "llm_reply_cache",
        *_timestamps(),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("reply", postgresql.JSONB(), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        sa.ForeignKeyConstraint(["scenario_id"], ["sauti.scenarios.id"], ondelete="CASCADE"),
        schema="sauti",
    )

    for table in ("email_verification_tokens", "password_reset_tokens"):
        op.create_table(
            table,
            *_timestamps(),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("token_hash", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
            sa.ForeignKeyConstraint(["user_id"], ["sauti.users.id"], ondelete="CASCADE"),
            schema="sauti",
        )
        op.create_index(f"ix_{table}_user", table, ["user_id"], schema="sauti")

    # Email-verification state on the user row itself.
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="sauti",
    )


def downgrade() -> None:
    op.drop_column("users", "email_verified_at", schema="sauti")
    for table in ("password_reset_tokens", "email_verification_tokens"):
        op.drop_index(f"ix_{table}_user", table_name=table, schema="sauti")
        op.drop_table(table, schema="sauti")
    op.drop_table("llm_reply_cache", schema="sauti")
    op.drop_index("ix_llm_usage_user_created", table_name="llm_usage", schema="sauti")
    op.drop_table("llm_usage", schema="sauti")
