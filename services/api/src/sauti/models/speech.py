from __future__ import annotations

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from sauti.db import TimestampedBase


class TtsCache(TimestampedBase):
    """Synthesize once, fetch forever: maps (voice, text)-derived key -> audio URL.

    `key` is sha256(f"{voice}|{text}")[:32] — the same string used as the
    Cloudinary public_id tail, so the cache key IS the remote asset id.
    """

    __tablename__ = "tts_cache"

    key: Mapped[str] = mapped_column(Text, unique=True)  # unique constraint = the lookup index
    voice: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text)
