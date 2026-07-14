from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import templates
from std_cards.models.template import TemplateCreate, TemplateDB, TemplateUpdate


class TemplateRepository(BaseRepository):
    async def list_all(self, conn: AsyncConnection | None = None) -> list[TemplateDB]:
        result = await self.ctx_wrap(sa.select(templates).order_by(templates.c.name), conn)
        return [TemplateDB.model_validate(row, from_attributes=True) for row in result.fetchall()]

    async def get_by_id(self, id: UUID, conn: AsyncConnection | None = None) -> TemplateDB | None:
        result = await self.ctx_wrap(sa.select(templates).where(templates.c.id == id), conn)
        row = result.fetchone()
        return TemplateDB.model_validate(row, from_attributes=True) if row else None

    async def create(
        self,
        data: TemplateCreate,
        created_by: UUID,
        conn: AsyncConnection | None = None,
    ) -> TemplateDB:
        values = data.model_dump(mode="python")
        values["created_by"] = created_by
        result = await self.ctx_wrap(
            sa.insert(templates).values(**values).returning(templates), conn
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create template")
        return TemplateDB.model_validate(row, from_attributes=True)

    async def update(
        self,
        id: UUID,
        data: TemplateUpdate,
        conn: AsyncConnection | None = None,
    ) -> TemplateDB | None:
        values = data.model_dump(exclude_unset=True, mode="python")
        if not values:
            return await self.get_by_id(id, conn=conn)
        values["updated_at"] = sa.func.now()
        result = await self.ctx_wrap(
            sa.update(templates).where(templates.c.id == id).values(**values).returning(templates),
            conn,
        )
        row = result.fetchone()
        return TemplateDB.model_validate(row, from_attributes=True) if row else None

    async def delete(self, id: UUID, conn: AsyncConnection | None = None) -> bool:
        result = await self.ctx_wrap(
            sa.delete(templates).where(templates.c.id == id).returning(templates.c.id),
            conn,
        )
        return result.fetchone() is not None

    async def get_default(self, conn: AsyncConnection | None = None) -> TemplateDB | None:
        result = await self.ctx_wrap(
            sa.select(templates).where(templates.c.is_default.is_(True)).limit(1),
            conn,
        )
        row = result.fetchone()
        return TemplateDB.model_validate(row, from_attributes=True) if row else None

    async def duplicate(
        self, id: UUID, new_name: str, conn: AsyncConnection | None = None
    ) -> TemplateDB | None:
        original = await self.get_by_id(id, conn=conn)
        if original is None:
            return None
        result = await self.ctx_wrap(
            sa.insert(templates)
            .values(
                name=new_name,
                category_id=original.category_id,
                default_fields=original.default_fields,
                default_styles=original.default_styles,
                custom_field_schema=original.custom_field_schema,
                created_by=original.created_by,
            )
            .returning(templates),
            conn,
        )
        row = result.fetchone()
        return TemplateDB.model_validate(row, from_attributes=True) if row else None
