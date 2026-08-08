from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep
from sauti.errors import ApiError
from sauti.models import Course, Profile
from sauti.schemas.auth import MeOut, ProfileOut, ProfilePatchIn, UserOut

router = APIRouter(tags=["me"])


def _profile_out(profile: Profile, course: Course | None) -> ProfileOut:
    return ProfileOut(
        course_id=profile.course_id,
        course_code=course.code if course else "KIN",
        pace_hours_week=profile.pace_hours_week,
        placed_level=profile.placed_level,
        gamification=profile.gamification,
        daily_goal_minutes=profile.daily_goal_minutes,
    )


@router.get("/me")
async def me(user: CurrentUser, db: DbDep) -> MeOut:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    profile_out = None
    if profile is not None:
        course = await db.scalar(select(Course).where(Course.id == profile.course_id))
        profile_out = _profile_out(profile, course)
    return MeOut(
        user=UserOut(id=user.id, email=user.email),
        profile=profile_out,
        email_verified=user.email_verified_at is not None,
    )


@router.patch("/me/profile")
async def patch_profile(body: ProfilePatchIn, user: CurrentUser, db: DbDep) -> ProfileOut:
    """Update learner-owned profile settings — today: the daily timer goal."""
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        raise ApiError(422, "NO_PROFILE", "Register with a course first")
    profile.daily_goal_minutes = body.daily_goal_minutes
    await db.commit()
    course = await db.scalar(select(Course).where(Course.id == profile.course_id))
    return _profile_out(profile, course)
