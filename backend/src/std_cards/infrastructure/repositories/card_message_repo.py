from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import card_messages
from std_cards.models.card_message import CardMessageDB


class CardMessageRepository(BaseRepository):
    async def create(
        self,
        card_id: UUID,
        text: str,
        image_key: str | None,
        created_by: UUID | None,
        conn: AsyncConnection | None = None,
    ) -> CardMessageDB:
        result = await self.ctx_wrap(
            sa.insert(card_messages)
            .values(
                card_id=card_id,
                text=text,
                image_key=image_key,
                created_by=created_by,
            )
            .returning(card_messages),
            conn,
        )
        row = result.fetchone()
        if row is None:
            raise RuntimeError("Failed to create card message")
        return CardMessageDB.model_validate(row, from_attributes=True)

    async def list_active_for_card(
        self,
        card_id: UUID,
        conn: AsyncConnection | None = None,
    ) -> list[CardMessageDB]:
        result = await self.ctx_wrap(
            sa.select(card_messages)
            .where(card_messages.c.card_id == card_id)
            .where(card_messages.c.deleted_at.is_(None))
            .order_by(card_messages.c.created_at.desc()),
            conn,
        )
        return [
            CardMessageDB.model_validate(row, from_attributes=True) for row in result.fetchall()
        ]

    async def get_latest_active_for_card(
        self,
        card_id: UUID,
        conn: AsyncConnection | None = None,
    ) -> CardMessageDB | None:
        result = await self.ctx_wrap(
            sa.select(card_messages)
            .where(card_messages.c.card_id == card_id)
            .where(card_messages.c.deleted_at.is_(None))
            .order_by(card_messages.c.created_at.desc())
            .limit(1),
            conn,
        )
        row = result.fetchone()
        if row is None:
            return None
        return CardMessageDB.model_validate(row, from_attributes=True)

    async def soft_delete(
        self,
        message_id: UUID,
        card_id: UUID,
        conn: AsyncConnection | None = None,
    ) -> bool:
        result = await self.ctx_wrap(
            sa.update(card_messages)
            .where(card_messages.c.id == message_id)
            .where(card_messages.c.card_id == card_id)
            .where(card_messages.c.deleted_at.is_(None))
            .values(deleted_at=sa.func.now()),
            conn,
        )
        return (result.rowcount or 0) > 0
