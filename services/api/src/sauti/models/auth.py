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


class _SingleUseEmailToken(TimestampedBase):
    """Shared shape for the emailed one-shot tokens: SHA-256 hash at rest
    (the raw 32-byte urlsafe token only ever lives in the email link),
    hard expiry, used_at marks single use."""

    __abstract__ = True

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None] = mapped_column(nullable=True)


class EmailVerificationToken(_SingleUseEmailToken):
    __tablename__ = "email_verification_tokens"
    __table_args__ = (Index("ix_email_verification_tokens_user", "user_id"),)


class PasswordResetToken(_SingleUseEmailToken):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user", "user_id"),)
