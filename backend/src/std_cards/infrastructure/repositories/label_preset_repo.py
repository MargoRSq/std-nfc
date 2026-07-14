from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import label_presets
from std_cards.models.label_preset import LabelPresetCreate, LabelPresetDB, LabelPresetUpdate


class LabelPresetRepository(BaseRepository):
    async def list_by_admin(
        self,
        admin_id: UUID,
        conn: AsyncConnection | None = None,
    ) -> list[LabelPresetDB]:
        q = (
            sa.select(label_presets)
            .where(label_presets.c.admin_id == admin_id)
            .order_by(label_presets.c.order_idx.asc(), label_presets.c.created_at.asc())
        )
        result = await self.ctx_wrap(q, conn)
        return [
            LabelPresetDB.model_validate(row, from_attributes=True) for row in result.fetchall()
        ]

    async def create(
        self,
        admin_id: UUID,
        data: LabelPresetCreate,
        conn: AsyncConnection | None = None,
    ) -> LabelPresetDB:
        max_order_q = sa.select(sa.func.coalesce(sa.func.max(label_presets.c.order_idx), -1)).where(
            label_presets.c.admin_id == admin_id
        )
        max_result = await self.ctx_wrap(max_order_q, conn)
        next_order = (max_result.scalar() or -1) + 1

        result = await self.ctx_wrap(
            sa.insert(label_presets)
            .values(
                admin_id=admin_id,
                name=data.name.strip(),
                type=data.type,
                order_idx=next_order,
            )
            .returning(label_presets),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create label preset")
        return LabelPresetDB.model_validate(row, from_attributes=True)

    async def update(
        self,
        preset_id: UUID,
        admin_id: UUID,
        data: LabelPresetUpdate,
        conn: AsyncConnection | None = None,
    ) -> LabelPresetDB | None:
        result = await self.ctx_wrap(
            sa.update(label_presets)
            .where(label_presets.c.id == preset_id, label_presets.c.admin_id == admin_id)
            .values(name=data.name.strip(), type=data.type, updated_at=sa.func.now())
            .returning(label_presets),
            conn,
        )
        row = result.fetchone()
        return LabelPresetDB.model_validate(row, from_attributes=True) if row else None

    async def delete(
        self,
        preset_id: UUID,
        admin_id: UUID,
        conn: AsyncConnection | None = None,
    ) -> bool:
        result = await self.ctx_wrap(
            sa.delete(label_presets)
            .where(label_presets.c.id == preset_id, label_presets.c.admin_id == admin_id)
            .returning(label_presets.c.id),
            conn,
        )
        return result.fetchone() is not None

    async def reorder(
        self,
        admin_id: UUID,
        ids: list[UUID],
        conn: AsyncConnection | None = None,
    ) -> None:
        if conn is not None:
            for idx, preset_id in enumerate(ids):
                await self.ctx_wrap(
                    sa.update(label_presets)
                    .where(label_presets.c.id == preset_id, label_presets.c.admin_id == admin_id)
                    .values(order_idx=idx, updated_at=sa.func.now()),
                    conn,
                )
        else:
            async with self.session_maker.session(query_type="write") as tx_conn:
                for idx, preset_id in enumerate(ids):
                    await self.ctx_wrap(
                        sa.update(label_presets)
                        .where(
                            label_presets.c.id == preset_id,
                            label_presets.c.admin_id == admin_id,
                        )
                        .values(order_idx=idx, updated_at=sa.func.now()),
                        tx_conn,
                    )
