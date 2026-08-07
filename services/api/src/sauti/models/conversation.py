from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sauti.db import TimestampedBase


class Scenario(TimestampedBase):
    __tablename__ = "scenarios"

    title: Mapped[str] = mapped_column(Text, unique=True)
    setting: Mapped[str] = mapped_column(Text)
    persona: Mapped[dict] = mapped_column(JSONB, default=dict)  # Mukamana…
    goals: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    min_cefr: Mapped[str] = mapped_column(Text)
    voice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voices.id", ondelete="SET NULL"), nullable=True
    )


class Conversation(TimestampedBase):
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    scenario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"))
    goals_met: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    started_at: Mapped[datetime]

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", order_by="Message.created_at", cascade="all, delete-orphan"
    )


class Message(TimestampedBase):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(Text)  # user | persona | coach
    text: Mapped[str] = mapped_column(Text)
    gloss: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # CoachNote
    audio_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
