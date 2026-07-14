from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"


class ConsumeResult(StrEnum):
    CONSUMED = "consumed"
    ALREADY_CONSUMED = "already_consumed"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"


class UserDB(BaseModel):
    """Полная row пользователя из БД."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    password_hash: str
    totp_secret: str | None
    totp_enabled: bool
    recovery_codes: list[str] | None
    role: UserRole
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None
    last_login_at: datetime | None
    token_version: int
    last_totp_step: int | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    password_hash: str
    role: UserRole = UserRole.ADMIN


class UserPublic(BaseModel):
    """Публичный slice для API ответов — без секретов."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    role: UserRole
    is_active: bool
    totp_enabled: bool
    last_login_at: datetime | None
    created_at: datetime


class RefreshTokenDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: UUID | None
    user_agent: str | None
    ip: str | None
    created_at: datetime

    @field_validator("ip", mode="before")
    @classmethod
    def _ip_to_str(cls, v):
        if v is None:
            return None
        return str(v)


class LoginChallengeDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    challenge_hash: str
    expires_at: datetime
    consumed_at: datetime | None
    ip: str | None

    @field_validator("ip", mode="before")
    @classmethod
    def _ip_to_str(cls, v):
        if v is None:
            return None
        return str(v)


class PasswordResetDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    consumed_at: datetime | None
