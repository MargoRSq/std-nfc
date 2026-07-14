from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CardMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    image_key: str | None = None


class CardMessageDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    card_id: UUID
    text: str
    image_key: str | None
    created_by: UUID | None
    created_at: datetime
    deleted_at: datetime | None


class CardMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    text: str
    image_key: str | None
    created_at: datetime
