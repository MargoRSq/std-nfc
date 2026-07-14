from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportJobDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_by: UUID | None
    template_id: UUID | None
    file_key: str
    file_name: str
    status: ImportStatus
    total_rows: int
    processed_rows: int
    inserted_rows: int
    error_count: int
    errors_sample: list[dict[str, Any]]
    errors_file_key: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
