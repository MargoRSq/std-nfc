import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import cards, categories, templates
from std_cards.models.card import CategoryDB, CategoryUpdate


class CategoryRepository(BaseRepository):
    async def list_all(self, conn: AsyncConnection | None = None) -> list[CategoryDB]:
        # Счётчики нужны фронту, чтобы прятать из фильтра категории, которыми
        # заказчик не пользуется (жалоба «что за шаблон бронзовые»).
        cards_count = (
            sa.select(sa.func.count())
            .select_from(cards)
            .where(cards.c.category_id == categories.c.id, cards.c.deleted_at.is_(None))
            .scalar_subquery()
            .label("cards_count")
        )
        templates_count = (
            sa.select(sa.func.count())
            .select_from(templates)
            .where(templates.c.category_id == categories.c.id)
            .scalar_subquery()
            .label("templates_count")
        )
        result = await self.ctx_wrap(
            sa.select(categories, cards_count, templates_count).order_by(categories.c.order_idx),
            conn,
        )
        return [CategoryDB.model_validate(row, from_attributes=True) for row in result.fetchall()]

    async def update(
        self,
        id: int,
        data: CategoryUpdate,
        conn: AsyncConnection | None = None,
    ) -> CategoryDB | None:
        values = data.model_dump(exclude_unset=True, exclude_none=True)
        if not values:
            return await self.get_by_id(id, conn=conn)
        if "name_ru" in values:
            values["name_ru"] = values["name_ru"].strip()
        values["updated_at"] = sa.func.now()
        result = await self.ctx_wrap(
            sa.update(categories)
            .where(categories.c.id == id)
            .values(**values)
            .returning(categories),
            conn,
        )
        row = result.fetchone()
        return CategoryDB.model_validate(row, from_attributes=True) if row else None

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
