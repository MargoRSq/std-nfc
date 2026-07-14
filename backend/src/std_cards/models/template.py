from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    category_id: int
    default_fields: dict[str, Any]
    default_styles: dict[str, Any]
    custom_field_schema: list[dict[str, Any]]
    created_by: UUID | None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: int
    default_fields: dict[str, Any] = Field(default_factory=dict)
    default_styles: dict[str, Any] = Field(default_factory=dict)
    custom_field_schema: list[dict[str, Any]] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = None
    category_id: int | None = None
    default_fields: dict[str, Any] | None = None
    default_styles: dict[str, Any] | None = None
    custom_field_schema: list[dict[str, Any]] | None = None
