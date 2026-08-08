"""notebook + daily goal — Ikaye word notebook, per-profile daily study goal

- notebook_entries: "a place I can take note of words that I have learned" —
  any word/phrase the learner keeps, with a personal note. item_id is a soft
  link back to the curriculum item (SET NULL if the item ever goes away); the
  entry snapshots text/gloss at save time so it survives curriculum edits.
- profiles.daily_goal_minutes: the configurable daily study timer goal
  ("if I choose to learn for 15 min…"). Default 25 matches the session length.

Revision ID: b8c2d4e6a917
Revises: f4a1c9d27e01
Create Date: 2026-08-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b8c2d4e6a917"
down_revision = "f4a1c9d27e01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebook_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("gloss", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["sauti.users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["sauti.items.id"], ondelete="SET NULL"),
        schema="sauti",
    )
    op.create_index(
        "ix_notebook_entries_user_created",
        "notebook_entries",
        ["user_id", "created_at"],
        schema="sauti",
    )

    op.add_column(
        "profiles",
        sa.Column("daily_goal_minutes", sa.Integer(), nullable=False, server_default="25"),
        schema="sauti",
    )


def downgrade() -> None:
    op.drop_column("profiles", "daily_goal_minutes", schema="sauti")
    op.drop_index(
        "ix_notebook_entries_user_created", table_name="notebook_entries", schema="sauti"
    )
    op.drop_table("notebook_entries", schema="sauti")
