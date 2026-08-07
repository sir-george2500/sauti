from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from sauti.deps import DbDep
from sauti.models import Course, Item, Lesson, Level, Unit
from sauti.schemas.curriculum import CourseOut

router = APIRouter(tags=["courses"])

# A course is "available" (fully seeded) once it has a meaningful item count;
# skeleton courses exist so the UI can list all three languages.
AVAILABLE_MIN_ITEMS = 30


@router.get("/courses")
async def courses(db: DbDep) -> list[CourseOut]:
    rows = await db.execute(
        select(Course, func.count(Item.id))
        .outerjoin(Level, Level.course_id == Course.id)
        .outerjoin(Unit, Unit.level_id == Level.id)
        .outerjoin(Lesson, Lesson.unit_id == Unit.id)
        .outerjoin(Item, Item.lesson_id == Lesson.id)
        .group_by(Course.id)
        .order_by(Course.code)
    )
    return [
        CourseOut(id=c.id, code=c.code, name=c.name, available=n >= AVAILABLE_MIN_ITEMS)
        for c, n in rows
    ]
