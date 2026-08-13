from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from std_cards.models.card import ContactBlock, drop_blank_contacts

DEFAULT_REGION = "*"


class RegionContactsDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    region: str
    contacts: list[ContactBlock] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RegionContactsUpsert(BaseModel):
    contacts: list[ContactBlock] = Field(default_factory=list)

    @field_validator("contacts")
    @classmethod
    def _drop_blank_blocks(cls, v: list[ContactBlock]) -> list[ContactBlock]:
        return drop_blank_contacts(v) or []
