"""Vocabulary decks — organised by situation, never alphabetical."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sauti.models import Course, Item, Lesson, Level, SrsState, Unit
from sauti.schemas.curriculum import ItemOut
from sauti.schemas.learning import (
    VocabDeckItemsOut,
    VocabDeckOut,
    VocabDeckSample,
    VocabDecksOut,
)
from sauti.services.audio import audio_urls_for_items

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


async def _deck_items(
    db: AsyncSession, course_id: uuid.UUID
) -> tuple[dict[str, list[Item]], str | None]:
    """Items grouped by their unit's situation_tag (curriculum order), and the
    course code — carried out of the SAME query, since the pronunciation
    respelling is only valid for Kinyarwanda and must cost nothing to gate."""
    rows = (
        await db.execute(
            select(Unit, Course.code)
            .join(Level, Level.id == Unit.level_id)
            .join(Course, Course.id == Level.course_id)
            .where(Level.course_id == course_id)
            .order_by(Level.ord, Unit.ord)
            .options(selectinload(Unit.lessons).selectinload(Lesson.items))
        )
    ).all()
    decks: dict[str, list[Item]] = {}
    course_code = rows[0][1] if rows else None
    for unit, _code in rows:
        bucket = decks.setdefault(unit.situation_tag, [])
        for lesson in unit.lessons:
            bucket.extend(lesson.items)
    return decks, course_code


async def _srs_by_item(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, SrsState]:
    return {
        s.item_id: s
        for s in await db.scalars(select(SrsState).where(SrsState.user_id == user_id))
    }


async def list_decks(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> VocabDecksOut:
    decks, _course_code = await _deck_items(db, course_id)
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
    decks, course_code = await _deck_items(db, course_id)
    items = decks.get(tag)
    if items is None:
        return None
    now = datetime.now(timezone.utc)
    states = await _srs_by_item(db, user_id)
    due_ids = [i.id for i in items if (s := states.get(i.id)) and _aware(s.due_at) <= now]
    title, _gloss = _names(tag)
    audio_urls = await audio_urls_for_items(db, items)  # one bulk query, never per-item
    # `pronunciation` is derived in-process from sentence + phoneme_ref — no
    # further query, no N+1.
    out_items = [
        ItemOut.from_item(i, audio_urls.get(i.id), course_code=course_code) for i in items
    ]
    return VocabDeckItemsOut(
        tag=tag,
        title=title,
        items=out_items,
        due_item_ids=due_ids,
    )
