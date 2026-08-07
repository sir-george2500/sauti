from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from sauti.schemas.common import Cefr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    course_code: str = Field(pattern="^(KIN|SWA|FRA)$")
    pace_hours_week: int = Field(ge=1, le=40, default=5)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailIn(BaseModel):
    token: str = Field(min_length=16, max_length=128)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileOut(BaseModel):
    course_id: uuid.UUID
    course_code: str
    pace_hours_week: int
    placed_level: Cefr | None = None
    gamification: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str


class MeOut(BaseModel):
    user: UserOut
    profile: ProfileOut | None = None
    email_verified: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
