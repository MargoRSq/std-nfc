from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class FeedbackCreate(BaseModel):
    card_id: UUID
    name: str
    contact: str
    message: str
    ip: str | None = None
    user_agent: str | None = None


class FeedbackDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    card_id: UUID
    name: str
    contact: str
    message: str
    ip: str | None
    user_agent: str | None
    created_at: datetime
    read_at: datetime | None

    @field_validator("ip", mode="before")
    @classmethod
    def coerce_ip(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)
