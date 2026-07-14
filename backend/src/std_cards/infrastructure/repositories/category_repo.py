import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import categories
from std_cards.models.card import CategoryDB


class CategoryRepository(BaseRepository):
    async def list_all(self, conn: AsyncConnection | None = None) -> list[CategoryDB]:
        result = await self.ctx_wrap(
            sa.select(categories).order_by(categories.c.order_idx),
            conn,
        )
        return [CategoryDB.model_validate(row, from_attributes=True) for row in result.fetchall()]

    async def get_by_id(self, id: int, conn: AsyncConnection | None = None) -> CategoryDB | None:
        result = await self.ctx_wrap(
            sa.select(categories).where(categories.c.id == id),
            conn,
        )
        row = result.fetchone()
        return CategoryDB.model_validate(row, from_attributes=True) if row else None

    async def get_by_code(
        self, code: str, conn: AsyncConnection | None = None
    ) -> CategoryDB | None:
        result = await self.ctx_wrap(
            sa.select(categories).where(categories.c.code == code),
            conn,
        )
        row = result.fetchone()
        return CategoryDB.model_validate(row, from_attributes=True) if row else None
