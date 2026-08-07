"""SessionBuilder — assembles the daily ≈25-minute plan.

Selection logic (`assemble_plan`) is pure and unit-tested; the async wrapper
just gathers inputs from the DB.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sauti.models import Item, Lesson, Level, Profile, SrsState, Unit
from sauti.schemas.common import SessionBlock, SessionPlan
from sauti.services import progress as progress_svc

REVIEW_MINS = 8
LESSON_MINS = 12
SPEAK_MINS = 5
MAX_DUE_IN_BLOCK = 8

SKILL_LABEL = {
    "speak": "speaking",
    "listen": "listening",
    "read": "reading",
    "write": "writing",
}


@dataclass(frozen=True)
class LessonRef:
    id: uuid.UUID
    title: str
    unit_title: str
    situation_tag: str


@dataclass(frozen=True)
class SpeakRef:
    item_id: uuid.UUID
    sentence: str
    gloss: str


def assemble_plan(
    due_count: int,
    lesson: LessonRef | None,
    speak: SpeakRef | None,
    weakest: str,
    review_deck_tag: str = "",
) -> SessionPlan:
    """Pure selection: due-reviews block + next-lesson block + speaking block.

    ref_id is a string per the frontend contract: the review block carries the
    situation deck tag, lesson/speak blocks carry entity UUIDs.
    """
    blocks: list[SessionBlock] = []
    if due_count > 0:
        shown = min(due_count, MAX_DUE_IN_BLOCK)
        blocks.append(
            SessionBlock(
                tag="REVIEW",
                mins=REVIEW_MINS,
                title=f"Review {shown} due",
                sub="Spaced repetition — keep yesterday's sentences fresh",
                kind="review",
                ref_id=review_deck_tag,
            )
        )
    if lesson is not None:
        blocks.append(
            SessionBlock(
                tag=lesson.situation_tag.upper(),
                mins=LESSON_MINS,
                title=lesson.title,
                sub=lesson.unit_title,
                kind="lesson",
                ref_id=str(lesson.id),
            )
        )
    if speak is not None:
        blocks.append(
            SessionBlock(
                tag="SPEAK",
                mins=SPEAK_MINS,
                title=f"Say it: “{speak.sentence}”",
                sub=f"Pronunciation — weighted to your weakest skill ({SKILL_LABEL.get(weakest, weakest)})",
                kind="speak",
                ref_id=str(speak.item_id),
            )
        )
    # Keep the session ≈25 min: grow the lesson block when there's nothing due.
    total = sum(b.mins for b in blocks)
    if blocks and total < REVIEW_MINS + LESSON_MINS + SPEAK_MINS:
        deficit = (REVIEW_MINS + LESSON_MINS + SPEAK_MINS) - total
        for i, b in enumerate(blocks):
            if b.kind == "lesson":
                blocks[i] = b.model_copy(update={"mins": b.mins + deficit})
                break
        total = sum(b.mins for b in blocks)
    return SessionPlan(blocks=blocks, total_min=total)


async def build_today(db: AsyncSession, user_id: uuid.UUID, profile: Profile) -> SessionPlan:
    now = datetime.now(timezone.utc)
    due_rows = list(
        await db.scalars(
            select(SrsState.item_id).where(
                SrsState.user_id == user_id, SrsState.due_at <= now
            )
        )
    )
    due_count = len(due_rows)
    review_deck_tag = ""
    if due_rows:
        # Deck with the most due items — where the review block links to.
        tag_row = await db.execute(
            select(Unit.situation_tag, func.count().label("n"))
            .join(Level, Level.id == Unit.level_id)
            .join(Lesson, Lesson.unit_id == Unit.id)
            .join(Item, Item.lesson_id == Lesson.id)
            .where(Item.id.in_(due_rows))
            .group_by(Unit.situation_tag)
            .order_by(func.count().desc(), Unit.situation_tag)
            .limit(1)
        )
        first = tag_row.first()
        if first:
            review_deck_tag = first[0]

    levels = await progress_svc.course_tree(db, profile.course_id)
    studied = await progress_svc.studied_item_ids(db, user_id)
    lesson, unit, _level = progress_svc.roadmap_position(levels, studied)

    lesson_ref = None
    speak_ref = None
    if lesson is not None and unit is not None:
        lesson_ref = LessonRef(
            id=lesson.id,
            title=lesson.title,
            unit_title=unit.title,
            situation_tag=unit.situation_tag,
        )
        if lesson.items:
            item = lesson.items[0]
            speak_ref = SpeakRef(item_id=item.id, sentence=item.sentence, gloss=item.gloss)

    estimates = await progress_svc.skill_estimates(db, user_id)
    weakest = progress_svc.weakest_skill(estimates)
    return assemble_plan(due_count, lesson_ref, speak_ref, weakest, review_deck_tag)
