"""Vocabulary decks — organised by situation, never alphabetical."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sauti.models import Item, Lesson, Level, SrsState, Unit
from sauti.schemas.curriculum import ItemOut
from sauti.schemas.learning import (
    VocabDeckItemsOut,
    VocabDeckOut,
    VocabDeckSample,
    VocabDecksOut,
)

MASTERY_STABILITY_DAYS = 21.0  # an item ~3 weeks stable counts as mastered

# Deck display names: (Kinyarwanda-flavoured title, English gloss).
DECK_NAMES = {
    "greetings": ("Indamukanyo", "Greetings & people"),
    "family": ("Umuryango", "Family & home"),
    "numbers": ("Imibare n'igihe", "Numbers & time"),
    "transport": ("Ingendo", "Getting around"),
    "market": ("Ku isoko", "Market & money"),
    "food": ("Ibiryo", "Food & eating"),
}


def _names(tag: str) -> tuple[str, str]:
    if tag in DECK_NAMES:
        return DECK_NAMES[tag]
    pretty = tag.replace("_", " ").replace("-", " ").title()
    return pretty, pretty


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def _deck_items(db: AsyncSession, course_id: uuid.UUID) -> dict[str, list[Item]]:
    """Items of the course grouped by their unit's situation_tag (curriculum order)."""
    units = list(
        await db.scalars(
            select(Unit)
            .join(Level, Level.id == Unit.level_id)
            .where(Level.course_id == course_id)
            .order_by(Level.ord, Unit.ord)
            .options(selectinload(Unit.lessons).selectinload(Lesson.items))
        )
    )
    decks: dict[str, list[Item]] = {}
    for unit in units:
        bucket = decks.setdefault(unit.situation_tag, [])
        for lesson in unit.lessons:
            bucket.extend(lesson.items)
    return decks


async def _srs_by_item(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, SrsState]:
    return {
        s.item_id: s
        for s in await db.scalars(select(SrsState).where(SrsState.user_id == user_id))
    }


async def list_decks(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> VocabDecksOut:
    decks = await _deck_items(db, course_id)
    now = datetime.now(timezone.utc)
    states = await _srs_by_item(db, user_id)
    out: list[VocabDeckOut] = []
    total_due = 0
    for tag, items in decks.items():
        if not items:
            continue
        due = sum(1 for i in items if (s := states.get(i.id)) and _aware(s.due_at) <= now)
        mastered = sum(
            1 for i in items if (s := states.get(i.id)) and s.stability >= MASTERY_STABILITY_DAYS
        )
        total_due += due
        title, gloss = _names(tag)
        sample = items[0]
        out.append(
            VocabDeckOut(
                tag=tag,
                title=title,
                gloss=gloss,
                word_count=len(items),
                mastery=round(mastered / len(items), 2),
                due_count=due,
                sample=VocabDeckSample(sentence=sample.sentence, gloss=sample.gloss),
            )
        )
    return VocabDecksOut(decks=out, total_due=total_due)


async def deck_detail(
    db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID, tag: str
) -> VocabDeckItemsOut | None:
    decks = await _deck_items(db, course_id)
    items = decks.get(tag)
    if items is None:
        return None
    now = datetime.now(timezone.utc)
    states = await _srs_by_item(db, user_id)
    due_ids = [i.id for i in items if (s := states.get(i.id)) and _aware(s.due_at) <= now]
    title, _gloss = _names(tag)
    return VocabDeckItemsOut(
        tag=tag,
        title=title,
        items=[ItemOut.model_validate(i, from_attributes=True) for i in items],
        due_item_ids=due_ids,
    )
