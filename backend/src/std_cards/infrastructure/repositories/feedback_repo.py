from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import feedback_messages
from std_cards.models.feedback import FeedbackDB


class FeedbackRepository(BaseRepository):
    async def create(
        self,
        card_id: UUID,
        name: str,
        contact: str,
        message: str,
        ip: str | None = None,
        user_agent: str | None = None,
        conn: AsyncConnection | None = None,
    ) -> FeedbackDB:
        result = await self.ctx_wrap(
            sa.insert(feedback_messages)
            .values(
                card_id=card_id,
                name=name,
                contact=contact,
                message=message,
                ip=ip,
                user_agent=user_agent,
            )
            .returning(feedback_messages),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create feedback message")
        return FeedbackDB.model_validate(row, from_attributes=True)

    async def list_for_card(
        self,
        card_id: UUID,
        page: int = 1,
        page_size: int = 50,
        conn: AsyncConnection | None = None,
    ) -> tuple[list[FeedbackDB], int]:
        where = feedback_messages.c.card_id == card_id

        count_result = await self.ctx_wrap(
            sa.select(sa.func.count()).select_from(feedback_messages).where(where),
            conn,
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        rows_result = await self.ctx_wrap(
            sa.select(feedback_messages)
            .where(where)
            .order_by(feedback_messages.c.created_at.desc())
            .limit(page_size)
            .offset(offset),
            conn,
        )
        items = [
            FeedbackDB.model_validate(row, from_attributes=True) for row in rows_result.fetchall()
        ]
        return items, total

    async def mark_read(self, id: UUID, conn: AsyncConnection | None = None) -> None:
        await self.ctx_wrap(
            sa.update(feedback_messages)
            .where(feedback_messages.c.id == id)
            .values(read_at=sa.func.now()),
            conn,
        )
