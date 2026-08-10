"""Roadmap assembly — embeds full lesson payloads (there is no GET /lessons/{id};
the frontend reads lesson content out of the roadmap, see docs/frontend-notes.md).
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from sauti.models import Course, Lesson, Level, Profile, Unit
from sauti.schemas.curriculum import (
    ItemOut,
    QuickCheck,
    QuickCheckOption,
    QuizQuestion,
    RoadmapCurrent,
    RoadmapEta,
    RoadmapLesson,
    RoadmapLevel,
    RoadmapOut,
    RoadmapUnit,
)
from sauti.seed.data_kin import KIN_QUIZZES
from sauti.services import progress as progress_svc
from sauti.services.audio import audio_urls_for_items

# Authored quizzes are curriculum content keyed by course code and lesson
# position — joined to DB lessons here (no schema change, seed-authored).
COURSE_QUIZZES: dict[str, dict[tuple[str, int, int], list[dict]]] = {"KIN": KIN_QUIZZES}


def item_out(item, audio_urls: dict[uuid.UUID, str], course_code: str) -> ItemOut:
    return ItemOut.from_item(item, audio_urls.get(item.id), course_code=course_code)


def build_quiz(lesson: Lesson, quiz_data: list[dict]) -> list[QuizQuestion]:
    """Serialize an authored quiz for a DB lesson: resolve item sentences to
    item ids and shuffle options with a stable per-question hash (so the
    correct answer isn't always first, but responses stay deterministic)."""
    id_by_sentence = {i.sentence: i.id for i in lesson.items}
    out: list[QuizQuestion] = []
    for ord_, data in enumerate(quiz_data, start=1):
        options = [
            QuickCheckOption(text=o["text"], correct=o["correct"]) for o in data["options"]
        ]
        options.sort(
            key=lambda o: hashlib.sha256(f"{lesson.id}|{ord_}|{o.text}".encode()).hexdigest()
        )
        out.append(
            QuizQuestion(
                ord=ord_,
                kind=data["kind"],
                question=data["question"],
                options=options,
                explanation=data["explanation"],
                item_id=id_by_sentence.get(data["item"]) if data.get("item") else None,
            )
        )
    return out


def build_quick_check(lesson: Lesson, distractor_pool: list[str]) -> QuickCheck | None:
    """Deterministic MCQ from the lesson's first item; distractors drawn from the
    lesson (then the unit pool), ordered by a stable per-lesson hash."""
    if not lesson.items:
        return None
    target = lesson.items[0]
    seen = {target.gloss}
    distractors: list[str] = []
    for gloss in [i.gloss for i in lesson.items[1:]] + distractor_pool:
        if gloss not in seen:
            distractors.append(gloss)
            seen.add(gloss)
        if len(distractors) == 3:
            break
    options = [QuickCheckOption(text=target.gloss, correct=True)] + [
        QuickCheckOption(text=d, correct=False) for d in distractors
    ]
    options.sort(
        key=lambda o: hashlib.sha256(f"{lesson.id}|{o.text}".encode()).hexdigest()
    )
    return QuickCheck(
        question=f"What does “{target.sentence}” mean?", options=options
    )


def _lesson_status(is_done: bool, is_current: bool, seen_current: bool) -> str:
    if is_done:
        return "done"
    if is_current:
        return "current"
    return "available" if not seen_current else "locked"


async def build_roadmap(
    db: AsyncSession, user_id: uuid.UUID, profile: Profile, course: Course
) -> RoadmapOut:
    levels = await progress_svc.course_tree(db, profile.course_id)
    studied = await progress_svc.studied_item_ids(db, user_id)
    current_lesson, current_unit, current_level = progress_svc.roadmap_position(levels, studied)

    # One bulk tts_cache lookup for every embedded item (never per-item).
    all_items = [
        i for level in levels for u in level.units for les in u.lessons for i in les.items
    ]
    audio_urls = await audio_urls_for_items(db, all_items)

    quizzes = COURSE_QUIZZES.get(course.code, {})
    out_levels: list[RoadmapLevel] = []
    for level in levels:
        unit_glosses = {u.id: [i.gloss for les in u.lessons for i in les.items] for u in level.units}
        out_units: list[RoadmapUnit] = []
        for unit in level.units:
            out_lessons: list[RoadmapLesson] = []
            for lesson in unit.lessons:
                is_done = progress_svc.lesson_done(lesson, studied)
                is_current = current_lesson is not None and lesson.id == current_lesson.id
                if is_done:
                    status = "done"
                elif is_current:
                    status = "current"
                elif current_unit is not None and unit.id == current_unit.id:
                    status = "available"  # later lessons of the current unit
                elif current_level is not None and level.id == current_level.id:
                    status = "available" if level.ord <= current_level.ord else "locked"
                else:
                    status = "locked" if _after_current(level, current_level) else "available"
                quiz = build_quiz(lesson, quizzes.get((level.cefr, unit.ord, lesson.ord), []))
                if quiz:
                    # Rollout compat: quick_check mirrors the quiz's first question.
                    quick_check = QuickCheck(question=quiz[0].question, options=quiz[0].options)
                else:
                    quick_check = build_quick_check(lesson, unit_glosses[unit.id])
                out_lessons.append(
                    RoadmapLesson(
                        id=lesson.id,
                        title=lesson.title,
                        ord=lesson.ord,
                        status=status,
                        grammar_md=lesson.grammar_md,
                        culture_note=lesson.culture_note,
                        items=[item_out(i, audio_urls, course.code) for i in lesson.items],
                        quick_check=quick_check,
                        quiz=quiz,
                    )
                )
            if all(l.status == "done" for l in out_lessons) and out_lessons:
                unit_status = "done"
            elif any(l.status == "current" for l in out_lessons):
                unit_status = "current"
            elif any(l.status == "available" for l in out_lessons):
                unit_status = "available"
            else:
                unit_status = "locked"
            out_units.append(
                RoadmapUnit(
                    id=unit.id,
                    title=unit.title,
                    situation_tag=unit.situation_tag,
                    ord=unit.ord,
                    status=unit_status,
                    lessons=out_lessons,
                )
            )
        if out_units and all(u.status == "done" for u in out_units):
            level_status = "done"
        elif any(u.status == "current" for u in out_units):
            level_status = "current"
        elif any(u.status in ("available",) for u in out_units):
            level_status = "available"
        else:
            level_status = "locked"
        out_levels.append(
            RoadmapLevel(
                id=level.id,
                cefr=level.cefr,
                title=level.title,
                ord=level.ord,
                status=level_status,
                units=out_units,
            )
        )

    eta_date, eta_cefr = progress_svc.eta_for(levels, studied, profile.pace_hours_week)
    eta = None
    if eta_date is not None and eta_cefr is not None:
        eta = RoadmapEta(
            target_cefr=eta_cefr,
            eta_date=eta_date.isoformat(),
            pace_hours_week=profile.pace_hours_week,
        )

    current = None
    if current_lesson is not None and current_unit is not None and current_level is not None:
        current = RoadmapCurrent(
            cefr=current_level.cefr,
            unit_title=current_unit.title,
            unit_ord=current_unit.ord,
            lesson_id=current_lesson.id,
            lesson_ord=current_lesson.ord,
        )

    return RoadmapOut(course_code=course.code, levels=out_levels, eta=eta, current=current)


def _after_current(level: Level, current_level: Level | None) -> bool:
    if current_level is None:
        return False
    return level.ord > current_level.ord
