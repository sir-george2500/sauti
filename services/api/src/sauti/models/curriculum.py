from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sauti.db import TimestampedBase

# CEFR: A1..C2 · Skill: speak listen read write gram vocab — stored as text,
# validated at the Pydantic boundary (no native PG enums: simpler migrations).


class Course(TimestampedBase):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(Text, unique=True)  # KIN | SWA | FRA
    name: Mapped[str] = mapped_column(Text)

    levels: Mapped[list[Level]] = relationship(
        back_populates="course", order_by="Level.ord", cascade="all, delete-orphan"
    )


class Level(TimestampedBase):
    __tablename__ = "levels"
    __table_args__ = (UniqueConstraint("course_id", "cefr"),)

    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    cefr: Mapped[str] = mapped_column(Text)  # A1..C2
    title: Mapped[str] = mapped_column(Text)
    ord: Mapped[int]

    course: Mapped[Course] = relationship(back_populates="levels")
    units: Mapped[list[Unit]] = relationship(
        back_populates="level", order_by="Unit.ord", cascade="all, delete-orphan"
    )
    candos: Mapped[list[CanDo]] = relationship(back_populates="level", cascade="all, delete-orphan")


class Unit(TimestampedBase):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("level_id", "ord"),)

    level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("levels.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    situation_tag: Mapped[str] = mapped_column(Text, index=True)
    ord: Mapped[int]

    level: Mapped[Level] = relationship(back_populates="units")
    lessons: Mapped[list[Lesson]] = relationship(
        back_populates="unit", order_by="Lesson.ord", cascade="all, delete-orphan"
    )


class Lesson(TimestampedBase):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("unit_id", "ord"),)

    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    ord: Mapped[int]
    grammar_md: Mapped[str] = mapped_column(Text)
    culture_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # Umuco

    unit: Mapped[Unit] = relationship(back_populates="lessons")
    items: Mapped[list[Item]] = relationship(
        back_populates="lesson", order_by="Item.created_at", cascade="all, delete-orphan"
    )


class Item(TimestampedBase):
    """The atom: a sentence you'd actually say."""

    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("lesson_id", "sentence"),
        Index("ix_items_tags", "tags", postgresql_using="gin"),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    sentence: Mapped[str] = mapped_column(Text)
    gloss: Mapped[str] = mapped_column(Text)
    phoneme_ref: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"syllables": [...]}
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    audio_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("voices.id", ondelete="SET NULL"), nullable=True
    )

    lesson: Mapped[Lesson] = relationship(back_populates="items")
    voice: Mapped[Voice | None] = relationship()


class Voice(TimestampedBase):
    __tablename__ = "voices"
    __table_args__ = (UniqueConstraint("speaker",),)

    speaker: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(Text)
    consent_ref: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)


class CanDo(TimestampedBase):
    __tablename__ = "cando"
    __table_args__ = (UniqueConstraint("level_id", "text"),)

    level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("levels.id", ondelete="CASCADE"))
    cefr: Mapped[str] = mapped_column(Text)
    skill: Mapped[str] = mapped_column(Text)  # speak listen read write gram vocab
    text: Mapped[str] = mapped_column(Text)

    level: Mapped[Level] = relationship(back_populates="candos")
