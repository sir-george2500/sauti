"""Auth — rent-rwanda rotate-and-detect pattern.

Access: HS256 JWT, 15 min. Refresh: opaque 32-byte token, SHA-256 hash at rest,
30-day TTL, family rotation, reuse detection revokes the family (revocation is
COMMITTED before the 401 is raised). Cookie: httpOnly, SameSite=Lax (frontend
runs on another port in dev), path-scoped to /api/v1/auth.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update

from sauti.deps import DbDep, SettingsDep, auth_rate_limit
from sauti.errors import ApiError
from sauti.models import Course, Profile, RefreshToken, User
from sauti.schemas.auth import LoginIn, MeOut, ProfileOut, RegisterIn, TokenOut, UserOut
from sauti.security import (
    COMMON_PASSWORDS,
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_refresh_token,
    mint_access_token,
    new_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(auth_rate_limit)])

REFRESH_COOKIE = "sauti_refresh"
COOKIE_PATH = "/api/v1/auth"

GENERIC_LOGIN_ERROR = ApiError(401, "INVALID_CREDENTIALS", "Invalid email or password")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _set_refresh_cookie(response: Response, settings, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.refresh_token_ttl_days * 86400,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response, settings) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value="",
        max_age=0,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


async def _issue_tokens(
    db, settings, response: Response, user: User, family_id: uuid.UUID | None = None
) -> str:
    raw, token_hash = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=family_id or uuid.uuid4(),
            expires_at=_utcnow() + timedelta(days=settings.refresh_token_ttl_days),
        )
    )
    await db.commit()
    _set_refresh_cookie(response, settings, raw)
    return mint_access_token(settings, user.id)


@router.post("/register", status_code=201)
async def register(body: RegisterIn, db: DbDep, settings: SettingsDep) -> dict:
    if body.password.lower() in COMMON_PASSWORDS:
        raise ApiError(422, "WEAK_PASSWORD", "That password is too common — pick another")
    existing = await db.scalar(select(User).where(User.email == body.email.lower()))
    if existing is not None:
        raise ApiError(409, "EMAIL_TAKEN", "An account with this email already exists")
    course = await db.scalar(select(Course).where(Course.code == body.course_code))
    if course is None:
        raise ApiError(422, "UNKNOWN_COURSE", "Unknown course code")
    user = User(email=body.email.lower(), password_hash=hash_password(body.password))
    db.add(user)
    await db.flush()
    db.add(
        Profile(
            user_id=user.id,
            course_id=course.id,
            pace_hours_week=body.pace_hours_week,
        )
    )
    await db.commit()
    return {"user": UserOut(id=user.id, email=user.email).model_dump(mode="json")}


@router.post("/login")
async def login(
    body: LoginIn, db: DbDep, settings: SettingsDep, response: Response
) -> TokenOut:
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    # One generic error for unknown-email vs wrong-password, and a constant-cost
    # bcrypt check either way so response timing doesn't enumerate emails.
    password_ok = verify_password(
        body.password, user.password_hash if user else DUMMY_PASSWORD_HASH
    )
    if user is None or not password_ok:
        raise GENERIC_LOGIN_ERROR
    access = await _issue_tokens(db, settings, response, user)
    return TokenOut(access_token=access, user=UserOut(id=user.id, email=user.email))


@router.post("/refresh")
async def refresh(request: Request, db: DbDep, settings: SettingsDep, response: Response) -> TokenOut:
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise ApiError(401, "UNAUTHORIZED", "Missing refresh token")
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
    )
    if row is None:
        raise ApiError(401, "UNAUTHORIZED", "Invalid refresh token")
    if row.revoked_at is not None:
        # Reuse detected: revoke the WHOLE family and COMMIT before raising.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=_utcnow())
        )
        await db.commit()
        raise ApiError(401, "UNAUTHORIZED", "Invalid refresh token")
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
    if expires <= _utcnow():
        raise ApiError(401, "UNAUTHORIZED", "Refresh token expired")
    user = await db.scalar(select(User).where(User.id == row.user_id))
    if user is None:
        raise ApiError(403, "FORBIDDEN", "Account unavailable")

    # Rotate: revoke old, mint new in the SAME family.
    raw_new, hash_new = new_refresh_token()
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_new,
        family_id=row.family_id,
        expires_at=_utcnow() + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(new_row)
    await db.flush()
    row.revoked_at = _utcnow()
    row.replaced_by = new_row.id
    await db.commit()
    _set_refresh_cookie(response, settings, raw_new)
    return TokenOut(
        access_token=mint_access_token(settings, user.id),
        user=UserOut(id=user.id, email=user.email),
    )


@router.post("/logout", status_code=204)
async def logout(request: Request, db: DbDep, settings: SettingsDep, response: Response) -> None:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        row = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
        )
        if row is not None:
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
                .values(revoked_at=_utcnow())
            )
            await db.commit()
    _clear_refresh_cookie(response, settings)  # idempotent
