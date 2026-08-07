"""Auth primitives: bcrypt hashing, HS256 access JWTs, opaque refresh tokens."""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from sauti.config import Settings

# Common-password denylist enforced at register (rent-rwanda rule).
COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789", "1234567890",
    "qwerty123", "letmein123", "iloveyou1", "admin123", "welcome1", "sunshine1",
    "changeme", "kigali123", "rwanda123",
}


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False


# Hash of a random throwaway value, verified when the email is unknown so login
# takes the same time for unknown-email and wrong-password (no user enumeration
# via response timing). The plaintext was discarded; it can never match.
DUMMY_PASSWORD_HASH = "$2b$12$auJ7HHHueblX/CEuWozhYOUJkB6v0moz1qzUhvztV/ekAy4FttBJO"


def mint_access_token(settings: Settings, user_id: uuid.UUID, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    claims = {
        "iss": settings.jwt_issuer,
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_min)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


def parse_access_token(settings: Settings, token: str) -> dict:
    """Raises jwt.PyJWTError on any problem. Issuer is required."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "iss", "sub"]},
    )


def new_refresh_token() -> tuple[str, str]:
    """Return (raw base64url token, sha256 hex hash). Only the hash is stored."""
    raw_bytes = secrets.token_bytes(32)
    raw = base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()
