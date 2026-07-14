from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from std_cards.models.auth import UserRole


class AdminCardGroupDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    category_id: int
    can_edit: bool
    can_export: bool


class AdminInvite(BaseModel):
    email: EmailStr
    name: str | None = None
    role: UserRole = UserRole.ADMIN
    category_ids: list[int] = []
    can_export: bool = False
    initial_password: str | None = None


class AdminUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    role: UserRole | None = None
    category_ids: list[int] | None = None
    can_export: bool | None = None


class AdminListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    role: UserRole
    is_active: bool
    totp_enabled: bool
    last_login_at: datetime | None
    created_at: datetime
    allowed_categories: list[int]
