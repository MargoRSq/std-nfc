import logging
from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from std_cards.infrastructure.repositories.base import BaseRepository
from std_cards.infrastructure.repositories.db_models import cards, categories, scan_events

logger = logging.getLogger(__name__)


def _apply_acl_join(q, acl_filter):
    """Join scan_events with cards and apply ACL filter on cards.

    When acl_filter is None — return q unchanged (super_admin / no-auth case).
    """
    if acl_filter is None:
        return q
    return q.join(cards, cards.c.id == scan_events.c.card_id).where(acl_filter)


class ScanEventRepository(BaseRepository):
    async def insert_batch(self, events: list[dict], conn=None) -> int:
        if not events:
            return 0
        await self.ctx_wrap_with_data(sa.insert(scan_events), events, conn)
        return len(events)

    async def total_scans(
        self,
        *,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        acl_filter=None,
        conn=None,
    ) -> int:
        q = (
            sa.select(sa.func.count())
            .select_from(scan_events)
            .where(scan_events.c.is_bot.is_(False))
        )
        if acl_filter is not None:
            q = q.select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id)).where(
                acl_filter
            )
        if from_dt is not None:
            q = q.where(scan_events.c.ts >= from_dt)
        if to_dt is not None:
            q = q.where(scan_events.c.ts < to_dt)
        result = await self.ctx_wrap(q, conn)
        return result.scalar() or 0

    async def by_day(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        card_id: UUID | None = None,
        acl_filter=None,
        conn=None,
    ) -> list[dict]:
        q = sa.select(
            sa.func.date_trunc("day", scan_events.c.ts).label("day"),
            sa.func.count().label("count"),
        ).where(
            scan_events.c.ts >= from_dt,
            scan_events.c.ts < to_dt,
            scan_events.c.is_bot.is_(False),
        )
        if acl_filter is not None:
            q = q.select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id)).where(
                acl_filter
            )
        if card_id is not None:
            q = q.where(scan_events.c.card_id == card_id)
        q = q.group_by(sa.text("1")).order_by(sa.text("1"))
        result = await self.ctx_wrap(q, conn)
        return [{"day": r.day.date(), "count": r.count} for r in result]

    async def top_regions(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 10,
        acl_filter=None,
        conn=None,
    ) -> list[dict]:
        region_expr = sa.func.coalesce(scan_events.c.city, scan_events.c.country_code)
        q = sa.select(
            region_expr.label("region"),
            sa.func.count().label("count"),
        ).where(
            scan_events.c.ts >= from_dt,
            scan_events.c.ts < to_dt,
            region_expr.is_not(None),
            scan_events.c.is_bot.is_(False),
        )
        if acl_filter is not None:
            q = q.select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id)).where(
                acl_filter
            )
        q = q.group_by(region_expr).order_by(sa.desc("count")).limit(limit)
        result = await self.ctx_wrap(q, conn)
        return [{"region": r.region, "count": r.count} for r in result]

    async def top_devices(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 10,
        acl_filter=None,
        conn=None,
    ) -> list[dict]:
        os_label = sa.case(
            (scan_events.c.os_family.in_(["iOS", "Android"]), scan_events.c.os_family),
            else_=sa.literal("Other"),
        ).label("os_label")
        q = sa.select(
            os_label,
            sa.func.count().label("count"),
        ).where(
            scan_events.c.ts >= from_dt,
            scan_events.c.ts < to_dt,
            scan_events.c.is_bot.is_(False),
        )
        if acl_filter is not None:
            q = q.select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id)).where(
                acl_filter
            )
        q = q.group_by(os_label).order_by(sa.desc("count")).limit(limit)
        result = await self.ctx_wrap(q, conn)
        return [{"device_type": r.os_label, "count": r.count} for r in result]

    async def top_cards(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 10,
        acl_filter=None,
        conn=None,
    ) -> list[dict]:
        q = (
            sa.select(
                scan_events.c.card_id,
                cards.c.last_name,
                cards.c.first_name,
                cards.c.membership_no,
                sa.func.count().label("count"),
            )
            .select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id))
            .where(
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
        )
        if acl_filter is not None:
            q = q.where(acl_filter)
        q = (
            q.group_by(
                scan_events.c.card_id,
                cards.c.last_name,
                cards.c.first_name,
                cards.c.membership_no,
            )
            .order_by(sa.desc("count"))
            .limit(limit)
        )
        result = await self.ctx_wrap(q, conn)
        return [
            {
                "card_id": r.card_id,
                "last_name": r.last_name,
                "first_name": r.first_name,
                "membership_no": r.membership_no,
                "scans": r.count,
            }
            for r in result
        ]

    async def top_active_users(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 10,
        offset: int = 0,
        acl_filter=None,
        conn=None,
    ) -> list[dict]:
        q = (
            sa.select(
                scan_events.c.card_id,
                cards.c.last_name,
                cards.c.first_name,
                cards.c.middle_name,
                cards.c.membership_no,
                categories.c.name_ru.label("category_name"),
                sa.func.count().label("count"),
            )
            .select_from(
                scan_events.join(cards, cards.c.id == scan_events.c.card_id).outerjoin(
                    categories, categories.c.id == cards.c.category_id
                )
            )
            .where(
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
        )
        if acl_filter is not None:
            q = q.where(acl_filter)
        q = (
            q.group_by(
                scan_events.c.card_id,
                cards.c.last_name,
                cards.c.first_name,
                cards.c.middle_name,
                cards.c.membership_no,
                categories.c.name_ru,
            )
            .order_by(sa.desc("count"))
            .limit(limit)
            .offset(offset)
        )
        result = await self.ctx_wrap(q, conn)
        return [
            {
                "card_id": r.card_id,
                "last_name": r.last_name,
                "first_name": r.first_name,
                "middle_name": r.middle_name,
                "membership_no": r.membership_no,
                "category_name": r.category_name,
                "scans": r.count,
            }
            for r in result
        ]

    async def top_region_per_card(
        self,
        *,
        card_ids: list[UUID],
        from_dt: datetime,
        to_dt: datetime,
        conn=None,
    ) -> dict[UUID, str]:
        if not card_ids:
            return {}
        region_expr = sa.func.coalesce(scan_events.c.city, scan_events.c.country_code)
        sub = (
            sa.select(
                scan_events.c.card_id.label("card_id"),
                region_expr.label("region"),
                sa.func.count().label("cnt"),
            )
            .where(
                scan_events.c.card_id.in_(card_ids),
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                region_expr.is_not(None),
                scan_events.c.is_bot.is_(False),
            )
            .group_by(scan_events.c.card_id, region_expr)
            .subquery()
        )
        windowed = sa.select(
            sub.c.card_id,
            sub.c.region,
            sa.func.row_number()
            .over(partition_by=sub.c.card_id, order_by=sa.desc(sub.c.cnt))
            .label("rn"),
        ).subquery()
        q = sa.select(windowed.c.card_id, windowed.c.region).where(windowed.c.rn == 1)
        result = await self.ctx_wrap(q, conn)
        return {r.card_id: r.region for r in result}

    async def top_device_per_card(
        self,
        *,
        card_ids: list[UUID],
        from_dt: datetime,
        to_dt: datetime,
        conn=None,
    ) -> dict[UUID, str]:
        if not card_ids:
            return {}
        os_label = sa.case(
            (scan_events.c.os_family.in_(["iOS", "Android"]), scan_events.c.os_family),
            else_=sa.literal("Other"),
        ).label("os_label")
        sub = (
            sa.select(
                scan_events.c.card_id.label("card_id"),
                os_label,
                sa.func.count().label("cnt"),
            )
            .where(
                scan_events.c.card_id.in_(card_ids),
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
            .group_by(scan_events.c.card_id, os_label)
            .subquery()
        )
        windowed = sa.select(
            sub.c.card_id,
            sub.c.os_label,
            sa.func.row_number()
            .over(partition_by=sub.c.card_id, order_by=sa.desc(sub.c.cnt))
            .label("rn"),
        ).subquery()
        q = sa.select(windowed.c.card_id, windowed.c.os_label).where(windowed.c.rn == 1)
        result = await self.ctx_wrap(q, conn)
        return {r.card_id: r.os_label for r in result}

    async def top_active_users_count(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        acl_filter=None,
        conn=None,
    ) -> int:
        q = (
            sa.select(sa.func.count(sa.distinct(scan_events.c.card_id)))
            .select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id))
            .where(
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
        )
        if acl_filter is not None:
            q = q.where(acl_filter)
        result = await self.ctx_wrap(q, conn)
        return result.scalar() or 0

    async def unique_cards(
        self,
        *,
        from_dt: datetime,
        to_dt: datetime,
        acl_filter=None,
        conn=None,
    ) -> int:
        q = sa.select(sa.func.count(sa.distinct(scan_events.c.card_id))).where(
            scan_events.c.ts >= from_dt,
            scan_events.c.ts < to_dt,
            scan_events.c.is_bot.is_(False),
        )
        if acl_filter is not None:
            q = q.select_from(scan_events.join(cards, cards.c.id == scan_events.c.card_id)).where(
                acl_filter
            )
        result = await self.ctx_wrap(q, conn)
        return result.scalar() or 0

    async def last_scan(self, card_id: UUID, conn=None) -> datetime | None:
        q = sa.select(sa.func.max(scan_events.c.ts)).where(scan_events.c.card_id == card_id)
        result = await self.ctx_wrap(q, conn)
        return result.scalar()

    async def card_total_scans(
        self,
        card_id: UUID,
        *,
        from_dt: datetime,
        to_dt: datetime,
        conn=None,
    ) -> int:
        q = (
            sa.select(sa.func.count())
            .select_from(scan_events)
            .where(
                scan_events.c.card_id == card_id,
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
        )
        result = await self.ctx_wrap(q, conn)
        return result.scalar() or 0

    async def by_region_for_card(
        self, card_id: UUID, *, from_dt: datetime, to_dt: datetime, limit: int = 10, conn=None
    ) -> list[dict]:
        region_expr = sa.func.coalesce(scan_events.c.city, scan_events.c.country_code)
        q = (
            sa.select(
                region_expr.label("region"),
                sa.func.count().label("count"),
            )
            .where(
                scan_events.c.card_id == card_id,
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                region_expr.is_not(None),
                scan_events.c.is_bot.is_(False),
            )
            .group_by(region_expr)
            .order_by(sa.desc("count"))
            .limit(limit)
        )
        result = await self.ctx_wrap(q, conn)
        return [{"region": r.region, "count": r.count} for r in result]

    async def by_device_for_card(
        self, card_id: UUID, *, from_dt: datetime, to_dt: datetime, limit: int = 10, conn=None
    ) -> list[dict]:
        os_label = sa.case(
            (scan_events.c.os_family.in_(["iOS", "Android"]), scan_events.c.os_family),
            else_=sa.literal("Other"),
        ).label("os_label")
        q = (
            sa.select(
                os_label,
                sa.func.count().label("count"),
            )
            .where(
                scan_events.c.card_id == card_id,
                scan_events.c.ts >= from_dt,
                scan_events.c.ts < to_dt,
                scan_events.c.is_bot.is_(False),
            )
            .group_by(os_label)
            .order_by(sa.desc("count"))
            .limit(limit)
        )
        result = await self.ctx_wrap(q, conn)
        return [{"device_type": r.os_label, "count": r.count} for r in result]
