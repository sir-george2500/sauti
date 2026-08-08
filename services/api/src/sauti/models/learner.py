from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sauti.db import TimestampedBase


class User(TimestampedBase):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    # Verification is NON-blocking: unverified users keep full access, the
    # frontend just nudges them with a banner until this is set.
    email_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Profile(TimestampedBase):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"))
    pace_hours_week: Mapped[int] = mapped_column(default=5)
    placed_level: Mapped[str | None] = mapped_column(Text, nullable=True)  # CEFR
    gamification: Mapped[str] = mapped_column(Text, default="light")  # light | structured
    daily_goal_minutes: Mapped[int] = mapped_column(default=25)  # daily timer goal, 5..120

    user: Mapped[User] = relationship(back_populates="profile")


class Attempt(TimestampedBase):
    __tablename__ = "attempts"
    __table_args__ = (Index("ix_attempts_user_ts", "user_id", "ts"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(Text)  # read | listen | speak | write
    score: Mapped[float] = mapped_column(Float)  # 0..1
    audio_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    pron: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # PronReport
    ts: Mapped[datetime]


class SrsState(TimestampedBase):
    __tablename__ = "srs_state"
    __table_args__ = (
        UniqueConstraint("user_id", "item_id"),
        Index("ix_srs_user_due", "user_id", "due_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    due_at: Mapped[datetime]
    reps: Mapped[int] = mapped_column(default=0)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CanDoStatus(TimestampedBase):
    __tablename__ = "cando_status"
    __table_args__ = (UniqueConstraint("user_id", "cando_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    cando_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cando.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(Text, default="learning")  # learning | confirmed
    confirmed_via_attempt: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True
    )


class NotebookEntry(TimestampedBase):
    """Ikaye — a word/phrase the learner chose to keep, with a personal note.

    text/gloss are snapshotted at save time (so entries survive curriculum
    edits); item_id is a soft link back to the source item for audio playback.
    """

    __tablename__ = "notebook_entries"
    __table_args__ = (Index("ix_notebook_entries_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("items.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text)
    gloss: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class PlacementSession(TimestampedBase):
    __tablename__ = "placement_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    theta: Mapped[float] = mapped_column(Float, default=0.0)
    served: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(PgUUID(as_uuid=True)), default=list)
    n_correct: Mapped[int] = mapped_column(default=0)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # CEFR
