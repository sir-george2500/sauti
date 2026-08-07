"""Alternate the two seeded voices across each lesson's items — idempotent.

    cd services/api && uv run python scripts/assign_listening_voices.py [KIN]

The listening screen renders a lesson's items as a two-speaker dialogue,
labelling line i as SPEAKERS[i % 2] with SPEAKERS = ["Emmanuel", "Diane"]
(apps/web .../practice/listening/[lessonId]/page.tsx). The seed assigns every
item to Diane, so the audio never matched the labels. This script sets each
item's voice to match the label: even line (0-based) -> Emmanuel, odd -> Diane,
ordered exactly as the roadmap serves them (Item.created_at).

Safe to re-run any number of times (pure function of the item order); the seed
runner never overwrites a non-null voice_id, so re-seeding won't undo it.
After running, re-render audio for the newly male-voiced items:

    uv run python -m sauti.speech.prerender KIN
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from sauti.config import get_settings
from sauti.db import build_engine, build_sessionmaker
from sauti.models import Course, Item, Lesson, Level, Unit, Voice

# Must mirror SPEAKERS in the listening page: line i is spoken by SPEAKERS[i % 2].
SPEAKERS = ["Emmanuel", "Diane"]


async def main(course_code: str = "KIN") -> None:
    settings = get_settings()
    engine = build_engine(settings)
    maker = build_sessionmaker(engine)
    try:
        async with maker() as db:
            voices = {
                v.speaker: v.id
                for v in await db.scalars(select(Voice).where(Voice.speaker.in_(SPEAKERS)))
            }
            missing = [s for s in SPEAKERS if s not in voices]
            if missing:
                raise SystemExit(f"voices not seeded: {missing} — run the seed first")

            lessons = list(
                await db.scalars(
                    select(Lesson)
                    .join(Unit, Unit.id == Lesson.unit_id)
                    .join(Level, Level.id == Unit.level_id)
                    .join(Course, Course.id == Level.course_id)
                    .where(Course.code == course_code)
                )
            )
            changed = kept = 0
            for lesson in lessons:
                items = list(
                    await db.scalars(
                        select(Item)
                        .where(Item.lesson_id == lesson.id)
                        .order_by(Item.created_at, Item.id)
                    )
                )
                for i, item in enumerate(items):
                    want = voices[SPEAKERS[i % 2]]
                    if item.voice_id != want:
                        item.voice_id = want
                        changed += 1
                    else:
                        kept += 1
            await db.commit()
            print(
                f"{course_code}: {len(lessons)} lessons — "
                f"{changed} items reassigned, {kept} already correct."
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "KIN"))
