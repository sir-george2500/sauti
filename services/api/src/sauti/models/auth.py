from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from sauti.db import TimestampedBase


class RefreshToken(TimestampedBase):
    """Rotating opaque refresh token. Only the SHA-256 hash is stored.

    family_id groups tokens from one login; reuse of a revoked token
    revokes the whole family (rent-rwanda rotate-and-detect pattern).
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_family", "family_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(PgUUID(as_uuid=True))
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), nullable=True
    )
