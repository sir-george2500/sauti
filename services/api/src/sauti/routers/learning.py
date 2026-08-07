"""Session, roadmap, progress, vocab, attempts — the learning loop."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep, SettingsDep, get_speech_gateway
from sauti.errors import ApiError
from sauti.models import Attempt, CanDo, Course, Item, Level, Profile, SrsState
from sauti.schemas.common import SessionPlan
from sauti.speech.gateway import SpeechUnavailableError
from sauti.schemas.curriculum import SKILL_LABELS, CanDoOut, RoadmapEta, RoadmapOut
from sauti.schemas.learning import (
    AttemptIn,
    AttemptOut,
    CandoSection,
    ConsistencyOut,
    ProgressOut,
    RecordingOut,
    SkillEstimateOut,
    TotalsOut,
    VocabDeckItemsOut,
    VocabDecksOut,
)
from sauti.services import progress as progress_svc
from sauti.services import roadmap as roadmap_svc
from sauti.services import session_builder, srs, vocab as vocab_svc
from sauti.models import CanDoStatus

router = APIRouter(tags=["learning"])


async def _profile_or_422(db, user_id: uuid.UUID) -> Profile:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise ApiError(422, "NO_PROFILE", "Register with a course first")
    return profile


@router.get("/session/today")
async def session_today(user: CurrentUser, db: DbDep) -> SessionPlan:
    profile = await _profile_or_422(db, user.id)
    return await session_builder.build_today(db, user.id, profile)


@router.get("/roadmap")
async def roadmap(user: CurrentUser, db: DbDep) -> RoadmapOut:
    profile = await _profile_or_422(db, user.id)
    course = await db.scalar(select(Course).where(Course.id == profile.course_id))
    return await roadmap_svc.build_roadmap(db, user.id, profile, course)


@router.get("/progress")
async def progress(user: CurrentUser, db: DbDep) -> ProgressOut:
    profile = await _profile_or_422(db, user.id)
    base_cefr = profile.placed_level or "A1"

    estimates = await progress_svc.skill_estimates(db, user.id)
    skills = [
        SkillEstimateOut(
            skill=SKILL_LABELS[s],
            cefr=progress_svc.score_to_cefr(estimates.get(s, 0.0), base_cefr),
            pct=round(estimates.get(s, 0.0), 2),
        )
        for s in ("speak", "listen", "read", "write")
    ]

    candos = list(
        await db.scalars(
            select(CanDo)
            .join(Level, Level.id == CanDo.level_id)
            .where(Level.course_id == profile.course_id)
            .order_by(Level.ord, CanDo.created_at)
        )
    )
    statuses = {
        s.cando_id: s.status
        for s in await db.scalars(select(CanDoStatus).where(CanDoStatus.user_id == user.id))
    }
    cando_items = [
        CanDoOut(
            id=c.id,
            cefr=c.cefr,
            skill=SKILL_LABELS.get(c.skill, c.skill),
            text=c.text,
            status=statuses.get(c.id, "learning"),
        )
        for c in candos
    ]
    confirmed = sum(1 for c in cando_items if c.status == "confirmed")

    active_days = await progress_svc.consistency_days(db, user.id)
    totals = await progress_svc.totals(db, user.id)

    levels = await progress_svc.course_tree(db, profile.course_id)
    studied = await progress_svc.studied_item_ids(db, user.id)
    eta_date, eta_cefr = progress_svc.eta_for(levels, studied, profile.pace_hours_week)
    eta = None
    if eta_date and eta_cefr:
        eta = RoadmapEta(
            target_cefr=eta_cefr,
            eta_date=eta_date.isoformat(),
            pace_hours_week=profile.pace_hours_week,
        )

    return ProgressOut(
        skills=skills,
        cando=CandoSection(items=cando_items, confirmed=confirmed, total=len(cando_items)),
        consistency=ConsistencyOut(active_days=active_days, window_days=14),
        totals=TotalsOut(
            hours_total=totals["hours"],
            weekly_avg_hours=totals["weekly_avg_hours"],
            sentences_spoken=totals["sentences_spoken"],
            attempts=totals["attempts"],
        ),
        eta=eta,
    )


@router.get("/progress/recordings")
async def progress_recordings(
    user: CurrentUser, db: DbDep, settings: SettingsDep
) -> list[RecordingOut]:
    """Chronological archive of the user's kept speaking takes.

    Design: the Progress page's "Hear yourself change" block — week-1 vs now.
    One query (attempts ⋈ items); audio_ref resolves to the same public route
    the speech upload flow serves recordings from (GET /speech/audio/{ref}).
    """
    rows = (
        await db.execute(
            select(Attempt.id, Attempt.ts, Attempt.audio_ref, Attempt.score, Item.sentence)
            .join(Item, Item.id == Attempt.item_id)
            .where(
                Attempt.user_id == user.id,
                Attempt.mode == "speak",
                Attempt.audio_ref.is_not(None),
            )
            .order_by(Attempt.ts, Attempt.id)
        )
    ).all()
    if not rows:
        return []
    first_day = rows[0].ts.date()
    return [
        RecordingOut(
            id=r.id,
            ts=r.ts,
            day_number=(r.ts.date() - first_day).days + 1,
            item_sentence=r.sentence,
            audio_url=f"{settings.app_base_url}/api/v1/speech/audio/{r.audio_ref}",
            score=r.score,
        )
        for r in rows
    ]


@router.get("/vocab/decks")
async def vocab_decks(user: CurrentUser, db: DbDep) -> VocabDecksOut:
    profile = await _profile_or_422(db, user.id)
    return await vocab_svc.list_decks(db, user.id, profile.course_id)


@router.get("/vocab/decks/{tag}")
async def vocab_deck(tag: str, user: CurrentUser, db: DbDep) -> VocabDeckItemsOut:
    profile = await _profile_or_422(db, user.id)
    deck = await vocab_svc.deck_detail(db, user.id, profile.course_id, tag)
    if deck is None:
        raise ApiError(404, "NOT_FOUND", f"No vocab deck '{tag}'")
    return deck


@router.post("/attempts")
async def post_attempt(
    body: AttemptIn, user: CurrentUser, db: DbDep, request: Request
) -> AttemptOut:
    item = await db.scalar(select(Item).where(Item.id == body.item_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "Unknown item")

    if body.score is not None:
        score = float(body.score)
    elif body.answer is not None:
        score = 1.0 if body.answer.strip().lower() == item.gloss.strip().lower() else 0.0
    else:
        raise ApiError(422, "VALIDATION", "Provide either score or answer")

    now = datetime.now(timezone.utc)
    pron = None
    if body.mode == "speak" and body.audio_ref:
        speech = request.app.state.speech_gateway
        try:
            pron = await speech.score(
                body.audio_ref, str(item.id), item.sentence, item.phoneme_ref or {}
            )
        except (SpeechUnavailableError, FileNotFoundError):
            pron = None  # pron detail is a bonus here — never fail the attempt

    attempt = Attempt(
        user_id=user.id,
        item_id=item.id,
        mode=body.mode,
        score=score,
        audio_ref=body.audio_ref,
        pron=pron.model_dump() if pron else None,
        ts=now,
    )
    db.add(attempt)
    await db.flush()

    # SRS update
    row = await db.scalar(
        select(SrsState).where(SrsState.user_id == user.id, SrsState.item_id == item.id)
    )
    prev = None
    if row is not None:
        last = row.last_reviewed_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        prev = srs.Srs(
            stability=row.stability,
            difficulty=row.difficulty,
            reps=row.reps,
            due_at=row.due_at,
            last_reviewed_at=last,
        )
    next_state = srs.apply(prev, srs.score_to_grade(score), now)
    if row is None:
        row = SrsState(user_id=user.id, item_id=item.id, due_at=next_state.due_at)
        db.add(row)
    row.due_at = next_state.due_at
    row.reps = next_state.reps
    row.stability = next_state.stability
    row.difficulty = next_state.difficulty
    row.last_reviewed_at = now

    confirmed = await progress_svc.confirm_candos_for_speak_attempt(db, user.id, attempt, item)
    await db.commit()

    return AttemptOut(
        item_id=item.id,
        due_at=next_state.due_at,
        reps=next_state.reps,
        stability=next_state.stability,
        difficulty=next_state.difficulty,
        pron=pron,
        confirmed_candos=confirmed,
    )
