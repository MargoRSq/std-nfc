from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import password_resets
from std_cards.models.auth import ConsumeResult, PasswordResetDB


class PasswordResetRepository(BaseRepository):
    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        conn: AsyncConnection | None = None,
    ) -> PasswordResetDB:
        result = await self.ctx_wrap(
            sa.insert(password_resets)
            .values(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
            .returning(password_resets),
            conn,
        )
        row = result.fetchone()
        return PasswordResetDB.model_validate(row, from_attributes=True)

    async def get_by_hash(
        self, token_hash: str, conn: AsyncConnection | None = None
    ) -> PasswordResetDB | None:
        result = await self.ctx_wrap(
            sa.select(password_resets).where(password_resets.c.token_hash == token_hash),
            conn,
        )
        row = result.fetchone()
        return PasswordResetDB.model_validate(row, from_attributes=True) if row else None

    async def consume(self, reset_id: UUID, conn: AsyncConnection | None = None) -> ConsumeResult:
        """Атомарно consume reset. Возвращает детальный статус."""
        select_result = await self.ctx_wrap(
            sa.select(
                password_resets.c.id,
                password_resets.c.consumed_at,
                password_resets.c.expires_at,
            ).where(password_resets.c.id == reset_id),
            conn,
        )
        row = select_result.fetchone()
        if row is None:
            return ConsumeResult.NOT_FOUND
        if row.consumed_at is not None:
            return ConsumeResult.ALREADY_CONSUMED
        if row.expires_at <= datetime.now(UTC):
            return ConsumeResult.EXPIRED
        update_result = await self.ctx_wrap(
            sa.update(password_resets)
            .where((password_resets.c.id == reset_id) & (password_resets.c.consumed_at.is_(None)))
            .values(consumed_at=datetime.now(UTC))
            .returning(password_resets.c.id),
            conn,
        )
        return (
            ConsumeResult.CONSUMED if update_result.fetchone() else ConsumeResult.ALREADY_CONSUMED
        )

    async def cleanup_expired(self, conn: AsyncConnection | None = None) -> int:
        result = await self.ctx_wrap(
            sa.delete(password_resets).where(password_resets.c.expires_at < datetime.now(UTC)),
            conn,
        )
        return result.rowcount or 0
