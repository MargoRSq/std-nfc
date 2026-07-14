from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import audit_log
from std_cards.models.audit import AuditLogEntry


class AuditRepository(BaseRepository):
    async def write(
        self,
        actor_id: UUID | None,
        actor_email: str | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        diff: dict[str, Any] | None = None,
        conn: AsyncConnection | None = None,
    ) -> None:
        await self.ctx_wrap(
            sa.insert(audit_log).values(
                actor_id=actor_id,
                actor_email=actor_email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                ip=ip,
                user_agent=user_agent,
                diff=diff,
            ),
            conn,
        )

    async def list_with_filters(
        self,
        actor_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        ts_from: datetime | None = None,
        ts_to: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
        conn: AsyncConnection | None = None,
    ) -> tuple[list[AuditLogEntry], int]:
        conditions = []
        if actor_id is not None:
            conditions.append(audit_log.c.actor_id == actor_id)
        if action is not None:
            conditions.append(audit_log.c.action == action)
        if entity_type is not None:
            conditions.append(audit_log.c.entity_type == entity_type)
        if entity_id is not None:
            conditions.append(audit_log.c.entity_id == entity_id)
        if ts_from is not None:
            conditions.append(audit_log.c.ts >= ts_from)
        if ts_to is not None:
            conditions.append(audit_log.c.ts <= ts_to)

        where_clause = sa.and_(*conditions) if conditions else sa.true()

        count_result = await self.ctx_wrap(
            sa.select(sa.func.count()).select_from(audit_log).where(where_clause),
            conn,
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        items_result = await self.ctx_wrap(
            sa.select(audit_log)
            .where(where_clause)
            .order_by(audit_log.c.ts.desc())
            .limit(page_size)
            .offset(offset),
            conn,
        )
        entries = [
            AuditLogEntry.model_validate(row, from_attributes=True)
            for row in items_result.fetchall()
        ]
        return entries, total
