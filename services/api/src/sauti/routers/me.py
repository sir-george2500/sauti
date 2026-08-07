from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep
from sauti.models import Course, Profile
from sauti.schemas.auth import MeOut, ProfileOut, UserOut

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(user: CurrentUser, db: DbDep) -> MeOut:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    profile_out = None
    if profile is not None:
        course = await db.scalar(select(Course).where(Course.id == profile.course_id))
        profile_out = ProfileOut(
            course_id=profile.course_id,
            course_code=course.code if course else "KIN",
            pace_hours_week=profile.pace_hours_week,
            placed_level=profile.placed_level,
            gamification=profile.gamification,
        )
    return MeOut(
        user=UserOut(id=user.id, email=user.email),
        profile=profile_out,
        email_verified=user.email_verified_at is not None,
    )
