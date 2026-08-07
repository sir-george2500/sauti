from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from sauti.deps import CurrentUser, DbDep
from sauti.models import Profile, Scenario
from sauti.schemas.common import CEFR_ORDER
from sauti.schemas.curriculum import ScenarioOut

router = APIRouter(tags=["scenarios"])


@router.get("/scenarios")
async def scenarios(user: CurrentUser, db: DbDep) -> list[ScenarioOut]:
    profile = await db.scalar(select(Profile).where(Profile.user_id == user.id))
    user_level = (profile.placed_level if profile else None) or "A1"
    max_idx = CEFR_ORDER.index(user_level)
    rows = list(await db.scalars(select(Scenario).order_by(Scenario.created_at)))
    out = []
    for s in rows:
        if CEFR_ORDER.index(s.min_cefr) > max_idx:
            continue
        persona = s.persona or {}
        out.append(
            ScenarioOut(
                id=s.id,
                title=s.title,
                setting=s.setting,
                persona=persona,
                goals=s.goals or [],
                min_cefr=s.min_cefr,
                voice_id=s.voice_id,
                umuco_tip=persona.get("umuco_tip"),
            )
        )
    return out
