"""DTOs matching apps/web/src/lib/api/types.ts (the frontend contract)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from sauti.schemas.common import Cefr

# Frontend skill labels are full words; DB stores short forms.
SKILL_LABELS = {
    "speak": "speaking",
    "listen": "listening",
    "read": "reading",
    "write": "writing",
    "gram": "grammar",
    "vocab": "vocabulary",
}


class CourseOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    available: bool  # fully seeded vs skeleton


class ItemOut(BaseModel):
    id: uuid.UUID
    sentence: str
    gloss: str
    tags: list[str] = []
    audio_ref: str | None = None
    voice_id: uuid.UUID | None = None
    phoneme_ref: dict = {}


class QuickCheckOption(BaseModel):
    text: str
    correct: bool


class QuickCheck(BaseModel):
    question: str
    options: list[QuickCheckOption]


class RoadmapLesson(BaseModel):
    id: uuid.UUID
    title: str
    ord: int
    status: str  # done | current | available | locked
    grammar_md: str | None = None
    culture_note: str | None = None
    items: list[ItemOut] = []
    quick_check: QuickCheck | None = None


class RoadmapUnit(BaseModel):
    id: uuid.UUID
    title: str
    situation_tag: str
    ord: int
    status: str
    lessons: list[RoadmapLesson]


class RoadmapLevel(BaseModel):
    id: uuid.UUID
    cefr: Cefr
    title: str
    ord: int
    status: str
    units: list[RoadmapUnit]


class RoadmapEta(BaseModel):
    target_cefr: Cefr
    eta_date: str  # ISO date
    pace_hours_week: int


class RoadmapCurrent(BaseModel):
    cefr: Cefr
    unit_title: str
    unit_ord: int | None = None
    lesson_id: uuid.UUID | None = None
    lesson_ord: int | None = None


class RoadmapOut(BaseModel):
    course_code: str
    levels: list[RoadmapLevel]
    eta: RoadmapEta | None = None
    current: RoadmapCurrent | None = None


class CanDoOut(BaseModel):
    id: uuid.UUID
    cefr: Cefr
    skill: str  # full-word label ("speaking", ...)
    text: str
    status: str  # learning | confirmed


class ScenarioOut(BaseModel):
    id: uuid.UUID
    title: str
    setting: str
    persona: dict
    goals: list[str]
    min_cefr: Cefr
    voice_id: uuid.UUID | None = None
    umuco_tip: str | None = None
