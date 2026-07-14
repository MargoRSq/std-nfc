from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import admin_card_groups
from std_cards.models.admin import AdminCardGroupDB


class AdminCardGroupRepository(BaseRepository):
    async def set_groups(
        self,
        user_id: UUID,
        category_ids: list[int],
        can_export: bool,
        conn: AsyncConnection | None = None,
    ) -> None:
        await self.ctx_wrap(
            sa.delete(admin_card_groups).where(admin_card_groups.c.user_id == user_id),
            conn,
        )
        if category_ids:
            rows = [
                {"user_id": user_id, "category_id": cid, "can_edit": True, "can_export": can_export}
                for cid in category_ids
            ]
            await self.ctx_wrap(sa.insert(admin_card_groups).values(rows), conn)

    async def list_for_user(
        self, user_id: UUID, conn: AsyncConnection | None = None
    ) -> list[AdminCardGroupDB]:
        result = await self.ctx_wrap(
            sa.select(admin_card_groups).where(admin_card_groups.c.user_id == user_id),
            conn,
        )
        return [
            AdminCardGroupDB.model_validate(row, from_attributes=True) for row in result.fetchall()
        ]

    async def categories_for_user(
        self, user_id: UUID, conn: AsyncConnection | None = None
    ) -> list[int]:
        result = await self.ctx_wrap(
            sa.select(admin_card_groups.c.category_id).where(
                admin_card_groups.c.user_id == user_id
            ),
            conn,
        )
        return [row.category_id for row in result.fetchall()]
