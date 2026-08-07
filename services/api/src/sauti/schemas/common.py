"""Value objects (Pydantic, stored as JSONB on parents, cross the API as-is)."""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]

Cefr = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
Mode = Literal["read", "listen", "speak", "write"]
Skill = Literal["speak", "listen", "read", "write", "gram", "vocab"]


class CoachNoteKind(str, Enum):
    fix = "fix"
    praise = "praise"
    culture = "culture"


class CoachNote(BaseModel):
    title: str
    body: str
    kind: Literal["fix", "praise", "culture"]


class PhonemeScore(BaseModel):
    phoneme: str
    score: int = Field(ge=0, le=100)
    note: str | None = None


class PronReport(BaseModel):
    overall: int = Field(ge=0, le=100)
    phonemes: list[PhonemeScore]
    tone_flags: list[str] = []


class SessionBlock(BaseModel):
    tag: str
    mins: int
    title: str
    sub: str
    kind: Literal["review", "lesson", "speak"]
    # Frontend contract: string. Review block carries the situation deck tag
    # (routes to /vocab/{tag}); lesson/speak blocks carry entity UUIDs.
    ref_id: str = ""


class SessionPlan(BaseModel):
    blocks: list[SessionBlock]
    total_min: int
