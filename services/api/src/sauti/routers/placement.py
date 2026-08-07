"""PlacementEngine endpoints — simple adaptive IRT over seeded curriculum items."""
from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep
from sauti.errors import ApiError
from sauti.models import Item, Lesson, Level, PlacementSession, Profile, Unit
from sauti.schemas.learning import (
    PlacementAnswerIn,
    PlacementAnswerOut,
    PlacementQuestion,
    PlacementStartOut,
)
from sauti.services import placement as engine

router = APIRouter(prefix="/placement", tags=["placement"])


async def _course_items(db, course_id: uuid.UUID) -> list[tuple[Item, str]]:
    rows = await db.execute(
        select(Item, Level.cefr)
        .join(Lesson, Lesson.id == Item.lesson_id)
        .join(Unit, Unit.id == Lesson.unit_id)
        .join(Level, Level.id == Unit.level_id)
        .where(Level.course_id == course_id)
        .order_by(Level.ord, Unit.ord, Lesson.ord, Item.created_at)
    )
    return [(item, cefr) for item, cefr in rows]


def _build_question(
    session_id: uuid.UUID, item: Item, pool: list[Item], number: int
) -> PlacementQuestion:
    """MCQ: what does the sentence mean? Distractors are other items' glosses,
    deterministically chosen and ordered by a session+item hash."""
    def h(text: str) -> str:
        return hashlib.sha256(f"{session_id}|{item.id}|{text}".encode()).hexdigest()

    seen = {item.gloss}
    distractors: list[str] = []
    for other in sorted((p for p in pool if p.id != item.id), key=lambda p: h(str(p.id))):
        if other.gloss not in seen:
            distractors.append(other.gloss)
            seen.add(other.gloss)
        if len(distractors) == 3:
            break
    options = sorted([item.gloss, *distractors], key=h)
    return PlacementQuestion(
        item_id=item.id,
        prompt=f"What does “{item.sentence}” mean?",
        options=options,
        number=number,
        total=engine.MAX_QUESTIONS,
    )


@router.post("/start")
async def start(user: CurrentUser, db: DbDep) -> PlacementStartOut:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        raise ApiError(422, "NO_PROFILE", "Register with a course first")
    pool = await _course_items(db, profile.course_id)
    if not pool:
        raise ApiError(422, "NO_CONTENT", "Course has no placement content yet")

    session = PlacementSession(user_id=user.id, theta=0.0, served=[], n_correct=0)
    db.add(session)
    await db.flush()

    first_id = engine.pick_next(0.0, [(str(i.id), cefr) for i, cefr in pool])
    first = next(i for i, _ in pool if str(i.id) == first_id)
    session.served = [first.id]
    await db.commit()
    return PlacementStartOut(
        session_id=session.id,
        question=_build_question(session.id, first, [i for i, _ in pool], 1),
    )


@router.post("/answer")
async def answer(body: PlacementAnswerIn, user: CurrentUser, db: DbDep) -> PlacementAnswerOut:
    session = await db.scalar(
        select(PlacementSession).where(
            PlacementSession.id == body.session_id, PlacementSession.user_id == user.id
        )
    )
    if session is None:
        raise ApiError(404, "NOT_FOUND", "Unknown placement session")
    if session.result is not None:
        raise ApiError(409, "FINISHED", "Placement session already finished")
    if not session.served or session.served[-1] != body.item_id:
        raise ApiError(409, "OUT_OF_ORDER", "Answer the currently served question")

    item = await db.scalar(select(Item).where(Item.id == body.item_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "Unknown item")

    correct = body.answer.strip().lower() == item.gloss.strip().lower()
    n_before = len(session.served) - 1  # answered before this one
    session.theta = engine.step_theta(session.theta, correct, n_before)
    if correct:
        session.n_correct += 1
    n_answered = n_before + 1

    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    pool = await _course_items(db, profile.course_id)

    if engine.is_done(n_answered):
        available = sorted({cefr for _, cefr in pool})
        placed = engine.theta_to_cefr(session.theta, available)
        session.result = placed
        profile.placed_level = placed
        await db.commit()
        return PlacementAnswerOut(result=placed, placed_level=placed)

    served_set = set(session.served)
    candidates = [(str(i.id), cefr) for i, cefr in pool if i.id not in served_set]
    next_id = engine.pick_next(session.theta, candidates)
    if next_id is None:  # ran out of items — finalize early
        available = sorted({cefr for _, cefr in pool})
        placed = engine.theta_to_cefr(session.theta, available)
        session.result = placed
        profile.placed_level = placed
        await db.commit()
        return PlacementAnswerOut(result=placed, placed_level=placed)

    next_item = next(i for i, _ in pool if str(i.id) == next_id)
    session.served = [*session.served, next_item.id]
    await db.commit()
    return PlacementAnswerOut(
        question=_build_question(session.id, next_item, [i for i, _ in pool], n_answered + 1)
    )
