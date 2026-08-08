"""Ikaye (word notebook) DTOs — mirror apps/web/src/lib/api/types.ts."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _clean(v: str | None) -> str | None:
    """Collapse whitespace-only strings to None so '' never lands in the DB."""
    if v is None:
        return None
    v = v.strip()
    return v or None


class NotebookEntryIn(BaseModel):
    """POST /notebook — free-form text, or item_id to snapshot a curriculum item."""

    text: str | None = Field(default=None, max_length=500)
    gloss: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    item_id: uuid.UUID | None = None

    _clean_fields = field_validator("text", "gloss", "note")(_clean)


class NotebookEntryPatch(BaseModel):
    """PATCH /notebook/{id} — only the provided fields change (exclude_unset)."""

    text: str | None = Field(default=None, max_length=500)
    gloss: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)

    _clean_fields = field_validator("text", "gloss", "note")(_clean)


class NotebookEntryOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID | None = None
    text: str
    gloss: str | None = None
    note: str | None = None
    created_at: datetime
    # Item-linked extras (null for free-form entries): the live item sentence/
    # gloss, and the cached Cloudinary audio URL playable as-is by <audio>.
    item_sentence: str | None = None
    item_gloss: str | None = None
    audio_url: str | None = None
