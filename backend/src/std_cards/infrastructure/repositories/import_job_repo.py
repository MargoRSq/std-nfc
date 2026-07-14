from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import import_jobs
from std_cards.models.import_job import ImportJobDB, ImportStatus


class ImportJobRepository(BaseRepository):
    async def create(
        self,
        data: dict[str, Any],
        created_by: UUID,
        conn: AsyncConnection | None = None,
    ) -> ImportJobDB:
        values: dict[str, Any] = {
            "file_key": data["file_key"],
            "file_name": data["file_name"],
            "template_id": data.get("template_id"),
            "created_by": created_by,
            "status": ImportStatus.PENDING,
        }
        result = await self.ctx_wrap(
            sa.insert(import_jobs).values(**values).returning(import_jobs), conn
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create import_job")
        return ImportJobDB.model_validate(row, from_attributes=True)

    async def get_by_id(self, id: UUID, conn: AsyncConnection | None = None) -> ImportJobDB | None:
        result = await self.ctx_wrap(sa.select(import_jobs).where(import_jobs.c.id == id), conn)
        row = result.fetchone()
        return ImportJobDB.model_validate(row, from_attributes=True) if row else None

    async def list_for_user(
        self,
        user_id: UUID,
        conn: AsyncConnection | None = None,
        limit: int = 50,
    ) -> list[ImportJobDB]:
        result = await self.ctx_wrap(
            sa.select(import_jobs)
            .where(import_jobs.c.created_by == user_id)
            .order_by(import_jobs.c.created_at.desc())
            .limit(limit),
            conn,
        )
        return [ImportJobDB.model_validate(row, from_attributes=True) for row in result.fetchall()]

    async def update_progress(
        self,
        id: UUID,
        processed_rows: int,
        inserted_rows: int,
        error_count: int,
        errors_sample: list[dict[str, Any]],
        total_rows: int | None = None,
        conn: AsyncConnection | None = None,
    ) -> None:
        values: dict[str, Any] = {
            "processed_rows": processed_rows,
            "inserted_rows": inserted_rows,
            "error_count": error_count,
            "errors_sample": errors_sample,
            "updated_at": sa.func.now(),
        }
        if total_rows is not None:
            values["total_rows"] = total_rows
        await self.ctx_wrap(
            sa.update(import_jobs).where(import_jobs.c.id == id).values(**values),
            conn,
        )

    async def mark_started(self, id: UUID, conn: AsyncConnection | None = None) -> None:
        await self.ctx_wrap(
            sa.update(import_jobs)
            .where(import_jobs.c.id == id)
            .values(
                status=ImportStatus.RUNNING,
                started_at=sa.func.now(),
                updated_at=sa.func.now(),
            ),
            conn,
        )

    async def mark_finished(
        self,
        id: UUID,
        status: ImportStatus,
        errors_file_key: str | None,
        conn: AsyncConnection | None = None,
    ) -> None:
        await self.ctx_wrap(
            sa.update(import_jobs)
            .where(import_jobs.c.id == id)
            .values(
                status=status,
                errors_file_key=errors_file_key,
                finished_at=sa.func.now(),
                updated_at=sa.func.now(),
            ),
            conn,
        )

    async def cancel(self, id: UUID, conn: AsyncConnection | None = None) -> bool:
        result = await self.ctx_wrap(
            sa.update(import_jobs)
            .where(
                import_jobs.c.id == id,
                import_jobs.c.status.in_([ImportStatus.PENDING, ImportStatus.RUNNING]),
            )
            .values(status=ImportStatus.CANCELLED, updated_at=sa.func.now())
            .returning(import_jobs.c.id),
            conn,
        )
        return result.fetchone() is not None
