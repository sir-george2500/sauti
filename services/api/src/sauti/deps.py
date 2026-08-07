"""FastAPI dependencies: settings, db session, current user, rate limits, seams."""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sauti.config import Settings
from sauti.db import get_db
from sauti.errors import ApiError
from sauti.models import User
from sauti.rate_limit import RateLimiter, client_key
from sauti.security import parse_access_token
from sauti.services.mail import Mailer


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[AsyncSession, Depends(get_db)]


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHORIZED", "Missing bearer token")
    return auth[7:].strip()


async def get_current_user(
    request: Request, settings: SettingsDep, db: DbDep
) -> User:
    token = _bearer_token(request)
    try:
        claims = parse_access_token(settings, token)
    except pyjwt.PyJWTError:
        raise ApiError(401, "UNAUTHORIZED", "Invalid or expired token")
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError):
        raise ApiError(401, "UNAUTHORIZED", "Invalid or expired token")
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def auth_rate_limit(request: Request, settings: SettingsDep, limiter: RateLimiterDep) -> None:
    key = client_key(request, trust_forwarded_for=settings.trust_proxy_headers)
    limiter.enforce(f"auth:{key}", settings.rate_limit_auth_max)


def get_llm_client(request: Request):
    """LlmClient seam — overridden in tests via app.dependency_overrides."""
    return request.app.state.llm_client


def get_speech_gateway(request: Request):
    return request.app.state.speech_gateway


def get_mailer(request: Request) -> Mailer:
    """Mailer seam — ConsoleMailer in dev/tests, SmtpMailer when configured."""
    return request.app.state.mailer


MailerDep = Annotated[Mailer, Depends(get_mailer)]
