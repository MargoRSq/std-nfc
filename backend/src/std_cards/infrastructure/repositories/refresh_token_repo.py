from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import refresh_tokens
from std_cards.models.auth import RefreshTokenDB


class RefreshTokenRepository(BaseRepository):
    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        family_id: UUID | None = None,
        user_agent: str | None = None,
        ip: str | None = None,
        conn: AsyncConnection | None = None,
    ) -> RefreshTokenDB:
        if family_id is None:
            family_id = uuid4()
        result = await self.ctx_wrap(
            sa.insert(refresh_tokens)
            .values(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                family_id=family_id,
                user_agent=user_agent,
                ip=ip,
            )
            .returning(refresh_tokens),
            conn,
        )
        row = result.fetchone()
        return RefreshTokenDB.model_validate(row, from_attributes=True)

    async def get_by_hash(
        self, token_hash: str, conn: AsyncConnection | None = None
    ) -> RefreshTokenDB | None:
        result = await self.ctx_wrap(
            sa.select(refresh_tokens).where(refresh_tokens.c.token_hash == token_hash), conn
        )
        row = result.fetchone()
        return RefreshTokenDB.model_validate(row, from_attributes=True) if row else None

    async def revoke(
        self,
        token_id: UUID,
        replaced_by_id: UUID | None = None,
        conn: AsyncConnection | None = None,
    ) -> None:
        await self.ctx_wrap(
            sa.update(refresh_tokens)
            .where(refresh_tokens.c.id == token_id)
            .values(revoked_at=datetime.now(UTC), replaced_by_id=replaced_by_id),
            conn,
        )

    async def revoke_chain_from(self, token_id: UUID, conn: AsyncConnection | None = None) -> int:
        """OAuth reuse-detection: ревокирует ВСЮ family токена.

        При replay-атаке (попытка использовать revoked token) caller передаёт token_id
        подозрительного запроса; этот метод revoke'ит все токены той же family,
        выгоняя атакующего и легитимного пользователя одновременно.
        """
        family_subq = (
            sa.select(refresh_tokens.c.family_id)
            .where(refresh_tokens.c.id == token_id)
            .scalar_subquery()
        )
        result = await self.ctx_wrap(
            sa.update(refresh_tokens)
            .where(
                (refresh_tokens.c.family_id == family_subq)
                & (refresh_tokens.c.revoked_at.is_(None))
            )
            .values(revoked_at=datetime.now(UTC))
            .returning(refresh_tokens.c.id),
            conn,
        )
        return len(result.fetchall())

    async def revoke_all_for_user(self, user_id: UUID, conn: AsyncConnection | None = None) -> int:
        result = await self.ctx_wrap(
            sa.update(refresh_tokens)
            .where((refresh_tokens.c.user_id == user_id) & (refresh_tokens.c.revoked_at.is_(None)))
            .values(revoked_at=datetime.now(UTC))
            .returning(refresh_tokens.c.id),
            conn,
        )
        return len(result.fetchall())

    async def get_active_for_user(
        self, user_id: UUID, conn: AsyncConnection | None = None
    ) -> list[RefreshTokenDB]:
        result = await self.ctx_wrap(
            sa.select(refresh_tokens).where(
                (refresh_tokens.c.user_id == user_id)
                & (refresh_tokens.c.revoked_at.is_(None))
                & (refresh_tokens.c.expires_at > datetime.now(UTC))
            ),
            conn,
        )
        return [
            RefreshTokenDB.model_validate(row, from_attributes=True) for row in result.fetchall()
        ]

    async def cleanup_expired(self, conn: AsyncConnection | None = None) -> int:
        result = await self.ctx_wrap(
            sa.delete(refresh_tokens).where(refresh_tokens.c.expires_at < datetime.now(UTC)),
            conn,
        )
        return result.rowcount or 0
