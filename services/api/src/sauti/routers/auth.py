"""Auth — rent-rwanda rotate-and-detect pattern.

Access: HS256 JWT, 15 min. Refresh: opaque 32-byte token, SHA-256 hash at rest,
30-day TTL, family rotation, reuse detection revokes the family (revocation is
COMMITTED before the 401 is raised). Cookie: httpOnly, SameSite=Lax (frontend
runs on another port in dev), path-scoped to /api/v1/auth.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy import select, update

from sauti.deps import CurrentUser, DbDep, MailerDep, SettingsDep, auth_rate_limit
from sauti.errors import ApiError
from sauti.models import (
    Course,
    EmailVerificationToken,
    PasswordResetToken,
    Profile,
    RefreshToken,
    User,
)
from sauti.rate_limit import client_key
from sauti.schemas.auth import (
    ForgotPasswordIn,
    LoginIn,
    MeOut,
    ProfileOut,
    RegisterIn,
    ResetPasswordIn,
    TokenOut,
    UserOut,
    VerifyEmailIn,
)
from sauti.security import (
    COMMON_PASSWORDS,
    DUMMY_PASSWORD_HASH,
    hash_email_token,
    hash_password,
    hash_refresh_token,
    mint_access_token,
    new_email_token,
    new_refresh_token,
    verify_password,
)
from sauti.services.mail import send_mail_safely

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


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _mint_verification(db, settings, user_id: uuid.UUID) -> str:
    """Add an EmailVerificationToken row (hash at rest) and return the raw
    token for the emailed link. Caller commits."""
    raw, token_hash = new_email_token()
    db.add(
        EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=_utcnow() + timedelta(hours=settings.verify_token_ttl_hours),
        )
    )
    return raw


def _queue_verification_mail(
    background: BackgroundTasks, mailer, settings, email: str, raw_token: str
) -> None:
    link = f"{settings.app_frontend_url}/verify-email?token={raw_token}"
    background.add_task(
        send_mail_safely,
        mailer,
        to=email,
        subject="Verify your email — Sauti",
        text=(
            "Muraho!\n\n"
            "Confirm this address to secure your Sauti account:\n\n"
            f"{link}\n\n"
            f"The link works for {settings.verify_token_ttl_hours} hours. "
            "If you didn't create a Sauti account, ignore this email.\n\n"
            "— Sauti"
        ),
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
async def register(
    body: RegisterIn,
    db: DbDep,
    settings: SettingsDep,
    mailer: MailerDep,
    background: BackgroundTasks,
) -> dict:
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
    raw_token = _mint_verification(db, settings, user.id)
    await db.commit()
    # Mail goes out AFTER the response: registration never waits on (or
    # fails because of) SMTP — verification is a nudge, not a gate.
    _queue_verification_mail(background, mailer, settings, user.email, raw_token)
    return {"user": UserOut(id=user.id, email=user.email).model_dump(mode="json")}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailIn, db: DbDep) -> dict:
    row = await db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == hash_email_token(body.token)
        )
    )
    if row is None:
        raise ApiError(400, "INVALID_TOKEN", "That verification link isn't valid — request a new one.")
    if row.used_at is not None:
        raise ApiError(410, "TOKEN_USED", "That verification link was already used.")
    if _aware(row.expires_at) <= _utcnow():
        raise ApiError(410, "TOKEN_EXPIRED", "That verification link has expired — request a new one.")
    now = _utcnow()
    row.used_at = now
    await db.execute(
        update(User)
        .where(User.id == row.user_id, User.email_verified_at.is_(None))
        .values(email_verified_at=now)
    )
    await db.commit()
    return {"ok": True}


@router.post("/resend-verification")
async def resend_verification(
    request: Request,
    user: CurrentUser,
    db: DbDep,
    settings: SettingsDep,
    mailer: MailerDep,
    background: BackgroundTasks,
) -> dict:
    # Tighter per-user cap on top of the router-wide auth limit — this
    # endpoint sends real mail.
    request.app.state.rate_limiter.enforce(
        f"email:u:{user.id}", settings.rate_limit_email_max
    )
    if user.email_verified_at is None:
        raw_token = _mint_verification(db, settings, user.id)
        await db.commit()
        _queue_verification_mail(background, mailer, settings, user.email, raw_token)
    # Already verified: same generic 200 no-op — nothing to learn here.
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordIn,
    db: DbDep,
    settings: SettingsDep,
    mailer: MailerDep,
    background: BackgroundTasks,
) -> dict:
    # Tighter per-IP cap on top of the router-wide auth limit — this
    # endpoint sends real mail.
    ip_key = client_key(request, trust_forwarded_for=settings.trust_proxy_headers)
    request.app.state.rate_limiter.enforce(
        f"email:{ip_key}", settings.rate_limit_email_max
    )
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is not None:
        raw, token_hash = new_email_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=_utcnow() + timedelta(hours=settings.reset_token_ttl_hours),
            )
        )
        await db.commit()
        link = f"{settings.app_frontend_url}/reset-password?token={raw}"
        background.add_task(
            send_mail_safely,
            mailer,
            to=user.email,
            subject="Reset your password — Sauti",
            text=(
                "Muraho!\n\n"
                "Someone (hopefully you) asked to reset the password for this "
                "Sauti account. Choose a new one here:\n\n"
                f"{link}\n\n"
                f"The link works for {settings.reset_token_ttl_hours} hour(s) and "
                "can be used once. If this wasn't you, ignore this email — your "
                "password is unchanged.\n\n"
                "— Sauti"
            ),
        )
    # Identical 200 whether or not the account exists: no email enumeration.
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordIn, db: DbDep) -> dict:
    if body.new_password.lower() in COMMON_PASSWORDS:
        raise ApiError(422, "WEAK_PASSWORD", "That password is too common — pick another")
    row = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_email_token(body.token)
        )
    )
    if row is None:
        raise ApiError(400, "INVALID_TOKEN", "That reset link isn't valid — request a new one.")
    if row.used_at is not None:
        raise ApiError(410, "TOKEN_USED", "That reset link was already used — request a new one.")
    if _aware(row.expires_at) <= _utcnow():
        raise ApiError(410, "TOKEN_EXPIRED", "That reset link has expired — request a new one.")
    now = _utcnow()
    # Consume this token AND any other outstanding reset links for the user.
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == row.user_id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    await db.execute(
        update(User)
        .where(User.id == row.user_id)
        .values(password_hash=hash_password(body.new_password))
    )
    # A reset signs out every device: revoke ALL the user's refresh families.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await db.commit()
    return {"ok": True}


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
