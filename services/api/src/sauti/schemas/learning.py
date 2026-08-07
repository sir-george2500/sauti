"""DTOs matching apps/web/src/lib/api/types.ts (the frontend contract)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from sauti.schemas.common import Cefr, Mode, PronReport
from sauti.schemas.curriculum import CanDoOut, ItemOut, RoadmapEta


class AttemptIn(BaseModel):
    item_id: uuid.UUID
    mode: Mode
    score: float | None = Field(default=None, ge=0, le=1)
    answer: str | None = None  # graded server-side against the gloss when score absent
    audio_ref: str | None = None


class SrsStateOut(BaseModel):
    item_id: uuid.UUID
    due_at: datetime
    reps: int
    stability: float
    difficulty: float


class AttemptOut(SrsStateOut):
    """POST /attempts -> updated SrsState (+pron for speak attempts)."""

    pron: PronReport | None = None
    confirmed_candos: list[uuid.UUID] = []  # extra info, ignored by the frontend


class SkillEstimateOut(BaseModel):
    skill: str  # speaking | listening | reading | writing
    cefr: Cefr
    pct: float  # 0..1


class CandoSection(BaseModel):
    items: list[CanDoOut]
    confirmed: int
    total: int


class ConsistencyOut(BaseModel):
    active_days: int
    window_days: int = 14


class TotalsOut(BaseModel):
    hours_total: float
    weekly_avg_hours: float
    sentences_spoken: int
    attempts: int = 0  # extra


class ProgressOut(BaseModel):
    skills: list[SkillEstimateOut]
    cando: CandoSection
    consistency: ConsistencyOut
    totals: TotalsOut
    eta: RoadmapEta | None = None


class RecordingOut(BaseModel):
    """One kept speaking take — GET /progress/recordings ('Hear yourself change')."""

    id: uuid.UUID
    ts: datetime
    day_number: int  # days since the user's first kept recording, 1-based
    item_sentence: str
    audio_url: str  # playable as-is by an <audio> element
    score: float  # 0..1


class VocabDeckSample(BaseModel):
    sentence: str
    gloss: str


class VocabDeckOut(BaseModel):
    tag: str
    title: str
    gloss: str
    word_count: int
    mastery: float  # 0..1
    due_count: int
    sample: VocabDeckSample | None = None


class VocabDecksOut(BaseModel):
    decks: list[VocabDeckOut]
    total_due: int


class VocabDeckItemsOut(BaseModel):
    tag: str
    title: str
    items: list[ItemOut]
    due_item_ids: list[uuid.UUID] = []  # extra


class PlacementQuestion(BaseModel):
    item_id: uuid.UUID
    prompt: str
    options: list[str]
    number: int | None = None  # 1-based
    total: int | None = None


class PlacementStartOut(BaseModel):
    session_id: uuid.UUID
    question: PlacementQuestion


class PlacementAnswerIn(BaseModel):
    session_id: uuid.UUID
    item_id: uuid.UUID
    answer: str


class PlacementAnswerOut(BaseModel):
    question: PlacementQuestion | None = None
    result: Cefr | None = None
    placed_level: Cefr | None = None


ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4"}


class UploadUrlIn(BaseModel):
    content_type: str = Field(default="audio/webm", max_length=100)

    @field_validator("content_type")
    @classmethod
    def _known_audio_type(cls, v: str) -> str:
        # Base type only — "audio/webm;codecs=opus" from MediaRecorder is fine.
        if v.split(";")[0].strip().lower() not in ALLOWED_AUDIO_TYPES:
            raise ValueError("unsupported audio content type")
        return v


class UploadUrlOut(BaseModel):
    upload_url: str
    audio_ref: str


class SpeechScoreIn(BaseModel):
    item_id: uuid.UUID
    audio_ref: str
