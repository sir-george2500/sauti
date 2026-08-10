"""DTOs matching apps/web/src/lib/api/types.ts (the frontend contract)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

from sauti.schemas.common import Cefr
from sauti.speech.respell import respell

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
    # Cached TTS URL (Cloudinary), playable as-is by an <audio> element.
    # Null when not yet cached — the client falls back to GET /tts/{item_id}.
    audio_url: str | None = None
    # English-intuitive respelling: "Mwaramutse!" -> "mwah-rah-MOOT-seh!".
    # Derived in-process from `sentence` + `phoneme_ref` (both already loaded),
    # so it costs no query. Null when there is nothing pronounceable.
    pronunciation: str | None = None

    @classmethod
    def from_item(cls, item, audio_url: str | None = None) -> "ItemOut":
        """Serialize a DB Item, enriching it with everything free to compute.

        Both call sites (roadmap, vocab decks) go through here so an item looks
        the same everywhere it is rendered.
        """
        out = cls.model_validate(item, from_attributes=True)
        out.audio_url = audio_url
        out.pronunciation = respell(item.sentence, item.phoneme_ref)
        return out


class QuickCheckOption(BaseModel):
    text: str
    correct: bool


class QuickCheck(BaseModel):
    question: str
    options: list[QuickCheckOption]


class QuizQuestion(BaseModel):
    """One question of a lesson's end-of-lesson quiz (4–6 per lesson).

    The frontend posts one attempt per question (mode "read", score 1/0)
    against item_id — or the lesson's first item when item_id is null.
    """

    ord: int  # 1-based
    kind: Literal["grammar", "vocab", "usage", "culture"]
    question: str
    options: list[QuickCheckOption]
    explanation: str  # one sentence: WHY the correct answer is right
    item_id: uuid.UUID | None = None


class RoadmapLesson(BaseModel):
    id: uuid.UUID
    title: str
    ord: int
    status: str  # done | current | available | locked
    grammar_md: str | None = None
    culture_note: str | None = None
    items: list[ItemOut] = []
    # Legacy single MCQ — populated from quiz[0] during rollout.
    quick_check: QuickCheck | None = None
    quiz: list[QuizQuestion] = []


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
