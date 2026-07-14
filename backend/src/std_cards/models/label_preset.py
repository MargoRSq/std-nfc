from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LabelPresetType = Literal["text", "number", "date", "url", "phone", "email"]


class LabelPresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: LabelPresetType = "text"


class LabelPresetUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: LabelPresetType = "text"


class LabelPresetReorder(BaseModel):
    ids: list[UUID]


class LabelPresetDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    admin_id: UUID
    name: str
    type: LabelPresetType
    order_idx: int
    created_at: datetime
    updated_at: datetime
