"""ProgressService + roadmap position logic."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sauti.models import (
    Attempt,
    CanDo,
    CanDoStatus,
    Course,
    Item,
    Lesson,
    Level,
    Profile,
    SrsState,
    Unit,
)
from sauti.schemas.common import CEFR_ORDER

SPEAK_CONFIRM_THRESHOLD = 0.8
MINUTES_PER_ATTEMPT = 0.75
HOURS_PER_LESSON = 0.4

SKILLS = ["speak", "listen", "read", "write", "gram", "vocab"]
CORE_SKILLS = ["speak", "listen", "write", "read"]  # tie-break order for "weakest"


async def course_tree(db: AsyncSession, course_id: uuid.UUID) -> list[Level]:
    result = await db.scalars(
        select(Level)
        .where(Level.course_id == course_id)
        .order_by(Level.ord)
        .options(selectinload(Level.units).selectinload(Unit.lessons).selectinload(Lesson.items))
    )
    return list(result)


async def studied_item_ids(db: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(SrsState.item_id).where(SrsState.user_id == user_id, SrsState.reps >= 1)
    )
    return set(rows)


def lesson_done(lesson: Lesson, studied: set[uuid.UUID]) -> bool:
    if not lesson.items:
        return False
    return all(item.id in studied for item in lesson.items)


def roadmap_position(
    levels: list[Level], studied: set[uuid.UUID]
) -> tuple[Lesson | None, Unit | None, Level | None]:
    """First lesson (in course order) that is not yet done = the current lesson."""
    for level in levels:
        for unit in level.units:
            for lesson in unit.lessons:
                if not lesson_done(lesson, studied):
                    return lesson, unit, level
    return None, None, None


async def skill_estimates(db: AsyncSession, user_id: uuid.UUID, per_mode: int = 20) -> dict[str, float]:
    """Mean score of the most recent `per_mode` attempts per mode.

    gram/vocab are derived views over the same attempts (gram from grammar-tagged
    items, vocab from the overall mean) — documented in docs/backend-notes.md.
    """
    estimates: dict[str, float] = {}
    all_scores: list[float] = []
    for mode in ("read", "listen", "speak", "write"):
        rows = await db.scalars(
            select(Attempt.score)
            .where(Attempt.user_id == user_id, Attempt.mode == mode)
            .order_by(Attempt.ts.desc())
            .limit(per_mode)
        )
        scores = list(rows)
        if scores:
            estimates[mode] = sum(scores) / len(scores)
            all_scores.extend(scores)
    if all_scores:
        estimates["vocab"] = sum(all_scores) / len(all_scores)
        gram_rows = await db.scalars(
            select(Attempt.score)
            .join(Item, Item.id == Attempt.item_id)
            .where(Attempt.user_id == user_id, Item.tags.contains(["grammar"]))
            .order_by(Attempt.ts.desc())
            .limit(per_mode)
        )
        gram = list(gram_rows)
        estimates["gram"] = sum(gram) / len(gram) if gram else estimates["vocab"]
    return estimates


def weakest_skill(estimates: dict[str, float]) -> str:
    """Weakest of the four core skills; skills never attempted count as weakest.

    Deterministic tie-break: speak > listen > write > read priority order,
    so a brand-new learner's speaking block targets speaking (the design's bias).
    """
    return min(CORE_SKILLS, key=lambda s: (estimates.get(s, 0.0), CORE_SKILLS.index(s)))


async def consistency_days(db: AsyncSession, user_id: uuid.UUID, window: int = 14) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=window)
    rows = await db.scalars(
        select(func.date(Attempt.ts)).where(
            Attempt.user_id == user_id, Attempt.ts >= since
        ).distinct()
    )
    return len(list(rows))


async def totals(db: AsyncSession, user_id: uuid.UUID) -> dict:
    n = await db.scalar(select(func.count(Attempt.id)).where(Attempt.user_id == user_id)) or 0
    spoken = await db.scalar(
        select(func.count(Attempt.id)).where(Attempt.user_id == user_id, Attempt.mode == "speak")
    ) or 0
    first_ts = await db.scalar(
        select(func.min(Attempt.ts)).where(Attempt.user_id == user_id)
    )
    hours = round(n * MINUTES_PER_ATTEMPT / 60.0, 1)
    weeks = 1.0
    if first_ts is not None:
        if first_ts.tzinfo is None:
            first_ts = first_ts.replace(tzinfo=timezone.utc)
        weeks = max(1.0, (datetime.now(timezone.utc) - first_ts).days / 7.0)
    return {
        "attempts": int(n),
        "sentences_spoken": int(spoken),
        "hours": hours,
        "weekly_avg_hours": round(hours / weeks, 1),
    }


def eta_for(
    levels: list[Level], studied: set[uuid.UUID], pace_hours_week: int
) -> tuple[date | None, str | None]:
    """Date the learner finishes all seeded content at their weekly pace,
    labelled with the CEFR level they'd reach (one past the last seeded level)."""
    remaining = 0
    last_cefr = None
    for level in levels:
        for unit in level.units:
            for lesson in unit.lessons:
                if lesson.items:
                    last_cefr = level.cefr
                    if not lesson_done(lesson, studied):
                        remaining += 1
    if remaining == 0 or last_cefr is None or pace_hours_week <= 0:
        return None, None
    weeks = (remaining * HOURS_PER_LESSON) / pace_hours_week
    eta = date.today() + timedelta(days=max(7, round(weeks * 7)))
    idx = CEFR_ORDER.index(last_cefr)
    eta_cefr = CEFR_ORDER[min(idx + 1, len(CEFR_ORDER) - 1)]
    return eta, eta_cefr


def score_to_cefr(score: float, base_cefr: str) -> str:
    """Map a 0..1 skill estimate to a displayed CEFR: at or just around base."""
    idx = CEFR_ORDER.index(base_cefr if base_cefr in CEFR_ORDER else "A1")
    if score >= 0.85:
        idx = min(idx + 1, len(CEFR_ORDER) - 1)
    elif score < 0.5:
        idx = max(idx - 1, 0)
    return CEFR_ORDER[idx]


async def confirm_candos_for_speak_attempt(
    db: AsyncSession, user_id: uuid.UUID, attempt: Attempt, item: Item
) -> list[uuid.UUID]:
    """A speaking attempt scoring >= threshold confirms the next unconfirmed
    speak can-do of the item's level. Returns confirmed can-do ids."""
    if attempt.mode != "speak" or attempt.score < SPEAK_CONFIRM_THRESHOLD:
        return []
    level_id = await db.scalar(
        select(Unit.level_id)
        .join(Lesson, Lesson.unit_id == Unit.id)
        .where(Lesson.id == item.lesson_id)
    )
    if level_id is None:
        return []
    candos = list(
        await db.scalars(
            select(CanDo)
            .where(CanDo.level_id == level_id, CanDo.skill == "speak")
            .order_by(CanDo.created_at)
        )
    )
    if not candos:
        return []
    statuses = {
        s.cando_id: s
        for s in await db.scalars(
            select(CanDoStatus).where(
                CanDoStatus.user_id == user_id,
                CanDoStatus.cando_id.in_([c.id for c in candos]),
            )
        )
    }
    for cando in candos:
        status = statuses.get(cando.id)
        if status is not None and status.status == "confirmed":
            continue
        if status is None:
            status = CanDoStatus(user_id=user_id, cando_id=cando.id, status="confirmed")
            db.add(status)
        else:
            status.status = "confirmed"
        status.confirmed_via_attempt = attempt.id
        return [cando.id]
    return []
