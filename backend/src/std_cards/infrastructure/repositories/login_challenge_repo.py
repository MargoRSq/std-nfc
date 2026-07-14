from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import login_challenges
from std_cards.models.auth import ConsumeResult, LoginChallengeDB


class LoginChallengeRepository(BaseRepository):
    async def create(
        self,
        user_id: UUID,
        challenge_hash: str,
        expires_at: datetime,
        ip: str | None = None,
        conn: AsyncConnection | None = None,
    ) -> LoginChallengeDB:
        result = await self.ctx_wrap(
            sa.insert(login_challenges)
            .values(
                user_id=user_id,
                challenge_hash=challenge_hash,
                expires_at=expires_at,
                ip=ip,
            )
            .returning(login_challenges),
            conn,
        )
        row = result.fetchone()
        return LoginChallengeDB.model_validate(row, from_attributes=True)

    async def get_by_hash(
        self, challenge_hash: str, conn: AsyncConnection | None = None
    ) -> LoginChallengeDB | None:
        result = await self.ctx_wrap(
            sa.select(login_challenges).where(login_challenges.c.challenge_hash == challenge_hash),
            conn,
        )
        row = result.fetchone()
        return LoginChallengeDB.model_validate(row, from_attributes=True) if row else None

    async def consume(
        self, challenge_id: UUID, conn: AsyncConnection | None = None
    ) -> ConsumeResult:
        """Атомарно consume challenge. Возвращает детальный статус."""
        select_result = await self.ctx_wrap(
            sa.select(
                login_challenges.c.id,
                login_challenges.c.consumed_at,
                login_challenges.c.expires_at,
            ).where(login_challenges.c.id == challenge_id),
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
            sa.update(login_challenges)
            .where(
                (login_challenges.c.id == challenge_id) & (login_challenges.c.consumed_at.is_(None))
            )
            .values(consumed_at=datetime.now(UTC))
            .returning(login_challenges.c.id),
            conn,
        )
        return (
            ConsumeResult.CONSUMED if update_result.fetchone() else ConsumeResult.ALREADY_CONSUMED
        )

    async def cleanup_expired(self, conn: AsyncConnection | None = None) -> int:
        result = await self.ctx_wrap(
            sa.delete(login_challenges).where(login_challenges.c.expires_at < datetime.now(UTC)),
            conn,
        )
        return result.rowcount or 0
