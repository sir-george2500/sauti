"""tts_cache — synthesized-audio cache index (Cloudinary URL per (voice, text) key)

Revision ID: 9c41f2ab7d10
Revises: 831bbb629ae4
Create Date: 2026-08-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9c41f2ab7d10"
down_revision = "831bbb629ae4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tts_cache",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("voice", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        schema="sauti",
    )


def downgrade() -> None:
    op.drop_table("tts_cache", schema="sauti")
