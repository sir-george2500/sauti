"""Idempotent seed — safe to run any number of times.

Upserts by natural keys: course.code, (course, cefr), (level, unit ord),
(unit, lesson ord), (lesson, item sentence), (level, cando text),
voice.speaker, scenario.title. Content fields are updated in place, so editing
the data files and re-running refreshes the curriculum without duplicates.

Run from services/api:  uv run python -m sauti.seed
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sauti.config import get_settings
from sauti.db import build_engine, build_sessionmaker
from sauti.models import CanDo, Course, Item, Lesson, Level, Scenario, Unit, Voice
from sauti.seed.data_kin import COURSE_KIN
from sauti.seed.data_skeletons import COURSE_FRA, COURSE_SWA

VOICES = [
    {
        "speaker": "Diane",
        "region": "Kigali",
        "consent_ref": "consent/diane-kigali-2026.pdf",
        "model_version": "stub-v0",
    },
    {
        "speaker": "Emmanuel",
        "region": "Kigali",
        "consent_ref": "consent/emmanuel-kigali-2026.pdf",
        "model_version": "stub-v0",
    },
]

SCENARIO_KIMIRONKO = {
    "title": "Kimironko market run",
    "setting": "Kimironko market, Kigali — a busy Saturday morning at a vegetable stall",
    "persona": {
        "name": "Mukamana",
        "role": "vegetable vendor",
        "description": (
            "Mukamana has sold tomatoes, plantains and greens at Kimironko for "
            "fifteen years. Warm and quick-witted, she enjoys a friendly bargain, "
            "keeps her sentences short, and is endlessly patient with learners — "
            "but she opens no bargain before a proper greeting."
        ),
        "situation_tag": "market",
        "umuco_tip": (
            "Greet before you ask a price — walking up and naming a number is "
            "rude. A warm “Mwaramutse! Amakuru?” opens every good bargain."
        ),
    },
    "goals": [
        "greet the vendor",
        "ask a price",
        "bargain the price down",
        "close politely",
    ],
    "min_cefr": "A1",
    "voice_speaker": "Diane",
}


async def _upsert_voice(db: AsyncSession, data: dict) -> Voice:
    row = await db.scalar(select(Voice).where(Voice.speaker == data["speaker"]))
    if row is None:
        row = Voice(**data)
        db.add(row)
    else:
        row.region = data["region"]
        row.consent_ref = data["consent_ref"]
        row.model_version = data["model_version"]
    await db.flush()
    return row


async def _upsert_course(db: AsyncSession, data: dict, default_voice: Voice) -> tuple[int, int, int]:
    n_lessons = n_items = n_candos = 0
    course = await db.scalar(select(Course).where(Course.code == data["code"]))
    if course is None:
        course = Course(code=data["code"], name=data["name"])
        db.add(course)
        await db.flush()
    else:
        course.name = data["name"]

    for level_data in data["levels"]:
        level = await db.scalar(
            select(Level).where(Level.course_id == course.id, Level.cefr == level_data["cefr"])
        )
        if level is None:
            level = Level(
                course_id=course.id,
                cefr=level_data["cefr"],
                title=level_data["title"],
                ord=level_data["ord"],
            )
            db.add(level)
            await db.flush()
        else:
            level.title = level_data["title"]
            level.ord = level_data["ord"]

        for skill, text in level_data.get("candos", []):
            cando = await db.scalar(
                select(CanDo).where(CanDo.level_id == level.id, CanDo.text == text)
            )
            if cando is None:
                db.add(CanDo(level_id=level.id, cefr=level.cefr, skill=skill, text=text))
            else:
                cando.skill = skill
                cando.cefr = level.cefr
            n_candos += 1

        for unit_data in level_data["units"]:
            unit = await db.scalar(
                select(Unit).where(Unit.level_id == level.id, Unit.ord == unit_data["ord"])
            )
            if unit is None:
                unit = Unit(
                    level_id=level.id,
                    title=unit_data["title"],
                    situation_tag=unit_data["situation_tag"],
                    ord=unit_data["ord"],
                )
                db.add(unit)
                await db.flush()
            else:
                unit.title = unit_data["title"]
                unit.situation_tag = unit_data["situation_tag"]

            for ord_, lesson_data in enumerate(unit_data["lessons"], start=1):
                lesson = await db.scalar(
                    select(Lesson).where(Lesson.unit_id == unit.id, Lesson.ord == ord_)
                )
                if lesson is None:
                    lesson = Lesson(
                        unit_id=unit.id,
                        title=lesson_data["title"],
                        ord=ord_,
                        grammar_md=lesson_data["grammar_md"],
                        culture_note=lesson_data.get("culture_note"),
                    )
                    db.add(lesson)
                    await db.flush()
                else:
                    lesson.title = lesson_data["title"]
                    lesson.grammar_md = lesson_data["grammar_md"]
                    lesson.culture_note = lesson_data.get("culture_note")
                n_lessons += 1

                for item_data in lesson_data["items"]:
                    row = await db.scalar(
                        select(Item).where(
                            Item.lesson_id == lesson.id,
                            Item.sentence == item_data["sentence"],
                        )
                    )
                    if row is None:
                        db.add(
                            Item(
                                lesson_id=lesson.id,
                                sentence=item_data["sentence"],
                                gloss=item_data["gloss"],
                                phoneme_ref=item_data["phoneme_ref"],
                                tags=item_data["tags"],
                                voice_id=default_voice.id,
                            )
                        )
                    else:
                        row.gloss = item_data["gloss"]
                        row.phoneme_ref = item_data["phoneme_ref"]
                        row.tags = item_data["tags"]
                        if row.voice_id is None:
                            row.voice_id = default_voice.id
                    n_items += 1
    return n_lessons, n_items, n_candos


async def _upsert_scenario(db: AsyncSession, data: dict) -> None:
    voice = await db.scalar(select(Voice).where(Voice.speaker == data["voice_speaker"]))
    row = await db.scalar(select(Scenario).where(Scenario.title == data["title"]))
    if row is None:
        row = Scenario(
            title=data["title"],
            setting=data["setting"],
            persona=data["persona"],
            goals=data["goals"],
            min_cefr=data["min_cefr"],
            voice_id=voice.id if voice else None,
        )
        db.add(row)
    else:
        row.setting = data["setting"]
        row.persona = data["persona"]
        row.goals = data["goals"]
        row.min_cefr = data["min_cefr"]
        row.voice_id = voice.id if voice else row.voice_id


async def seed(db: AsyncSession) -> dict:
    voices = [await _upsert_voice(db, v) for v in VOICES]
    diane = voices[0]
    totals = {"lessons": 0, "items": 0, "candos": 0}
    for course_data in (COURSE_KIN, COURSE_SWA, COURSE_FRA):
        lessons, items, candos = await _upsert_course(db, course_data, diane)
        totals["lessons"] += lessons
        totals["items"] += items
        totals["candos"] += candos
    await _upsert_scenario(db, SCENARIO_KIMIRONKO)
    await db.commit()
    return totals


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings)
    maker = build_sessionmaker(engine)
    try:
        async with maker() as db:
            totals = await seed(db)
        print(
            f"Seed complete: {totals['lessons']} lessons, {totals['items']} items, "
            f"{totals['candos']} can-dos, {len(VOICES)} voices, 1 scenario."
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
