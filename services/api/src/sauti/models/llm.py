"""LLM cost tables (migration f4a1c9d27e01): synthesize-once reply cache."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sauti.db import TimestampedBase


class LlmReplyCache(TimestampedBase):
    """Early-turn learner utterances repeat constantly ("Muraho!", "Ni angahe?")
    — serve the whole structured turn payload {reply, gloss, praise,
    correction_candidates, goals_met} without an LLM call.

    `key` = sha256(f"{scenario_id}|{turn_index}|{normalized user text}").
    Only turns 1-3 are cached: deeper context diverges.
    """

    __tablename__ = "llm_reply_cache"

    key: Mapped[str] = mapped_column(Text, unique=True)  # unique constraint = lookup index
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scenarios.id", ondelete="CASCADE")
    )
    reply: Mapped[dict] = mapped_column(JSONB)
    hits: Mapped[int] = mapped_column(default=0)
